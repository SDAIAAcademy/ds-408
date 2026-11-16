# /// script
# requires-python = ">=3.11"
# dependencies = ["duckdb>=1.4", "pandas>=2.2", "pyyaml>=6.0"]
# ///
# %% [markdown]
# # Lab 2.1 · Four areas, one customer, one calendar
#
# Day 2 · Session 1 (Conformed dimensions across areas) · 25 min. A manager asks for billing and complaints by
# region and month in one table. You see what a wide join does to both numbers, conform the complaint area to the
# shared customer and calendar so the layer can drill across, join the tariff history as of each month, and prove
# the model against source totals.
#
# **AI-tutor.** An assistant may explain a join; the model is yours.
#
# **Reference state.** `data/semantic/model_starter.yaml`: usage, billing and collections are conformed; the
# complaint dataset has no calendar and no join to the customer, and the tariff join has no validity dates.
# The finished model is `data/semantic/qamar_model.yaml`.
#
# **Tasks**
# - [ ] 1 · Read the starter model (4')
# - [ ] 2 · The wide query and its fan-out (6')
# - [ ] 3 · Drill across instead (6')
# - [ ] 4 · Tariff history as of the month (5')
# - [ ] 5 · Reconcile four areas to the source (4')
# - [ ] ✱ Stretch · The same figure by Hijri month and by fiscal quarter

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

import copy
import qamar as Q
import qsem as S

con = Q.db()
METRICS = S.load_metrics("data/metrics")
STARTER = S.load_yaml("data/semantic/model_starter.yaml")
TRUTH = con.execute("""SELECT (SELECT SUM(amount_due) FROM fct_bill) AS billed, (SELECT COUNT(*) FROM fct_complaint) AS complaints,
                              (SELECT SUM(data_gb) FROM fct_usage_monthly) AS data_gb""").df().iloc[0]
print(TRUTH.to_string())

# %% [markdown]
# ## 1 · Read the starter model (4')
#
# Each dataset lists its fields, its `time` field (joined to the shared calendar `time`) and its many-to-one
# `joins`. Ask the starter for complaints by region and read the error.

# %%
starter = S.Model(S.with_metrics(STARTER, METRICS), con)
for d in STARTER["datasets"]:
    print(f"{d['name']:12s} time={d.get('time', '-'):12s} joins={[j['to'] for j in d.get('joins', [])]}")
try:
    starter.query(["complaints"], by=["customer.region"])
except S.SemanticError as e:
    print("\nstarter refuses:", e)

# %% [markdown]
# ## 2 · The wide query and its fan-out (6')
#
# Before a semantic layer, the analyst writes one wide query: customers joined to their bills and to their
# complaints, then grouped.
#
# ✏️ **Exercise** · Run `WIDE` and return how many times too large each total is (`billed_factor`,
# `complaints_factor`) compared with `TRUTH`.

# %%
WIDE = """
SELECT c.region_code AS region, SUM(b.amount_due) AS billed, COUNT(q.complaint_id) AS complaints
FROM dim_customer c
JOIN fct_bill b USING (customer_id)
LEFT JOIN fct_complaint q USING (customer_id)
GROUP BY 1 ORDER BY 1"""


def fan_out(con) -> dict:
    # BEGIN SOLUTION
    wide = con.execute(WIDE).df()
    return {"billed_factor": round(float(wide.billed.sum() / TRUTH.billed), 2),
            "complaints_factor": round(float(wide.complaints.sum() / TRUTH.complaints), 2)}
    # END SOLUTION


# %%
try:
    fo = fan_out(con)
except NotImplementedError:
    fo = Q.reference("d2_1_fan_out")
print(con.execute(WIDE).df().to_string(index=False))
print(fo)
Q.check(fo["billed_factor"] > 1.2 and fo["complaints_factor"] > 5, "the wide join multiplies both totals")

# %% [markdown]
# 🔍 Each bill row is repeated once per complaint of its customer, and each complaint once per bill. Which total
# is hurt more, and why? A `DISTINCT` would not save the sum of amounts: why not?
#
# ## 3 · Drill across instead (6')
#
# The layer aggregates each metric on its own dataset, then joins the results on the shared keys. For that, the
# complaint dataset must reach the conformed customer and the calendar.
#
# ✏️ **Exercise** · Return a copy of the model in which `complaint` has `time: opened_date` and a many-to-one join
# to `customer` on `customer_id`.

# %%
def conform(doc: dict) -> dict:
    # BEGIN SOLUTION
    doc = copy.deepcopy(doc)
    comp = next(d for d in doc["datasets"] if d["name"] == "complaint")
    comp["time"] = "opened_date"
    comp["joins"] = [{"to": "customer", "keys": [["customer_id", "customer_id"]]}]
    return doc
    # END SOLUTION


# %%
try:
    doc = conform(STARTER)
except NotImplementedError:
    doc = Q.reference("d2_1_conformed")
model = S.Model(S.with_metrics(doc, METRICS), con)
across = model.query(["billed_amount", "complaints"], by=["customer.region"])
print(across.to_string(index=False))
print(model.sql(["billed_amount", "complaints"], by=["customer.region"]).split("SELECT customer__region")[0][:400], "...")
Q.check(abs(across.billed_amount.sum() - TRUTH.billed) < 0.01 and across.complaints.sum() == TRUTH.complaints,
        "drill-across keeps both totals")
