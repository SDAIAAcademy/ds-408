---
course: "Analytics Products: Semantic Layers and Conversational Analytics"
code: "DS-408"
version: "2027.1.0"
language: "en"
view: "trainee"
source: "https://sdaiaacademy.github.io/ds-408/index.html"
---

# Analytics Products: Semantic Layers and Conversational Analytics

منتجات التحليلات: الطبقات الدلالية والتحليلات الحوارية

Data Science Track · 4 teaching days + capstone day · 26 hours · Level 400

Define metrics once as tested code, serve them through a governed semantic layer, and let an assistant answer only the questions it has proved it can answer

Participants build the analytics product of the fictional Qamar Telecom, whose 300 managers want to ask questions in Arabic and English about usage, billing, collections and complaints. They define metrics once as tested code with owners, design a semantic layer with conformed time, tariff history and access rules by region and classification, expose it to tools and agents, and evaluate a conversational assistant on certified questions, ending with a policy on which questions the assistant may answer. DS-307 covers single-area metrics, dashboards and a first agent test; this course designs the layer across business areas and governs the assistant.

**Who it is for:** Specialists. Data scientists who have completed the level 300 core and practicum, or can show equivalent work: an analysis they led from question to recommendation and defended.

**Format:** Intensive: 4 teaching days of four sessions and a capstone day, with guided pre-work and a tracked follow-up task

## The case study

**Qamar Telecom.** Qamar Telecom is a fictional Saudi telecom operator whose 300 managers want to ask, in Arabic and English, about usage, billing, collections and complaints, while finance, collections and customer care each report a different collection rate. Participants certify one collection rate, write the metrics as tested code with owners and change control, build a conformed semantic layer with tariff history, fiscal and Hijri calendars and access rules by region and classification, export it to an open format, serve it to tools and agents, and evaluate Muhsi, the bilingual assistant, on 60 certified questions before deciding which questions it may answer. All data is synthetic and generated with a fixed seed.

## The course

### Day 1: Metrics as products

Slides: https://sdaiaacademy.github.io/ds-408/slides/day1.md

