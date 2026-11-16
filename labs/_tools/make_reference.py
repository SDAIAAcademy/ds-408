"""Write data/reference/*.json: the reference results the labs' safety nets fall back on.

    uv run python _tools/make_reference.py

Days 1 and 2 are computed from the marts with plain SQL, not with the lab solutions, so a solution run
that matches them is an independent check; Day 3 from the supplied scorer (muhsi.py). Day 4's results
are judgements and protocol exchanges, so they are captured from a solution run of each lab source and
checked by hand. Run after prepare_data.py and make_case_files.py.
"""
from __future__ import annotations

import json
import sys
from pathlib import Path

LABS = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(LABS))
import qamar as Q  # noqa: E402

OUT = LABS / "data" / "reference"
M = "DATE '2026-03-01'"


def save(name, obj):
    OUT.mkdir(parents=True, exist_ok=True)
    (OUT / f"{name}.json").write_text(json.dumps(obj, indent=1, ensure_ascii=False, default=str) + "\n", encoding="utf-8", newline="\n")
    print("wrote", name)


def cohort(con, window, net, dedup=True, extra=""):
    den = "amount_due - disputed_amount" if net else "amount_due"
    pay = "(SELECT DISTINCT bill_id, paid_date, amount, batch_id FROM fct_payment)" if dedup else "fct_payment"
    return float(con.execute(f"""
        WITH b AS (SELECT b.* FROM fct_bill b JOIN dim_customer c USING (customer_id) WHERE bill_month = {M} {extra})
        SELECT (SELECT SUM(p.amount) FROM {pay} p JOIN b USING (bill_id) WHERE p.paid_date <= b.due_date + {window})
             / (SELECT SUM({den}) FROM b)""").fetchone()[0])


def d1_1(con):
    billed = con.execute(f"SELECT SUM(amount_due) FROM fct_bill WHERE bill_month = {M}").fetchone()[0]
    cash = con.execute("SELECT SUM(amount) FROM fct_payment WHERE paid_date BETWEEN DATE '2026-03-01' AND DATE '2026-03-31'").fetchone()[0]
    cash_dedup = con.execute("""SELECT SUM(amount) FROM (SELECT DISTINCT bill_id, paid_date, amount, batch_id FROM fct_payment)
                                WHERE paid_date BETWEEN DATE '2026-03-01' AND DATE '2026-03-31'""").fetchone()[0]
    care = con.execute(f"""
        SELECT AVG(CASE WHEN coalesce(paid, 0) >= amount_due - disputed_amount - 0.01 THEN 1 ELSE 0 END) FROM fct_bill b
        LEFT JOIN (SELECT p.bill_id, SUM(p.amount) AS paid FROM fct_payment p JOIN fct_bill x USING (bill_id)
                   WHERE p.paid_date <= x.due_date GROUP BY 1) USING (bill_id) WHERE bill_month = {M}""").fetchone()[0]
    rates = {"finance": cash / billed, "collections": cohort(con, 60, True, dedup=False), "care": float(care),
             "certified": cohort(con, 30, True)}
    save("d1_1_rates", rates)
    dup = con.execute("""SELECT batch_id, COUNT(*) FILTER (WHERE load_no > 1) AS n, SUM(amount) FILTER (WHERE load_no > 1) AS amt
                         FROM fct_payment GROUP BY 1 HAVING n > 0""").fetchone()
    save("d1_1_duplicate", {"batch_id": dup[0], "extra_rows": int(dup[1]), "extra_amount": round(float(dup[2]), 2),
                            "finance_without_duplicates": cash_dedup / billed})
    save("d1_1_walk", [
        {"step": "Finance as reported", "rate": rates["finance"]},
        {"step": "Remove the duplicated batch", "rate": cash_dedup / billed},
        {"step": "Cohort: March bills, 60 days, gross", "rate": cohort(con, 60, False)},
        {"step": "Disputes out of the denominator", "rate": cohort(con, 60, True)},
        {"step": "Window 30 days", "rate": cohort(con, 30, True)},
    ])
    save("d1_1_certified", {"name": "collection_rate", "owner": "Majdi Bawazir", "approver": "Jood Al-Muhaisen",
                            "basis": "value", "population": "bills of the service month (cohort)",
                            "window_days_after_due": 30, "disputes": "excluded from the denominator until decided",
                            "duplicates": "removed in the data", "maturity": "reported once due date plus window has passed"})


