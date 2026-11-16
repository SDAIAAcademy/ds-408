# /// script
# requires-python = ">=3.11"
# dependencies = ["duckdb>=1.4", "pandas>=2.2", "pyyaml>=6.0"]
# ///
# %% [markdown]
# # Lab 2.4 · Export to Ossie, query from SQLite
#
# Day 2 · Session 4 (Portability) · 25 min. Qamar Telecom does not want its metric definitions locked into one
# tool. You export the semantic model to an Apache Ossie document, check it, compile three metrics from the
# document for a second engine (SQLite, in Python's standard library), compare with DuckDB, and fix the
# expressions that did not port. Then you list what did not travel at all.
#
# **AI-tutor.** An assistant may explain SQL dialect differences; the export is yours.
#
# **Reference state.** `data/semantic/qamar_model.yaml`, `data/metrics/`, and `qossie.py` (export of datasets and
# relationships, structural checks, a SQLite copy of the sources and a small compiler for Ossie metrics).
#
# **Tasks**
# - [ ] 1 · Export the model (6')
# - [ ] 2 · Check the document (4')
# - [ ] 3 · Compile three metrics for SQLite (6')
# - [ ] 4 · Compare and fix the expressions that did not port (6')
# - [ ] 5 · What did not travel (3')
# - [ ] ✱ Stretch · Round trip: read the document back into the layer

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
import re
import pandas as pd
import qamar as Q
import qsem as S
import qossie as O

con = Q.db()
model = S.Model.load("data/semantic/qamar_model.yaml", con, metrics_dir="data/metrics")
FIELDS = {d["name"]: {f["name"] for f in d["fields"]} for d in model.doc["datasets"]}
THREE = [("billed_amount", ["bill.service_month"]), ("collection_rate", ["customer.segment"]), ("complaints", ["complaint.region"])]

# %% [markdown]
# ## 1 · Export the model (6')
#
# `O.export_datasets` writes the datasets, fields and relationships. Metrics are yours. An Ossie model-scoped
# metric is one SQL aggregate over `dataset.field` names; there are no metric types.
#
# ✏️ **Exercise** · Write `metric_to_ossie(m)` for the layer's metric types: simple (with a filter, use
# `CASE WHEN … THEN … END` inside the aggregate), ratio and derived (substitute the input metrics' SQL). Return
# `None` for a cumulative metric: the core has no window over time. Keep owner, version and status in a
# `nonportable_extensions` entry.

# %%
def metric_to_ossie(m: dict, metrics: dict) -> dict | None:
    # BEGIN SOLUTION
    def sql(name):
        x = metrics[name]
        t = x.get("type", "simple")
        if t == "simple":
            ds, f = x["dataset"], FIELDS[x["dataset"]]
            expr = O.qualify(x["expr"], ds, f)
            if x.get("filter"):
                expr = f"CASE WHEN {O.qualify(x['filter'], ds, f)} THEN {expr} END"
            agg = x["agg"].lower()
            return f"COUNT(DISTINCT {expr})" if agg == "count_distinct" else f"{agg.upper()}({expr})"
        if t == "ratio":
            return f"({sql(x['numerator'])}) * 1.0 / ({sql(x['denominator'])})"
        if t == "derived":
            e = x["expr"]
            for i in sorted(x["inputs"], key=len, reverse=True):
                e = re.sub(rf"\b{i}\b", lambda _: f"({sql(i)})", e)
            return e
        return None
    s = sql(m["name"])
    if s is None:
        return None
    return {"name": m["name"], "expression": {"sql": s}, "description": m.get("description", ""),
            "nonportable_extensions": [{"vendor_name": O.VENDOR, "data": {k: m.get(k) for k in ("owner", "version", "status", "unit")}}]}
    # END SOLUTION


# %%
doc = O.export_datasets(model.doc)
kept, left = [], []
for m in model.metrics.values():
    try:
        x = metric_to_ossie(m, model.metrics)
    except NotImplementedError:
        x = next((r for r in Q.reference("d2_4_metrics") if r["name"] == m["name"]), None)
    (kept.append(x) if x else left.append(m["name"]))
doc["metrics"] = kept
doc["nonportable_extensions"] = [{"vendor_name": O.VENDOR, "data": {"cumulative_metrics": left}}]
print(f"{len(doc['datasets'])} datasets, {len(doc['relationships'])} relationships, {len(kept)} metrics; not exported: {left}")
print(next(m for m in doc["metrics"] if m["name"] == "collection_rate")["expression"]["sql"])
Q.check(len(kept) >= 20 and "cash_collected_fytd" in left, "metrics exported; the cumulative one stays behind")

