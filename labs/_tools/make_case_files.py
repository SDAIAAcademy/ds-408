"""Write the case files of Qamar Telecom that are not marts: the 40-metric catalogue and its report
inventory, the query log, the certified question set and its candidates, the stand-in model's recorded
replies and the peer package for the design review.

    uv run python _tools/make_case_files.py [catalogue] [querylog] [questions] [recordings] [peer]

Deterministic (fixed seed). Run after prepare_data.py. Everything is synthetic.
"""
from __future__ import annotations

import csv
import random
import sys
from pathlib import Path

LABS = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(LABS))
import qamar as Q  # noqa: E402

DATA = LABS / "data"


def write_csv(path: Path, rows: list[dict]):
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("w", newline="", encoding="utf-8") as f:
        w = csv.DictWriter(f, fieldnames=list(rows[0]), lineterminator="\n")
        w.writeheader()
        w.writerows(rows)
    print("wrote", path.relative_to(LABS), len(rows), "rows")


# ---------------------------------------------------------------------------------- catalogue (Lab 1.4)
def catalogue():
    J, M, E, Z = "Jood Al-Muhaisen", "Majdi Bawazir", "Ebtihal Al-Ghanim", "Zeyad Al-Juraisy"
    rows = [
        # name, area, owner, version, status, tests, depends_on, aliases
        ("billed_amount", "billing", J, "1.0.0", "certified", 1, [], ["billing", "total billed"]),
        ("bills_issued", "billing", J, "1.0.0", "certified", 1, [], []),
        ("billed_customers", "billing", J, "1.0.0", "certified", 1, [], []),
        ("arpa", "billing", J, "1.0.0", "certified", 0, ["billed_amount", "billed_customers"], ["ARPA", "average bill"]),
        ("disputed_amount", "billing", J, "1.0.0", "certified", 1, [], []),
        ("billed_amount_ex_vat", "billing", J, "0.2.0", "draft", 0, ["billed_amount"], []),
        ("credit_notes", "billing", J, "1.1.0", "certified", 1, [], []),
        ("revenue_per_line", "billing", "", "1.0.0", "certified", 0, ["billed_amount"], ["RPL"]),
        ("net_due_30", "collections", M, "1.0.0", "certified", 1, [], []),
        ("collected_30", "collections", M, "1.0.0", "certified", 1, [], []),
        ("collection_rate", "collections", M, "1.0.0", "certified", 1, ["collected_30", "net_due_30"], ["collection rate (certified)"]),
        ("cash_collected", "collections", J, "1.0.0", "certified", 1, [], ["receipts"]),
        ("cash_collected_fytd", "collections", J, "1.0.0", "certified", 0, ["cash_collected"], []),
        ("collection_rate_finance", "collections", J, "1.3.0", "certified", 1, ["cash_collected", "billed_amount"], ["collection %", "cash collection rate"]),
        ("collection_rate_60d", "collections", M, "2.1.0", "certified", 1, [], ["collections rate", "recovery rate 60"]),
        ("paid_on_time_rate", "collections", E, "1.0.0", "certified", 0, [], ["on-time payers %"]),
        ("collections_score", "collections", M, "1.0.0", "certified", 0, ["collection_rate_60d", "disputed_amount"], []),
        ("bad_debt_provision", "collections", J, "1.0.0", "certified", 1, [], []),
        ("arrears_over_90", "collections", M, "1.2.0", "certified", 1, [], ["90+ arrears"]),
        ("promise_to_pay_kept", "collections", M, "0.3.0", "draft", 0, [], []),
        ("data_gb", "usage", Z, "1.0.0", "certified", 1, [], ["traffic"]),
        ("voice_minutes", "usage", Z, "1.0.0", "certified", 1, [], []),
        ("active_lines", "usage", Z, "1.0.0", "certified", 1, [], ["active subscriptions"]),
        ("data_per_line", "usage", Z, "1.0.0", "certified", 0, ["data_gb", "active_lines"], []),
        ("roaming_mb", "usage", Z, "1.0.0", "certified", 1, [], []),
        ("sms_count", "usage", Z, "0.9.0", "draft", 0, [], []),
        ("peak_hour_load", "usage", Z, "1.0.0", "deprecated", 1, [], []),
        ("fibre_uptake", "usage", Z, "1.0.0", "certified", 0, ["active_lines"], []),
        ("complaints", "complaints", E, "1.0.0", "certified", 1, [], ["tickets"]),
        ("billing_complaints", "complaints", E, "1.0.0", "certified", 1, [], []),
        ("median_resolution_days", "complaints", E, "1.0.0", "certified", 1, [], []),
        ("complaints_per_1k_lines", "complaints", E, "1.0.0", "certified", 0, ["complaints", "active_lines"], ["complaint rate"]),
        ("first_contact_resolution", "complaints", E, "1.1.0", "certified", 1, [], ["FCR"]),
        ("repeat_complaints", "complaints", E, "1.0.0", "certified", 0, ["complaints"], []),
        ("complaint_backlog", "complaints", E, "1.0.0", "certified", 1, [], []),
        ("csat_after_complaint", "complaints", E, "0.5.0", "draft", 0, [], []),
        ("region_health_index", "cross-area", "", "1.0.0", "certified", 0, ["collections_score", "complaints_per_1k_lines"], ["RHI"]),
        ("billing_complaint_share", "cross-area", E, "1.0.0", "certified", 0, ["billing_complaints", "bills_issued"], []),
        ("customer_value_index", "cross-area", J, "0.4.0", "draft", 0, ["arpa", "paid_on_time_rate"], []),
        ("legacy_kpi_pack", "cross-area", Z, "1.0.0", "deprecated", 0, ["peak_hour_load"], []),
    ]
    assert len(rows) == 40
    cat = [{"name": n, "area": a, "owner": o or None, "version": v, "status": s, "tests": t,
            "depends_on": d, "aliases": al} for n, a, o, v, s, t, d, al in rows]
    Q.yaml_dump({"catalogue": cat}, DATA / "catalogue" / "catalogue.yaml")
    print("wrote data/catalogue/catalogue.yaml", len(cat), "metrics")
    reports = [
        ("Monthly finance pack", J, ["billed_amount", "collection %", "cash_collected_fytd", "arpa"]),
        ("Board pack", J, ["billed_amount", "collection_rate", "RHI", "active_lines"]),
        ("Collections weekly", M, ["collections rate", "arrears_over_90", "collected_30", "promise_to_pay_kept"]),
        ("Collections region scorecard", M, ["collections_score", "collection_rate"]),
        ("Customer care scorecard", E, ["complaints", "on-time payers %", "FCR", "median_resolution_days"]),
        ("Care quality review", E, ["complaint rate", "repeat_complaints", "billing_complaint_share"]),
        ("Network monthly", Z, ["traffic", "data_per_line", "roaming_mb"]),
        ("Regional managers dashboard", Z, ["region_health_index", "complaints", "billed_amount", "active subscriptions"]),
        ("Retail targets", J, ["ARPA", "fibre_uptake", "customer_value_index"]),
        ("Data platform health", Z, ["legacy_kpi_pack", "data_gb"]),
        ("Executive daily", J, ["cash collection rate", "complaints", "active_lines"]),
        ("Disputes tracker", J, ["disputed_amount", "billing_complaints", "credit_notes"]),
    ]
    write_csv(DATA / "catalogue" / "reports.csv",
              [{"report": r, "report_owner": o, "metric_ref": m} for r, o, ms in reports for m in ms])