def d1_2(con):
    fy = con.execute("""
        WITH b AS (SELECT * FROM fct_bill WHERE bill_month BETWEEN DATE '2025-04-01' AND DATE '2026-03-01'
                   AND due_date + 30 <= DATE '2026-06-30')
        SELECT (SELECT SUM(p.amount) FROM (SELECT DISTINCT bill_id, paid_date, amount, batch_id FROM fct_payment) p
                JOIN b USING (bill_id) WHERE p.paid_date <= b.due_date + 30) / (SELECT SUM(amount_due - disputed_amount) FROM b)
    """).fetchone()[0]
    save("d1_2_values", {"collection_rate_fy2025": fy})


def d1_3(con):
    save("d1_3_process", {
        "request": "Anyone may open a change request naming the metric, the reason and the reports affected",
        "implement": "The data platform team edits the metric file on a branch and opens a pull request",
        "approve": "The metric's owner approves the new version; the author cannot approve",
        "versioning": "Meaning changed: major. New field or status: minor. Words only: patch",
        "notice": "A major change is announced two monthly closes before it takes effect",
        "old_version": "The old meaning stays under a new name, deprecated, until its reports move",
        "checks": "CI runs the review rules and the reconciliation tests; both must pass to merge"})


def d1_4(con):
    import csv
    cat = Q.yaml_load("data/catalogue/catalogue.yaml")["catalogue"]
    cert = [m for m in cat if m["status"] == "certified"]
    save("d1_4_health", {"no_owner": sorted(m["name"] for m in cert if not m["owner"]),
                         "simple_untested": sorted(m["name"] for m in cert if not m["depends_on"] and m["tests"] == 0),
                         "derived_untested": sorted(m["name"] for m in cert if m["depends_on"] and m["tests"] == 0)})
    succ = {"collection_rate_finance": "collection_rate", "collection_rate_60d": "collection_rate",
            "paid_on_time_rate": "on_time_payment_share"}
    new = []
    for m in cat:
        m = dict(m)
        if m["name"] in succ:
            a, b, _ = m["version"].split(".")
            m.update(status="deprecated", replaced_by=succ[m["name"]], sunset="2026-08-31", version=f"{a}.{int(b) + 1}.0")
        new.append(m)
    save("d1_4_catalogue", new)
    dep = {m["name"] for m in new if m["status"] == "deprecated"}
    down = set()
    for _ in range(10):
        down |= {m["name"] for m in new if set(m["depends_on"]) & (dep | down)}
    down -= dep
    save("d1_4_downstream", sorted(down))
    alias = {m["name"].lower(): m["name"] for m in new}
    alias.update({a.lower(): m["name"] for m in new for a in m["aliases"]})
    rows = []
    with open(Q.LABS / "data" / "catalogue" / "reports.csv", encoding="utf-8") as f:
        for r in csv.DictReader(f):
            name = alias.get(r["metric_ref"].lower())
            if name in dep | down:
                rows.append({**r, "metric": name, "why": "deprecated" if name in dep else "built on deprecated",
                             "move_to": succ.get(name, "review")})
    save("d1_4_reports", rows)


