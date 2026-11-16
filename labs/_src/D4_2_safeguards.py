# /// script
# requires-python = ">=3.11"
# dependencies = ["duckdb>=1.4", "pandas>=2.2", "pyyaml>=6.0"]
# ///
# %% [markdown]
# # Lab 4.2 · Cite the metric, refuse the uncertified
#
# Day 4 · Session 2 (Safeguards that show their work) · 25 min. Lab 3.3 found three answers nobody would notice.
# One was a draft metric answered as if certified. You give every figure an answer card that names its metric,
# version, filters and grain, put a guard between Daleel's reply and the layer, re-score the certified set with
# the guard on, and write the refusals a manager actually reads.
#
# **AI-tutor.** An assistant may help word the refusals; the guard's rules are tested code, not a prompt.
#
# **Reference state.** The certified set and recorded replies of Day 3, the governed policy
# `data/access/policy_governed.yaml`, and the candidate drafts of Lab 3.1 (`data/assistant/candidates.yaml`).
#
# **Tasks**
# - [ ] 1 · The answer card (7')
# - [ ] 2 · The guard (8')
# - [ ] 3 · Re-score with the guard on (6')
# - [ ] 4 · Read three refusals (4')
# - [ ] ✱ Stretch · The answer card in Arabic

# %%
import os, sys, subprocess
from pathlib import Path

IN_COLAB = "google.colab" in sys.modules
if IN_COLAB:
    REPO_URL = "https://github.com/SDAIAAcademy/ds-408.git"
    if not Path("/content/ds-408").exists():
        subprocess.run(["git", "clone", "-q", REPO_URL, "/content/ds-408"], check=True)
    os.chdir("/content/ds-408/labs")
    subprocess.run([sys.executable, "-m", "pip", "install", "-q", "-r", "requirements-colab.txt"], check=True)
else:
    while not Path("qamar.py").exists() and Path.cwd() != Path.cwd().parent:
        os.chdir("..")  # solutions/ notebooks run from labs/
sys.path.insert(0, os.getcwd())

import pandas as pd
import qamar as Q
import qsem as S
import daleel as D

POLICY = Q.yaml_load("data/access/policy_governed.yaml")
model = S.Model.load("data/semantic/qamar_model.yaml", Q.db(), metrics_dir="data/metrics", policy=POLICY, lineage=True)
QS = D.load_set("data/assistant/certified_60.yaml")
BYID = {q["id"]: q for q in QS}
CANDS = {c["id"]: c for c in D.load_set("data/assistant/candidates.yaml")}
TIME_FIELDS = ("time.month", "time.fiscal_year", "time.fiscal_quarter", "time.hijri_month", "time.year", "time.day")

# %% [markdown]
# ## 1 · The answer card (7')
#
# A figure without its definition invites the Day 1 argument again. The card travels with the figure.
#
# ✏️ **Exercise** · Write `card(query, value)` returning a dict with `figure` (a ratio as a percentage with one
# decimal, an amount as `SAR 1,234,567`, other numbers with thousands separators), `metric` (label and version),
# `status`, `owner`, `filters`, `grain` (the group-by fields, or `total`) and `text`, one line joining them.

# %%
def fmt(value, unit: str) -> str:
    if isinstance(value, str):
        return value
    if unit == "ratio":
        return f"{value:.1%}"
    if unit == "SAR":
        return f"SAR {value:,.0f}"
    return f"{value:,.1f}" if abs(value) < 1000 and value != int(value) else f"{value:,.0f}"


def card(query: dict, value) -> dict:
    # BEGIN SOLUTION
    m = model.describe(query["metrics"][0])
    c = {"figure": fmt(value, m["unit"]), "metric": f"{m['label']} v{m['version']}", "status": m["status"], "owner": m["owner"],
         "filters": "; ".join(query.get("where", []) or []) or "none", "grain": ", ".join(query.get("by", []) or []) or "total"}
    c["text"] = f"{c['figure']} · {c['metric']} ({c['status']}, {c['owner']}) · filters: {c['filters']} · grain: {c['grain']}"
    return c
    # END SOLUTION


# %%
cards = []
for qid in ["C01", "B07", "U10"]:
    q = BYID[qid]
    try:
        cards.append(card(q["query"], q["expect"]["value"]))
    except NotImplementedError:
        cards.append(Q.reference("d4_2_cards")[len(cards)])
for qid, c in zip(["C01", "B07", "U10"], cards):
    print(qid, BYID[qid]["question"], "\n   ", c["text"])
Q.check(cards[0]["figure"] == "86.5%" and "v1.0.0" in cards[0]["metric"] and cards[1]["figure"].startswith("SAR ") and cards[2]["grain"] == "tariff.plan_name",
        "cards show the figure, the metric and version, and the grain")

