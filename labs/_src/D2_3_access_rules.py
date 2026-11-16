# /// script
# requires-python = ">=3.11"
# dependencies = ["duckdb>=1.4", "pandas>=2.2", "pyyaml>=6.0"]
# ///
# %% [markdown]
# # Lab 2.3 · Three roles and a seeded leak
#
# Day 2 · Session 3 (Access rules) · 25 min. Qamar Telecom's layer serves an executive, the Eastern regional
# manager and a collections officer. You read the policy and the classification register, write access tests that
# run every role against every area, let them find two leaks, fix the policy and the layer, and run the tests
# until they pass.
#
# **AI-tutor.** An assistant may explain an error; the policy and the tests are yours.
#
# **Reference state.** `data/semantic/qamar_model.yaml`, `data/metrics/` and the access policy
# `data/access/policy.yaml` (roles, row rules, the classification register). It contains two planted leaks.
#
# **Tasks**
# - [ ] 1 · The roles and the classification register (4')
# - [ ] 2 · Access tests for each role (7')
# - [ ] 3 · Find the two leaks (5')
# - [ ] 4 · Fix the policy and the layer (6')
# - [ ] 5 · Run the tests again (3')
# - [ ] ✱ Stretch · An audit line for every query

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
import qsem as S

con = Q.db()
base = S.Model.load("data/semantic/qamar_model.yaml", con, metrics_dir="data/metrics")
POLICY = Q.yaml_load("data/access/policy.yaml")

# %% [markdown]
# ## 1 · The roles and the classification register (4')
#
# The NDMO Data Classification Policy has four levels: Top Secret, Secret, Restricted and Public. Qamar's register
# says which source columns are Restricted. The layer masks a Restricted field for a role without clearance, and
# applies the role's row rule to every dataset a query aggregates.

# %%
print(pd.DataFrame(POLICY["roles"]).T.to_string())
print("\nRestricted columns:", ", ".join(POLICY["classification"]))
print("\nrow rules:", POLICY["row_rules"])
fields = pd.DataFrame([{"dataset": d["name"], "field": f["name"], "sql": f["sql"], "tag": f.get("classification", "")}
                       for d in base.doc["datasets"] if d["name"] == "customer" for f in d["fields"]])
print(fields.to_string(index=False))

# %% [markdown]
# 🔍 Which datasets have no row rule? Which customer field reads a Restricted column without carrying the tag?
#
# ## 2 · Access tests for each role (7')
#
# One test per role and area. A limited role must see no row of another region; a role without clearance must see
# no Restricted value.
#
# ✏️ **Exercise** · Write `access_tests(model, policy)` returning one row per test with `role`, `test`, `passed` and
# `detail`. Cover: for each role, the five areas by their region field (`customer.region`, and `complaint.region`
# for complaints); and for each role, billed amount grouped by `customer.full_name` and by `customer.contact_name`.

# %%
AREAS = {"billing": ("billed_amount", "customer.region"), "collections": ("collection_rate", "customer.region"),
         "payments": ("cash_collected", "customer.region"), "usage": ("data_gb", "customer.region"),
         "complaints": ("complaints", "complaint.region")}


def access_tests(model, policy) -> pd.DataFrame:
    # BEGIN SOLUTION
    rows = []
    for role, r in policy["roles"].items():
        m = model.as_role(role, policy=policy)
        allowed = None if r["regions"] == "all" else set(r["regions"])
        for area, (metric, region) in AREAS.items():
            try:
                seen = set(m.query([metric], by=[region])[region])
                ok = allowed is None or seen <= allowed
                detail = ",".join(sorted(seen))
            except S.AccessDenied as e:
                ok, detail = allowed is not None, f"denied: {e}"
            rows.append({"role": role, "test": f"rows:{area}", "passed": ok, "detail": detail})
        for field in ("customer.full_name", "customer.contact_name"):
            vals = set(m.query(["billed_amount"], by=[field])[field])
            masked = vals == {"***"}
            ok = masked != bool(r.get("restricted"))
            rows.append({"role": role, "test": f"mask:{field}", "passed": ok,
                         "detail": "masked" if masked else f"{len(vals)} values visible"})
    return pd.DataFrame(rows)
    # END SOLUTION


# %%
try:
    first = access_tests(base, POLICY)
    MINE = True
except NotImplementedError:
    first, MINE = pd.DataFrame(Q.reference("d2_3_first_run")), False
print(first.to_string(index=False))
print(f"\n{(~first.passed).sum()} of {len(first)} tests fail")

# %% [markdown]
# ## 3 · Find the two leaks (5')
#
# ✏️ **Exercise** · From the failing tests, name the two leaks: return `{"row_leak": <dataset without a rule>,
# "mask_leak": <field>}`, and show one leaked figure for each: complaints outside the Eastern region seen by its
# manager, and a few names the executive can read.