# ---------------------------------------------------------------------------------- starter model (Lab 2.1)
def starter():
    import copy
    import qsem as S
    doc = copy.deepcopy(S.load_yaml(DATA / "semantic" / "qamar_model.yaml"))
    for d in doc["datasets"]:
        if d["name"] == "complaint":
            d.pop("time")
            d.pop("joins")
        if d["name"] == "line":
            for j in d["joins"]:
                j.pop("asof", None)
    head = ("# Lab 2.1 starting state: the complaint dataset is not yet conformed (no time, no join to customer)\n"
            "# and the tariff join of line has no validity dates. The finished model is qamar_model.yaml.\n")
    (DATA / "semantic" / "model_starter.yaml").write_text(head + Q.yaml_dump(doc), encoding="utf-8", newline="\n")
    print("wrote data/semantic/model_starter.yaml")


# ---------------------------------------------------------------------------------- query log (Lab 2.2)
def querylog():
    rng = random.Random(4082)
    patterns = [  # (metrics, by, weight): what managers ask most, by area
        (["session_data_gb"], ["customer.region", "time.month"], 60),
        (["sessions"], ["time.month"], 48),
        (["session_data_gb", "lines_with_sessions"], ["tariff.plan_name"], 40),
        (["call_minutes"], ["customer.region", "time.month"], 36),
        (["session_data_gb"], ["customer.segment", "time.fiscal_year"], 33),
        (["sessions", "call_minutes"], ["usage_event.kind", "time.month"], 30),
        (["session_data_gb"], ["time.day"], 26),
        (["sessions"], ["customer.region", "customer.segment"], 24),
        (["call_minutes"], ["tariff.plan_name", "time.fiscal_quarter"], 21),
        (["session_data_gb", "sessions"], ["customer.city"], 19),
        (["lines_with_sessions"], ["time.month"], 12),
        (["billed_amount"], ["time.month"], 9),
        (["collection_rate"], ["customer.segment"], 8),
        (["complaints"], ["complaint.category", "time.month"], 7),
        (["session_data_gb"], ["line.product", "customer.region"], 5),
        (["data_gb"], ["tariff.plan_name"], 4),
    ]
    roles = ["executive", "regional_manager_eas", "collections_officer"]
    rows = []
    for i in range(1, 401):
        mets, by, _ = rng.choices(patterns, weights=[p[2] for p in patterns])[0]
        rows.append({"query_id": f"QL{i:04d}", "asked_by_role": rng.choice(roles), "metrics": "|".join(mets),
                     "group_by": "|".join(by), "days_ago": rng.randrange(0, 30)})
    write_csv(DATA / "semantic" / "query_log.csv", rows)