# %% [markdown]
# 🔍 The card for B07 says `time.fiscal_year = 'FY2025-26'`. Would a manager read that? Write the same filter in
# words a manager would read, and say where that wording should live (the card code, or the metric files?).
#
# ## 2 · The guard (8')
#
# The guard runs on Daleel's parsed reply, before the layer. It returns a refusal reason, or None to let the
# query run. Its rules, in order:
#
# | Reason | When |
# |---|---|
# | `no_metric` | a metric is not in the layer |
# | `uncertified` | a metric is not `certified` |
# | `restricted` | a group-by or filter field is Restricted, by tag or by lineage (`model.is_restricted`) |
# | `no_period` | no filter on a `time.` field |
# | `not_matured` | a `collection_rate` whose cohort has no closed 30-day window (`net_due_30` is empty or zero) |
#
# ✏️ **Exercise** · Write `guard(query)`.

# %%
def guard(query: dict):
    # BEGIN SOLUTION
    mets = query.get("metrics", [])
    if not mets or any(m not in model.metrics for m in mets):
        return "no_metric"
    if any(model.metrics[m].get("status") != "certified" for m in mets):
        return "uncertified"
    fields = (query.get("by", []) or []) + (query.get("where", []) or [])
    for text in fields:
        for ds, f in S.REF.findall(text):
            if ds in model.datasets and model.is_restricted(ds, model.field(ds, f)):
                return "restricted"
    if not any(w.strip().startswith(TIME_FIELDS) for w in query.get("where", []) or []):
        return "no_period"
    if "collection_rate" in mets:
        due = model.query(["net_due_30"], where=query.get("where", []))
        if due.empty or pd.isna(due.net_due_30.iloc[0]) or due.net_due_30.iloc[0] == 0:
            return "not_matured"
    return None
    # END SOLUTION


# %%
PROBES = {"X01": CANDS["X01"]["draft"], "X06": CANDS["X06"]["draft"], "X07": CANDS["X07"]["draft"],
          "contact": {"metrics": ["billed_amount"], "by": ["customer.contact_name"], "where": ["time.month = DATE '2026-03-01'"]},
          "C14 answered": {"metrics": ["collection_rate"], "where": ["time.month = DATE '2026-05-01'"]},
          "C01": BYID["C01"]["query"]}
try:
    verdicts = {k: guard(v) for k, v in PROBES.items()}
except NotImplementedError:
    verdicts = Q.reference("d4_2_verdicts")
print(verdicts)
Q.check(verdicts == {"X01": "no_period", "X06": "uncertified", "X07": "restricted", "contact": "restricted",
                     "C14 answered": "not_matured", "C01": None}, "the guard refuses each kind and lets a certified query through")
try:
    false_refusals = [q["id"] for q in QS if "query" in q and guard(q["query"]) is not None]
except NotImplementedError:
    false_refusals = []
Q.check(false_refusals == [], "the guard never refuses a certified question's own query")

# %% [markdown]
# ## 3 · Re-score with the guard on (6')
#
# ✏️ **Exercise** · Score the recorded replies with the guard between parse and execute (a reply the guard refuses
# counts as a refusal with the guard's reason). Return accuracy and the wrong-but-plausible rate with and without
# the guard, for the full context over three runs and for the context without descriptions (run 1).

# %%
def guarded_score(variant: str, runs=(1,)) -> pd.DataFrame:
    # BEGIN SOLUTION
    rows = []
    for q in QS:
        for run in runs:
            reply = D.parse(D.ask(q, variant, run))
            reason = guard(reply) if "metrics" in reply else None
            out = {"refused": reason} if reason else D.execute(model, reply, q)
            rows.append({"id": q["id"], "lang": q["lang"], "area": q["area"], "difficulty": q["difficulty"], "variant": variant,
                         "run": run, "got": out.get("value", out.get("refused", out.get("error"))),
                         "want": q["expect"].get("value", q["expect"].get("refuse")), "outcome": D.outcome(q, out)})
    return pd.DataFrame(rows)
    # END SOLUTION


# %%
rows = []
for variant, runs in [("full", (1, 2, 3)), ("no_descriptions", (1,))]:
    before = D.summary(D.score(model, QS, variant, runs=runs))
    try:
        after = D.summary(guarded_score(variant, runs))
    except NotImplementedError:
        after = pd.DataFrame([Q.reference("d4_2_after")[variant]], index=["all"])
    rows.append({"variant": variant, "accuracy": before.accuracy.iloc[0], "accuracy_guarded": after.accuracy.iloc[0],
                 "plausible": before.wrong_plausible.iloc[0], "plausible_guarded": after.wrong_plausible.iloc[0]})
