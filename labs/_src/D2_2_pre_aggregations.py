# /// script
# requires-python = ">=3.11"
# dependencies = ["duckdb>=1.4", "pandas>=2.2", "pyyaml>=6.0"]
# ///
# %% [markdown]
# # Lab 2.2 · Ten pre-aggregations, measured
#
# Day 2 · Session 2 (Performance and cost) · 25 min. Most questions managers ask read the session table, about 2.8
# million rows. You find the ten most-asked patterns in a month of the query log, measure them, add
# pre-aggregations the layer routes to by itself, measure again, and check that no answer changed. One metric
# refuses to roll up: you find out why.
#
# **AI-tutor.** An assistant may help with pandas; the choice of pre-aggregations is yours.
#
# **Reference state.** `data/semantic/qamar_model.yaml`, `data/metrics/`, the session table built in memory by
# `qamar.usage_events` (one line in eight in quick mode), and `data/semantic/query_log.csv` (400 queries).
#
# **Tasks**
# - [ ] 1 · The ten most-asked patterns (5')
# - [ ] 2 · Baseline latency and rows scanned (5')
# - [ ] 3 · Define the pre-aggregations (7')
# - [ ] 4 · Measure again, compare the answers (5')
# - [ ] 5 · The metric that cannot roll up (3')
# - [ ] ✱ Stretch · Which pre-aggregations to rebuild when late payments arrive

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

con = Q.db(events=True)
model = S.Model.load("data/semantic/qamar_model.yaml", con, metrics_dir="data/metrics")
LOG = pd.read_csv("data/semantic/query_log.csv")
print(f"session table: {con.execute('SELECT count(*) FROM fct_usage_event').fetchone()[0]:,} rows"
      f"{' (quick mode)' if Q.QUICK else ''} | query log: {len(LOG)} queries")
LOG.head()

# %% [markdown]
# ## 1 · The ten most-asked patterns (5')
#
# A pattern is a set of metrics and a set of group-by fields (filters change; the shape does not).
#
# ✏️ **Exercise** · Return the ten most frequent patterns as a DataFrame with `metrics` and `by` (lists) and `n`.

# %%
def top_patterns(log: pd.DataFrame, k: int = 10) -> pd.DataFrame:
    # BEGIN SOLUTION
    top = log.groupby(["metrics", "group_by"]).size().rename("n").reset_index().sort_values("n", ascending=False).head(k)
    return pd.DataFrame({"metrics": top.metrics.str.split("|"), "by": top.group_by.str.split("|"), "n": top.n}).reset_index(drop=True)
    # END SOLUTION


# %%
try:
    TOP = top_patterns(LOG)
except NotImplementedError:
    TOP = pd.DataFrame(Q.reference("d2_2_top"))
print(TOP.to_string())
print(f"the ten patterns are {TOP.n.sum() / len(LOG):.0%} of the month's queries")
Q.check(len(TOP) == 10 and TOP.n.iloc[0] == Q.reference("d2_2_top")[0]["n"], "ten patterns, most frequent first")

# %% [markdown]
# ## 2 · Baseline latency and rows scanned (5')
#
# Latency depends on your machine; rows scanned does not. `model.plan(...)` says which table each part of a query
# reads and how many rows it has.

# %%
def measure(model) -> pd.DataFrame:
    rows = []
    for i, p in TOP.iterrows():
        ms = Q.timed(lambda: model.query(p.metrics, by=p.by))
        plan = model.plan(p.metrics, by=p.by)
        rows.append({"pattern": i, "metrics": ",".join(p.metrics), "by": ",".join(p.by), "ms": ms,
                     "rows_scanned": sum(x["rows"] for x in plan), "reads": ",".join(sorted({x["reads"] for x in plan}))})
    return pd.DataFrame(rows)


answers_before = {i: model.query(p.metrics, by=p.by) for i, p in TOP.iterrows()}
before = measure(model)
print(before.to_string(index=False))
print(f"total {before.ms.sum():.0f} ms, {before.rows_scanned.sum():,} rows scanned")

# %% [markdown]
# ## 3 · Define the pre-aggregations (7')
#
# A pre-aggregation is a table of additive measures (sums and counts) grouped by a set of fields. The layer reads
# it instead of the session table when the query's group-by and filters are all among its fields. Fewer, coarser
# pre-aggregations cost less to keep fresh; more, finer ones answer faster.
#
# ✏️ **Exercise** · Return a list of pre-aggregations (`name`, `dataset`, `measures`, `by`) that serves the ten
# patterns. Keep it to four or fewer.

# %%
def preaggs() -> list[dict]:
    # BEGIN SOLUTION
    m = ["session_data_gb", "sessions", "call_minutes"]
    return [
        {"name": "usage_region_month", "dataset": "usage_event", "measures": m,
         "by": ["customer.region", "customer.segment", "usage_event.kind", "time.month", "time.fiscal_year"]},
        {"name": "usage_plan_quarter", "dataset": "usage_event", "measures": m,
         "by": ["tariff.plan_name", "time.fiscal_quarter"]},
        {"name": "usage_day", "dataset": "usage_event", "measures": m, "by": ["time.day"]},
        {"name": "usage_city", "dataset": "usage_event", "measures": m, "by": ["customer.city"]},
    ]
    # END SOLUTION


