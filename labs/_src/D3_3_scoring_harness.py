# /// script
# requires-python = ">=3.11"
# dependencies = ["duckdb>=1.4", "pandas>=2.2", "pyyaml>=6.0"]
# ///
# %% [markdown]
# # Lab 3.3 · Accuracy and wrong but plausible
#
# Day 3 · Session 3 (A scoring harness) · 25 min. Eissa (data governance) will not accept "Muhsi is 95%
# accurate" from a slide. He wants a harness that executes every reply on the semantic layer, compares it
# with the certified answer, separates the wrong answers anyone would notice from the ones nobody would, and a
# report he can re-run himself and get the same numbers.
#
# **AI-tutor.** An assistant may help with pandas; the outcome classes and the tolerance are decisions you defend.
#
# **Reference state.** `data/assistant/certified_60.yaml`, the stand-in's recorded replies (synthetic, see
# Lab 3.2) and the supplied scorer `harness/score.py`, which you will re-run against your own harness.
#
# **Tasks**
# - [ ] 1 · Execute a reply and compare (6')
# - [ ] 2 · Classify every outcome (7')
# - [ ] 3 · The report a reviewer can re-run (7')
# - [ ] 4 · Read the wrong but plausible answers (5')
# - [ ] ✱ Stretch · A tolerance for rounding: where does it stop being right?

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

import json
import re
import pandas as pd
import qamar as Q
import qsem as S
import muhsi as D

model = S.Model.load("data/semantic/qamar_model.yaml", Q.db(), metrics_dir="data/metrics")
QS = D.load_set("data/assistant/certified_60.yaml")
BYID = {q["id"]: q for q in QS}
TOL = 0.005
for qid in ["C01", "C15", "Q11"]:
    print(qid, BYID[qid]["question"], "\n   reply:", D.ask(BYID[qid], "full", 1).replace("\n", " "))

# %% [markdown]
# ## 1 · Execute a reply and compare (6')
#
# A reply is text. It may wrap its JSON in a code fence, refuse, or write a sentence instead.
#
# ✏️ **Exercise** · Write `run_reply(text, q)`: find the JSON object in the text, return `{"refused": reason}`
# for a refusal, `{"value": ...}` from `D.answer(model, query, kind)` for a query, and `{"error": message}`
# when there is no JSON or the layer fails. Write `is_right(got, want)`: labels must match exactly, numbers
# within a relative tolerance `TOL`.

# %%
def run_reply(text: str, q: dict) -> dict:
    # BEGIN SOLUTION
    m = re.search(r"\{.*\}", text or "", re.S)
    if not m:
        return {"error": "no JSON"}
    try:
        obj = json.loads(m.group(0))
    except json.JSONDecodeError as e:
        return {"error": f"bad JSON: {e.msg}"}
    if "refuse" in obj:
        return {"refused": obj["refuse"]}
    try:
        return {"value": D.answer(model, obj, q["expect"].get("kind", "value"))}
    except Exception as e:  # noqa: BLE001
        return {"error": str(e).splitlines()[0][:100]}
    # END SOLUTION


def is_right(got, want, tol: float = TOL) -> bool:
    # BEGIN SOLUTION
    if got is None or want is None:
        return False
    if isinstance(want, str) or isinstance(got, str):
        return str(got) == str(want)
    return abs(got - want) <= tol * max(abs(want), 1e-9)
    # END SOLUTION


# %%
cases = [("C01", "```json\n{\"metrics\": [\"collection_rate\"], \"by\": [], \"where\": [\"time.month = DATE '2026-03-01'\"]}\n```"),
         ("C01", "{\"metrics\": [\"collection_rate\"], \"where\": [\"time.month = DATE '2026-30-01'\"]}"),
         ("Q09", "The complaint rate was about 36 per 1,000 lines."),
         ("U14", "{\"refuse\": \"restricted\"}")]
try:
    got = [run_reply(t, BYID[i]) for i, t in cases]
except NotImplementedError:
    got = [D.execute(model, D.parse(t), BYID[i]) for i, t in cases]
for (i, t), g in zip(cases, got):
    print(i, "->", g)
try:
    right = is_right(got[0].get("value"), BYID["C01"]["expect"]["value"])
