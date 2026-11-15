# /// script
# requires-python = ">=3.11"
# dependencies = ["pandas>=2.2", "pyyaml>=6.0", "duckdb>=1.4"]
# ///
# %% [markdown]
# # Lab 1.4 · Certify, version and deprecate in a 40-metric catalogue
#
# Day 1 · Session 4 (Certification and deprecation) · 25 min. Qamar Telecom's catalogue has 40 metrics, three of
# which are old collection rates the council has replaced. You check the catalogue's health, deprecate the three
# with a successor and a sunset date, follow the lineage to everything built on them, and list the reports that
# still use a deprecated metric, by name, by alias or through a metric built on it.
#
# **AI-tutor.** An assistant may help with pandas; the decisions are yours.
#
# **Reference state.** `data/catalogue/catalogue.yaml` (40 metrics: owner, version, status, tests, dependencies,
# aliases) and `data/catalogue/reports.csv` (12 reports and the metric names they use, as typed by their owners).
#
# **Tasks**
# - [ ] 1 · The catalogue's health (5')
# - [ ] 2 · Deprecate three metrics (6')
# - [ ] 3 · Everything built on a deprecated metric (6')
# - [ ] 4 · Reports that still use one (8')
# - [ ] ✱ Stretch · One notice per report owner

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
import pandas as pd
import qamar as Q

CAT = Q.yaml_load("data/catalogue/catalogue.yaml")["catalogue"]
REPORTS = pd.read_csv("data/catalogue/reports.csv")
cat = pd.DataFrame(CAT)
print(cat.status.value_counts().to_string(), "\n")
print(cat.groupby("area").size().to_string())
print(f"\n{REPORTS.report.nunique()} reports, {len(REPORTS)} metric references")

# %% [markdown]
# ## 1 · The catalogue's health (5')
#
# A certified metric is a promise: it has an owner, and a simple metric has a test. Derived metrics (with
# `depends_on`) inherit their inputs' tests, but nothing tests the formula that combines them.
#
# ✏️ **Exercise** · Return three lists of names: certified without an owner; certified simple metrics (no
# `depends_on`) without a test; certified derived metrics without a test of their own.

# %%
def health(cat: pd.DataFrame) -> dict:
    # BEGIN SOLUTION
    cert = cat[cat.status == "certified"]
    simple = cert.depends_on.map(len) == 0
    return {"no_owner": sorted(cert[cert.owner.isna()].name),
            "simple_untested": sorted(cert[simple & (cert.tests == 0)].name),
            "derived_untested": sorted(cert[~simple & (cert.tests == 0)].name)}
    # END SOLUTION


# %%
try:
    h = health(cat)
except NotImplementedError:
    h = Q.reference("d1_4_health")
for k, v in h.items():
    print(f"{k:17s} {len(v):2d}  {', '.join(v)}")
Q.check(h == Q.reference("d1_4_health"), "health lists match the reference")

# %% [markdown]
# 🔍 `paid_on_time_rate` is certified and untested, and its owner calls it a collection rate. Is it one?
#
# ## 2 · Deprecate three metrics (6')
#
# The council replaced `collection_rate_finance` and `collection_rate_60d` with the certified `collection_rate`.
# `paid_on_time_rate` answers another question (bills, by count, paid on time): it is not replaced by the
# collection rate but renamed to `on_time_payment_share`.
#
# ✏️ **Exercise** · Return a new catalogue in which the three are `deprecated`, each with `replaced_by`, a
# `sunset` date two monthly closes after 2026-07-01 (`2026-08-31`), and a minor version bump (a status change).

# %%
SUCCESSOR = {"collection_rate_finance": "collection_rate", "collection_rate_60d": "collection_rate",
             "paid_on_time_rate": "on_time_payment_share"}


def deprecate(cat_list: list[dict]) -> list[dict]:
    # BEGIN SOLUTION
    out = copy.deepcopy(cat_list)
    for m in out:
        if m["name"] in SUCCESSOR:
            major, minor, _ = (int(x) for x in m["version"].split("."))
            m.update(status="deprecated", replaced_by=SUCCESSOR[m["name"]], sunset="2026-08-31",
                     version=f"{major}.{minor + 1}.0")
    return out
    # END SOLUTION


# %%
try:
    new_cat = deprecate(CAT)
except NotImplementedError:
    new_cat = Q.reference("d1_4_catalogue")
new = pd.DataFrame(new_cat)
print(new[new.name.isin(SUCCESSOR)][["name", "version", "status", "replaced_by", "sunset"]].to_string(index=False))
DEPRECATED = set(new[new.status == "deprecated"].name)
print("deprecated now:", sorted(DEPRECATED))
Q.check(set(SUCCESSOR) <= DEPRECATED and new.loc[new.name == "collection_rate_60d", "version"].item() == "2.2.0",
        "three deprecated, with a minor bump")

