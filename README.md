<!-- academy:title -->
# Analytics Products: Semantic Layers and Conversational Analytics

منتجات التحليلات: الطبقات الدلالية والتحليلات الحوارية

Data Science Track · SDAIA Academy · DS-408 · Level 400

REPLACE: one line under the title: what participants can do after the course

Participants build the analytics product of the fictional Qamar Telecom, whose 300 managers want to ask questions in Arabic and English about usage, billing, collections and complaints. They define metrics once as tested code with owners, design a semantic layer with conformed time, tariff history and access rules by region and classification, expose it to tools and agents, and evaluate a conversational assistant on certified questions, ending with a policy on which questions the assistant may answer. DS-307 covers single-area metrics, dashboards and a first agent test; this course designs the layer across business areas and governs the assistant.

**Format:** Intensive: 4 teaching days of four sessions and a capstone day, with guided pre-work and a tracked follow-up task

**Course page:** https://sdaiaacademy.github.io/ds-408/
<!-- /academy:title -->

## Outcomes

| | Outcomes | Level | Evidence |
|---|---|---|---|
| LO1 | Design a semantic layer with entities, grain, conformed time and governed metrics for several business areas, given the company's marts, a tariff history and Hijri and fiscal calendars | Performance | model files whose reconciliation tests pass against source totals |
| LO2 | Implement metric definitions as code with owners, tests and change control, given three conflicting definitions of the collection rate | Applied | metric files and one change taken through review in continuous integration |
| LO3 | Configure row-level access and field masking in the semantic layer according to data classification, given three user roles and the national classification levels | Applied | access tests that pass for each role and catch a seeded leak |
| LO4 | Evaluate a conversational assistant on certified questions, measuring accuracy, stability, wrong but plausible answers and the contribution of each kind of semantic context, given 60 bilingual questions with certified answers and a fixed model | Performance | a report from a harness a reviewer can re-run |
| LO5 | Decide which question types the assistant may answer and under which safeguards, given the evaluation results and a stated tolerance for wrong figures | Performance | a routing policy with a decision record |
| LO6 | Review the design of a peer's analytics product for correctness, portability and governance, given a peer's semantic model and evaluation | Performance | design review notes with findings ranked by risk |

<!-- academy:units -->
## Units

| Unit | Title | Sessions | Slides |
|---|---|---|---|
| Day 1 | Metrics as products | One metric, three owners; Metrics as code with tests; Ownership and change control; Certification and deprecation | [`slides/day1.html`](slides/day1.html) |
| Day 2 | Design the semantic layer | Conformed dimensions across areas; Performance and cost; Access rules; Portability | [`slides/day2.html`](slides/day2.html) |
| Day 3 | Test the assistant | A certified set for a platform; Which context helps; A scoring harness; Ask it again | [`slides/day3.html`](slides/day3.html) |
| Day 4 | Ship and govern | Serving metrics to tools and agents; Safeguards that show their work; Which questions may go to the assistant; Design review | [`slides/day4.html`](slides/day4.html) |
| Capstone | Capstone project presentations |  | [`slides/capstone.html`](slides/capstone.html) |
<!-- /academy:units -->

## Case study

**REPLACE: the name of the fictional organisation every lab works on.** REPLACE: two sentences on the case study and its synthetic data

<!-- academy:labs -->
## Labs

Every lab is a notebook in `labs/`. Open it in Google Colab from the course page, or run it locally with `uv`. Exercises raise `NotImplementedError` until they are done; the reference versions are in `labs/solutions/`.

