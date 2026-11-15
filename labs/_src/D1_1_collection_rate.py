# /// script
# requires-python = ">=3.11"
# dependencies = ["duckdb>=1.4", "pandas>=2.2", "pyyaml>=6.0"]
# ///
# %% [markdown]
# # Lab 1.1 · One collection rate, three owners
#
# Day 1 · Session 1 (One metric, three owners) · 25 min. Finance, collections and customer care each report
# "the collection rate" for March 2026, and the three numbers disagree. You compute all three from the marts,
# find the data error under one of them, walk from one figure to another one difference at a time, and write
# the definition the metrics council certifies.
#
# **AI-off.** This lab is done without an assistant: the reconciliation is the skill being assessed.
#
# **Reference state.** The marts in `data/marts/` and the three definitions in
# `data/definitions/collection_rate_three.yaml`.
#
# **Tasks**
# - [ ] 1 · Three rates for March 2026 (8')
# - [ ] 2 · The payment batch loaded twice (5')
# - [ ] 3 · Walk from the finance figure to the collections figure (7')
# - [ ] 4 · The certified definition (5')
# - [ ] ✱ Stretch · The government segment under each definition

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

import qamar as Q
con = Q.db()
DEFS = Q.yaml_load("data/definitions/collection_rate_three.yaml")
for k in ("finance", "collections", "care"):
    print(f"{k:12s} {DEFS[k]['owner']}\n             {DEFS[k]['definition']}")

# %% [markdown]
# ## 1 · Three rates for March 2026 (8')
#
# The service month is March 2026 (`bill_month = DATE '2026-03-01'`). Bills for March are issued on 3 April and
# due 21 days later. Payments are in `fct_payment` as loaded.
#
# ✏️ **Exercise** · Write one SQL query per definition. Return a dict `{"finance": …, "collections": …, "care": …}`
# of rates between 0 and 1.

# %%
MONTH = "DATE '2026-03-01'"


def three_rates(con) -> dict:
    # BEGIN SOLUTION
    finance = con.execute(f"""
        SELECT (SELECT SUM(amount) FROM fct_payment WHERE date_trunc('month', paid_date) = {MONTH})
             / (SELECT SUM(amount_due) FROM fct_bill WHERE bill_month = {MONTH})""").fetchone()[0]
    collections = con.execute(f"""
        WITH b AS (SELECT * FROM fct_bill WHERE bill_month = {MONTH})
        SELECT (SELECT SUM(p.amount) FROM fct_payment p JOIN b USING (bill_id) WHERE p.paid_date <= b.due_date + 60)
             / (SELECT SUM(amount_due - disputed_amount) FROM b)""").fetchone()[0]
    care = con.execute(f"""
        WITH b AS (SELECT * FROM fct_bill WHERE bill_month = {MONTH}),
        paid AS (SELECT b.bill_id, b.amount_due - b.disputed_amount AS net,
                        coalesce(SUM(p.amount) FILTER (WHERE p.paid_date <= b.due_date), 0) AS by_due
                 FROM b LEFT JOIN fct_payment p USING (bill_id) GROUP BY ALL)
        SELECT AVG(CASE WHEN by_due >= net - 0.01 THEN 1 ELSE 0 END) FROM paid""").fetchone()[0]
    return {"finance": float(finance), "collections": float(collections), "care": float(care)}
    # END SOLUTION


# %%
# Check, with a safety net: the cells below still run when the exercise is not done yet
try:
    rates = three_rates(con)
except NotImplementedError:
    rates = Q.reference("d1_1_rates")
ref = Q.reference("d1_1_rates")
for k, v in rates.items():
    print(f"{k:12s} {v:.4f}   reference {ref[k]:.4f}")
Q.check(all(abs(rates[k] - ref[k]) < 5e-4 for k in rates), "three rates match the reference")

# %% [markdown]
# 🔍 Three numbers for one name, and the care figure is not even in the same unit. Which one would the board
# read as "how much of what we billed did we collect"?
#
# ## 2 · The payment batch loaded twice (5')
#
# A batch is identified by `batch_id`; `load_no` says which load wrote the row. A payment is the same payment when
# bill, day, amount and batch are the same.
#
# ✏️ **Exercise** · Find the batch whose payments appear twice, the amount it adds, and the finance rate without it.

# %%
def duplicated_batch(con) -> dict:
    # BEGIN SOLUTION
    dup = con.execute("""
        SELECT batch_id, COUNT(*) - COUNT(DISTINCT (bill_id, paid_date, amount)) AS extra_rows,
               SUM(amount) FILTER (WHERE load_no > 1) AS extra_amount
        FROM fct_payment GROUP BY batch_id HAVING extra_rows > 0""").df()
    row = dup.iloc[0]
    fin = con.execute(f"""
        SELECT (SELECT SUM(amount) FROM fct_payment WHERE date_trunc('month', paid_date) = {MONTH} AND load_no = 1)
             / (SELECT SUM(amount_due) FROM fct_bill WHERE bill_month = {MONTH})""").fetchone()[0]
    return {"batch_id": row.batch_id, "extra_rows": int(row.extra_rows), "extra_amount": round(float(row.extra_amount), 2),
            "finance_without_duplicates": float(fin)}
    # END SOLUTION


# %%
try:
    dup = duplicated_batch(con)
except NotImplementedError:
    dup = Q.reference("d1_1_duplicate")
print(dup)
Q.check(dup["batch_id"] == Q.reference("d1_1_duplicate")["batch_id"], "the duplicated batch is found")

