# /// script
# requires-python = ">=3.11"
# dependencies = ["duckdb>=1.4", "pandas>=2.2", "pyyaml>=6.0"]
# ///
# %% [markdown]
# # Lab 1.2 · Five metrics as code, with reconciliation tests
#
# Day 1 · Session 2 (Metrics as code with tests) · 25 min. A metric is a file: a definition, an owner, a version,
# a status and tests. You write five of Qamar Telecom's metrics, two simple ones with a filter, the certified
# collection rate as a ratio and a fiscal-year-to-date cumulative, and prove each against an independent total
# from the marts.
#
# **AI-tutor.** An assistant may explain an error message; the definitions are yours.
#
# **Reference state.** The semantic model `data/semantic/qamar_model.yaml` and the metric files in
# `data/metrics/`, from which this lab removes the five metrics you write. `qsem.py` is the course's small
# semantic layer (a stand-in for MetricFlow or Cube).
#
# **Tasks**
# - [ ] 1 · Read one metric file (3')
# - [ ] 2 · Three simple metrics (7')
# - [ ] 3 · The ratio: a ratio of sums (6')
# - [ ] 4 · The cumulative metric (4')
# - [ ] 5 · Run the tests, then break one (5')
# - [ ] ✱ Stretch · A derived metric for the collection gap, with its test

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

import yaml
import qamar as Q
import qsem as S

con = Q.db()
MODEL = S.load_yaml("data/semantic/qamar_model.yaml")
FIVE = ["billed_amount", "net_due_30", "collected_30", "collection_rate", "cash_collected_fytd"]
ALL = S.load_metrics("data/metrics")
START = [m for m in ALL if m["name"] not in FIVE]
REFERENCE_FIVE = [m for m in ALL if m["name"] in FIVE]
print(len(START), "metrics in the starting state; you write", ", ".join(FIVE))

# %% [markdown]
# ## 1 · Read one metric file (3')
#
# `cash_collected` is already written. Read every key: which ones does the compiler use, which ones are for people
# (and for the assistant on Day 3)?

# %%
print(yaml.safe_dump(next(m for m in START if m["name"] == "cash_collected"), allow_unicode=True, sort_keys=False))

# %% [markdown]
# ## 2 · Three simple metrics (7')
#
# The datasets you need are `bill` (fields `amount_due`, `disputed_amount`) and `collection` (one row per bill with
# `net_due`, `paid_30` and the flag `matured_30`). Every metric carries `owner`, `version`, `status`,
# `description` and at least one `reconcile` test: a SQL query on the marts that returns the expected total.
#
# ✏️ **Exercise** · Write `billed_amount` (finance owns it), `net_due_30` and `collected_30` (collections owns
# them; matured cohorts only) as YAML.

# %%
def simple_metrics() -> list[dict]:
    # BEGIN SOLUTION
    text = """
- name: billed_amount
  label: Billed amount
  type: simple
  dataset: bill
  agg: sum
  expr: amount_due
  unit: SAR
  owner: Jood Al-Muhaisen
  version: 1.0.0
  status: certified
  description: Total amount on bills for the service month, VAT included, before disputes
  tests:
    - reconcile: "SELECT SUM(amount_due) FROM fct_bill"
- name: net_due_30
  label: Net amount due, matured cohorts
  type: simple
  dataset: collection
  agg: sum
  expr: net_due
  filter: matured_30
  unit: SAR
  owner: Majdi Bawazir
  version: 1.0.0
  status: certified
  description: Amount due minus disputed amounts, for bills whose due date plus 30 days has passed
  tests:
    - reconcile: "SELECT SUM(amount_due - disputed_amount) FROM fct_bill WHERE due_date + 30 <= DATE '2026-06-30'"
- name: collected_30
  label: Collected within 30 days of due date
  type: simple
  dataset: collection
  agg: sum
  expr: paid_30
  filter: matured_30
  unit: SAR
  owner: Majdi Bawazir
  version: 1.0.0
  status: certified
  description: Payments up to 30 days after the due date against the period's bills, deduplicated, matured cohorts
  tests:
    - reconcile: >-
        SELECT SUM(p.amount) FROM (SELECT DISTINCT bill_id, paid_date, amount, batch_id FROM fct_payment) p
        JOIN fct_bill b USING (bill_id) WHERE p.paid_date <= b.due_date + 30 AND b.due_date + 30 <= DATE '2026-06-30'
"""
    # END SOLUTION
    return yaml.safe_load(text)