| | Session | Lab | File |
|---|---|---|---|
| 1.1 | Day 1 · Session 1 | Reconcile the collection rate as finance, collections and customer care define it and agree one certified definition | [`D1_1_reconcile_collection_rate.ipynb`](labs/D1_1_reconcile_collection_rate.ipynb) |
| 1.2 | Day 1 · Session 2 | Implement five metrics, including a ratio and a cumulative metric, with reconciliation tests | [`D1_2_implement_five_metrics.ipynb`](labs/D1_2_implement_five_metrics.ipynb) |
| 1.3 | Day 1 · Session 3 | Write the change process for a metric and take one change through review | [`D1_3_write_change_process.ipynb`](labs/D1_3_write_change_process.ipynb) |
| 1.4 | Day 1 · Session 4 | Version and deprecate metrics in a 40-metric catalogue and list the reports that still use a deprecated one | [`D1_4_version_deprecate_metrics.ipynb`](labs/D1_4_version_deprecate_metrics.ipynb) |
| 2.1 | Day 2 · Session 1 | Model subscribers, lines, bills and complaints with conformed customer and time dimensions and fix a cross-area fan-out | [`D2_1_model_subscribers_lines.ipynb`](labs/D2_1_model_subscribers_lines.ipynb) |
| 2.2 | Day 2 · Session 2 | Add pre-aggregations for the ten most-asked metrics and measure query latency before and after | [`D2_2_add_pre_aggregations.ipynb`](labs/D2_2_add_pre_aggregations.ipynb) |
| 2.3 | Day 2 · Session 3 | Add row-level rules by region, mask Restricted fields and test with three roles | [`D2_3_add_row_level.ipynb`](labs/D2_3_add_row_level.ipynb) |
| 2.4 | Day 2 · Session 4 | Export the model to an open interchange format and query it from a second engine | [`D2_4_export_model_open.ipynb`](labs/D2_4_export_model_open.ipynb) |
| 3.1 | Day 3 · Session 1 | Extend the supplied certified set to cover each business area and difficulty level, including questions the assistant must refuse | [`D3_1_extend_supplied_certified.ipynb`](labs/D3_1_extend_supplied_certified.ipynb) |
| 3.2 | Day 3 · Session 2 | Remove synonyms, descriptions and examples one at a time from the supplied configuration and re-score each variant with the supplied scorer | [`D3_2_remove_synonyms_descriptions.ipynb`](labs/D3_2_remove_synonyms_descriptions.ipynb) |
| 3.3 | Day 3 · Session 3 | Build a harness that reports execution accuracy and the rate of wrong but plausible answers | [`D3_3_build_harness_that.ipynb`](labs/D3_3_build_harness_that.ipynb) |
| 3.4 | Day 3 · Session 4 | Run each question three times and measure how often the answers agree | [`D3_4_run_each_question.ipynb`](labs/D3_4_run_each_question.ipynb) |
| 4.1 | Day 4 · Session 1 | Expose the semantic layer through an API or protocol server with role-scoped credentials | [`D4_1_expose_semantic_layer.ipynb`](labs/D4_1_expose_semantic_layer.ipynb) |
| 4.2 | Day 4 · Session 2 | Make the assistant cite the metric and filters used and refuse uncertified metrics | [`D4_2_make_assistant_cite.ipynb`](labs/D4_2_make_assistant_cite.ipynb) |
| 4.3 | Day 4 · Session 3 | Set a routing policy from the evaluation and a stated tolerance for wrong figures | [`D4_3_set_routing_policy.ipynb`](labs/D4_3_set_routing_policy.ipynb) |
| 4.4 | Day 4 · Session 4 | Present the product design to a peer panel and log the decisions taken | [`D4_4_present_product_design.ipynb`](labs/D4_4_present_product_design.ipynb) |
<!-- /academy:labs -->

## Capstone

A governed analytics product for two business areas (metrics as code, a semantic layer with tested access rules, an assistant evaluation on at least 40 certified questions, a routing policy) in a public repository whose README reports measured accuracy and stability, defended in a design review

**Submission:** REPLACE: what participants submit and how: a public repository link, or a shared folder for a course without code

## Prerequisites

- DS-307 Metrics, Semantic Models and Dashboards
- Writes SQL over a star schema, including window functions
- Has defined metrics in a semantic layer or a BI calculation language

<!-- academy:tools -->
## Tools

Each line is a capability; the examples are interchangeable.

- **Transformation framework:** SQLMesh, dbt
- **Semantic layer and metric definitions:** MetricFlow, Cube Core, Apache Ossie (Open Semantic Interchange) files
- **Analytical engine:** DuckDB, PostgreSQL
- **Access for tools and agents:** a Model Context Protocol server, a REST API over the semantic layer
- **Language model through a chat-completions style endpoint:** a locally served open-weight model, a free hosted model
- **Evaluation harness:** pytest with custom assertions, promptfoo, Inspect
<!-- /academy:tools -->

<!-- academy:sources -->
## Sources

- REPLACE: every source the course cites, with its address, in course.json under "sources"; this list is written from there
<!-- /academy:sources -->

### National references

- NDMO Data Management and Personal Data Protection Standards (Business Intelligence and Analytics domain): REPLACE: the address of the official text
- NDMO Data Classification Policy: REPLACE: the address of the official text
- Personal Data Protection Law and its implementing regulations: REPLACE: the address of the official text
- SDAIA Generative AI Guidelines for Government: REPLACE: the address of the official text
- National AI Risk Management Framework: REPLACE: the address of the official text