# %%
try:
    PRE = preaggs()
except NotImplementedError:
    PRE = Q.reference("d2_2_preaggs")
built = model.materialize(PRE)
print("pre-aggregation rows:", built)
Q.check(len(PRE) <= 4, "four pre-aggregations or fewer")

# %% [markdown]
# ## 4 · Measure again, compare the answers (5')
#
# ✏️ **Exercise** · Measure the ten patterns again, and check that each answer equals the answer before (to a
# rounding tolerance). Return the comparison table.

# %%
def compare(model) -> pd.DataFrame:
    # BEGIN SOLUTION
    after = measure(model)
    same = []
    for i, p in TOP.iterrows():
        a, b = answers_before[i], model.query(p.metrics, by=p.by)
        num = a.select_dtypes("number").columns
        same.append(len(a) == len(b) and bool(((a[num] - b[num]).abs() < 1e-6 * (1 + a[num].abs())).all().all()))
    t = before[["pattern", "metrics", "by", "ms", "rows_scanned"]].merge(
        after[["pattern", "ms", "rows_scanned", "reads"]], on="pattern", suffixes=("_before", "_after"))
    t["same_answer"] = same
    return t
    # END SOLUTION


# %%
try:
    cmp = compare(model)
except NotImplementedError:
    cmp = before.assign(same_answer=True)
print(cmp.drop(columns=["metrics"]).to_string(index=False))
if "ms_after" in cmp:
    print(f"total latency {cmp.ms_before.sum():.0f} ms -> {cmp.ms_after.sum():.0f} ms | rows scanned "
          f"{cmp.rows_scanned_before.sum():,} -> {cmp.rows_scanned_after.sum():,}")
Q.check(bool(cmp.same_answer.all()), "every answer is unchanged")

# %% [markdown]
# 🔍 One pattern still reads `usage_event`. Which, and why did no pre-aggregation take it?
#
# ## 5 · The metric that cannot roll up (3')
#
# ✏️ **Exercise** · Try to add `lines_with_sessions` to a pre-aggregation and read the error. Then show why: compare
# the distinct lines of the fiscal year with the sum of the twelve monthly distinct counts.

# %%
def cannot_roll_up(model) -> dict:
    # BEGIN SOLUTION
    try:
        model.materialize([{"name": "bad", "dataset": "usage_event", "measures": ["lines_with_sessions"], "by": ["time.month"]}])
        err = None
    except S.SemanticError as e:
        err = str(e)
    fy = ["time.fiscal_year = 'FY2025-26'"]
    year = model.value("lines_with_sessions", fy)
    months = model.query(["lines_with_sessions"], by=["time.month"], where=fy).lines_with_sessions.sum()
    return {"error": err, "fy_distinct_lines": int(year), "sum_of_monthly": int(months)}
    # END SOLUTION


# %%
try:
    r = cannot_roll_up(model)
except NotImplementedError:
    r = {"error": "lines_with_sessions cannot roll up from a pre-aggregation (not a sum or count)"}
print(r)
Q.check("cannot roll up" in (r["error"] or ""), "the layer refuses to pre-aggregate a distinct count")

# %% [markdown]
# ## ✱ Stretch · Late payments arrive
#
# Pre-aggregations are copies; copies go stale. Suppose 40 late payments for May bills are loaded on 2 July.
# Which tables of this lab, and which metrics of the model, must be rebuilt? Write the rule as a function of the
# dataset that changed.

# %%
def stretch():
    # BEGIN SOLUTION
    def to_rebuild(changed_dataset: str) -> dict:
        pre = [p["name"] for p in PRE if p["dataset"] == changed_dataset]
        mets = [n for n, m in model.metrics.items() if m.get("dataset") == changed_dataset]
        return {"pre_aggregations": pre, "metrics_affected": mets}
    print("payment:", to_rebuild("payment"))
    print("collection:", to_rebuild("collection"))
    print("usage_event:", to_rebuild("usage_event"))
    # END SOLUTION


try:
    stretch()
except NotImplementedError:
    print("✱ Stretch not attempted")

# %% [markdown]
# ## Checkpoint
#
# 1. Why does `rows_scanned` belong in the report even though latency is what people feel?
#
# <details><summary>Answer</summary>It does not depend on the machine or the cache, so it compares runs fairly and
# predicts cost on a warehouse that bills by data scanned.</details>
#
# 2. A query filters on `customer.city` and groups by `time.month`. Which pre-aggregation serves it?
#
# <details><summary>Answer</summary>None: no pre-aggregation has both fields, so the layer falls back to the session
# table. That is correct, not a failure.</details>
#
# 3. Why can a ratio such as data per line use a pre-aggregation for its numerator but not its denominator here?
#
# <details><summary>Answer</summary>The numerator is a sum and rolls up; the denominator is a distinct count of lines,
# which double counts lines active in several months.</details>
#
# **Carry forward.** Nothing: Lab 2.3 starts from the supplied model.
