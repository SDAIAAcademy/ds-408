# /// script
# requires-python = ">=3.11"
# dependencies = ["pandas>=2.2", "pyyaml>=6.0"]
# ///
# %% [markdown]
# # Lab 4.3 · A routing policy from the evaluation
#
# Day 4 · Session 3 (Which questions may go to the assistant) · 25 min. Qamar's executive committee states a
# tolerance: **at most 10% wrong figures** for any type of question Daleel answers alone. You measure the
# wrong-figure rate by question type with the guard on, put an upper bound on each rate, give each type a route,
# and write the decision record Eissa will file.
#
# **AI-off for steps 1 to 3.** The routes follow from the numbers; write the decision record yourself, then an
# assistant may check its wording.
#
# **Reference state.** `data/assistant/evaluation.csv`: the 60 certified questions, three runs each, full context,
# Lab 4.2's guard on (stand-in model, synthetic). A wrong figure is `wrong_plausible`, `wrong_visible` or
# `missed_refusal`: a number the manager would read.
#
# **Tasks**
# - [ ] 1 · Wrong-figure rate by question type (6')
# - [ ] 2 · An upper bound, not a point (6')
# - [ ] 3 · The routes under the tolerance (6')
# - [ ] 4 · The decision record (7')
# - [ ] ✱ Stretch · How the routes move when the tolerance halves

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

import hashlib
import math
import pandas as pd
import qamar as Q

EVAL = pd.read_csv("data/assistant/evaluation.csv")
TOLERANCE = 0.10
WRONG = ["wrong_plausible", "wrong_visible", "missed_refusal"]
print(EVAL.head().to_string(index=False))
print(EVAL.groupby("type").id.nunique().to_string())

# %% [markdown]
# ## 1 · Wrong-figure rate by question type (6')
#
# ✏️ **Exercise** · Return one row per `type` with `questions`, `answers` (questions times runs), `wrong` (answers
# that are wrong figures) and `rate`.

# %%
def rates(ev: pd.DataFrame) -> pd.DataFrame:
    # BEGIN SOLUTION
    ev = ev.assign(wrong=ev.outcome.isin(WRONG))
    g = ev.groupby("type").agg(questions=("id", "nunique"), answers=("id", "size"), wrong=("wrong", "sum")).reset_index()
    g["rate"] = (g.wrong / g.answers).round(3)
    return g
    # END SOLUTION


# %%
try:
    r = rates(EVAL)
except NotImplementedError:
    r = pd.DataFrame(Q.reference("d4_3_rates"))
print(r.to_string(index=False))
Q.check(int(r.answers.sum()) == 180 and int(r.wrong.sum()) == 12, "180 answers, 12 wrong figures")

# %% [markdown]
# 🔍 Hijri questions show 0 wrong figures. Would you let Daleel answer them alone? How many answers is that
# zero based on?
#
# ## 2 · An upper bound, not a point (6')
#
# Nine answers with no error do not show a rate of zero. The Wilson score interval gives an upper bound that is
# honest about small samples:
#
# $$\text{upper} = \frac{\hat p + \frac{z^2}{2n} + z\sqrt{\frac{\hat p(1-\hat p)}{n} + \frac{z^2}{4n^2}}}{1 + \frac{z^2}{n}}, \quad z = 1.96$$
#
# ✏️ **Exercise** · Write `wilson_upper(k, n)` and add a column `upper` to the rates.

# %%
def wilson_upper(k: int, n: int, z: float = 1.96) -> float:
    # BEGIN SOLUTION
    if n == 0:
        return 1.0
    p = k / n
    centre = p + z * z / (2 * n)
    spread = z * math.sqrt(p * (1 - p) / n + z * z / (4 * n * n))
    return (centre + spread) / (1 + z * z / n)
    # END SOLUTION


# %%
try:
    r["upper"] = [round(wilson_upper(k, n), 3) for k, n in zip(r.wrong, r.answers)]
except NotImplementedError:
    r["upper"] = pd.DataFrame(Q.reference("d4_3_bounds")).set_index("type").loc[r.type, "upper"].values
print(r.to_string(index=False))
Q.check(r.set_index("type").loc["hijri_period", "upper"] > 0.25 and r.set_index("type").loc["lookup", "upper"] < TOLERANCE,
        "zero of nine still allows about 30%; three of ninety stays under 10%")

# %% [markdown]
# 🔍 The three runs of one question are not independent: C13 is wrong in all three. Recompute the lookup bound with
# questions as the unit (1 wrong question of 30). Does the route change?
#
# ## 3 · The routes under the tolerance (6')
#
# | Route | When |
# |---|---|
# | `assistant` | the upper bound is within the tolerance |
# | `assistant_with_review` | the rate is within the tolerance but the upper bound is not: answer with the card, and an analyst samples the answers weekly |
# | `analyst` | the rate itself is above the tolerance: the question goes to an analyst or a certified report |
#
# ✏️ **Exercise** · Return the rates with a `route` column.

# %%
def routes(r: pd.DataFrame, tolerance: float) -> pd.DataFrame:
    # BEGIN SOLUTION
    def route(row):
        if row.upper <= tolerance:
            return "assistant"
        return "assistant_with_review" if row.rate <= tolerance else "analyst"
    return r.assign(route=r.apply(route, axis=1))
    # END SOLUTION


# %%
try:
    policy = routes(r, TOLERANCE)
except NotImplementedError:
    policy = pd.DataFrame(Q.reference("d4_3_routes"))
