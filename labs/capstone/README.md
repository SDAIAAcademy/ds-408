# Capstone: a governed analytics product and its design review

Build a governed analytics product for **two business areas** of Qamar Telecom (usage, billing, collections or
complaints) in your own public GitHub repository, then defend it in a design review: 12 minutes to present,
8 minutes of questions.

## Start

1. Create a new public repository and copy into it, from this course's `labs/`: `qamar.py`, `qsem.py`,
   `daleel.py`, `harness/`, `pyproject.toml`, `uv.lock`, `prepare_data.py` and `data/marts/` (or run
   `prepare_data.py` to regenerate the marts).
2. Copy `README_template.md` from this folder as your repository's `README.md`, and `questions_template.yaml`
   as the start of your certified set.
3. Choose your two areas. At least one must cross areas with conformed dimensions (for example complaints per
   1,000 lines, or the collection rate by tariff).

## What the repository must hold

| Rubric line | Points | Evidence the panel looks for |
|---|---|---|
| Semantic model and metrics | 30 | metric files with owners, versions and reconciliation tests that pass against source totals; the review rules running in CI; splits that add up (a test by the dimension with history or fan-out risk) |
| Access rules | 15 | a policy with at least three roles, row rules for every dataset, masking by lineage, deny by default, and access tests that catch a seeded leak |
| Assistant evaluation | 30 | at least 40 certified questions across your two areas, three difficulties, Arabic and English, with must-refuse questions; accuracy, wrong-but-plausible rate and stability over three runs; one ablation of context |
| Routing policy | 15 | routes by question type from a stated tolerance and upper bounds, and a decision record with owner, evidence and review triggers |
| Reproducibility | 10 | one command that re-runs the evaluation, input hashes in the report, a README that states the model (stand-in or live, with name and date) |

## The defence

- Present the problem (one slide), what you built and why, then what you measured.
- During the questions the assessor gives you **five certified questions** to add to your set. Re-run your
  harness on them live. Rehearse the command.
- Expect the three lenses of Lab 4.4: correctness, governance, portability.

## Model

The stand-in model only knows the course's 60 questions. For your own questions use the live mode
(`QAMAR_MODEL_MODE=live` and a free OpenRouter key). Save the replies the live model returned, one JSON line per
question and run in the format of `data/assistant/replies.jsonl`, so the panel can re-score them offline if the
free model is unavailable on the day. Never write replies by hand: state the model name and the date of the run
in your README.
