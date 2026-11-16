# /// script
# requires-python = ">=3.11"
# dependencies = ["duckdb>=1.4", "pandas>=2.2", "pyyaml>=6.0"]
# ///
# %% [markdown]
# # Lab 3.1 · From 44 to 60 certified questions
#
# Day 3 · Session 1 (A certified set for a platform) · 25 min. Before Muhsi answers 300 managers, the platform
# needs a set of questions whose answers are certified: the figure, and the metric, filters and grain that
# produce it. You read the coverage of the supplied set, screen 24 candidate questions, certify the ones that
# pass through the semantic layer, and check the finished set covers every area, difficulty and language,
# with questions Muhsi must refuse.
#
# **AI-tutor.** An assistant may suggest paraphrases; a certified answer comes from the layer, never from a model.
#
# **Reference state.** `data/assistant/supplied_44.yaml` (44 certified questions) and
# `data/assistant/candidates.yaml` (24 drafts written by three analysts, with a draft query each).
#
# **Tasks**
# - [ ] 1 · Coverage of the supplied set (5')
# - [ ] 2 · Screen the candidate questions (7')
# - [ ] 3 · Certify the answers (7')
# - [ ] 4 · Check coverage, languages and refusals (6')
# - [ ] ✱ Stretch · Three paraphrases of one question

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
import muhsi as D

con = Q.db()
model = S.Model.load("data/semantic/qamar_model.yaml", con, metrics_dir="data/metrics")
SUPPLIED = D.load_set("data/assistant/supplied_44.yaml")
CANDIDATES = D.load_set("data/assistant/candidates.yaml")
print(len(SUPPLIED), "certified,", len(CANDIDATES), "candidates")
for q in SUPPLIED[:2] + [q for q in SUPPLIED if "refuse" in q["expect"]][:1]:
    print(Q.yaml_dump(q))

# %% [markdown]
# ## 1 · Coverage of the supplied set (5')
#
# A certified answer is four things: the **value**, the **metric**, the **filters** and the **grain**. A set
# for a platform also needs coverage: every business area at every difficulty (1 one filter, 2 two filters
# or a fiscal period, 3 a ranking, a Hijri period or a cumulative figure), in both languages, and questions the
# assistant must refuse.
#
# ✏️ **Exercise** · Return a table with one row per area and difficulty, one column per language with the count
# of answerable questions, and a column `refusals` with the count of must-refuse questions in that cell.

# %%
def coverage(questions: list[dict]) -> pd.DataFrame:
    # BEGIN SOLUTION
    df = pd.DataFrame([{"area": q["area"], "difficulty": q["difficulty"], "lang": q["lang"],
                        "refuse": "refuse" in q["expect"]} for q in questions])
    ans = df[~df.refuse].pivot_table(index=["area", "difficulty"], columns="lang", values="refuse", aggfunc="size", fill_value=0)
    ans = ans.reindex(pd.MultiIndex.from_product([["usage", "billing", "collections", "complaints"], [1, 2, 3]],
                                                  names=["area", "difficulty"]), fill_value=0)
    ans["refusals"] = [int((df.refuse & (df.area == a) & (df.difficulty == d)).sum()) for a, d in ans.index]
    return ans.reindex(columns=["ar", "en", "refusals"], fill_value=0)
    # END SOLUTION


# %%
try:
    cov = coverage(SUPPLIED)
except NotImplementedError:
    cov = pd.DataFrame(Q.reference("d3_1_coverage")).set_index(["area", "difficulty"])
print(cov.to_string())
gaps = cov[(cov.ar == 0) | (cov.en == 0)]
print("\ncells with no question in a language:", list(gaps.index))
Q.check(len(gaps) == 2 and int(cov.refusals.sum()) == 2, "two empty cells and only two refusals in the supplied set")