def d2_1(con):
    import copy
    import qsem as S
    t = con.execute("SELECT (SELECT SUM(amount_due) FROM fct_bill), (SELECT COUNT(*) FROM fct_complaint)").fetchone()
    w = con.execute("""SELECT SUM(b.amount_due), COUNT(q.complaint_id) FROM dim_customer c JOIN fct_bill b USING (customer_id)
                       LEFT JOIN fct_complaint q USING (customer_id)""").fetchone()
    save("d2_1_fan_out", {"billed_factor": round(w[0] / t[0], 2), "complaints_factor": round(w[1] / t[1], 2)})
    full = S.load_yaml(Q.LABS / "data" / "semantic" / "qamar_model.yaml")
    save("d2_1_model", full)
    conf = copy.deepcopy(full)
    for j in next(d for d in conf["datasets"] if d["name"] == "line")["joins"]:
        j.pop("asof", None)
    save("d2_1_conformed", conf)


def d2_2(con):
    import collections
    import csv
    with open(Q.LABS / "data" / "semantic" / "query_log.csv", encoding="utf-8") as f:
        cnt = collections.Counter((r["metrics"], r["group_by"]) for r in csv.DictReader(f))
    top = sorted(cnt.items(), key=lambda kv: (-kv[1], kv[0]))[:10]
    save("d2_2_top", [{"metrics": m.split("|"), "by": b.split("|"), "n": n} for (m, b), n in top])
    m = ["session_data_gb", "sessions", "call_minutes"]
    save("d2_2_preaggs", [
        {"name": "usage_region_month", "dataset": "usage_event", "measures": m,
         "by": ["customer.region", "customer.segment", "usage_event.kind", "time.month", "time.fiscal_year"]},
        {"name": "usage_plan_quarter", "dataset": "usage_event", "measures": m, "by": ["tariff.plan_name", "time.fiscal_quarter"]},
        {"name": "usage_day", "dataset": "usage_event", "measures": m, "by": ["time.day"]},
        {"name": "usage_city", "dataset": "usage_event", "measures": m, "by": ["customer.city"]}])


def d2_3(con):
    import copy
    import qsem as S
    pol = Q.yaml_load("data/access/policy.yaml")
    areas = {"billing": ("billed_amount", "customer.region"), "collections": ("collection_rate", "customer.region"),
             "payments": ("cash_collected", "customer.region"), "usage": ("data_gb", "customer.region"),
             "complaints": ("complaints", "complaint.region")}

    def run(model, policy):
        rows = []
        for role, r in policy["roles"].items():
            m = model.as_role(role, policy=policy)
            allowed = None if r["regions"] == "all" else set(r["regions"])
            for area, (metric, region) in areas.items():
                seen = set(m.query([metric], by=[region])[region])
                rows.append({"role": role, "test": f"rows:{area}", "passed": allowed is None or seen <= allowed,
                             "detail": ",".join(sorted(seen))})
            for field in ("customer.full_name", "customer.contact_name"):
                vals = set(m.query(["billed_amount"], by=[field])[field])
                masked = vals == {"***"}
                rows.append({"role": role, "test": f"mask:{field}", "passed": masked != bool(r.get("restricted")),
                             "detail": "masked" if masked else f"{len(vals)} values visible"})
        return rows

    base = S.Model.load(Q.LABS / "data/semantic/qamar_model.yaml", con, metrics_dir=Q.LABS / "data/metrics")
    save("d2_3_first_run", run(base, pol))
    save("d2_3_leaks", {"row_leak": "complaint", "mask_leak": "customer.contact_name"})
    pol2 = copy.deepcopy(pol)
    pol2["row_rules"]["complaint"] = "complaint.region"
    save("d2_3_policy", pol2)
    save("d2_3_second_run", run(S.Model(base.doc, con, policy=pol2, deny_by_default=True, lineage=True), pol2))