# %% [markdown]
# ## 3 · Everything built on a deprecated metric (6')
#
# `depends_on` is the lineage. A metric built on a deprecated one inherits the problem, and so does a metric
# built on *that* one.
#
# ✏️ **Exercise** · Return the set of metrics that depend on a deprecated metric directly or through other
# metrics, and that are not deprecated themselves.

# %%
def dependents(cat: pd.DataFrame, roots: set[str]) -> set[str]:
    # BEGIN SOLUTION
    deps = dict(zip(cat.name, cat.depends_on))
    hit, changed = set(), True
    while changed:
        changed = False
        for name, d in deps.items():
            if name not in hit and (set(d) & (roots | hit)):
                hit.add(name)
                changed = True
    return hit - roots
    # END SOLUTION


# %%
try:
    downstream = dependents(new, DEPRECATED)
except NotImplementedError:
    downstream = set(Q.reference("d1_4_downstream"))
print("built on a deprecated metric:", sorted(downstream))
Q.check(downstream == set(Q.reference("d1_4_downstream")), "downstream set matches the reference")

# %% [markdown]
# ## 4 · Reports that still use one (8')
#
# Report owners typed metric names as they say them: some are names, some are aliases ("collection %",
# "RHI"). Resolve every reference to a catalogue name first, then flag it.
#
# ✏️ **Exercise** · Return a table with one row per affected reference: `report`, `report_owner`, `metric_ref`,
# `metric` (resolved), `why` (`deprecated` or `built on deprecated`) and `move_to` (the successor, or "review").

# %%
def affected_reports(cat: pd.DataFrame, reports: pd.DataFrame, deprecated: set, downstream: set) -> pd.DataFrame:
    # BEGIN SOLUTION
    resolve = {n.lower(): n for n in cat.name}
    for n, aliases in zip(cat.name, cat.aliases):
        resolve.update({a.lower(): n for a in aliases})
    r = reports.copy()
    r["metric"] = r.metric_ref.str.lower().map(resolve)
    r = r[r.metric.isin(deprecated | downstream)].copy()
    r["why"] = r.metric.map(lambda m: "deprecated" if m in deprecated else "built on deprecated")
    succ = dict(zip(cat.name, cat.get("replaced_by", pd.Series([None] * len(cat)))))
    r["move_to"] = r.metric.map(lambda m: succ.get(m) if isinstance(succ.get(m), str) else "review")
    return r.reset_index(drop=True)
    # END SOLUTION


# %%
try:
    hits = affected_reports(new, REPORTS, DEPRECATED, downstream)
except NotImplementedError:
    hits = pd.DataFrame(Q.reference("d1_4_reports"))
print(hits.to_string(index=False))
print(f"\n{hits.report.nunique()} of {REPORTS.report.nunique()} reports must move before the sunset")
Q.check(sorted(hits.report.unique()) == sorted({r['report'] for r in Q.reference('d1_4_reports')}), "affected reports match the reference")
unresolved = REPORTS[~REPORTS.metric_ref.str.lower().isin({n.lower() for n in new.name} |
                                                          {a.lower() for al in new.aliases for a in al})]
print("references that resolve to nothing:", unresolved.metric_ref.tolist() or "none")

# %% [markdown]
# 🔍 Eight of the nine affected reports never typed a deprecated name. What would a search for "collection_rate_60d" in the
# report definitions have missed?
#
# ## ✱ Stretch · One notice per report owner
#
# Group the affected references by `report_owner` and write one short notice each: which reports, which
# metric to move to, and the sunset date.

# %%
def stretch():
    # BEGIN SOLUTION
    for owner, g in hits.groupby("report_owner"):
        lines = [f"- {r.report}: replace '{r.metric_ref}' ({r.why}) with {r.move_to}" for r in g.itertuples()]
        print(f"To {owner}: before 2026-08-31\n" + "\n".join(lines) + "\n")
    # END SOLUTION


try:
    stretch()
except NotImplementedError:
    print("✱ Stretch not attempted")

# %% [markdown]
# ## Checkpoint
#
# 1. Why not delete `collection_rate_60d` today?
#
# <details><summary>Answer</summary>Reports still read it; deleting breaks them silently or loudly on the day of a
# board meeting. Deprecate, announce, move the reports, then remove after the sunset.</details>
#
# 2. Why is `paid_on_time_rate` renamed rather than replaced by the collection rate?
#
# <details><summary>Answer</summary>It measures something else (bills paid on time, by count). Replacing it with the
# collection rate would change what the care scorecard says without anyone deciding it.</details>
#
# 3. `region_health_index` has no owner. Who decides how it moves?
#
# <details><summary>Answer</summary>Nobody, which is the finding: an ownerless certified metric is assigned an owner
# (or decertified) before the sunset plan can be agreed.</details>
#
# **Carry forward.** Day 2 builds the semantic layer from the certified metrics only.
