# /// script
# requires-python = ">=3.11"
# dependencies = ["duckdb>=1.4", "pandas>=2.2", "pyyaml>=6.0"]
# ///
# %% [markdown]
# # Lab 4.4 · Review a peer's product
#
# Day 4 · Session 4 (Design review) · 25 min. Team B presents its governed analytics product for billing and
# collections to the review panel; you sit on the panel. You run the review checks on their package, add what the
# checks cannot see, rank every finding by risk, and log the panel's decisions. This is a rehearsal of the
# capstone's design review, from the other chair.
#
# **AI-tutor.** An assistant may help you read Team B's files; the findings, their ranking and the decisions are yours.
#
# **Reference state.** Team B's package in `data/review/`: `README.md`, `model.yaml`, `metrics.yml`, `policy.yaml`,
# `evaluation.csv` and `routing.yaml` (synthetic). It runs on the same Qamar marts.
#
# **Tasks**
# - [ ] 1 · Run the review checks (6')
# - [ ] 2 · What the checks cannot see (6')
# - [ ] 3 · Rank the findings by risk (7')
# - [ ] 4 · Log the panel's decisions (6')
# - [ ] ✱ Stretch · The same checklist on your own capstone plan

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

import math
import re
import pandas as pd
import qamar as Q
import qsem as S

PKG = Path("data/review")
print((PKG / "README.md").read_text(encoding="utf-8"))
con = Q.db()
POLICY = S.load_yaml(PKG / "policy.yaml")
DOC = S.with_metrics(S.load_yaml(PKG / "model.yaml"), S.load_yaml(PKG / "metrics.yml"))
peer = S.Model(DOC, con, policy=POLICY, **POLICY.get("settings", {}))
EVAL = pd.read_csv(PKG / "evaluation.csv")
ROUTING = S.load_yaml(PKG / "routing.yaml")
DUCKDB_ONLY = ["date_diff", "split_part", "strftime", "list_", "regexp_extract", "epoch_ms"]


def finding(lens: str, title: str, evidence: str) -> dict:
    return {"lens": lens, "finding": title, "evidence": evidence}


def model_checks(model) -> list[dict]:
    """The supplied checks of the model, the access rules and portability (lenses: correctness, governance, portability)."""
    out = []
    tests = S.run_tests(model)
    out.append(finding("correctness", "reconciliation tests", f"{int(tests.passed.sum())} of {len(tests)} pass"))
    total = con.execute("SELECT SUM(data_gb) FROM fct_usage_monthly").fetchone()[0]
    by_plan = model.query(["data_gb"], by=["tariff.plan_name"]).data_gb.sum()
    if abs(by_plan - total) > 0.01:
        out.append(finding("correctness", "data by plan does not add up to the total", f"{by_plan:,.0f} GB against {total:,.0f} GB"))
    mgr = model.as_role("regional_manager_eas")
    regions = sorted(mgr.query(["complaints"], by=["complaint.region"])["complaint.region"].dropna().unique())
    if regions != ["EAS"]:
        out.append(finding("governance", "the Eastern manager sees complaints of other regions", f"regions returned: {regions}"))
    names = model.as_role("executive").query(["billed_amount"], by=["customer.contact_name"]).head(3)["customer.contact_name"].tolist()
    if any(n != "***" for n in names):
        out.append(finding("governance", "a field derived from a Restricted column is readable", f"contact_name: {names}"))
    for d in model.doc["datasets"]:
        for f in d.get("fields", []):
            hits = [fn for fn in DUCKDB_ONLY if re.search(rf"\b{fn}", f["sql"])]
            if hits:
                out.append(finding("portability", f"DuckDB-only SQL in {d['name']}.{f['name']}", f"{hits}: {f['sql']}"))
    return out


checks = model_checks(peer)
print(pd.DataFrame(checks).to_string(index=False, max_colwidth=80))

# %% [markdown]
# ## 1 · Run the review checks (6')
#
# The model, access and portability checks above are supplied. The evaluation and the routing need checks too.
#
# ✏️ **Exercise** · Write `evaluation_checks(ev, routing)` returning findings (lens `evaluation` or `routing`) for:
# fewer than 40 questions; one language only; fewer than three runs; no must-refuse question; and any type routed
# to the assistant whose Wilson 95% upper bound on wrong figures is above the tolerance.

# %%
def wilson_upper(k, n, z=1.96):
    p = k / n
    return (p + z * z / (2 * n) + z * math.sqrt(p * (1 - p) / n + z * z / (4 * n * n))) / (1 + z * z / n)


