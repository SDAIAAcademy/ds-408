---
course: "Analytics Products: Semantic Layers and Conversational Analytics"
code: "DS-408"
version: "2027.1.0"
deck: "day2"
day: 2
language: "en"
view: "trainee"
source: "https://sdaiaacademy.github.io/ds-408/slides/day2.html"
---

# Analytics Products: Semantic Layers and Conversational Analytics

## Day 2: Design the semantic layer

Conformed, fast, governed and portable

#### [day2#title] Design the semantic layer

*SDAIA Academy · Analytics Products: Semantic Layers and Conversational Analytics*

Day 2: Conformed, fast, governed and portable

Data Science Track · 4 teaching days + capstone day · 4 sessions · 4 labs · DS-408

#### [day2#agenda] Design the semantic layer

*Today*

- **Session 1 · Conformed dimensions across areas**: One customer, one region and one calendar shared by four business areas, joined without multiplying a figure
- **Session 2 · Performance and cost**: Pre-aggregations for the questions people actually ask, measured before and after
- **Session 3 · Access rules**: Row rules by region and masking by classification, written in the layer and tested for each role
- **Session 4 · Portability**: What an open interchange format carries between tools, and what stays behind

#### [day2#review-day1] A change that looks harmless

*Review of Day 1*

**Question:** A steward fixes a typo in the description of `collection_rate` and also changes its window from 30 to 31 days "to be safe". Version 1.0.0 becomes 1.0.1. What does review find?

- A. A meaning change hidden in a patch: it needs a major version and the owner's approval
- B. Nothing: a typo fix is a patch
- C. A minor version is enough for one more day
- D. The duplicate batch rule applies: fix it in the data

### Session 1: Conformed dimensions across areas

#### [day2#s1] Conformed dimensions across areas

*Session 1*

- Model several business areas on conformed customer and time dimensions
- Detect and remove a cross-area fan-out by drilling across
- Join a type 2 tariff history as of the fact's date

#### [day2#cross-area-question] "Billing and complaints by region and month, in one table"

*The question that crosses areas*

- Two facts at different grains: one bill per account and month; one row per complaint
- Two calendars to agree on: service month for bills, opening day for complaints
- Two regions to choose between: the customer's, or where the complaint was raised

- **What the layer must guarantee.** Each figure is the same as it would be alone, whatever it is shown beside.

#### [day2#wide-join] One wide join multiplies both figures

*Lab 2.1, step 2*

```sql
-- file: the wide query
SELECT c.region_code,
       SUM(b.amount_due)     AS billed,
       COUNT(q.complaint_id) AS complaints
FROM dim_customer c
JOIN fct_bill b USING (customer_id)
LEFT JOIN fct_complaint q USING (customer_id)
GROUP BY 1;
```

- **1.48×** billed amount, against the source
- **13.3×** complaints, against the source

#### [day2#drill-across] Drill across: aggregate each fact alone, then join on the shared keys

*The fix the layer applies for you*

1. **1 · Bills** billed amount by region and month
2. **2 · Complaints** complaints by region and month
3. **3 · Join** one row per region and month on each side

The join meets one row per key on each side, so nothing repeats. It needs every area to reach the same customer and calendar: conformed dimensions.

#### [day2#conformed] A dimension is conformed when every area reaches the same rows with the same keys

*One customer, one region, one calendar*

| Area | Reaches customer through | Reaches the calendar on |
| --- | --- | --- |
| Usage | line, then customer | usage month |
| Billing and collections | customer | service month |
| Payments | customer | paid date |
| Complaints | customer (added in Lab 2.1) | opening day (added in Lab 2.1) |

#### [day2#eastern-january] In January 2026 the Eastern region's complaints rate more than doubled

*What the conformed model shows*

| Item | Value |
| --- | --- |
| Nov 2025 | 30.6 |
| Dec 2025 | 42.3 |
| Jan 2026 | 98.1 |
| Feb 2026 | 39.9 |

Complaints per 1,000 active lines, Eastern region, customer's region. The billed amount kept its steady growth of about 5% a month.

#### [day2#tariff-history] A price change makes two tariff rows; the join must pick the one valid that month

*Lab 2.1, step 4*