# ---------------------------------------------------------------------------------- question sets (Day 3)
ASSIST = DATA / "assistant"
UNITS = {"data_gb": "GB", "voice_minutes": "minutes", "active_lines": "lines", "data_per_line": "GB per line",
         "billed_amount": "SAR", "bills_issued": "bills", "disputed_amount": "SAR", "billed_customers": "customers",
         "arpa": "SAR per account", "collection_rate": "ratio", "cash_collected": "SAR", "collected_30": "SAR",
         "cash_collected_fytd": "SAR", "complaints": "complaints", "billing_complaints": "complaints",
         "median_resolution_days": "days", "complaints_per_1k_lines": "per 1,000 lines"}


def _model():
    import qsem as S
    return S.Model.load(DATA / "semantic" / "qamar_model.yaml", Q.db(), metrics_dir=DATA / "metrics")


def _certified():
    sys.path.insert(0, str(LABS / "_tools"))
    import daleel as D
    from questions import ANSWERABLE, REFUSALS
    model = _model()
    out = []
    for qid, lang, area, diff, text, query, kind, _tags in ANSWERABLE:
        val = D.answer(model, query, kind)
        unit = "label" if kind == "label" else UNITS[query["metrics"][0]]
        out.append({"id": qid, "lang": lang, "area": area, "difficulty": diff, "question": text,
                    "query": {k: v for k, v in query.items()}, "expect": {"kind": kind, "value": val, "unit": unit}})
    for qid, lang, area, text, reason in REFUSALS:
        out.append({"id": qid, "lang": lang, "area": area, "difficulty": 2, "question": text, "expect": {"refuse": reason}})
    order = {"usage": 0, "billing": 1, "collections": 2, "complaints": 3}
    return sorted(out, key=lambda q: (order[q["area"]], q["id"]))


