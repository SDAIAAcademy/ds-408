"""Write data/reference/*.json: the reference results the labs' safety nets fall back on.

    uv run python _tools/make_reference.py

Computed from the marts with plain SQL, not with the lab solutions, so a solution run that matches
them is an independent check. Run after prepare_data.py.
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
    (OUT / f"{name}.json").write_text(json.dumps(obj, indent=1, ensure_ascii=False, default=str) + "\n", encoding="utf-8")
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


STEPS = {"d1_1": d1_1, "d1_2": d1_2, "d1_3": d1_3, "d1_4": d1_4}

if __name__ == "__main__":
    con = Q.db()
    for name, fn in STEPS.items():
        if len(sys.argv) == 1 or name in sys.argv[1:]:
            fn(con)