# %%
def leaks(first: pd.DataFrame) -> dict:
    # BEGIN SOLUTION
    bad = first[~first.passed]
    row = bad[bad.test.str.startswith("rows:")].test.str.split(":").str[1].unique().tolist()
    mask = bad[bad.test.str.startswith("mask:")].test.str.split(":").str[1].unique().tolist()
    return {"row_leak": "complaint" if row == ["complaints"] else row, "mask_leak": mask[0] if len(mask) == 1 else mask}
    # END SOLUTION


# %%
try:
    found = leaks(first)
except NotImplementedError:
    found = Q.reference("d2_3_leaks")
print(found)
mgr = base.as_role("regional_manager_eas", policy=POLICY)
print(mgr.query(["complaints"], by=["complaint.region"]).to_string(index=False))
print(base.as_role("executive", policy=POLICY).query(["billed_amount"], by=["customer.contact_name"]).head(3).to_string(index=False))
Q.check(found == Q.reference("d2_3_leaks"), "both leaks named")

# %% [markdown]
# ## 4 · Fix the policy and the layer (6')
#
# Fix the cause, not the symptom. Three changes:
# 1. a row rule for `complaint` (Qamar's policy: a regional manager sees complaints raised in the region,
#    `complaint.region`);
# 2. deny by default: a limited role querying a dataset without a rule gets an error, not every row;
# 3. classify by lineage: a field is Restricted when its expression reads a Restricted column, whether or not
#    someone tagged it.
#
# ✏️ **Exercise** · Return the fixed policy and a model built with `deny_by_default=True` and `lineage=True`.

# %%
def fix(policy, base):
    # BEGIN SOLUTION
    policy = copy.deepcopy(policy)
    policy["row_rules"]["complaint"] = "complaint.region"
    model = S.Model(base.doc, base.con, policy=policy, deny_by_default=True, lineage=True)
    return policy, model
    # END SOLUTION


# %%
try:
    POLICY2, fixed = fix(POLICY, base)
except NotImplementedError:
    POLICY2 = Q.reference("d2_3_policy")
    fixed = S.Model(base.doc, con, policy=POLICY2, deny_by_default=True, lineage=True)
probe = copy.deepcopy(POLICY2)
probe["row_rules"].pop("payment")
try:
    S.Model(base.doc, con, policy=probe, deny_by_default=True).as_role("regional_manager_eas").query(["cash_collected"])
    denied = False
except S.AccessDenied as e:
    denied = True
    print("deny by default works:", e)
Q.check(denied, "a dataset without a rule is refused for a limited role")

# %% [markdown]
# ## 5 · Run the tests again (3')

# %%
if MINE:
    second = access_tests(fixed, POLICY2)
else:
    second = pd.DataFrame(Q.reference("d2_3_second_run"))
print(second.to_string(index=False))
Q.check(bool(second.passed.all()), "every access test passes for every role")
Q.yaml_dump(POLICY2, Q.lab_dir("D2_3") / "policy.yaml")
second.to_csv(Q.lab_dir("D2_3", reset=False) / "access_tests.csv", index=False)

# %% [markdown]
# 🔍 The collections officer sees names on purpose. Under the Personal Data Protection Law, what must Qamar be able
# to say about why that role needs them, and for how long?
#
# ## ✱ Stretch · An audit line for every query
#
# Wrap the model so that every query appends one line: role, metrics, group-by, filters, rows returned. Never the
# values.

# %%
def stretch():
    # BEGIN SOLUTION
    log = []

    def audited(model, role):
        m = model.as_role(role, policy=POLICY2)

        def q(metrics, by=None, where=None):
            out = m.query(metrics, by, where)
            log.append({"role": role, "metrics": metrics, "by": by or [], "where": where or [], "rows": len(out)})
            return out
        return q

    audited(fixed, "regional_manager_eas")(["complaints"], ["time.month"])
    audited(fixed, "collections_officer")(["collection_rate"], ["customer.segment"])
    print(pd.DataFrame(log).to_string(index=False))
    # END SOLUTION


try:
    stretch()
except NotImplementedError:
    print("✱ Stretch not attempted")

# %% [markdown]
# ## Checkpoint
#
# 1. The manager's dashboard filters complaints to the Eastern region. Why was that not enough?
#
# <details><summary>Answer</summary>The filter lived in one dashboard; the layer still answered any other tool or the
# assistant with every region. The rule belongs in the layer, where every consumer passes.</details>
#
# 2. Why is "deny by default" safer than "allow by default" for a dataset with no rule?
#
# <details><summary>Answer</summary>A forgotten rule then fails loudly for one role instead of leaking silently to all
# of them.</details>
#
# 3. `contact_name` held only first names. Why is it still Restricted?
#
# <details><summary>Answer</summary>It is derived from a Restricted column and, with region and city, can identify a
# customer; classification follows the data's lineage, not the field's name.</details>
#
# **Carry forward.** `artifacts/D2_3/policy.yaml` and `access_tests.csv`: the pattern of the capstone's access tests.
