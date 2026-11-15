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


# ---------------------------------------------------------------------------------- main
STEPS = {"catalogue": catalogue}

if __name__ == "__main__":
    for name, fn in STEPS.items():
        if len(sys.argv) == 1 or name in sys.argv[1:]:
            fn()
