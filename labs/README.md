# Analytics Products: Semantic Layers and Conversational Analytics: labs

Sixteen notebook labs on the synthetic case of Qamar Telecom, one per session, each 25 minutes with a stretch.
Every lab starts from supplied files in `data/`, so no lab depends on finishing another. Everything runs on a
laptop CPU or in Colab; no model is downloaded.

## Quick start

- **Colab.** Open a notebook from the table; its first cell clones this repository and installs
  `requirements-colab.txt`.
- **Locally.** Install [uv](https://docs.astral.sh/uv/), then from `labs/`:

  ```
  uv sync
  uv run jupyter lab
  ```

  On Windows, if `uv sync` fails with a path that is too long, put the environment on a short path first:
  `set UV_PROJECT_ENVIRONMENT=C:\uvds408` (PowerShell: `$env:UV_PROJECT_ENVIRONMENT="C:\uvds408"`).
- Run [`00_setup_check.ipynb`](https://colab.research.google.com/github/SDAIAAcademy/ds-408/blob/main/labs/00_setup_check.ipynb)
  once before Day 1.

| Unit | Session | Notebook |
|---|---|---|
| Day 1 | 1 · One metric, three owners | [`D1_1_collection_rate.ipynb`](https://colab.research.google.com/github/SDAIAAcademy/ds-408/blob/main/labs/D1_1_collection_rate.ipynb) |
| Day 1 | 2 · Metrics as code with tests | [`D1_2_metrics_as_code.ipynb`](https://colab.research.google.com/github/SDAIAAcademy/ds-408/blob/main/labs/D1_2_metrics_as_code.ipynb) |
| Day 1 | 3 · Ownership and change control | [`D1_3_change_control.ipynb`](https://colab.research.google.com/github/SDAIAAcademy/ds-408/blob/main/labs/D1_3_change_control.ipynb) |
| Day 1 | 4 · Certification and deprecation | [`D1_4_catalogue_lifecycle.ipynb`](https://colab.research.google.com/github/SDAIAAcademy/ds-408/blob/main/labs/D1_4_catalogue_lifecycle.ipynb) |
| Day 2 | 1 · Conformed dimensions across areas | [`D2_1_conformed_model.ipynb`](https://colab.research.google.com/github/SDAIAAcademy/ds-408/blob/main/labs/D2_1_conformed_model.ipynb) |
| Day 2 | 2 · Performance and cost | [`D2_2_pre_aggregations.ipynb`](https://colab.research.google.com/github/SDAIAAcademy/ds-408/blob/main/labs/D2_2_pre_aggregations.ipynb) |
| Day 2 | 3 · Access rules | [`D2_3_access_rules.ipynb`](https://colab.research.google.com/github/SDAIAAcademy/ds-408/blob/main/labs/D2_3_access_rules.ipynb) |
| Day 2 | 4 · Portability | [`D2_4_portability.ipynb`](https://colab.research.google.com/github/SDAIAAcademy/ds-408/blob/main/labs/D2_4_portability.ipynb) |
| Day 3 | 1 · A certified set for a platform | [`D3_1_certified_set.ipynb`](https://colab.research.google.com/github/SDAIAAcademy/ds-408/blob/main/labs/D3_1_certified_set.ipynb) |
| Day 3 | 2 · Which context helps | [`D3_2_context_ablation.ipynb`](https://colab.research.google.com/github/SDAIAAcademy/ds-408/blob/main/labs/D3_2_context_ablation.ipynb) |
| Day 3 | 3 · A scoring harness | [`D3_3_scoring_harness.ipynb`](https://colab.research.google.com/github/SDAIAAcademy/ds-408/blob/main/labs/D3_3_scoring_harness.ipynb) |
| Day 3 | 4 · Ask it again | [`D3_4_stability.ipynb`](https://colab.research.google.com/github/SDAIAAcademy/ds-408/blob/main/labs/D3_4_stability.ipynb) |
| Day 4 | 1 · Serving metrics to tools and agents | [`D4_1_serve_layer.ipynb`](https://colab.research.google.com/github/SDAIAAcademy/ds-408/blob/main/labs/D4_1_serve_layer.ipynb) |
| Day 4 | 2 · Safeguards that show their work | [`D4_2_safeguards.ipynb`](https://colab.research.google.com/github/SDAIAAcademy/ds-408/blob/main/labs/D4_2_safeguards.ipynb) |
| Day 4 | 3 · Which questions may go to the assistant | [`D4_3_routing_policy.ipynb`](https://colab.research.google.com/github/SDAIAAcademy/ds-408/blob/main/labs/D4_3_routing_policy.ipynb) |
| Day 4 | 4 · Design review | [`D4_4_design_review.ipynb`](https://colab.research.google.com/github/SDAIAAcademy/ds-408/blob/main/labs/D4_4_design_review.ipynb) |

## The assistant: stand-in and live modes

Muhsi (`muhsi.py`) answers a question with a semantic query, which the layer executes.

- **Stand-in (default).** 720 recorded replies in `data/assistant/replies.jsonl`: 60 certified questions, four
  context configurations, three runs. They are synthetic, written by `_tools/make_case_files.py` from an error
  model stated at the top of its `recordings` section, so every figure in the Day 3 and Day 4 labs is
  reproducible without a key. They are not the output of a real model; do not quote them as one.
- **Live (optional).** Set `QAMAR_MODEL_MODE=live` and `OPENROUTER_API_KEY` (a free key from openrouter.ai)
  before starting Jupyter. The same prompt goes to `google/gemma-4-31b-it:free` (change it with `QAMAR_MODEL`).
  Free models change and are rate limited: write the model name and the date beside any live figure.

## What is in this folder

| Path | What it is |
|---|---|
| `qamar.py` | data access (DuckDB views over `data/marts/`), `check`, `reference`, quick mode |
| `qsem.py` | the course's semantic layer: models, metrics, drill-across, pre-aggregations, access rules |
| `qossie.py` | export to the Ossie open format and a second engine (SQLite) |
| `muhsi.py` | the assistant: prompt from the metric context, stand-in and live modes, scoring |
| `harness/score.py` | the scorer a reviewer re-runs (PEP 723 script): `uv run python harness/score.py` |
| `servers/qamar_mcp.py` | the semantic layer as an MCP server over standard input and output |
| `ci/` | metric review rules and the CI workflow of Lab 1.3 |
| `capstone/` | the capstone brief, a README template and a question template |
| `data/` | marts, semantic model, metrics, access policy, assistant files, peer package, reference results |
| `_src/` | the percent-format sources of the notebooks |
| `_tools/` | data generators, notebook builder, reference writer |

Quick mode (`QAMAR_QUICK=1`) runs the heavier cells (the 2.8-million-row session table of Lab 2.2) on a sample.

## Regenerating the data

All data is synthetic. From `labs/`:

```
uv run python prepare_data.py
uv run python _tools/make_case_files.py
uv run python _tools/make_reference.py
uv run python _tools/py2nb.py
```

The notebooks are generated from `_src/` by `_tools/py2nb.py`, which also writes the solutions to
`solutions/`. Edit the sources, not the notebooks.