# %% [markdown]
# ## 2 · Check the document (4')
#
# `O.validate` checks what the core specification requires: version, unique names, sources, expressions, and
# relationships and metrics that name declared fields.

# %%
errors = O.validate(doc)
print(errors or "valid")
broken = copy.deepcopy(doc)
broken["metrics"][0]["expression"]["sql"] = "SUM(bill.amount)"
print("a misspelt field:", O.validate(broken))
Q.check(errors == [], "the document passes the structural checks")
path = Q.lab_dir("D2_4") / "qamar_telecom.ossie.yaml"
Q.yaml_dump(doc, path)
print("written:", path.relative_to(Q.LABS), f"({path.stat().st_size:,} bytes)")

# %% [markdown]
# ## 3 · Compile three metrics for SQLite (6')
#
# `O.sqlite_copy` builds an in-memory SQLite database with each dataset's source: tables are copied; the two
# sources that are DuckDB queries (collections and deduplicated payments) are materialized as `sem_collection`
# and `sem_payment`, as a transformation framework would. `O.compile_sql(doc, metric, by, "SQLITE")` writes the
# SQL from the document alone.
#
# ✏️ **Exercise** · Run the three metrics of `THREE` on SQLite. Return a dict of DataFrames, or of the error
# message when a query fails.

# %%
lite = O.sqlite_copy(con, model.doc)


def run_three(doc) -> dict:
    # BEGIN SOLUTION
    out = {}
    for metric, by in THREE:
        try:
            out[metric] = O.run(doc, lite, metric, by)
        except Exception as e:
            out[metric] = f"error: {str(e).splitlines()[-1][-90:]}"
    return out
    # END SOLUTION


# %%
try:
    first = run_three(doc)
except NotImplementedError:
    first = {k: (pd.DataFrame(v) if isinstance(v, list) else v) for k, v in Q.reference("d2_4_first").items()}
for k, v in first.items():
    print(f"--- {k}\n{v.head(4).to_string(index=False) if isinstance(v, pd.DataFrame) else v}")

# %% [markdown]
# ## 4 · Compare and fix the expressions that did not port (6')
#
# Two queries fail loudly: a function DuckDB has and SQLite does not. One runs and is wrong: read it twice.
#
# ✏️ **Exercise** · Add a `SQLITE` entry to `expression.dialects` of each field that did not port, run the three
# metrics again, and compare each with DuckDB.

# %%
def sqlite_fixes() -> dict:
    """{"dataset.field": the SQLite expression} for each field that did not port."""
    # BEGIN SOLUTION
    return {"bill.service_month": "strftime('%Y-%m', bill_month)",
            "customer.contact_name": "substr(full_name, 1, instr(full_name || ' ', ' ') - 1)",
            "complaint.resolution_days": "CAST(julianday(closed_date) - julianday(opened_date) AS INTEGER)"}
    # END SOLUTION


def add_dialects(doc, fixes) -> dict:
    doc = copy.deepcopy(doc)
    for key, expr in fixes.items():
        ds, field = key.split(".")
        f = next(x for d in doc["datasets"] if d["name"] == ds for x in d["fields"] if x["name"] == field)
        f["expression"]["dialects"] = [{"dialect": "SQLITE", "expression": expr}]
    return doc


try:
    FIXES = sqlite_fixes()
except NotImplementedError:
    FIXES = Q.reference("d2_4_fixes")
fixed = add_dialects(doc, FIXES)
rows = []
for metric, by in THREE:
    a = model.query([metric], by=by).rename(columns={metric: "duckdb"})
    b = O.run(fixed, lite, metric, by).rename(columns={metric: "sqlite"})
    a[by[0]] = a[by[0]].astype(str)
    j = a.merge(b, on=by[0], how="outer")
    rows.append({"metric": metric, "groups": len(j), "max_abs_diff": float((j.duckdb - j.sqlite).abs().max())})
cmp = pd.DataFrame(rows)
print(cmp.to_string(index=False))
Q.check(bool((cmp.max_abs_diff < 1e-6).all()), "DuckDB and SQLite agree on the three metrics")
Q.yaml_dump(fixed, path)

