"""daleel: Qamar Telecom's analytics assistant (دليل), as far as the labs need it.

Daleel does not write SQL. It reads the metric catalogue (names, descriptions, synonyms, examples)
and answers a question with a semantic query, a JSON object the layer executes:

    {"metrics": ["collection_rate"], "by": [], "where": ["time.month = DATE '2026-03-01'"]}
    {"refuse": "uncertified"}

Two modes:
  stand-in (default)  recorded replies in data/assistant/replies.jsonl, one per question, context
                      variant and run (1 to 3). Synthetic: written by _tools/make_case_files.py with a
                      stated error model, so every number in the labs is reproducible offline.
  live                QAMAR_MODEL_MODE=live and OPENROUTER_API_KEY set: the same prompt goes to a free
                      hosted model on OpenRouter (QAMAR_MODEL, default google/gemma-4-31b-it:free).

    import daleel as D
    qs = D.load_set("data/assistant/certified_60.yaml")
    reply = D.ask(qs[0], variant="full", run=1)        # the reply text
    out = D.execute(model, D.parse(reply), qs[0])      # what the layer returns for it
    table = D.score(model, qs, variant="full")         # one row per question and run, with an outcome
"""
from __future__ import annotations

import json
import os
import re
import time
import urllib.error
import urllib.request
from pathlib import Path

import pandas as pd
import yaml

LABS = Path(__file__).resolve().parent
ASSISTANT = LABS / "data" / "assistant"
VARIANTS = ["full", "no_synonyms", "no_descriptions", "no_examples"]
MODE = os.environ.get("QAMAR_MODEL_MODE", "standin")
LIVE_MODEL = os.environ.get("QAMAR_MODEL", "google/gemma-4-31b-it:free")
TOLERANCE = 0.005  # relative: a figure within 0.5% of the certified value counts as right
PLAUSIBLE = (0.5, 2.0)  # a wrong figure within half to twice the certified value looks right on a slide
REFUSE_REASONS = ["restricted", "forecast", "not_matured", "uncertified", "causal", "no_period", "no_metric"]

SYSTEM = """You are Daleel, the analytics assistant of Qamar Telecom. Answer a manager's question with ONE
JSON object and nothing else.
To answer: {"metrics": [metric names], "by": [fields to group by], "where": [SQL conditions on fields],
"order": "desc" or "asc" (only to find the top or bottom group), "limit": 1 (with order)}.
To refuse: {"refuse": reason}, where reason is one of: restricted (asks for a person's details),
forecast (asks about the future), not_matured (a collection rate whose 30-day window has not closed by
2026-06-30), uncertified (only a draft metric fits), causal (asks why), no_period (no time period given),
no_metric (no metric fits).
Use only certified metrics and only the fields listed. Fields are written dataset.field.
Months are written time.month = DATE 'YYYY-MM-01'. The fiscal year runs April to March, written
time.fiscal_year = 'FY2025-26'; quarters time.fiscal_quarter = 'FY2025-26-Q1'. Hijri months are
time.hijri_month = '1447-09'. Regions: CEN Central, EAS Eastern, WES Western, NOR Northern, SOU Southern."""


# ------------------------------------------------------------------------------------ the question set
def load_set(path) -> list[dict]:
    doc = yaml.safe_load((LABS / path).read_text(encoding="utf-8"))
    return doc["questions"] if isinstance(doc, dict) else doc


def save_set(questions: list[dict], path, title: str = "") -> Path:
    path = Path(path)
    path.parent.mkdir(parents=True, exist_ok=True)
    doc = {"title": title, "questions": questions}
    path.write_text(yaml.safe_dump(doc, allow_unicode=True, sort_keys=False, width=200), encoding="utf-8", newline="\n")
    return path