def d2_4(con):
    import re
    import qsem as S
    import qossie as O
    model = S.Model.load(Q.LABS / "data/semantic/qamar_model.yaml", con, metrics_dir=Q.LABS / "data/metrics")
    fields = {d["name"]: {f["name"] for f in d["fields"]} for d in model.doc["datasets"]}

    def sql(name):
        x = model.metrics[name]
        t = x.get("type", "simple")
        if t == "simple":
            e = O.qualify(x["expr"], x["dataset"], fields[x["dataset"]])
            if x.get("filter"):
                e = f"CASE WHEN {O.qualify(x['filter'], x['dataset'], fields[x['dataset']])} THEN {e} END"
            return f"COUNT(DISTINCT {e})" if x["agg"] == "count_distinct" else f"{x['agg'].upper()}({e})"
        if t == "ratio":
            return f"({sql(x['numerator'])}) * 1.0 / ({sql(x['denominator'])})"
        if t == "derived":
            e = x["expr"]
            for i in sorted(x["inputs"], key=len, reverse=True):
                e = re.sub(rf"\b{i}\b", lambda _: f"({sql(i)})", e)
            return e
        return None
    mets = []
    for n, m in model.metrics.items():
        s = sql(n)
        if s:
            mets.append({"name": n, "expression": {"sql": s}, "description": m.get("description", ""),
                         "nonportable_extensions": [{"vendor_name": O.VENDOR, "data": {k: m.get(k) for k in ("owner", "version", "status", "unit")}}]})
    save("d2_4_metrics", mets)
    doc = O.export_datasets(model.doc)
    doc["metrics"] = mets
    lite = O.sqlite_copy(con, model.doc)
    first = {}
    for metric, by in [("billed_amount", ["bill.service_month"]), ("collection_rate", ["customer.segment"]), ("complaints", ["complaint.region"])]:
        try:
            first[metric] = O.run(doc, lite, metric, by).to_dict("records")
        except Exception as e:
            first[metric] = f"error: {str(e).splitlines()[-1][-90:]}"
    save("d2_4_first", first)
    save("d2_4_fixes", {"bill.service_month": "strftime('%Y-%m', bill_month)",
                        "customer.contact_name": "substr(full_name, 1, instr(full_name || ' ', ' ') - 1)",
                        "complaint.resolution_days": "CAST(julianday(closed_date) - julianday(opened_date) AS INTEGER)"})
    save("d2_4_left_behind", {"extensions": ["dataset collection: materialize_as, duckdb_sql", "dataset payment: materialize_as, duckdb_sql",
                                             "field customer.full_name: classification", "relationship line_to_tariff: asof_valid_between",
                                             "model: {'cumulative_metrics': ['cash_collected_fytd']}"],
                              "median_resolution_days on SQLite": "no such function: MEDIAN"})


def _d3_setup(con):
    import muhsi as D
    import qsem as S
    model = S.Model.load(LABS / "data/semantic/qamar_model.yaml", con, metrics_dir=LABS / "data/metrics")
    return D, model, D.load_set("data/assistant/certified_60.yaml")


def d3_1(con):
    """From the supplied files: the 44, the candidates and the certified 60 (built by make_case_files.py)."""
    D, model, full = _d3_setup(con)
    sup = D.load_set("data/assistant/supplied_44.yaml")
    cands = D.load_set("data/assistant/candidates.yaml")
    rows = []
    for a in ["usage", "billing", "collections", "complaints"]:
        for d in (1, 2, 3):
            cell = [q for q in sup if q["area"] == a and q["difficulty"] == d]
            ans = [q for q in cell if "refuse" not in q["expect"]]
            rows.append({"area": a, "difficulty": d, "ar": sum(q["lang"] == "ar" for q in ans),
                         "en": sum(q["lang"] == "en" for q in ans), "refusals": len(cell) - len(ans)})
    save("d3_1_coverage", rows)
    flawed = {"X01": "period", "X02": "duplicate", "X03": "certified", "X04": "period", "X05": "duplicate",
              "X06": "certified", "X07": "restricted", "X08": "period"}  # stated in _tools/questions.py
    save("d3_1_screen", [{"id": c["id"], "keep": c["id"] not in flawed, "rule": flawed.get(c["id"], "")} for c in cands])
    byid = {q["id"]: q for q in full}
    new = []
    for c in cands:
        if c["id"] in flawed:
            continue
        q = dict(byid[c["id"]])
        if "query" in q:
            q["expect"] = dict(q["expect"], metric_version=model.describe(q["query"]["metrics"][0])["version"])
        new.append(q)
    save("d3_1_certified_new", new)
    ref = [q for q in full if "refuse" in q["expect"]]
    save("d3_1_final", {"n": len(full), "gaps": 0, "ar": sum(q["lang"] == "ar" for q in full), "en": sum(q["lang"] == "en" for q in full),
                        "refusals": len(ref), "refusal_kinds": sorted({q["expect"]["refuse"] for q in ref}),
                        "areas_with_refusal": len({q["area"] for q in ref})})