- **Session 1: One metric, three owners**
  - Compute one metric as each of its owners defines it
  - Separate a data error from a definition choice with a walk
  - Write a certified definition with an owner and its choices
  - [Lab 1.1: Three collection rates, one certified (25 min)](https://sdaiaacademy.github.io/ds-408/labs/D1_1_collection_rate.ipynb)
- **Session 2: Metrics as code with tests**
  - Write simple, ratio, cumulative and derived metrics as code
  - Explain why a ratio is computed after aggregation
  - Prove a metric against an independent total from the marts
  - [Lab 1.2: Five metrics as code (25 min)](https://sdaiaacademy.github.io/ds-408/labs/D1_2_metrics_as_code.ipynb)
- **Session 3: Ownership and change control**
  - Distinguish the owner, the steward and the approver of a metric
  - Version a metric change as major, minor or patch
  - Take a change through review rules that run in continuous integration
  - [Lab 1.3: A change taken through review (25 min)](https://sdaiaacademy.github.io/ds-408/labs/D1_3_change_control.ipynb)
- **Session 4: Certification and deprecation**
  - Check a metric catalogue for owners and tests
  - Deprecate a metric with a successor and a sunset date
  - Find every report that depends on a deprecated metric, directly or through lineage
  - [Lab 1.4: Deprecate in a 40-metric catalogue (25 min)](https://sdaiaacademy.github.io/ds-408/labs/D1_4_catalogue_lifecycle.ipynb)

### Day 2: Design the semantic layer

Slides: https://sdaiaacademy.github.io/ds-408/slides/day2.md

- **Session 1: Conformed dimensions across areas**
  - Model several business areas on conformed customer and time dimensions
  - Detect and remove a cross-area fan-out by drilling across
  - Join a type 2 tariff history as of the fact's date
  - [Lab 2.1: Four areas, one customer, one calendar (25 min)](https://sdaiaacademy.github.io/ds-408/labs/D2_1_conformed_model.ipynb)
- **Session 2: Performance and cost**
  - Choose pre-aggregations from a query log
  - Measure latency and rows scanned before and after
  - Explain which metrics cannot roll up from a pre-aggregation
  - [Lab 2.2: Pre-aggregations for the most-asked queries (25 min)](https://sdaiaacademy.github.io/ds-408/labs/D2_2_pre_aggregations.ipynb)
- **Session 3: Access rules**
  - Map the national classification levels to fields of the model
  - Write row rules and masking in the semantic layer
  - Test access for each role and catch a seeded leak
  - [Lab 2.3: Three roles and a seeded leak (25 min)](https://sdaiaacademy.github.io/ds-408/labs/D2_3_access_rules.ipynb)
- **Session 4: Portability**
  - Export a semantic model to an open interchange format
  - Run the exported model on a second engine and compare
  - Name what does not port: access rules, cumulative metrics, dialects
  - [Lab 2.4: Export to Ossie, query from SQLite (25 min)](https://sdaiaacademy.github.io/ds-408/labs/D2_4_portability.ipynb)

### Day 3: Test the assistant

Slides: https://sdaiaacademy.github.io/ds-408/slides/day3.md

- **Session 1: A certified set for a platform**
  - Write a certified answer as value, metric, filters and grain
  - Cover areas, difficulty levels and both languages
  - Include questions the assistant must refuse
  - [Lab 3.1: From 44 to 60 certified questions (25 min)](https://sdaiaacademy.github.io/ds-408/labs/D3_1_certified_set.ipynb)
- **Session 2: Which context helps**
  - Design an ablation that changes one kind of context at a time
  - Score each variant with a fixed model and question set
  - Read the contribution of each kind of context by language and area
  - [Lab 3.2: Remove one kind of context at a time (25 min)](https://sdaiaacademy.github.io/ds-408/labs/D3_2_context_ablation.ipynb)
- **Session 3: A scoring harness**
  - Score an answer by executing it and comparing with the certified value
  - Separate wrong but plausible answers from obvious failures
  - Write an evaluation report that a reviewer can re-run
  - [Lab 3.3: Accuracy and wrong but plausible (25 min)](https://sdaiaacademy.github.io/ds-408/labs/D3_3_scoring_harness.ipynb)
- **Session 4: Ask it again**
  - Measure answer agreement across repeated runs
  - Separate stable right, stable wrong and unstable answers
  - Explain what a response cache hides from a stability test
  - [Lab 3.4: Three runs per question (25 min)](https://sdaiaacademy.github.io/ds-408/labs/D3_4_stability.ipynb)

### Day 4: Ship and govern

Slides: https://sdaiaacademy.github.io/ds-408/slides/day4.md

- **Session 1: Serving metrics to tools and agents**
  - Expose semantic-layer queries as tools of a protocol server
  - Take the caller's role from the credential, never from the request
  - Test the server for each role
  - [Lab 4.1: A protocol server with role-scoped credentials (25 min)](https://sdaiaacademy.github.io/ds-408/labs/D4_1_serve_layer.ipynb)
- **Session 2: Safeguards that show their work**
  - Show the metric, filters, grain and version behind each figure
  - Refuse uncertified metrics, Restricted fields and questions without a period
  - Measure the effect of the safeguards on the certified set
  - [Lab 4.2: Cite the metric, refuse the uncertified (25 min)](https://sdaiaacademy.github.io/ds-408/labs/D4_2_safeguards.ipynb)
- **Session 3: Which questions may go to the assistant**
  - Estimate the wrong-figure rate by question type with an upper bound
  - Route each question type under a stated tolerance
  - Record the decision with its evidence and its review date
  - [Lab 4.3: A routing policy from the evaluation (25 min)](https://sdaiaacademy.github.io/ds-408/labs/D4_3_routing_policy.ipynb)
- **Session 4: Design review**
  - Review a semantic model and an evaluation with a checklist
  - Rank findings by likelihood and impact
  - Log the decisions a review panel takes
  - [Lab 4.4: Review a peer's product (25 min)](https://sdaiaacademy.github.io/ds-408/labs/D4_4_design_review.ipynb)

### Capstone: Capstone: a governed analytics product and its design review

Slides: https://sdaiaacademy.github.io/ds-408/slides/capstone.md

## Capstone

A governed analytics product for two business areas (metrics as code, a semantic layer with tested access rules, an assistant evaluation on at least 40 certified questions, a routing policy) in a public repository whose README reports measured accuracy and stability, defended in a design review

**What you submit:** A public GitHub repository for two business areas of Qamar Telecom: metric files with tests and the review rules in continuous integration, the semantic model with access rules and their tests, an evaluation of the assistant on at least 40 certified questions (accuracy, wrong but plausible answers, stability over three runs) from a harness a reviewer can re-run, and a routing policy with its decision record; the README reports the measured accuracy and stability. Then a live design review in which the participant re-runs the evaluation on five questions the assessor adds.

**Rubric:**

- Semantic model and metrics: 30%
- Access rules: 15%
- Assistant evaluation: 30%
- Routing policy: 15%
- Reproducibility: 10%

## Outcomes

- **LO1** Design a semantic layer with entities, grain, conformed time and governed metrics for several business areas, given the company's marts, a tariff history and Hijri and fiscal calendars (Performance) Evidence: model files whose reconciliation tests pass against source totals
- **LO2** Implement metric definitions as code with owners, tests and change control, given three conflicting definitions of the collection rate (Applied) Evidence: metric files and one change taken through review in continuous integration
- **LO3** Configure row-level access and field masking in the semantic layer according to data classification, given three user roles and the national classification levels (Applied) Evidence: access tests that pass for each role and catch a seeded leak
- **LO4** Evaluate a conversational assistant on certified questions, measuring accuracy, stability, wrong but plausible answers and the contribution of each kind of semantic context, given 60 bilingual questions with certified answers and a fixed model (Performance) Evidence: a report from a harness a reviewer can re-run
- **LO5** Decide which question types the assistant may answer and under which safeguards, given the evaluation results and a stated tolerance for wrong figures (Performance) Evidence: a routing policy with a decision record
- **LO6** Review the design of a peer's analytics product for correctness, portability and governance, given a peer's semantic model and evaluation (Performance) Evidence: design review notes with findings ranked by risk

## Tools

- **Transformation framework:** SQLMesh, dbt
- **Semantic layer and metric definitions:** MetricFlow, Cube Core, Apache Ossie (Open Semantic Interchange) files
- **Analytical engine:** DuckDB, PostgreSQL
- **Access for tools and agents:** a Model Context Protocol server, a REST API over the semantic layer
- **Language model through a chat-completions style endpoint:** a locally served open-weight model, a free hosted model
- **Evaluation harness:** pytest with custom assertions, promptfoo, Inspect

## Prerequisites

- DS-307 Metrics, Semantic Models and Dashboards
- Writes SQL over a star schema, including window functions
- Has defined metrics in a semantic layer or a BI calculation language
- Setup: a laptop CPU with uv, or Google Colab. Nothing downloads a model; the assistant labs replay recorded replies of a scripted stand-in model, and a free hosted model is optional. Run 00_setup_check before Day 1; see labs/README.md.

## Sources

### National references

- [NDMO Data Management and Personal Data Protection Standards (Business Intelligence and Analytics domain)](https://sdaia.gov.sa/en/SDAIA/about/Documents/DataManagementPersonalDataProtectionStandards.pdf)
- [NDMO Data Classification Policy](https://sdaia.gov.sa/en/SDAIA/about/Documents/DataClassificationPolicy.pdf)
- [Personal Data Protection Law](https://sdaia.gov.sa/en/SDAIA/about/Documents/PersonalDataProtectionLaw.pdf)
- [Implementing Regulation of the Personal Data Protection Law](https://sdaia.gov.sa/en/SDAIA/about/Documents/ImplementingRegulationPersonalDataProtectionLaw.pdf)
- [SDAIA Generative AI Guidelines for Government](https://sdaia.gov.sa/en/SDAIA/about/Files/GenAIGuidelinesForGovernmentENCompressed.pdf)
- [National AI Risk Management Framework, English executive summary (SDAIA, April 2026)](https://sdaia.gov.sa/en/MediaCenter/KnowledgeCenter/ResearchLibrary/ExecutiveSummaryEn.pdf)

### Semantic layers and metrics as code

- [Apache Ossie (Incubating): the new name for Open Semantic Interchange](https://ossie.apache.org/updates/ossie-enters-apache-incubator/)
- [Apache Ossie core metadata specification (draft 0.3.0.dev0)](https://github.com/apache/ossie/blob/main/core-spec/spec.md)
- [Apache Ossie converters](https://github.com/apache/ossie-converters)
- [MetricFlow](https://github.com/dbt-labs/metricflow)
- [dbt documentation: about MetricFlow](https://docs.getdbt.com/docs/build/about-metricflow)
- [Cube documentation: data modeling concepts](https://cube.dev/docs/product/data-modeling/concepts)
- [Cube Core](https://github.com/cube-js/cube)
- [SQLMesh documentation](https://sqlmesh.readthedocs.io/en/stable/)
- [dbt Core](https://github.com/dbt-labs/dbt-core)

### Engines and libraries

- [DuckDB documentation](https://duckdb.org/docs/stable/)
- [DuckDB on PyPI](https://pypi.org/project/duckdb/)
- [SQLite: date and time functions](https://www.sqlite.org/lang_datefunc.html)
- [hijridate: Hijri and Gregorian dates on the Umm al-Qura calendar](https://pypi.org/project/hijridate/)
- [uv: running scripts with inline dependencies](https://docs.astral.sh/uv/guides/scripts/)

### Serving to tools and agents

- [Model Context Protocol specification, revision 2025-11-25](https://modelcontextprotocol.io/specification/2025-11-25)
- [Model Context Protocol specification: tools](https://modelcontextprotocol.io/specification/2025-11-25/server/tools)
- [Model Context Protocol Python SDK](https://github.com/modelcontextprotocol/python-sdk)

### Evaluating conversational analytics

- [Lei et al., Spider 2.0: Evaluating Language Models on Real-World Enterprise Text-to-SQL Workflows (ICLR 2025)](https://arxiv.org/abs/2411.07763)
- [BIRD: a big bench for large-scale database grounded text-to-SQL evaluation](https://bird-bench.github.io/)
- [promptfoo documentation](https://www.promptfoo.dev/docs/intro/)
- [Inspect, an evaluation framework from the UK AI Security Institute](https://inspect.aisi.org.uk/)
- [OpenRouter: free models](https://openrouter.ai/models?max_price=0)
- [OpenRouter API: limits](https://openrouter.ai/docs/api/reference/limits)

---

SDAIA Academy · Data Science Track · Analytics Products: Semantic Layers and Conversational Analytics

Course version 2027.1.0 · engine 1.0.0 · built 2026-11-16 · commit 30c3cc0