# %% [markdown]
# 🔍 The query that ran without an error returned one row, `None`, with the whole billed amount in it. Which of
# the three failures would reach a manager's slide?
#
# ## 5 · What did not travel (3')
#
# ✏️ **Exercise** · List what the Ossie core did not carry: the non-portable extensions in the document, and one
# metric that still fails on SQLite after the fixes.

# %%
def left_behind(doc) -> dict:
    # BEGIN SOLUTION
    ext = []
    for d in doc["datasets"]:
        for e in d.get("nonportable_extensions", []):
            ext.append(f"dataset {d['name']}: {', '.join(e['data'])}")
        for f in d["fields"]:
            for e in f.get("nonportable_extensions", []):
                ext.append(f"field {d['name']}.{f['name']}: {', '.join(e['data'])}")
    for r in doc["relationships"]:
        for e in r.get("nonportable_extensions", []):
            ext.append(f"relationship {r['name']}: {', '.join(e['data'])}")
    for e in doc["nonportable_extensions"]:
        ext.append(f"model: {e['data']}")
    try:
        O.run(doc, lite, "median_resolution_days", ["complaint.category"])
        still = None
    except Exception as e:
        still = str(e).splitlines()[-1][-60:]
    return {"extensions": ext, "median_resolution_days on SQLite": still}
    # END SOLUTION


# %%
try:
    lb = left_behind(fixed)
except NotImplementedError:
    lb = Q.reference("d2_4_left_behind")
for e in lb["extensions"]:
    print("-", e)
print("median_resolution_days on SQLite:", lb["median_resolution_days on SQLite"])
print("Not in the document at all: the access policy (roles, row rules) and the metric tests.")
Q.check(any("asof" in e for e in lb["extensions"]) and lb["median_resolution_days on SQLite"], "the gaps are listed")

# %% [markdown]
# ## ✱ Stretch · Round trip
#
# Read the Ossie document back into a qsem model (datasets, fields with the default `sql`, relationships as joins)
# and check that `billed_amount` by `customer.region` is unchanged. What did the round trip lose?

# %%
def stretch():
    # BEGIN SOLUTION
    back = {"name": fixed["name"], "datasets": []}
    for d in fixed["datasets"]:
        src = next(x for x in model.doc["datasets"] if x["name"] == d["name"])["source"]
        nd = {"name": d["name"], "source": src, "fields": [{"name": f["name"], "sql": f["expression"]["sql"]} for f in d["fields"]],
              "joins": [{"to": r["to"], "keys": list(map(list, zip(r["from_columns"], r["to_columns"])))}
                        for r in fixed["relationships"] if r["from"] == d["name"] and r["to"] != "time"]}
        t = next((r["from_columns"][0] for r in fixed["relationships"] if r["from"] == d["name"] and r["to"] == "time"), None)
        if t:
            nd["time"] = t
        back["datasets"].append(nd)
    m2 = S.Model(S.with_metrics(back, [model.metrics["billed_amount"]]), con)
    a, b = model.query(["billed_amount"], by=["customer.region"]), m2.query(["billed_amount"], by=["customer.region"])
    print("same billed amount by region:", bool((a.billed_amount - b.billed_amount).abs().max() < 1e-6))
    print("lost: the as-of tariff join, classifications, metric types and tests (unless read from the extensions)")
    # END SOLUTION


try:
    stretch()
except NotImplementedError:
    print("✱ Stretch not attempted")

# %% [markdown]
# ## Checkpoint
#
# 1. Why did the two collections sources become tables (`sem_collection`, `sem_payment`) for the second engine?
#
# <details><summary>Answer</summary>Their logic was DuckDB SQL inside the semantic model. Logic that every engine
# must share belongs in the transformation layer (SQLMesh, dbt), where it is built once as a table.</details>
#
# 2. Which failure was the dangerous one, and how would a test have caught it?
#
# <details><summary>Answer</summary>`strftime` with its arguments in DuckDB's order ran on SQLite and returned NULL:
# one group with the whole amount. A reconciliation test by month, not only in total, catches it.</details>
#
# 3. The access policy is not in the Ossie document. What follows for a team that moves tools?
#
# <details><summary>Answer</summary>Access rules and their tests must be carried and re-run by hand on the new tool;
# portability of definitions is not portability of governance.</details>
#
# **Carry forward.** `artifacts/D2_4/qamar_telecom.ossie.yaml`.