def d3_2(con):
    D, model, qs = _d3_setup(con)
    mets = list(model.metrics.values())
    sizes = []
    for v in D.VARIANTS:
        ctx = D.context(mets, v)
        sizes.append({"variant": v, "chars": len(json.dumps(ctx, ensure_ascii=False)), "synonyms": sum("synonyms" in m for m in ctx),
                      "descriptions": sum("description" in m for m in ctx), "examples": sum("examples" in m for m in ctx)})
    save("d3_2_sizes", sizes)
    t = {v: D.score(model, qs, v) for v in D.VARIANTS}
    for v, name in [("no_synonyms", "syn"), ("no_descriptions", "desc"), ("no_examples", "ex")]:
        m = t["full"].merge(t[v], on=["id", "lang", "area", "difficulty", "run"], suffixes=("_full", "_variant"))
        m = m[m.outcome_full != m.outcome_variant]
        save(f"d3_2_flips_{name}", m[["id", "lang", "area", "difficulty", "outcome_full", "outcome_variant", "got_variant", "want_full"]].to_dict("records"))
    rows = []
    good = ["right", "refused_right"]
    for kind, v in [("synonyms", "no_synonyms"), ("descriptions", "no_descriptions"), ("examples", "no_examples")]:
        f, x = t["full"], t[v]
        acc = lambda d: d.outcome.isin(good).mean()  # noqa: E731
        area = {a: acc(f[f.area == a]) - acc(x[x.area == a]) for a in sorted(f.area.unique())}
        rows.append({"context": kind, "drop": round(acc(f) - acc(x), 3), "drop_ar": round(acc(f[f.lang == "ar"]) - acc(x[x.lang == "ar"]), 3),
                     "drop_en": round(acc(f[f.lang == "en"]) - acc(x[x.lang == "en"]), 3), "area_most": max(area, key=area.get),
                     "more_plausible": round(x.outcome.isin(["wrong_plausible", "missed_refusal"]).mean() - f.outcome.isin(["wrong_plausible", "missed_refusal"]).mean(), 3)})
    save("d3_2_contribution", sorted(rows, key=lambda r: -r["drop"]))


def d3_3(con):
    D, model, qs = _d3_setup(con)
    t = D.score(model, qs, "full")
    save("d3_3_accuracy", round(float(t.outcome.isin(["right", "refused_right"]).mean()), 3))
    byid = {q["id"]: q for q in qs}
    rows = []
    for _, r in t[t.outcome.isin(["wrong_plausible", "missed_refusal"])].iterrows():
        q, used = byid[r.id], D.parse(D.ask(byid[r.id], "full", 1))
        cert = q.get("query", {"refuse": q["expect"].get("refuse")})
        rows.append({"id": r.id, "outcome": r.outcome, "question": q["question"][:60], "used": f"{used.get('metrics')} {used.get('where')}",
                     "certified": f"{cert.get('metrics', cert.get('refuse'))} {cert.get('where', '')}"})
    save("d3_3_plausible", rows)