# %%
try:
    mine = simple_metrics()
except NotImplementedError:
    mine = [m for m in REFERENCE_FIVE if m["name"] in ("billed_amount", "net_due_30", "collected_30")]
model = S.Model(S.with_metrics(dict(MODEL, metrics=START), mine), con)
print(model.query(["billed_amount", "net_due_30", "collected_30"], by=["time.fiscal_year"]).round(0).to_string(index=False))
Q.check({"billed_amount", "net_due_30", "collected_30"} <= set(model.metrics), "three simple metrics compile")

# %% [markdown]
# ## 3 · The ratio: a ratio of sums (6')
#
# A ratio metric divides two metrics **after** they are aggregated at the grain asked for. The tempting shortcut,
# averaging rates computed for parts, weights a small part like a large one.
#
# ✏️ **Exercise** · Write `collection_rate` as `type: ratio`. Then compare, for the fiscal year 2025-26, the
# metric's value with the plain average of its twelve monthly values and of its three segment values.

# %%
def ratio_metric() -> dict:
    # BEGIN SOLUTION
    return yaml.safe_load("""
name: collection_rate
label: Collection rate (certified)
type: ratio
numerator: collected_30
denominator: net_due_30
unit: ratio
owner: Majdi Bawazir
version: 1.0.0
status: certified
description: Share of the net amount due on the period's bills paid within 30 days of the due date (certified)
tests:
  - reconcile: >-
      SELECT (SELECT SUM(p.amount) FROM (SELECT DISTINCT bill_id, paid_date, amount, batch_id FROM fct_payment) p
              JOIN fct_bill b USING (bill_id) WHERE p.paid_date <= b.due_date + 30 AND b.due_date + 30 <= DATE '2026-06-30')
           / (SELECT SUM(amount_due - disputed_amount) FROM fct_bill WHERE due_date + 30 <= DATE '2026-06-30')
""")
    # END SOLUTION


# %%
try:
    mine_ratio = ratio_metric()
except NotImplementedError:
    mine_ratio = next(m for m in REFERENCE_FIVE if m["name"] == "collection_rate")
model = S.Model(S.with_metrics(model.doc, [mine_ratio]), con)
fy = ["time.fiscal_year = 'FY2025-26'"]
year_value = model.value("collection_rate", fy)
monthly = model.query(["collection_rate"], by=["time.month"], where=fy)
segments = model.query(["collection_rate", "net_due_30"], by=["customer.segment"], where=fy)
print(f"FY2025-26 ratio of sums {year_value:.4f}")
print(f"average of {len(monthly)} monthly rates {monthly.collection_rate.mean():.4f}  (months are of similar size)")
print(f"average of {len(segments)} segment rates {segments.collection_rate.mean():.4f}  (segments are not)")
print(segments.round(4).to_string(index=False))
Q.check(abs(year_value - Q.reference("d1_2_values")["collection_rate_fy2025"]) < 1e-6, "ratio of sums matches the reference")

# %% [markdown]
# 🔍 The monthly average is close because months are of similar size; the segment average is far off. Which
# segment does the plain average give too much weight to, and by how much?
#
# ## 4 · The cumulative metric (4')
#
# ✏️ **Exercise** · Write `cash_collected_fytd`: `type: cumulative` over the base metric `cash_collected`. The
# compiler restarts the sum at each fiscal year (April) and needs `time.month` in the group-by.

# %%
def cumulative_metric() -> dict:
    # BEGIN SOLUTION
    return {"name": "cash_collected_fytd", "label": "Cash collected, fiscal year to date", "type": "cumulative",
            "base": "cash_collected", "unit": "SAR", "owner": "Jood Al-Muhaisen", "version": "1.0.0",
            "status": "certified", "description": "Cash collected from April to the month shown"}
    # END SOLUTION


# %%
try:
    mine_cum = cumulative_metric()
except NotImplementedError:
    mine_cum = next(m for m in REFERENCE_FIVE if m["name"] == "cash_collected_fytd")