# %% [markdown]
# ## 3 · Walk from the finance figure to the collections figure (7')
#
# A walk (a bridge) changes one thing at a time and records the rate after each change. Each step is a
# difference in the definitions, so each step is a decision the council can take separately.
#
# ✏️ **Exercise** · Fill `walk` with five rows, in this order: the finance figure as reported; without the
# duplicated batch; cohort basis (payments against March bills within 60 days of due, over the gross amount due);
# disputed amounts out of the denominator (this is the collections figure); the window shortened to 30 days.

# %%
def cohort_rate(con, window: int, net: bool) -> float:
    den = "amount_due - disputed_amount" if net else "amount_due"
    return float(con.execute(f"""
        WITH b AS (SELECT * FROM fct_bill WHERE bill_month = {MONTH}),
        p AS (SELECT * FROM fct_payment WHERE load_no = 1)
        SELECT (SELECT SUM(p.amount) FROM p JOIN b USING (bill_id) WHERE p.paid_date <= b.due_date + {window})
             / (SELECT SUM({den}) FROM b)""").fetchone()[0])


def walk_rows(con, rates, dup) -> list[dict]:
    # BEGIN SOLUTION
    return [
        {"step": "Finance as reported", "rate": rates["finance"]},
        {"step": "Remove the duplicated batch", "rate": dup["finance_without_duplicates"]},
        {"step": "Cohort: March bills, 60 days, gross", "rate": cohort_rate(con, 60, net=False)},
        {"step": "Disputes out of the denominator", "rate": cohort_rate(con, 60, net=True)},
        {"step": "Window 30 days", "rate": cohort_rate(con, 30, net=True)},
    ]
    # END SOLUTION


# %%
import pandas as pd

try:
    walk = pd.DataFrame(walk_rows(con, rates, dup))
except NotImplementedError:
    walk = pd.DataFrame(Q.reference("d1_1_walk"))
walk["change"] = walk.rate.diff().round(4)
print(walk.round(4).to_string(index=False))
Q.check(abs(walk.rate.iloc[3] - rates["collections"]) < 5e-4, "the walk lands on the collections figure")

# %% [markdown]
# 🔍 Which step moves the figure most? Is that step a definition choice or a data error?
#
# ## 4 · The certified definition (5')
#
# Read the council's five criteria in `DEFS["council"]`. Each criterion settles one choice of the walk.
#
# ✏️ **Exercise** · Fill `certified` with the choices the criteria lead to, then compute its value for March 2026.

# %%
for c in DEFS["council"]:
    print("-", c)


def certified_definition() -> dict:
    # BEGIN SOLUTION
    return {"name": "collection_rate", "owner": "Majdi Bawazir", "approver": "Jood Al-Muhaisen",
            "basis": "value", "population": "bills of the service month (cohort)", "window_days_after_due": 30,
            "disputes": "excluded from the denominator until decided", "duplicates": "removed in the data",
            "maturity": "reported once due date plus window has passed"}
    # END SOLUTION


# %%
try:
    certified = certified_definition()
except NotImplementedError:
    certified = Q.reference("d1_1_certified")
value = cohort_rate(con, certified["window_days_after_due"], net="excluded" in certified["disputes"])
print(Q.yaml_dump(certified))
print(f"certified collection rate, March 2026: {value:.4f}")
Q.check(certified["basis"] == "value" and certified["window_days_after_due"] == 30, "value basis, 30-day window")
Q.check(abs(value - Q.reference("d1_1_rates")["certified"]) < 5e-4, "the certified value matches the reference")
Q.yaml_dump(certified, Q.lab_dir("D1_1") / "collection_rate_certified.yaml")

# %% [markdown]
# ## ✱ Stretch · The government segment under each definition
#
# Government accounts pay late in the quarter. Compute the collections figure (60 days) and the certified figure
# (30 days) for government bills of March 2026. Which definition would the government account team prefer, and
# why must the council not let that decide?

# %%
def stretch():
    # BEGIN SOLUTION
    gov = con.execute(f"""
        WITH b AS (SELECT b.* FROM fct_bill b JOIN dim_customer c USING (customer_id)
                   WHERE bill_month = {MONTH} AND c.segment = 'government'),
        p AS (SELECT * FROM fct_payment WHERE load_no = 1)
        SELECT w, (SELECT SUM(p.amount) FROM p JOIN b USING (bill_id) WHERE p.paid_date <= b.due_date + w)
                  / (SELECT SUM(amount_due - disputed_amount) FROM b) AS rate
        FROM (VALUES (30), (60)) t(w)""").df()
    print(gov.round(4).to_string(index=False))
    # END SOLUTION


try:
    stretch()
except NotImplementedError:
    print("✱ Stretch not attempted")

# %% [markdown]
# ## Checkpoint
#
# 1. Which step of the walk was a data error rather than a definition choice, and where should it be fixed?
#
# <details><summary>Answer</summary>The duplicated batch. It is fixed once in the data (the payment mart), so every
# metric built on payments is right, not in one report's formula.</details>
#
# 2. Why is the care figure not on the walk?
#
# <details><summary>Answer</summary>It counts bills, not value. It answers another question (how many customers pay
# on time) and deserves its own name.</details>
#
# 3. Why can the certified rate not be reported yet for May 2026 bills?
#
# <details><summary>Answer</summary>Their due date plus 30 days falls after the data cut-off: the cohort has not
# matured, and a partial window would look like a collapse.</details>
#
# **Carry forward.** `artifacts/D1_1/collection_rate_certified.yaml`. Lab 1.2 starts from the supplied metric files,
# which already hold this definition.