effect = pd.DataFrame(rows)
print(effect.to_string(index=False))
full = effect.iloc[0]
Q.check(full.accuracy_guarded > full.accuracy and full.plausible_guarded < full.plausible, "the guard raises accuracy and cuts plausible errors")
effect.to_csv(Q.lab_dir("D4_2") / "guard_effect.csv", index=False, lineterminator="\n")

# %% [markdown]
# 🔍 Without descriptions, the finance ratio (`cash_collection_ratio`) is a draft, so the guard refuses it instead of
# answering. Accuracy barely moves, but what happens to the wrong-but-plausible rate? Which is better for a manager?
#
# ## 4 · Read three refusals (4')
#
# "I cannot answer that" teaches nothing. A refusal should say why, in the manager's terms, and offer the nearest
# certified alternative when there is one.
#
# ✏️ **Exercise** · Write `refusal(reason, query)` returning one or two sentences for `uncertified`, `restricted`,
# `no_period` and `not_matured`; name the draft metric's owner for `uncertified`, and the nearest certified metric
# with the same unit when one exists.

# %%
def refusal(reason: str, query: dict) -> str:
    # BEGIN SOLUTION
    m = model.metrics.get(query["metrics"][0], {}) if query.get("metrics") else {}
    area = {"collection": "collections", "payment": "collections", "bill": "billing", "usage": "usage", "complaint": "complaints"}
    near = [n for n, x in model.metrics.items() if x.get("status") == "certified" and x.get("unit") == m.get("unit")]
    if reason == "uncertified":
        alt = f" The nearest certified metric is {near[0]}." if near else ""
        return f"{m.get('label', m.get('name'))} is a draft owned by {m.get('owner')} and has no certified definition yet.{alt}"
    if reason == "restricted":
        return "That needs customers' personal data, which this assistant does not show. The collections team can contact customers through their own tools."
    if reason == "no_period":
        return f"Which period? For example: '{m.get('label', 'this figure')} for March 2026' or 'for the fiscal year 2025-26'."
    if reason == "not_matured":
        due = model.query(["net_due_30"], by=["time.month"]).dropna()
        last = due[due.net_due_30 > 0]["time.month"].max()
        return (f"Bills of that month have not reached 30 days past their due date by {Q.DATA_END}, so their collection rate "
                f"is not final yet. The latest final month is {last:%B %Y}.")
    return f"I cannot answer that ({reason}); area: {area.get(m.get('dataset'), 'unknown')}."
    # END SOLUTION


# %%
texts = {}
for key in ["X06", "X07", "X01", "C14 answered"]:
    try:
        texts[key] = refusal(verdicts[key], PROBES[key])
    except NotImplementedError:
        texts[key] = Q.reference("d4_2_refusals")[key]
    print(f"{key:13s} [{verdicts[key]}] {texts[key]}")
Q.check("Ebtihal" in texts["X06"] and "collection_rate" in texts["X06"], "the uncertified refusal names the draft's owner and the certified alternative")

# %% [markdown]
# 🔍 Read the not-matured refusal. A manager asks on 1 July and again on 1 August: should the latest final month in
# the sentence change? Where does that date come from, and who must keep it right?
#
# ## ✱ Stretch · The answer card in Arabic
#
# Write the card of C02 in Arabic: the figure, the metric's Arabic synonym as its name, the version and the
# period in words ("فواتير يناير 2026"). Which parts should come from the metric files rather than from code?

# %%
def stretch():
    # BEGIN SOLUTION
    q = BYID["C02"]
    m = model.metrics["collection_rate"]
    name = m["ai"]["synonyms"]["ar"][0]
    print(f"{name}: {q['expect']['value']:.1%} · الإصدار {m['version']} · معتمد · المالك: {m['owner']} · فواتير يناير 2026 · الإجمالي")
    # END SOLUTION


try:
    stretch()
except NotImplementedError:
    print("✱ Stretch not attempted")

# %% [markdown]
# ## Checkpoint
#
# 1. Why put the guard in code between the reply and the layer, rather than as a rule in the prompt?
#
# <details><summary>Answer</summary>A prompt rule is a request the model may ignore, and the stand-in's C15 shows it
# does; code checks every reply the same way and can be tested.</details>
#
# 2. The guard refuses questions without a period. Name a question type where that rule is wrong.
#
# <details><summary>Answer</summary>A metric's definition ("What does collection rate mean?") or the current
# catalogue: no figure is computed, so no period is needed. Route them to `describe_metric`.</details>
#
# **Carry forward.** `artifacts/D4_2/guard_effect.csv`. Lab 4.3 starts from the supplied evaluation.