def questions():
    import daleel as D
    from questions import FLAWED, HELD_OUT
    full = _certified()
    D.save_set(full, ASSIST / "certified_60.yaml", "Qamar Telecom: certified questions for Daleel (synthetic)")
    supplied = [q for q in full if q["id"] not in HELD_OUT]
    D.save_set(supplied, ASSIST / "supplied_44.yaml", "Qamar Telecom: the supplied certified set (44 questions)")
    cands = []
    for q in full:
        if q["id"] in HELD_OUT:
            c = {k: q[k] for k in ("id", "lang", "area", "difficulty", "question")}
            c["draft"] = q["query"] if "query" in q else {"refuse": q["expect"]["refuse"]}
            if "query" in q:
                c["kind"] = q["expect"]["kind"]
            cands.append(c)
    for qid, lang, area, diff, text, draft, refuse in FLAWED:
        c = {"id": qid, "lang": lang, "area": area, "difficulty": diff, "question": text,
             "draft": draft if draft else {"refuse": refuse}}
        if draft:
            c["kind"] = "label" if draft.get("order") else "value"
        cands.append(c)
    random.Random(4083).shuffle(cands)
    D.save_set(cands, ASSIST / "candidates.yaml", "Candidate questions for the certified set: drafts, not yet certified")
    print("wrote data/assistant/certified_60.yaml", len(full), "supplied_44.yaml", len(supplied), "candidates.yaml", len(cands))


# ---------------------------------------------------------------------------------- stand-in replies (Day 3)
# The stand-in's error model, stated so the Director and trainers can see what the recordings encode:
#   no_synonyms      Arabic questions tagged syn pick a neighbouring metric or find none
#   no_descriptions  collection_rate becomes the finance ratio, billed_customers becomes bills, complaints by
#                    complaint.region become complaints by customer.region; one immature cohort is answered
#   no_examples      fiscal years become calendar years, fiscal quarters calendar quarters, Hijri months
#                    Gregorian months, the fiscal-year-to-date metric the plain monthly one
#   unstable         in every variant, the run pattern below swaps in the no_examples error (or drops a filter)
#   stable_wrong     wrong the same way in every run: Riyadh read as the Central region; all complaints
#                    instead of billing complaints
#   refusals         refused in every variant, except C15 (a draft metric answered every time), Q15 (answered
#                    on run 2) and C14 (answered without descriptions)
SYN_WRONG = {"data_gb": "voice_minutes", "billed_amount": "bills_issued", "arpa": "billed_amount",
             "cash_collected": None, "complaints": None, "median_resolution_days": "complaints"}
DESC_WRONG = {"collection_rate": "cash_collection_ratio", "billed_customers": "bills_issued"}
UNSTABLE_RUNS = {"U11": (0, 1, 0), "U13": (0, 0, 1), "B10": (1, 0, 0), "C09": (0, 1, 1), "C12": (0, 1, 0), "Q13": (0, 0, 1)}
CAL_Q = {1: ("2025-01-01", "2025-03-01"), 2: ("2025-04-01", "2025-06-01"), 3: ("2025-07-01", "2025-09-01"), 4: ("2025-10-01", "2025-12-01")}


def _no_examples(query: dict) -> dict:
    import copy
    import re
    q = copy.deepcopy(query)
    where = []
    for w in q.get("where", []):
        if m := re.match(r"time\.fiscal_year = 'FY(\d{4})-\d\d'", w):
            where.append(f"time.year = {m.group(1)}")
        elif m := re.match(r"time\.fiscal_quarter = 'FY\d{4}-\d\d-Q(\d)'", w):
            a, b = CAL_Q[int(m.group(1))]
            where.append(f"time.month BETWEEN DATE '{a}' AND DATE '{b}'")
        elif m := re.match(r"time\.hijri_month = '\d{4}-(\d\d)'", w):
            where.append(f"time.month = DATE '2025-{m.group(1)}-01'")
        else:
            where.append(w)
    q["where"] = where
    if q["metrics"] == ["cash_collected_fytd"]:
        q["metrics"] = ["cash_collected"]
    return q