def evaluation_checks(ev: pd.DataFrame, routing: dict) -> list[dict]:
    # BEGIN SOLUTION
    out = []
    nq = ev.id.nunique()
    if nq < 40:
        out.append(finding("evaluation", "fewer than 40 certified questions", f"{nq} questions"))
    if ev.lang.nunique() < 2:
        out.append(finding("evaluation", "one language only", f"languages: {sorted(ev.lang.unique())}"))
    if ev.run.nunique() < 3:
        out.append(finding("evaluation", "stability not measured", f"{ev.run.nunique()} run per question"))
    if "must_refuse" not in set(ev.type):
        out.append(finding("evaluation", "no must-refuse question", f"types: {sorted(ev.type.unique())}"))
    wrong = ev.assign(w=ev.outcome.isin(["wrong_plausible", "wrong_visible", "missed_refusal"])).groupby("type").w.agg(["sum", "size"])
    for t, route in routing["routes"].items():
        up = wilson_upper(int(wrong.loc[t, "sum"]), int(wrong.loc[t, "size"]))
        if route == "assistant" and up > routing["tolerance"]:
            out.append(finding("routing", f"{t} routed to the assistant on a point rate",
                               f"{int(wrong.loc[t, 'sum'])} of {int(wrong.loc[t, 'size'])} wrong; upper bound {up:.0%} > {routing['tolerance']:.0%}"))
    return out
    # END SOLUTION


# %%
try:
    checks2 = evaluation_checks(EVAL, ROUTING)
except NotImplementedError:
    checks2 = Q.reference("d4_4_eval_checks")
print(pd.DataFrame(checks2).to_string(index=False))
Q.check(len(checks2) == 7 and {c["lens"] for c in checks2} == {"evaluation", "routing"}, "four evaluation findings and three routing findings")
found = [c for c in checks + checks2 if not c["finding"].startswith("reconciliation tests")]

# %% [markdown]
# 🔍 Every reconciliation test of Team B passes. Does that make their metrics correct? Read their `collection_rate`
# in `data/review/metrics.yml` and its test before step 2.
#
# ## 2 · What the checks cannot see (6')
#
# Checks find what someone thought to check. A panel reads for meaning: is each certified metric the definition the
# business agreed (Day 1)? Does each claim in the README come with the way to reproduce it?
#
# ✏️ **Exercise** · Return the findings the checks missed, each with `lens` (correctness, governance, evaluation or
# reproducibility), `finding` and `evidence` quoted from Team B's files. Find at least two.

# %%
def beyond_checks() -> list[dict]:
    # BEGIN SOLUTION
    cr = next(m for m in DOC["metrics"] if m["name"] == "collection_rate")
    readme = (PKG / "README.md").read_text(encoding="utf-8")
    return [
        finding("correctness", "collection_rate is finance's cash-over-billed ratio, marked certified",
                f"expr: {cr['expr']}; the agreed definition is paid within 30 days of due date over net due, by bill cohort"),
        finding("correctness", "the collection_rate test reconciles to its own formula",
                "the test divides deduplicated cash by billed amount: it passes whatever the definition, so it proves nothing"),
        finding("reproducibility", "the README claims 97% with no command and no input hashes",
                re.search(r"\*\*97% accurate\*\*[^.]*", readme).group(0)),
        finding("governance", "the README sends every question type to the assistant",
                "'managers can use it for every question type': no refusals, no routes to an analyst"),
    ]
    # END SOLUTION


# %%
try:
    extra = beyond_checks()
except NotImplementedError:
    extra = Q.reference("d4_4_beyond")
print(pd.DataFrame(extra).to_string(index=False, max_colwidth=90))
Q.check(len(extra) >= 2 and any("collection_rate" in f["finding"] for f in extra), "the panel finds the collection rate the checks passed")
findings = found + extra

# %% [markdown]
# ## 3 · Rank the findings by risk (7')
#
# | Score | Impact | Likelihood |
# |---|---|---|
# | 3 | a wrong figure or a leak reaches managers without anyone noticing | on most questions of a common type |
# | 2 | a visible failure, or a wrong figure someone would notice | on some questions or one role |
# | 1 | documentation, cost or a future move of tools | rarely, or only after a change |
#
# ✏️ **Exercise** · Give each finding an `impact` and a `likelihood` (write your scores in `SCORES`, keyed by the
# finding's text), compute `risk` as their product, and return the findings sorted by risk, highest first.

# %%
def rank(findings: list[dict]) -> pd.DataFrame:
    # BEGIN SOLUTION
    SCORES = {
        "collection_rate is finance's cash-over-billed ratio, marked certified": (3, 3),
        "the Eastern manager sees complaints of other regions": (3, 3),
        "a field derived from a Restricted column is readable": (3, 2),
        "data by plan does not add up to the total": (3, 2),
        "the collection_rate test reconciles to its own formula": (2, 3),
        "no must-refuse question": (3, 2),
        "one language only": (2, 3),
        "stability not measured": (2, 2),
        "fewer than 40 certified questions": (2, 2),
        "the README sends every question type to the assistant": (2, 2),
        "the README claims 97% with no command and no input hashes": (1, 3),
    }
    rows = []
    for f in findings:
        key = f["finding"]
        imp, lik = SCORES.get(key, (3, 2) if f["lens"] == "routing" else (1, 1) if f["lens"] == "portability" else (2, 1))
        rows.append(dict(f, impact=imp, likelihood=lik, risk=imp * lik))
    return pd.DataFrame(rows).sort_values(["risk", "impact"], ascending=False).reset_index(drop=True)
    # END SOLUTION