def d3_4(con):
    import pandas as pd
    D, model, qs = _d3_setup(con)
    runs = D.score(model, qs, "full", runs=(1, 2, 3))
    runs["answer"] = runs.got.map(str)
    good = ["right", "refused_right"]
    per = runs.groupby(["id", "lang", "area", "difficulty"]).agg(agree=("answer", lambda s: int(s.value_counts().iloc[0])),
                                                                 n_right=("outcome", lambda s: int(s.isin(good).sum()))).reset_index()
    save("d3_4_agreement", per.to_dict("records"))
    per["stability"] = ["unstable" if a < 3 else ("stable_right" if n == 3 else "stable_wrong") for a, n in zip(per.agree, per.n_right)]
    save("d3_4_stability", per.to_dict("records"))
    parts = []
    for col in ["area", "difficulty", "lang"]:
        g = per.groupby(col).stability.value_counts(normalize=True).unstack(fill_value=0)
        g = g.reindex(columns=["unstable", "stable_wrong"], fill_value=0).round(3)
        g.index = [f"{col}={i}" for i in g.index]
        parts.append(g)
    save("d3_4_groups", pd.concat(parts).rename_axis("group").reset_index().to_dict("records"))
    first = set(runs[(runs.run == 1) & runs.outcome.isin(good)].id)
    save("d3_4_hidden", sorted(set(per[per.stability == "unstable"].id) & first))


def _solution_run(name: str) -> dict:
    """Run one lab source (solutions included) from labs/ and return its namespace."""
    import os
    os.chdir(LABS)
    ns = {"__name__": "__lab__"}
    exec(compile((LABS / "_src" / f"{name}.py").read_text(encoding="utf-8"), name, "exec"), ns)
    return ns


def _records(df):
    return json.loads(df.to_json(orient="records", force_ascii=False))


def d4_1(con):
    ns = _solution_run("D4_1_serve_layer")
    save("d4_1_handshake", ns["hs"])
    save("d4_1_three_roles", _records(ns["seen"]))
    save("d4_1_raise", _records(ns["tries"]))
    save("d4_1_tests", _records(ns["tests"]))


def d4_2(con):
    ns = _solution_run("D4_2_safeguards")
    save("d4_2_cards", ns["cards"])
    save("d4_2_verdicts", ns["verdicts"])
    after = {}
    for variant, runs in [("full", (1, 2, 3)), ("no_descriptions", (1,))]:
        after[variant] = ns["D"].summary(ns["guarded_score"](variant, runs)).iloc[0].to_dict()
    save("d4_2_after", after)
    save("d4_2_refusals", ns["texts"])


def d4_3(con):
    ns = _solution_run("D4_3_routing_policy")
    save("d4_3_rates", _records(ns["rates"](ns["EVAL"])))
    save("d4_3_bounds", _records(ns["r"][["type", "upper"]]))
    save("d4_3_routes", _records(ns["policy"]))
    save("d4_3_record", ns["record"])


def d4_4(con):
    ns = _solution_run("D4_4_design_review")
    save("d4_4_eval_checks", ns["checks2"])
    save("d4_4_beyond", ns["extra"])
    save("d4_4_ranked", _records(ns["ranked"]))
    save("d4_4_log", _records(ns["log"]))


STEPS = {"d1_1": d1_1, "d1_2": d1_2, "d1_3": d1_3, "d1_4": d1_4, "d2_1": d2_1, "d2_2": d2_2, "d2_3": d2_3, "d2_4": d2_4,
         "d3_1": d3_1, "d3_2": d3_2, "d3_3": d3_3, "d3_4": d3_4, "d4_1": d4_1, "d4_2": d4_2, "d4_3": d4_3, "d4_4": d4_4}

if __name__ == "__main__":
    con = Q.db()
    for name, fn in STEPS.items():
        if len(sys.argv) == 1 or name in sys.argv[1:]:
            fn(con)