# ------------------------------------------------------------------------------------ context and prompt
def context(metrics: list[dict], variant: str = "full", certified_only: bool = True) -> list[dict]:
    """The metric context Daleel sees. Each variant removes one kind of context and keeps the rest."""
    if variant not in VARIANTS:
        raise ValueError(f"variant must be one of {VARIANTS}")
    out = []
    for m in metrics:
        if m.get("dataset") == "usage_event" or (certified_only and m.get("status") != "certified"):
            continue
        ai = m.get("ai", {}) or {}
        item = {"name": m["name"], "label": m.get("label", m["name"]), "unit": m.get("unit", "")}
        if variant != "no_descriptions":
            item["description"] = " ".join(str(m.get("description", "")).split())
        if variant != "no_synonyms" and ai.get("synonyms"):
            item["synonyms"] = ai["synonyms"]
        if variant != "no_examples" and ai.get("examples"):
            item["examples"] = ai["examples"]
        out.append(item)
    return out


FIELDS = ["time.month", "time.fiscal_year", "time.fiscal_quarter", "time.hijri_month", "customer.segment",
          "customer.region", "customer.city", "tariff.plan_name", "line.product", "complaint.region",
          "complaint.category"]


def prompt(question: str, metrics: list[dict], variant: str = "full") -> list[dict]:
    ctx = {"metrics": context(metrics, variant), "fields": FIELDS}
    return [{"role": "system", "content": SYSTEM},
            {"role": "user", "content": "Catalogue:\n" + json.dumps(ctx, ensure_ascii=False) + "\n\nQuestion: " + question}]


# ------------------------------------------------------------------------------------ asking
_RECORDED: dict | None = None


def _recorded() -> dict:
    global _RECORDED
    if _RECORDED is None:
        _RECORDED = {}
        with (ASSISTANT / "replies.jsonl").open(encoding="utf-8") as f:
            for line in f:
                r = json.loads(line)
                _RECORDED[(r["id"], r["variant"], r["run"])] = r["reply"]
    return _RECORDED


def ask(q: dict, variant: str = "full", run: int = 1, metrics: list[dict] | None = None) -> str:
    """Daleel's reply text to one question of the set."""
    if MODE == "live":
        if metrics is None:
            raise ValueError("live mode needs the metric list")
        return ask_live(prompt(q["question"], metrics, variant))
    try:
        return _recorded()[(q["id"], variant, run)]
    except KeyError:
        raise KeyError(f"no recorded reply for {q['id']} ({variant}, run {run}): the stand-in only knows the "
                       "60 certified questions; set QAMAR_MODEL_MODE=live for others") from None


def ask_live(messages: list[dict], retries: int = 4) -> str:
    """One chat completion on OpenRouter, waiting and retrying on rate limits and network errors."""
    key = os.environ.get("OPENROUTER_API_KEY", "")
    if not key:
        raise RuntimeError("live mode needs OPENROUTER_API_KEY (a free key from openrouter.ai)")
    body = json.dumps({"model": LIVE_MODEL, "messages": messages, "temperature": 0}).encode()
    req = urllib.request.Request("https://openrouter.ai/api/v1/chat/completions", data=body, method="POST",
                                 headers={"Authorization": f"Bearer {key}", "Content-Type": "application/json"})
    for attempt in range(retries):
        try:
            with urllib.request.urlopen(req, timeout=90) as r:
                return json.loads(r.read())["choices"][0]["message"]["content"]
        except (urllib.error.URLError, TimeoutError, KeyError) as e:
            if attempt == retries - 1:
                raise RuntimeError(f"OpenRouter did not answer after {retries} tries: {e}") from e
            time.sleep(5 * (attempt + 1))
    return ""


def parse(reply: str) -> dict:
    """The JSON object in a reply (code fences and text around it are ignored)."""
    m = re.search(r"\{.*\}", reply or "", re.S)
    if not m:
        return {"error": "no JSON in the reply"}
    try:
        obj = json.loads(m.group(0))
    except json.JSONDecodeError as e:
        return {"error": f"bad JSON: {e.msg}"}
    return obj if isinstance(obj, dict) else {"error": "not an object"}