# %% [markdown]
# 🔍 Both refusals in the supplied set are about personal data. Which other kinds of question should Muhsi
# refuse at Qamar? Name three before reading the candidates.
#
# ## 2 · Screen the candidate questions (7')
#
# Each candidate has a draft: a query, or a refusal. Four rules decide whether it may enter the set:
#
# | Rule | Reject when |
# |---|---|
# | `period` | the draft answers but has no time condition (`time.` in a filter) |
# | `certified` | a metric of the draft is not `certified` |
# | `duplicate` | the draft asks the same metrics, groups and filters as a question already in the set |
# | `restricted` | the draft groups by or filters on a field classified Restricted (it should be a refusal) |
#
# ✏️ **Exercise** · Return one row per candidate: `id`, `keep` (True or False) and `rule` (the first rule broken,
# or empty).

# %%
def screen(candidates: list[dict], supplied: list[dict], model) -> pd.DataFrame:
    # BEGIN SOLUTION
    def sig(query):
        return (tuple(query["metrics"]), tuple(query.get("by", []) or []), tuple(sorted(query.get("where", []) or [])))

    seen = {sig(q["query"]) for q in supplied if "query" in q}
    rows = []
    for c in candidates:
        d, rule = c["draft"], ""
        if "refuse" not in d:
            fields = [f for f in (d.get("by", []) or []) + (d.get("where", []) or [])]
            refs = [r for f in fields for r in S.REF.findall(f)]
            if not any(f.startswith("time.") for f in d.get("where", []) or []):
                rule = "period"
            elif any(model.metrics[m].get("status") != "certified" for m in d["metrics"]):
                rule = "certified"
            elif sig(d) in seen:
                rule = "duplicate"
            elif any(ds in model.datasets and model.is_restricted(ds, model.field(ds, f)) for ds, f in refs):
                rule = "restricted"
        rows.append({"id": c["id"], "keep": rule == "", "rule": rule})
    return pd.DataFrame(rows)
    # END SOLUTION


# %%
try:
    screened = screen(CANDIDATES, SUPPLIED, model)
except NotImplementedError:
    screened = pd.DataFrame(Q.reference("d3_1_screen"))
view = screened.merge(pd.DataFrame(CANDIDATES)[["id", "lang", "area", "question"]], on="id")
print(view.sort_values(["keep", "rule"]).to_string(index=False, max_colwidth=70))
Q.check(int(screened.keep.sum()) == 16 and sorted(screened[~screened.keep].rule.unique()) == ["certified", "duplicate", "period", "restricted"],
        "16 candidates kept, 8 rejected under all four rules")

# %% [markdown]
# 🔍 X06 asks for the share of bills paid on time, and only a draft metric fits. Rejecting the draft is right;
# is the *question* useless? What should Muhsi say to it, and where does that question belong in the set?
#
# ## 3 · Certify the answers (7')
#
# ✏️ **Exercise** · For each kept candidate, return a certified question: the candidate's fields, `query` (the
# draft, for an answer), and `expect`: `{kind, value, unit, metric_version}` from running the query through
# the layer with `D.answer`, or `{refuse: reason}` for a refusal. Use the metric's `unit`, or `label` for a
# ranking.

# %%
def certify(candidates: list[dict], keep: set, model) -> list[dict]:
    # BEGIN SOLUTION
    out = []
    for c in candidates:
        if c["id"] not in keep:
            continue
        q = {k: c[k] for k in ("id", "lang", "area", "difficulty", "question")}
        if "refuse" in c["draft"]:
            q["expect"] = {"refuse": c["draft"]["refuse"]}
        else:
            m = model.describe(c["draft"]["metrics"][0])
            q["query"] = c["draft"]
            q["expect"] = {"kind": c["kind"], "value": D.answer(model, c["draft"], c["kind"]),
                           "unit": "label" if c["kind"] == "label" else m["unit"], "metric_version": m["version"]}
        out.append(q)
    return out
    # END SOLUTION


# %%
keep = set(screened[screened.keep].id)
try:
    new = certify(CANDIDATES, keep, model)
except NotImplementedError:
    new = Q.reference("d3_1_certified_new")
for q in new[:6]:
    print(f"{q['id']} {q['lang']} {q['area']:12s} {q['expect']}")
answered = [q for q in new if "value" in q["expect"]]
Q.check(len(new) == 16 and all(q["expect"]["value"] is not None for q in answered), "16 questions certified, every answer has a value")