| Plan | Fee (SAR) | Valid |
| --- | --- | --- |
| Qamar Fibre 100 | 299 | to 30 Sep 2025 |
| Qamar Fibre 100 | 279 | from 1 Oct 2025 |
| Qamar Postpaid M | 149 | to 30 Sep 2025 |
| Qamar Postpaid M | 165 | from 1 Oct 2025 |

> **Join on the code only:** data by plan sums to 4,769,001 GB.

> **Join as of the usage month:** 3,043,658 GB, the source total.

#### [day2#reconcile-model] A model is done when its parts add up to the source, area by area

*The evidence for the first outcome*

- One reconciliation test per area: usage, billing, collections, complaints
- Regions add up to the total for the billed amount; plans add up to the total for data
- Run in CI with the metric tests, so a model change that breaks a total cannot merge

> **Totals are the minimum.** A split that does not add up (by plan before the as-of join) is a test worth keeping.

#### [day2#checkpoint-1] A dashboard that adds up wrongly

*Checkpoint*

**Question:** A dashboard shows data used by plan. The plan rows add up to 1.6 times the company total. Two plans changed price last October. What is the most likely cause?

- A. Duplicate usage records in the source
- B. The fiscal year starts in April
- C. Active lines are counted as distinct lines
- D. The tariff is joined on its code, so lines of those plans match two price rows

#### [day2#lab-2-1] Four areas, one customer, one calendar

Lab 2.1 · 25 min

Model subscribers, lines, bills and complaints with conformed customer and time dimensions, fix a cross-area fan-out and a tariff join without validity dates, and prove the model with reconciliation tests against source totals.