# %%
try:
    ranked = rank(findings)
except NotImplementedError:
    ranked = pd.DataFrame(Q.reference("d4_4_ranked"))
print(ranked[["risk", "impact", "likelihood", "lens", "finding"]].to_string(index=False))
top2 = set(ranked.finding.head(2))
Q.check(top2 == {"collection_rate is finance's cash-over-billed ratio, marked certified", "the Eastern manager sees complaints of other regions"},
        "the silent wrong figure and the silent leak rank first")

# %% [markdown]
# 🔍 The portability findings rank last. When would they rank first? (Think of Team B's plans for next year.)
#
# ## 4 · Log the panel's decisions (6')
#
# ✏️ **Exercise** · Add `decision` (`fix before release` for risk 6 or more, `fix with an owner and a date` for 3 to 5,
# `accept and record` below 3), `owner` (Team B's role for the lens: correctness the metrics owner, governance the
# data protection officer, evaluation and routing the product owner, portability and reproducibility the platform
# lead) and `due`. Save `decision_log.csv` and return it.

# %%
OWNERS = {"correctness": "metrics owner", "governance": "data protection officer", "evaluation": "product owner",
          "routing": "product owner", "portability": "platform lead", "reproducibility": "platform lead"}


def decision_log(ranked: pd.DataFrame) -> pd.DataFrame:
    # BEGIN SOLUTION
    def decide(risk):
        return "fix before release" if risk >= 6 else ("fix with an owner and a date" if risk >= 3 else "accept and record")
    log = ranked.assign(decision=ranked.risk.map(decide), owner=ranked.lens.map(OWNERS))
    log["due"] = log.decision.map({"fix before release": "before release", "fix with an owner and a date": "within 30 days",
                                   "accept and record": "next review"})
    return log
    # END SOLUTION


# %%
try:
    log = decision_log(ranked)
except NotImplementedError:
    log = pd.DataFrame(Q.reference("d4_4_log"))
print(log[["risk", "finding", "decision", "owner", "due"]].to_string(index=False))
log.to_csv(Q.lab_dir("D4_4") / "decision_log.csv", index=False, lineterminator="\n")
Q.check(not ((log.risk >= 6) & (log.decision != "fix before release")).any() and log.owner.notna().all(),
        "every high-risk finding is fixed before release and every finding has an owner")
print("panel verdict:", "not ready for release" if (log.decision == "fix before release").any() else "ready")

# %% [markdown]
# ## ✱ Stretch · The same checklist on your own capstone plan
#
# Run `model_checks` and `evaluation_checks` on the supplied Qamar model (`data/semantic/qamar_model.yaml` with the
# governed policy) and on `data/assistant/evaluation.csv`. Which findings remain, and which belong in your capstone
# README as known limits?

# %%
def stretch():
    # BEGIN SOLUTION
    pol = Q.yaml_load("data/access/policy_governed.yaml")
    mets = [m for m in S.load_metrics("data/metrics") if m.get("dataset") != "usage_event"]  # no session table here
    mine = S.Model(S.with_metrics(S.load_yaml("data/semantic/qamar_model.yaml"), mets), con, policy=pol, deny_by_default=True, lineage=True)
    ev = pd.read_csv("data/assistant/evaluation.csv")
    routes = {"tolerance": 0.10, "routes": {"lookup": "assistant", "hijri_period": "assistant_with_review", "must_refuse": "assistant_with_review"}}
    remaining = [f for f in model_checks(mine) + evaluation_checks(ev, routes) if not f["finding"].startswith("reconciliation")]
    print(pd.DataFrame(remaining).to_string(index=False, max_colwidth=70))
    # END SOLUTION


try:
    stretch()
except NotImplementedError:
    print("✱ Stretch not attempted")

# %% [markdown]
# ## Checkpoint
#
# 1. All of Team B's tests pass. Why did the panel still rank a metric finding first?
#
# <details><summary>Answer</summary>A test that reconciles a metric to its own formula cannot find a wrong
# definition; only a reader who knows the agreed definition can. Passing tests are evidence of consistency, not of
# correctness.</details>
#
# 2. Why log an owner and a date for each finding, not just the finding?
#
# <details><summary>Answer</summary>A finding without an owner is not fixed; the log is what the next review
# checks against.</details>
#
# **Carry forward.** `artifacts/D4_4/decision_log.csv`. In the capstone you sit in Team B's chair.
