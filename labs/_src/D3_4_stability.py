# /// script
# requires-python = ">=3.11"
# dependencies = ["duckdb>=1.4", "pandas>=2.2", "pyyaml>=6.0"]
# ///
# %% [markdown]
# # Lab 3.4 · Three runs per question
#
# Day 3 · Session 4 (Ask it again) · 25 min. A manager who asks the same question on Sunday and on Monday and
# gets two figures stops trusting every figure. You ask each certified question three times, measure how often
# the answers agree, and find the cell that matters most: questions Muhsi answers the same way every time,
# and wrongly.
#
# **AI-tutor.** An assistant may explain a result or help with the plots; the classification rules and the conclusions are yours.
#
# **Reference state.** `data/assistant/certified_60.yaml` and three recorded runs per question in
# `data/assistant/replies.jsonl` (stand-in, synthetic: see Lab 3.2).
#
# **Tasks**
# - [ ] 1 · Load the three runs (3')
# - [ ] 2 · Agreement per question (6')
# - [ ] 3 · Stable right, stable wrong, unstable (7')
# - [ ] 4 · Stability by area, difficulty and language (6')
# - [ ] 5 · What a cache would hide (3')
# - [ ] ✱ Stretch · Does a majority vote of three fix the unstable questions?

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
import muhsi as D

model = S.Model.load("data/semantic/qamar_model.yaml", Q.db(), metrics_dir="data/metrics")
QS = D.load_set("data/assistant/certified_60.yaml")
GOOD = {"right", "refused_right"}

# %% [markdown]
# ## 1 · Load the three runs (3')
#
# With a hosted model you would call it three times at the same settings; the stand-in has the three replies
# recorded. One row per question and run.

# %%
runs = D.score(model, QS, "full", runs=(1, 2, 3))
runs["answer"] = runs.got.map(str)
print(runs.groupby("run").outcome.apply(lambda s: s.isin(GOOD).mean()).round(3).to_string())
print(runs.head(6).to_string(index=False))

# %% [markdown]
# 🔍 The three runs score about the same overall. Does that mean the answers are the same?
#
# ## 2 · Agreement per question (6')
#
# ✏️ **Exercise** · Return one row per question with `agree` (how many of the three answers equal the most
# common one: 3, 2 or 1) and `n_right` (how many runs are right). Then the share of questions where all three agree.

# %%
def agreement(runs: pd.DataFrame) -> pd.DataFrame:
    # BEGIN SOLUTION
    g = runs.groupby(["id", "lang", "area", "difficulty"])
    return g.agg(agree=("answer", lambda s: int(s.value_counts().iloc[0])),
                 n_right=("outcome", lambda s: int(s.isin(GOOD).sum()))).reset_index()
    # END SOLUTION


# %%
try:
    per_q = agreement(runs)
except NotImplementedError:
    per_q = pd.DataFrame(Q.reference("d3_4_agreement"))
share = (per_q.agree == 3).mean()
print(per_q[per_q.agree < 3].to_string(index=False))
print(f"all three agree on {share:.1%} of questions")
Q.check(0.85 <= share < 1, "most, not all, questions get the same answer three times")

# %% [markdown]
# ## 3 · Stable right, stable wrong, unstable (7')
#
# ✏️ **Exercise** · Label each question `stable_right` (three agreeing right answers), `stable_wrong` (three
# agreeing answers, not right) or `unstable`. Return the counts and the stable-wrong questions.

# %%
def stability(per_q: pd.DataFrame) -> pd.DataFrame:
    # BEGIN SOLUTION
    def label(r):
        if r.agree < 3:
            return "unstable"
        return "stable_right" if r.n_right == 3 else "stable_wrong"
    return per_q.assign(stability=per_q.apply(label, axis=1))
    # END SOLUTION


# %%
try:
    st = stability(per_q)
except NotImplementedError:
    st = pd.DataFrame(Q.reference("d3_4_stability"))