except NotImplementedError:
    right = D.same(got[0].get("value"), BYID["C01"]["expect"]["value"])
Q.check(right and "error" in got[1] and "error" in got[2] and got[3] == {"refused": "restricted"},
        "a fenced reply runs, a bad date and a sentence are errors, a refusal is kept")

# %% [markdown]
# ## 2 · Classify every outcome (7')
#
# | Outcome | When |
# |---|---|
# | `right` | the figure is the certified one, within tolerance |
# | `wrong_plausible` | a figure between half and twice the certified one, or a valid but wrong group name |
# | `wrong_visible` | any other figure |
# | `error` | no JSON, the layer failed, or no figure came back |
# | `refused_wrongly` | refused an answerable question |
# | `refused_right` | refused a must-refuse question |
# | `missed_refusal` | answered a must-refuse question |
#
# ✏️ **Exercise** · Write `classify(q, out)` and score run 1 of the full configuration: one row per question with
# `id`, `lang`, `area`, `difficulty`, `got`, `want`, `outcome`.

# %%
def classify(q: dict, out: dict) -> str:
    # BEGIN SOLUTION
    exp = q["expect"]
    if "refuse" in exp:
        return "refused_right" if "refused" in out else "missed_refusal"
    if "refused" in out:
        return "refused_wrongly"
    if "error" in out or out.get("value") is None:
        return "error"
    got, want = out["value"], exp["value"]
    if is_right(got, want):
        return "right"
    if isinstance(want, str):
        return "wrong_plausible"
    return "wrong_plausible" if 0.5 <= got / want <= 2 else "wrong_visible"
    # END SOLUTION


def my_score(questions, variant="full", run=1) -> pd.DataFrame:
    rows = []
    for q in questions:
        out = run_reply(D.ask(q, variant, run), q)
        rows.append({"id": q["id"], "lang": q["lang"], "area": q["area"], "difficulty": q["difficulty"],
                     "got": out.get("value", out.get("refused", out.get("error"))),
                     "want": q["expect"].get("value", q["expect"].get("refuse")), "outcome": classify(q, out)})
    return pd.DataFrame(rows)


# %%
try:
    mine = my_score(QS)
except NotImplementedError:
    mine = D.score(model, QS, "full")
supplied = D.score(model, QS, "full")
print(mine.outcome.value_counts().to_string())
Q.check((mine.outcome.values == supplied.outcome.values).all(), "your harness agrees with the supplied scorer on all 60")

# %% [markdown]
# 🔍 Execution accuracy counts a refusal as right when the question must be refused. Should `missed_refusal`
# count with the errors or with the wrong-but-plausible answers? Defend one in a sentence.
#
# ## 3 · The report a reviewer can re-run (7')
#
# A figure in a report is only as good as the command that reproduces it. The supplied scorer prints a hash of
# every input: the question set, the replies, the model and the metric files.
#
# ✏️ **Exercise** · Write `report(table, folder)`: save `results.csv` and a `report.md` with the accuracy, the
# wrong-but-plausible rate, a count per outcome, accuracy by area and by language, the input hashes from
# `harness/score.py`, and the exact command that re-runs it. Return the accuracy.

# %%
sys.path.insert(0, "harness")
import score as H  # the supplied scorer, harness/score.py

CMD = "uv run python harness/score.py --variant full --runs 1"


def report(table: pd.DataFrame, folder: Path) -> float:
    # BEGIN SOLUTION
    t = table.assign(correct=table.outcome.isin(["right", "refused_right"]))
    acc = round(float(t.correct.mean()), 3)
    plaus = round(float(t.outcome.isin(["wrong_plausible", "missed_refusal"]).mean()), 3)
    lines = ["# Muhsi on the certified set: run 1, full context", "",
             f"Accuracy **{acc:.1%}** on {len(t)} questions; wrong but plausible **{plaus:.1%}**.", "",
             "## Outcomes", "", t.outcome.value_counts().to_string(), "",
             "## By area and language", "", t.groupby("area").correct.mean().round(3).to_string(), "",
             t.groupby("lang").correct.mean().round(3).to_string(), "",
             "## Re-run", "", f"From `labs/`: `{CMD}`", "", "Inputs:", ""]
    lines += [f"- {k}: `{v}`" for k, v in H.inputs(Path("data/assistant/certified_60.yaml").resolve()).items()]
    folder.mkdir(parents=True, exist_ok=True)
    table.to_csv(folder / "results.csv", index=False, lineterminator="\n")
    (folder / "report.md").write_text("\n".join(lines) + "\n", encoding="utf-8")
    return acc
    # END SOLUTION


