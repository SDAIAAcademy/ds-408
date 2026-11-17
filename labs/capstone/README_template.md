# <Product name>: governed analytics for <area 1> and <area 2>

Qamar Telecom (synthetic case of SDAIA Academy DS-408). <One sentence: who uses it and for what decisions.>

## Results

| Measure | Value | How measured |
|---|---|---|
| Certified questions | <n> (<ar> Arabic, <en> English, <r> must-refuse) | `questions.yaml` |
| Accuracy, run 1 | <x>% | `uv run python harness/score.py --set questions.yaml` |
| Wrong but plausible | <x>% | same run |
| Stability | <x>% of questions agree over three runs; <k> stable and wrong | `--runs 1 2 3` |
| Context ablation | <which kind matters most, by language> | `--variant no_synonyms` and the others |
| Model | <stand-in, or live: model name and date> | |

Input hashes of the run above: <paste the `inputs` block the scorer prints>.

## Semantic model and metrics

- Model: `model.yaml`; metrics: `metrics/*.yml`, each with owner, version, status and reconciliation tests.
- Conformed dimensions: <customer, calendar (fiscal, Hijri), tariff history as of the month>.
- Review rules in CI: `<workflow file>`; last run: <link>.

## Access rules

- Roles: <three roles and what each sees>. Policy: `policy.yaml`, deny by default, masking by lineage.
- Access tests: `<file>`; the seeded leak they catch: <what>.

## Routing policy

- Tolerance: <one sentence>.
- Routes by question type with upper bounds: `routing_policy.csv`. Decision record: `decision_record.md`.

## Re-run

```
uv sync
uv run python harness/score.py --set questions.yaml --runs 1 2 3 --out results
```

## Known limits

- <What the evaluation does not cover, what the panel should know, what you would fix next.>