print(policy[["type", "questions", "answers", "wrong", "rate", "upper", "route"]].to_string(index=False))
by = policy.set_index("type").route
Q.check(by["lookup"] == "assistant" and by["hijri_period"] == "assistant_with_review" and by["fiscal_period"] == "analyst",
        "lookups go to the assistant, Hijri periods with review, fiscal periods to an analyst")
policy.to_csv(Q.lab_dir("D4_3") / "routing_policy.csv", index=False, lineterminator="\n")

# %% [markdown]
# 🔍 Fiscal periods go to an analyst, yet Lab 3.2 showed examples fix most fiscal errors. What would you change, and
# what evidence would move the route back to the assistant?
#
# ## 4 · The decision record (7')
#
# A routing policy is a risk decision. The National AI Risk Management Framework (SDAIA, April 2026) frames AI risk
# management as identifying, assessing, treating and monitoring risks; this record is the treatment and its
# monitoring for one system.
#
# ✏️ **Exercise** · Write `decision_record(policy)` returning Markdown with: title, status and date, the decision
# owner (Eissa Al-Mahfouth, data governance), context (the system, the question set, the stand-in or live model),
# the tolerance in one sentence, the evidence (the routes table and a SHA-256 of `evaluation.csv`), the decision,
# its consequences, when it is reviewed (at least: a model change, a major metric version, monthly), and the
# framework it follows. Save it as `decision_record.md`.

# %%
def decision_record(policy: pd.DataFrame) -> str:
    # BEGIN SOLUTION
    digest = hashlib.sha256(Path("data/assistant/evaluation.csv").read_bytes().replace(b"\r\n", b"\n")).hexdigest()[:12]
    table = ["| Question type | Questions | Answers | Wrong figures | Rate | Upper bound (95%) | Route |", "|---|---|---|---|---|---|---|"]
    table += [f"| {x.type} | {x.questions} | {x.answers} | {x.wrong} | {x.rate:.1%} | {x.upper:.1%} | {x.route} |" for x in policy.itertuples()]
    alone = ", ".join(policy[policy.route == "assistant"].type)
    review = ", ".join(policy[policy.route == "assistant_with_review"].type)
    analyst = ", ".join(policy[policy.route == "analyst"].type)
    return "\n".join([
        "# Decision record: which questions Daleel may answer", "",
        f"Status: proposed · Date: {pd.Timestamp.today():%Y-%m-%d} · Owner: Eissa Al-Mahfouth (data governance)", "",
        "## Context", "",
        "Daleel answers managers' questions through Qamar's semantic layer, with the guard of Lab 4.2 on. Evidence: 60 certified",
        "questions (30 Arabic, 30 English), three runs each, full context. Model: the course's stand-in (recorded, synthetic);",
        "a live model must be re-evaluated before this record applies to it.", "",
        "## Tolerance", "",
        f"At most {TOLERANCE:.0%} of the figures Daleel gives alone may be wrong, judged on the 95% upper bound, not the point rate.", "",
        "## Evidence", "", *table, "", f"evaluation.csv SHA-256 (first 12): `{digest}`", "",
        "## Decision", "",
        f"- Daleel answers alone: {alone or 'none'}.",
        f"- Daleel answers with the answer card; an analyst samples the answers weekly: {review or 'none'}.",
        f"- Routed to an analyst or a certified report: {analyst or 'none'}.", "",
        "## Consequences", "",
        "Managers wait longer for fiscal, ranking and cumulative questions; the analysts' weekly sample costs about two hours.",
        "Adding examples for fiscal periods is the first improvement to evaluate.", "",
        "## Review", "",
        "Re-run the evaluation and this record on any model change, any major version of a certified metric, and monthly.", "",
        "## Framework", "",
        "Follows the National AI Risk Management Framework (SDAIA, April 2026; advisory): risks identified (Lab 3.3),",
        "assessed (this table), treated (routes and guard) and monitored (review triggers above).", ""])
    # END SOLUTION


# %%
try:
    record = decision_record(policy)
except NotImplementedError:
    record = Q.reference("d4_3_record")
path = Q.lab_dir("D4_3", reset=False) / "decision_record.md"
path.write_text(record, encoding="utf-8")
print(record)
Q.check(all(t in record for t in policy.type) and "10%" in record and "monitor" in record.lower() and "Owner" in record,
        "the record names every type, the tolerance, the owner and how it is monitored")

# %% [markdown]
# ## ✱ Stretch · How the routes move when the tolerance halves
#
# The committee asks what 5% would mean. Re-route with 5% and list the types whose route changes.

# %%
def stretch():
    # BEGIN SOLUTION
    half = routes(r, TOLERANCE / 2).set_index("type").route
    moved = {t: f"{by[t]} -> {half[t]}" for t in by.index if by[t] != half[t]}
    print("routes that move at 5%:", moved)
    # END SOLUTION


try:
    stretch()
except NotImplementedError:
    print("✱ Stretch not attempted")

# %% [markdown]
# ## Checkpoint
#
# 1. Why route on the upper bound rather than the measured rate?
#
# <details><summary>Answer</summary>A small sample can show zero errors by luck; the upper bound says how bad the
# rate could still be, and it tightens only with more evidence.</details>
#
# 2. Name two events that should reopen this decision.
#
# <details><summary>Answer</summary>A new or updated model, and a major version of a certified metric (the
# certified answers change). Also a new question type that the set does not cover.</details>
#
# **Carry forward.** `artifacts/D4_3/routing_policy.csv` and `decision_record.md`: the capstone's routing policy
# (15 points) follows the same form.