print(st.stability.value_counts().to_string())
print(st[st.stability == "stable_wrong"].to_string(index=False))
Q.check(set(st[st.stability == "stable_wrong"].id) == {"C13", "C15", "Q11"}, "three questions are stable and wrong")
st.to_csv(Q.lab_dir("D3_4") / "stability.csv", index=False, lineterminator="\n")

# %% [markdown]
# 🔍 Re-asking catches an unstable question. What catches a stable-wrong one? (Look back at Lab 3.3.)
#
# ## 4 · Stability by area, difficulty and language (6')
#
# ✏️ **Exercise** · Return the share of unstable and of stable-wrong questions by area, by difficulty and by
# language, as one table with a `group` column.

# %%
def by_groups(st: pd.DataFrame) -> pd.DataFrame:
    # BEGIN SOLUTION
    parts = []
    for col in ["area", "difficulty", "lang"]:
        t = st.groupby(col).stability.value_counts(normalize=True).unstack(fill_value=0)
        t = t.reindex(columns=["unstable", "stable_wrong"], fill_value=0).round(3)
        t.index = [f"{col}={i}" for i in t.index]
        parts.append(t)
    return pd.concat(parts).rename_axis("group").reset_index()
    # END SOLUTION


# %%
try:
    groups = by_groups(st)
except NotImplementedError:
    groups = pd.DataFrame(Q.reference("d3_4_groups"))
print(groups.to_string(index=False))
d1 = groups[groups.group == "difficulty=1"].iloc[0]
Q.check(d1.unstable == 0 and d1.stable_wrong == 0, "difficulty 1 questions are all stable and right")

# %% [markdown]
# ## 5 · What a cache would hide (3')
#
# Many assistants cache the first answer to a question. If run 1 were cached for every user, how many questions
# would *look* stable and right while a fresh ask would sometimes differ?
#
# ✏️ **Exercise** · Return the ids of unstable questions whose run 1 is right.

# %%
def hidden_by_cache(runs: pd.DataFrame, st: pd.DataFrame) -> list[str]:
    # BEGIN SOLUTION
    first_right = set(runs[(runs.run == 1) & runs.outcome.isin(GOOD)].id)
    return sorted(set(st[st.stability == "unstable"].id) & first_right)
    # END SOLUTION


# %%
try:
    hidden = hidden_by_cache(runs, st)
except NotImplementedError:
    hidden = Q.reference("d3_4_hidden")
print(hidden)
Q.check(len(hidden) >= 3, "a cache of run 1 hides most of the unstable questions")

# %% [markdown]
# ## ✱ Stretch · Does a majority vote of three fix the unstable questions?
#
# Answer each question with the most common of its three answers. Which unstable questions does the vote fix,
# which does it break, and what does a vote cost per question?

# %%
def stretch():
    # BEGIN SOLUTION
    def voted(g):  # the outcome of the most common answer
        return g[g.answer == g.answer.value_counts().index[0]].outcome.iloc[0]
    vote = runs.groupby("id")[["answer", "outcome"]].apply(voted)
    first = runs[runs.run == 1].set_index("id").outcome
    unstable = st[st.stability == "unstable"].id
    print("right with a vote of three:", int(vote.isin(GOOD).sum()), "of 60; with run 1 only:", int(first.isin(GOOD).sum()),
          "; cost: three calls per question")
    print(pd.DataFrame({"run 1": first[unstable], "vote": vote[unstable]}).to_string())
    # END SOLUTION


try:
    stretch()
except NotImplementedError:
    print("✱ Stretch not attempted")

# %% [markdown]
# ## Checkpoint
#
# 1. Which cell of the stability table is the most dangerous, and why?
#
# <details><summary>Answer</summary>Stable and wrong: the same wrong figure every time looks reliable, and re-asking
# never reveals it. Only a certified answer does.</details>
#
# 2. A vendor reports accuracy from one run at temperature zero. What two questions do you ask?
#
# <details><summary>Answer</summary>How often the same question gets the same answer on repeated runs (hosted
# models are not exactly deterministic), and how many of the agreeing answers are wrong.</details>
#
# **Carry forward.** `artifacts/D3_4/stability.csv`. Day 4 starts from the supplied files.