model = S.Model(S.with_metrics(model.doc, [mine_cum]), con)
fytd = model.query(["cash_collected", "cash_collected_fytd"], by=["time.month"])
print(fytd[fytd["time.month"].astype(str).between("2026-01-01", "2026-05-01")].round(0).to_string(index=False))
march = fytd.loc[fytd["time.month"].astype(str) == "2026-03-01", "cash_collected_fytd"].iloc[0]
raw = con.execute("""SELECT SUM(amount) FROM (SELECT DISTINCT bill_id, paid_date, amount, batch_id FROM fct_payment)
                     WHERE paid_date BETWEEN DATE '2025-04-01' AND DATE '2026-03-31'""").fetchone()[0]
Q.check(abs(march - raw) < 0.01, "March 2026 year to date equals April 2025 to March 2026 from the marts")

# %% [markdown]
# ## 5 · Run the tests, then break one (5')
#
# `S.run_tests` runs every `reconcile` test: the metric over all data against the test's SQL.
#
# ✏️ **Exercise** · Run the tests of the five metrics. Then copy `net_due_30`, drop its filter (as if someone
# forgot the maturity rule), and show that its test fails.

# %%
def tests_then_break(model):
    # BEGIN SOLUTION
    results = S.run_tests(model, FIVE)
    broken = dict(model.metrics["net_due_30"])
    broken.pop("filter")
    failing = S.run_tests(S.Model(S.with_metrics(model.doc, [broken]), con), ["net_due_30"])
    return results, failing
    # END SOLUTION


# %%
try:
    results, failing = tests_then_break(model)
except NotImplementedError:
    results, failing = S.run_tests(model, FIVE), None
print(results[["metric", "expected", "actual", "passed"]].round(2).to_string(index=False))
Q.check(results.passed.all() and len(results) >= 4, "every reconciliation test passes")
if failing is not None:
    print(failing[["metric", "expected", "actual", "passed"]].round(2).to_string(index=False))
    Q.check(not failing.passed.any(), "the test catches the dropped maturity filter")

# %% [markdown]
# ## ✱ Stretch · A derived metric for the collection gap
#
# Write `collection_gap = net_due_30 - collected_30` (SAR still owed after 30 days on matured bills), with a
# reconcile test, and show it by `customer.segment`.

# %%
def stretch():
    # BEGIN SOLUTION
    gap = {"name": "collection_gap", "type": "derived", "inputs": ["net_due_30", "collected_30"],
           "expr": "net_due_30 - collected_30", "unit": "SAR", "owner": "Majdi Bawazir", "version": "0.1.0",
           "status": "draft", "description": "Net amount still unpaid 30 days after the due date, matured cohorts",
           "tests": [{"reconcile": f"SELECT {S.run_tests(model, ['net_due_30']).expected.iloc[0]} - "
                                   f"{S.run_tests(model, ['collected_30']).expected.iloc[0]}"}]}
    m2 = S.Model(S.with_metrics(model.doc, [gap]), con)
    print(m2.query(["collection_gap", "collection_rate"], by=["customer.segment"]).round(3).to_string(index=False))
    print(S.run_tests(m2, ["collection_gap"])[["metric", "passed"]])
    # END SOLUTION


try:
    stretch()
except NotImplementedError:
    print("✱ Stretch not attempted")

# %% [markdown]
# ## Checkpoint
#
# 1. Why does `collection_rate` have no `dataset` of its own?
#
# <details><summary>Answer</summary>A ratio is computed from two metrics after each is aggregated; it inherits their
# datasets and filters, so a fix to either one reaches the ratio.</details>
#
# 2. A test compares the metric with SQL written by the same person. What makes it still worth having?
#
# <details><summary>Answer</summary>It is written against the marts, not through the semantic layer, so it catches
# a wrong join, a lost filter or a compiler change; and it keeps catching them after the author has left.</details>
#
# 3. Why must `cash_collected_fytd` be asked with `time.month` in the group-by?
#
# <details><summary>Answer</summary>"To date" needs an order in time; without months there is nothing to accumulate
# over, and the compiler refuses rather than guess.</details>
#
# **Carry forward.** Lab 1.3 starts from the supplied `data/metrics/`, which hold these five definitions.