def _unstable_wrong(query: dict) -> dict:
    q = _no_examples(query)
    if q == query and len(q.get("where", [])) > 1:
        q = dict(q, where=q["where"][:-1])
    return q


def _reply(qid: str, variant: str, run: int, query: dict | None, tags: list, refuse: str | None) -> dict | str:
    import copy
    q = copy.deepcopy(query) if query else None
    if refuse:  # a must-refuse question
        if qid == "C15":
            return {"metrics": ["on_time_payment_share"], "by": [], "where": ["time.month = DATE '2026-03-01'"]}
        if qid == "Q15" and run == 2:
            return {"metrics": ["complaints"], "by": ["complaint.category"], "where": ["time.month = DATE '2026-01-01'"], "order": "desc", "limit": 1}
        if qid == "C14" and variant == "no_descriptions":
            return {"metrics": ["collection_rate"], "by": [], "where": ["time.month = DATE '2026-05-01'"]}
        return {"refuse": refuse}
    if "stable_wrong" in tags:
        if qid == "C13":
            q["where"] = [w.replace("customer.city = 'Riyadh'", "customer.region = 'CEN'") for w in q["where"]]
        if qid == "Q11":
            q["metrics"] = ["complaints"]
    if variant == "no_synonyms" and "syn" in tags:
        alt = SYN_WRONG.get(q["metrics"][0], q["metrics"][0])
        if alt is None:
            return {"refuse": "no_metric"}
        q["metrics"] = [alt]
    if variant == "no_descriptions" and "desc" in tags:
        q["metrics"] = [DESC_WRONG.get(m, m) for m in q["metrics"]]
        q["where"] = [w.replace("complaint.region", "customer.region") for w in q.get("where", [])]
    if variant == "no_examples" and "ex" in tags:
        q = _no_examples(q)
    if "unstable" in tags and UNSTABLE_RUNS[qid][run - 1]:
        q = _unstable_wrong(q)
    return q


def recordings():
    import json
    from questions import ANSWERABLE, REFUSALS
    items = [(a[0], a[5], a[7], None) for a in ANSWERABLE] + [(r[0], None, [], r[4]) for r in REFUSALS]
    rows = []
    for qid, query, tags, refuse in sorted(items):
        for variant in ["full", "no_synonyms", "no_descriptions", "no_examples"]:
            for run in (1, 2, 3):
                r = _reply(qid, variant, run, query, tags, refuse)
                text = json.dumps(r, ensure_ascii=False)
                if (sum(map(ord, qid)) + run) % 5 == 0:  # some models wrap their JSON in a code fence
                    text = "```json\n" + text + "\n```"
                if qid == "Q09" and variant == "no_examples" and run == 3:
                    text = "The complaint rate for business customers was about 36 per 1,000 lines in June 2026."
                rows.append({"id": qid, "variant": variant, "run": run, "reply": text})
    path = ASSIST / "replies.jsonl"
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("w", encoding="utf-8", newline="\n") as f:
        for r in rows:
            f.write(json.dumps(r, ensure_ascii=False) + "\n")
    print("wrote data/assistant/replies.jsonl", len(rows), "replies (stand-in, synthetic)")


# ---------------------------------------------------------------------------------- main
STEPS = {"catalogue": catalogue, "starter": starter, "querylog": querylog, "questions": questions,
         "recordings": recordings}

if __name__ == "__main__":
    for name, fn in STEPS.items():
        if len(sys.argv) == 1 or name in sys.argv[1:]:
            fn()