monthly = model.query(["billed_amount", "complaints", "complaints_per_1k_lines"], by=["time.month"], where=["customer.region = 'EAS'"])
print(monthly[monthly["time.month"].astype(str).between("2025-11-01", "2026-02-01")].round(1).to_string(index=False))

# %% [markdown]
# 🔍 January 2026 in the Eastern region stands out. Which business area would you ask first, and which field of
# the complaint would you group by next?
#
# ## 4 · Tariff history as of the month (5')
#
# Two plans changed price on 1 October 2025, so `dim_tariff` has two rows for each of them. A join on the tariff
# code alone gives a line two plans' worth of rows.
#
# ✏️ **Exercise** · Show the fan-out (data by plan from the current model, against the source total), then return a
# model whose `line` to `tariff` join has `asof: [valid_from, valid_to]`, so the row valid in the usage month is
# chosen.

# %%
def tariff_as_of(doc: dict) -> dict:
    # BEGIN SOLUTION
    doc = copy.deepcopy(doc)
    line = next(d for d in doc["datasets"] if d["name"] == "line")
    for j in line["joins"]:
        if j["to"] == "tariff":
            j["asof"] = ["valid_from", "valid_to"]
    return doc
    # END SOLUTION


# %%
before = model.query(["data_gb"], by=["tariff.plan_name"]).data_gb.sum()
try:
    doc = tariff_as_of(doc)
except NotImplementedError:
    doc = Q.reference("d2_1_model")
model = S.Model(S.with_metrics(doc, METRICS), con)
by_plan = model.query(["data_gb", "active_lines"], by=["tariff.plan_name", "tariff.monthly_fee"], where=["time.month IN (DATE '2025-09-01', DATE '2025-10-01')"])
after = model.query(["data_gb"], by=["tariff.plan_name"]).data_gb.sum()
print(f"data by plan, summed: {before:,.0f} GB before, {after:,.0f} GB after; source {TRUTH.data_gb:,.0f} GB")
print(by_plan[by_plan["tariff.plan_name"].isin(["Qamar Postpaid M", "Qamar Fibre 100"])].round(0).to_string(index=False))
Q.check(abs(after - TRUTH.data_gb) < 0.01 < before - TRUTH.data_gb, "as-of join removes the tariff fan-out")

# %% [markdown]
# ## 5 · Reconcile four areas to the source (4')
#
# ✏️ **Exercise** · Run the reconciliation tests of one metric per area, and add two checks of your own: the
# regions add up to the total for `billed_amount`, and the plans add up to the total for `data_gb`.

# %%
def reconcile(model) -> dict:
    # BEGIN SOLUTION
    tests = S.run_tests(model, ["data_gb", "billed_amount", "collection_rate", "complaints"])
    regions = abs(model.query(["billed_amount"], by=["customer.region"]).billed_amount.sum() - TRUTH.billed) < 0.01
    plans = abs(model.query(["data_gb"], by=["tariff.plan_name"]).data_gb.sum() - TRUTH.data_gb) < 0.01
    return {"tests_passed": bool(tests.passed.all()), "n_tests": len(tests), "regions_add_up": bool(regions),
            "plans_add_up": bool(plans)}
    # END SOLUTION


# %%
try:
    rec = reconcile(model)
except NotImplementedError:
    rec = {"tests_passed": bool(S.run_tests(model, ["data_gb", "billed_amount", "collection_rate", "complaints"]).passed.all()),
           "n_tests": 4, "regions_add_up": True, "plans_add_up": True}
print(rec)
Q.check(rec["tests_passed"] and rec["regions_add_up"] and rec["plans_add_up"], "four areas reconcile to the source")
Q.yaml_dump(doc, Q.lab_dir("D2_1") / "qamar_model.yaml")

# %% [markdown]
# ## ✱ Stretch · The same figure by Hijri month and by fiscal quarter
#
# Ask `billed_amount` and `complaints` by `time.hijri_month` for the Hijri year 1447 and by `time.fiscal_quarter` for
# FY2025-26. Why does a Hijri month never line up with a service month?

# %%
def stretch():
    # BEGIN SOLUTION
    print(model.query(["billed_amount", "complaints"], by=["time.hijri_month"], where=["time.hijri_year = 1447"]).head(10).round(0).to_string(index=False))
    print(model.query(["billed_amount", "complaints"], by=["time.fiscal_quarter"], where=["time.fiscal_year = 'FY2025-26'"]).round(0).to_string(index=False))
    # END SOLUTION


try:
    stretch()
except NotImplementedError:
    print("✱ Stretch not attempted")

# %% [markdown]
# ## Checkpoint
#
# 1. Why is a drill-across safe where the wide join was not?
#
# <details><summary>Answer</summary>Each metric is aggregated at the asked grain on its own dataset first; the join
# then matches one row per key on each side, so nothing is repeated.</details>
#
# 2. What makes `customer` and `time` "conformed"?
#
# <details><summary>Answer</summary>Every area reaches the same customer and calendar rows, with the same keys and
# labels, so "Eastern, January 2026" means the same thing in billing and in complaints.</details>
#
# 3. Bills are dated by service month on the first of the month. What does grouping bills by Hijri month mean?
#
# <details><summary>Answer</summary>It places each service month in the Hijri month of its first day, which is a
# labelling choice, not a measurement; say so in the metric's description.</details>
#
# **Carry forward.** `artifacts/D2_1/qamar_model.yaml`. Labs 2.2 to 2.4 start from the supplied
# `data/semantic/qamar_model.yaml`, which is the same model.