[D2_1_conformed_model.ipynb](https://sdaiaacademy.github.io/ds-408/labs/D2_1_conformed_model.ipynb)

- [ ] Read the starter model (4 min)
- [ ] The wide query and its fan-out (6 min)
- [ ] Drill across instead (6 min)
- [ ] Tariff history as of the month (5 min)
- [ ] Reconcile four areas to the source (4 min)
- [ ] ✱ Stretch: The same figure by Hijri month and by fiscal quarter

### Session 2: Performance and cost

#### [day2#s2] Performance and cost

*Session 2*

- Choose pre-aggregations from a query log
- Measure latency and rows scanned before and after
- Explain which metrics cannot roll up from a pre-aggregation

#### [day2#what-is-asked] Ten question shapes are 91% of a month's queries

*Lab 2.2, step 1*

| Metrics | Grouped by | Queries |
| --- | --- | --- |
| data from sessions | region, month | 64 |
| sessions | month | 58 |
| data from sessions | segment, fiscal year | 37 |
| data, lines with a session | plan | 37 |
| sessions | region, segment | 33 |

The first five of ten, from 400 logged queries. Filters change; shapes repeat.

#### [day2#preagg-idea] A pre-aggregation stores additive measures at a coarser grain, and the layer routes to it

*What a pre-aggregation is*

- **Additive only.** Sums and counts. A ratio uses its stored numerator and denominator.
- **Covers the query.** Every group-by and filter field of the query is among its fields.
- **Same answer.** Routing changes the cost, never the number. Test that.

#### [day2#preagg-results] Four pre-aggregations cut rows scanned by 92% and latency by 84%

*Lab 2.2, steps 3 and 4*

- **36.5M → 2.8M** rows scanned by the ten shapes
- **1,426 → 225 ms** total latency, one laptop, full size

- Region and month, plan and quarter, day, city: 540, 48, 504 and 17 rows
- Every answer equal to the answer before
- One shape still reads the session table

#### [day2#cannot-roll-up] A distinct count cannot be summed from a coarser table

*Lab 2.2, step 5*

- **3,253** lines with a session in FY2025-26
- **31,226** the twelve monthly counts, added

A line active all year is counted twelve times. The layer refuses to pre-aggregate it; some tools store a sketch instead and accept an approximate answer.

#### [day2#freshness] Every copy goes stale: rebuild by the dataset that changed

*The cost on the other side*

- Late payments touch `payment` and `collection`, not usage
- A rebuild rule per dataset, not one nightly rebuild of everything
- Show the refresh time beside each figure the copy serves

> **Stale and fast is still wrong.** A collection rate served from yesterday's copy after a late batch arrives is a wrong but plausible figure.

#### [day2#checkpoint-2] Which question can the pre-aggregation serve?

*Checkpoint*

**Question:** A pre-aggregation stores data and sessions by region, segment, session kind, month and fiscal year. Which question does the layer route to it?

- A. Data by city for March 2026
- B. Sessions by region for the fiscal year 2025-26
- C. Lines with a session by month
- D. Data by day in January 2026

#### [day2#lab-2-2] Pre-aggregations for the most-asked queries

Lab 2.2 · 25 min

Add pre-aggregations for the ten most-asked metric patterns of the query log, measure query latency and rows scanned before and after, and check that every answer stayed the same.

[D2_2_pre_aggregations.ipynb](https://sdaiaacademy.github.io/ds-408/labs/D2_2_pre_aggregations.ipynb)

- [ ] The ten most-asked patterns (5 min)
- [ ] Baseline latency and rows scanned (5 min)
- [ ] Define the pre-aggregations (7 min)
- [ ] Measure again, compare the answers (5 min)
- [ ] The metric that cannot roll up (3 min)
- [ ] ✱ Stretch: Which pre-aggregations to rebuild when late payments arrive

### Session 3: Access rules

#### [day2#s3] Access rules

*Session 3*

- Map the national classification levels to fields of the model
- Write row rules and masking in the semantic layer
- Test access for each role and catch a seeded leak

#### [day2#classification-levels] Four national levels; Qamar's register marks its customer identifiers Restricted

*NDMO Data Classification Policy*

- **Top Secret.** Exceptionally serious, irreparable harm.
- **Secret.** Serious harm.
- **Restricted.** Limited harm; sub-levels A, B and C by scale of impact.
- **Public.** No harm from disclosure.

In the case: full name, national identifier, mobile number and date of birth are Restricted (a fictional register).

#### [day2#three-roles-access] Three roles: what rows and which fields each one sees

*The access policy*

| Role | Rows | Restricted fields |
| --- | --- | --- |
| Executive | all regions | masked |
| Regional manager, Eastern | Eastern region only | masked |
| Collections officer | all regions | visible, to contact customers who owe |

> **Rules in the layer, not in the dashboard.** Every consumer, the assistant included, passes through the same rules.

#### [day2#access-tests] Test every role against every area, by asking as that role

*Lab 2.3, step 2*

```python
# file: Lab 2.3
for role, r in policy["roles"].items():
    m = model.as_role(role, policy=policy)
    for area, (metric, region) in AREAS.items():
        seen = set(m.query([metric], by=[region])[region])
        passed = r["regions"] == "all" or seen <= set(r["regions"])
    for field in ("customer.full_name", "customer.contact_name"):
        masked = set(m.query(["billed_amount"], by=[field])[field]) == {"***"}
        passed = masked != r["restricted"]
```

#### [day2#two-leaks] Three of 21 tests fail, and they point at two leaks

*Lab 2.3, step 3*

- **A dataset without a rule.** The Eastern manager sees complaints of all five regions: 612 in the Central region alone. The policy has no rule for `complaint`, and the layer allowed by default.
- **A copy without its label.** `contact_name` takes the first word of `full_name`. Nobody tagged it, so the executive and the manager read first names.

#### [day2#fix-the-cause] Fix the cause: a rule per dataset, deny by default, classify by lineage

*Lab 2.3, step 4*

1. **1 · Rule** complaints by the region where raised
2. **2 · Deny by default** no rule means an error for a limited role
3. **3 · Lineage** a field reading a Restricted column is Restricted

After the fix, 21 of 21 tests pass. The tests stay, and run in CI with the metric tests.

#### [day2#checkpoint-3] A new area arrives

*Checkpoint*

**Question:** Next quarter Qamar adds a `roaming` dataset to the layer and forgets its row rule. With the fixed layer, what does the Eastern regional manager get when asking for roaming by region?

- A. Every region's roaming, without a warning
- B. Only Eastern roaming, inferred from the customer join
- C. An error saying the role has no row rule for the dataset
- D. Every region's roaming with the figures masked

#### [day2#lab-2-3] Three roles and a seeded leak

Lab 2.3 · 25 min

Add row-level rules by region, mask Restricted fields and test with three roles; the tests find a dataset without a rule and a field that copies a Restricted column without its label.

[D2_3_access_rules.ipynb](https://sdaiaacademy.github.io/ds-408/labs/D2_3_access_rules.ipynb)

- [ ] The roles and the classification register (4 min)
- [ ] Access tests for each role (7 min)
- [ ] Find the two leaks (5 min)
- [ ] Fix the policy and the layer (6 min)
- [ ] Run the tests again (3 min)
- [ ] ✱ Stretch: An audit line for every query

### Session 4: Portability

#### [day2#s4] Portability

*Session 4*

- Export a semantic model to an open interchange format
- Run the exported model on a second engine and compare
- Name what does not port: access rules, cumulative metrics, dialects

#### [day2#why-portable] Definitions written once should outlive the tool that serves them

*Open interchange*

- **Apache Ossie** (incubating), formerly Open Semantic Interchange: one YAML or JSON document per model
- Datasets, fields, relationships and model-scoped metrics; AI context such as synonyms
- The core specification is a draft, 0.3.0.dev0: expect changes

- **From DS-307.** You wrote a first model in this format. Today you export a whole layer and run it somewhere else.

#### [day2#ossie-shape] An Ossie metric is one SQL aggregate over dataset fields

*Lab 2.4, step 1*

```yaml
# file: qamar_telecom.ossie.yaml
version: 0.3.0.dev0
name: qamar_telecom
datasets:
  - name: bill
    source: fct_bill
    fields:
      - name: service_month
        expression: {sql: "strftime(bill_month, '%Y-%m')"}
metrics:
  - name: collection_rate
    expression:
      sql: (SUM(CASE WHEN collection.matured_30 THEN collection.paid_30 END)) * 1.0
         / (SUM(CASE WHEN collection.matured_30 THEN collection.net_due END))
```

#### [day2#second-engine] On a second engine, two queries fail loudly and one is quietly wrong

*Lab 2.4, steps 3 and 4*

| Metric, grouped by | On SQLite | Fix |
| --- | --- | --- |
| billed amount, service month | one row, month empty, all SAR 9,366,506 | `strftime('%Y-%m', bill_month)` |
| collection rate, segment | error: no function `split_part` | a SQLite expression for `contact_name` |
| complaints, region | error: no function `date_diff` | a SQLite expression with `julianday` |

With a `dialects` entry for each field, DuckDB and SQLite agree on all three.

#### [day2#not-travelled] Definitions travel; governance and some logic stay behind

*Lab 2.4, step 5*

- Access rules and roles: not in the core at all
- Classification of fields, the as-of tariff join: vendor extensions only
- The cumulative metric, and `MEDIAN`, which SQLite lacks
- Two datasets defined as DuckDB queries: materialized as tables first

> **Moving tools moves the risk.** The access tests of Lab 2.3 must be carried and re-run on the new tool by hand.

#### [day2#checkpoint-4] The test that would have caught it

*Checkpoint*

**Question:** After a move to a new engine, the billed amount by service month shows one row with an empty month and the amount of all months together. Which test, run on the new engine, catches this before a manager sees it?

- A. Reconcile the billed amount by month with the source, not only in total
- B. Reconcile the billed amount in total with the source
- C. Validate the exported document against the specification
- D. Re-run the access tests for the three roles

#### [day2#lab-2-4] Export to Ossie, query from SQLite

Lab 2.4 · 25 min

Export the model to an Apache Ossie document, compile three metrics from it for a second engine (SQLite), compare the results with DuckDB and fix the expression that did not port.

[D2_4_portability.ipynb](https://sdaiaacademy.github.io/ds-408/labs/D2_4_portability.ipynb)

- [ ] Export the model (6 min)
- [ ] Check the document (4 min)
- [ ] Compile three metrics for SQLite (6 min)
- [ ] Compare and fix the expression that did not port (6 min)
- [ ] What did not travel (3 min)
- [ ] ✱ Stretch: Round-trip: read the Ossie document back into the layer

#### [day2#wrap-up] Three things to keep

*Day 2 · Wrap-up*

- **Conform, then drill across.** Shared customer and calendar; each fact aggregated alone; history joined as of the date.
- **Govern in the layer.** Rows by rule, fields by lineage, deny by default, tested for every role.
- **Measure, then copy.** Pre-aggregate what the log shows; port what the core holds; test both at the grain.

#### [day2#next] Day 3: test the assistant

*Next*

- Sixty certified questions in Arabic and English
- Bring three questions your managers would ask an assistant, one of them in Arabic
- Optional: a free OpenRouter key, for the live stretch of Lab 3.2