# %% [markdown]
# 🔍 U12 asks about Ramadan 1447. Bills and monthly usage are dated on the first day of the service month: what
# does the certified value actually count? Write the one sentence a trainer would add to the question.
#
# ## 4 · Check coverage, languages and refusals (6')
#
# ✏️ **Exercise** · Merge the supplied and new questions and return a dict: `n`, `gaps` (cells of `coverage`
# with no question in a language), `ar`, `en`, `refusals`, `refusal_kinds` (sorted list of reasons) and
# `areas_with_refusal`.

# %%
def final_check(questions: list[dict]) -> dict:
    # BEGIN SOLUTION
    cov = coverage(questions)
    ref = [q for q in questions if "refuse" in q["expect"]]
    return {"n": len(questions), "gaps": int(((cov.ar == 0) | (cov.en == 0)).sum()),
            "ar": sum(q["lang"] == "ar" for q in questions), "en": sum(q["lang"] == "en" for q in questions),
            "refusals": len(ref), "refusal_kinds": sorted({q["expect"]["refuse"] for q in ref}),
            "areas_with_refusal": len({q["area"] for q in ref})}
    # END SOLUTION


# %%
full_set = SUPPLIED + new
try:
    fc = final_check(full_set)
except NotImplementedError:
    fc = Q.reference("d3_1_final")
print(fc)
Q.check(fc["n"] == 60 and fc["gaps"] == 0 and fc["ar"] == fc["en"] == 30 and fc["refusals"] >= 6 and fc["areas_with_refusal"] == 4,
        "60 questions, no empty cell, 30 per language, refusals in every area")
path = D.save_set(full_set, Q.lab_dir("D3_1") / "certified_60.yaml", "Qamar Telecom: certified questions for Muhsi")
supplied_60 = {q["id"]: q["expect"].get("value", q["expect"].get("refuse")) for q in D.load_set("data/assistant/certified_60.yaml")}
mine = {q["id"]: q["expect"].get("value", q["expect"].get("refuse")) for q in full_set}
Q.check(all(D.same(mine[k], v) or mine[k] == v for k, v in supplied_60.items()), "the same answers as the supplied certified_60.yaml")
print("saved", path)

# %% [markdown]
# ## ✱ Stretch · Three paraphrases of one question
#
# Managers rarely ask in the words of the set. Write three paraphrases of C02 (one formal Arabic, one Gulf
# colloquial, one English), each with the same `expect` as C02 and ids `C02-p1` to `C02-p3`. With a free key,
# `QAMAR_MODEL_MODE=live` scores them (Lab 3.2's stretch); the stand-in has no recording for new wording.

# %%
def stretch():
    # BEGIN SOLUTION
    c02 = next(q for q in full_set if q["id"] == "C02")
    texts = ["ما معدل تحصيل فواتير يناير 2026؟", "كم نسبة اللي انحصّل من فواتير يناير 2026؟",
             "What share of January 2026 bills was collected?"]
    paras = [dict(copy.deepcopy(c02), id=f"C02-p{i}", question=t, lang="en" if i == 3 else "ar") for i, t in enumerate(texts, 1)]
    for p in paras:
        print(p["id"], p["question"], p["expect"]["value"])
    # END SOLUTION


try:
    stretch()
except NotImplementedError:
    print("✱ Stretch not attempted")

# %% [markdown]
# ## Checkpoint
#
# 1. Two analysts certify the same question and get 0.8495 and 0.8645. Both ran the layer. What else must a
#    certified answer record so a reviewer can tell who is right?
#
# <details><summary>Answer</summary>The metric, the filters and the grain (here one ran March, not January) and the
# metric's version: the value alone cannot be checked.</details>
#
# 2. Why do refusals belong in the certified set?
#
# <details><summary>Answer</summary>An assistant that answers everything scores well on answerable questions; only
# must-refuse questions measure whether it invents figures for forecasts, personal data or draft metrics.</details>
#
# **Carry forward.** `artifacts/D3_1/certified_60.yaml`. Labs 3.2 to 3.4 start from the supplied
# `data/assistant/certified_60.yaml`, which has the same answers.