# %%
out_dir = Q.lab_dir("D3_3")
try:
    acc = report(mine, out_dir)
except NotImplementedError:
    acc = Q.reference("d3_3_accuracy")
print((out_dir / "report.md").read_text(encoding="utf-8") if (out_dir / "report.md").exists() else "no report written")
rerun = subprocess.run([sys.executable, "harness/score.py", "--variant", "full", "--runs", "1"], capture_output=True, text=True,
                       encoding="utf-8", env={**os.environ, "PYTHONIOENCODING": "utf-8"})
reviewer = json.loads(rerun.stdout)
print("reviewer's re-run:", reviewer["accuracy"], reviewer["inputs"])
Q.check(abs(reviewer["accuracy"] - acc) < 1e-9, "the reviewer's re-run gives your accuracy")

# %% [markdown]
# ## 4 · Read the wrong but plausible answers (5')
#
# ✏️ **Exercise** · For every `wrong_plausible` or `missed_refusal` row, return the question, the metric and
# filters Muhsi used, and the certified metric and filters, so a reader sees *what* went wrong.

# %%
def read_plausible(table: pd.DataFrame) -> pd.DataFrame:
    # BEGIN SOLUTION
    rows = []
    for _, r in table[table.outcome.isin(["wrong_plausible", "missed_refusal"])].iterrows():
        q, used = BYID[r.id], D.parse(D.ask(BYID[r.id], "full", 1))
        cert = q.get("query", {"refuse": q["expect"].get("refuse")})
        rows.append({"id": r.id, "outcome": r.outcome, "question": q["question"][:60],
                     "used": f"{used.get('metrics')} {used.get('where')}", "certified": f"{cert.get('metrics', cert.get('refuse'))} {cert.get('where', '')}"})
    return pd.DataFrame(rows)
    # END SOLUTION


# %%
try:
    wp = read_plausible(mine)
except NotImplementedError:
    wp = pd.DataFrame(Q.reference("d3_3_plausible"))
with pd.option_context("display.max_colwidth", 90):
    print(wp.to_string(index=False))
Q.check(set(wp.id) == {"C13", "C15", "Q11"}, "three answers nobody would notice on a slide")

# %% [markdown]
# 🔍 C13 used the Central region for "Riyadh". Is that a model error, a missing synonym, or a missing field in
# the layer? Which fix would you ask Zeyad for, and which test would catch it next time?
#
# ## ✱ Stretch · A tolerance for rounding: where does it stop being right?
#
# Score run 1 again with tolerances from 0.1% to 10%. At which tolerance does a wrong collection rate start to
# count as right, and what is the largest tolerance you would sign?

# %%
def stretch():
    # BEGIN SOLUTION
    for tol in [0.001, 0.005, 0.01, 0.02, 0.05, 0.1]:
        n = sum(D.outcome(q, D.execute(model, D.parse(D.ask(q, "full", 1)), q), tol) in ("right", "refused_right") for q in QS)
        print(f"tolerance {tol:>5.1%}: {n} of 60 right")
    # END SOLUTION


try:
    stretch()
except NotImplementedError:
    print("✱ Stretch not attempted")

# %% [markdown]
# ## Checkpoint
#
# 1. Why execute the reply instead of comparing its SQL or JSON with the certified query?
#
# <details><summary>Answer</summary>Different queries can return the same figure (filters in another order, a
# fiscal year written as a date range); the figure is what the manager sees, so the figure is what is scored.</details>
#
# 2. Eissa re-runs the command and gets a different accuracy. Name the first thing to compare.
#
# <details><summary>Answer</summary>The input hashes: a different question set, recording, model or metric file
# explains a different number before any code does.</details>
#
# **Carry forward.** `artifacts/D3_3/report.md` and `results.csv`. Lab 3.4 starts from the supplied files.