# ------------------------------------------------------------------------------------ executing
def norm_label(v) -> str:
    if isinstance(v, pd.Timestamp) or hasattr(v, "strftime"):
        return v.strftime("%Y-%m")
    return str(v)


def answer(model, query: dict, kind: str = "value"):
    """Run a semantic query and return the one figure (kind value) or group label (kind label) it answers."""
    metrics, by = query["metrics"], query.get("by", []) or []
    df = model.query(metrics, by=by, where=query.get("where", []) or [])
    if df.empty:
        return None
    if query.get("order"):
        df = df.sort_values(metrics[0], ascending=query["order"] == "asc", kind="stable")
    row = df.iloc[0]
    if kind == "label":
        return norm_label(row[by[0]]) if by else None
    v = row[metrics[0]]
    return None if pd.isna(v) else round(float(v), 6)


def execute(model, reply: dict, q: dict) -> dict:
    """What the layer returns for a parsed reply: {'refused': reason} or {'value': ...} or {'error': ...}."""
    if "error" in reply:
        return {"error": reply["error"]}
    if "refuse" in reply:
        return {"refused": reply["refuse"]}
    try:
        kind = q.get("expect", {}).get("kind", "value")
        return {"value": answer(model, reply, kind)}
    except Exception as e:  # noqa: BLE001 - every failure of the layer is an outcome, not a crash
        return {"error": f"{type(e).__name__}: {str(e).splitlines()[0][:120]}"}


def same(got, want, tolerance: float = TOLERANCE) -> bool:
    if got is None or want is None:
        return False
    if isinstance(want, str) or isinstance(got, str):
        return str(got) == str(want)
    return abs(got - want) <= tolerance * max(abs(want), 1e-9)


def outcome(q: dict, out: dict, tolerance: float = TOLERANCE) -> str:
    """One of: right, wrong_plausible, wrong_visible, error, refused_wrongly, refused_right, missed_refusal."""
    exp = q["expect"]
    if "refuse" in exp:
        return "refused_right" if "refused" in out else "missed_refusal"
    if "refused" in out:
        return "refused_wrongly"
    if "error" in out or out.get("value") is None:
        return "error"
    got, want = out["value"], exp["value"]
    if same(got, want, tolerance):
        return "right"
    if isinstance(want, str):
        return "wrong_plausible"  # a valid group name, just the wrong one
    lo, hi = PLAUSIBLE
    return "wrong_plausible" if want and lo <= got / want <= hi else "wrong_visible"


def score(model, questions: list[dict], variant: str = "full", runs=(1,), metrics=None) -> pd.DataFrame:
    """One row per question and run: the reply, what the layer returned and the outcome."""
    rows = []
    for q in questions:
        for run in runs:
            text = ask(q, variant, run, metrics)
            out = execute(model, parse(text), q)
            rows.append({"id": q["id"], "lang": q["lang"], "area": q["area"], "difficulty": q.get("difficulty"),
                         "variant": variant, "run": run, "got": out.get("value", out.get("refused", out.get("error"))),
                         "want": q["expect"].get("value", q["expect"].get("refuse")), "outcome": outcome(q, out)})
    return pd.DataFrame(rows)


def summary(table: pd.DataFrame, by: list[str] | None = None) -> pd.DataFrame:
    """Accuracy (right or refused_right) and the wrong-but-plausible rate, overall or by groups."""
    t = table.assign(correct=table.outcome.isin(["right", "refused_right"]),
                     plausible=table.outcome.isin(["wrong_plausible", "missed_refusal"]))
    g = t.groupby(by) if by else t.groupby(lambda _: "all")
    return g.agg(n=("id", "size"), accuracy=("correct", "mean"), wrong_plausible=("plausible", "mean")).round(3)
