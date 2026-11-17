---
course: "Analytics Products: Semantic Layers and Conversational Analytics"
code: "DS-408"
version: "2027.1.0"
deck: "day1"
day: 1
language: "en"
view: "trainee"
source: "https://sdaiaacademy.github.io/ds-408/slides/day1.html"
---

# Analytics Products: Semantic Layers and Conversational Analytics

## Day 1: Metrics as products

Define a metric once, as code, with an owner

#### [day1#title] Metrics as products

*SDAIA Academy · Analytics Products: Semantic Layers and Conversational Analytics*

Day 1: Define a metric once, as code, with an owner

Data Science Track · 4 teaching days + capstone day · 4 sessions · 4 labs · DS-408

#### [day1#agenda] Metrics as products

*Today*

- **Session 1 · One metric, three owners**: Why three collection rates disagree, and how a walk turns the disagreement into decisions
- **Session 2 · Metrics as code with tests**: A metric as a file with an owner, a version, a status and reconciliation tests
- **Session 3 · Ownership and change control**: Who may change a metric, how its version moves, and review rules that run in continuous integration
- **Session 4 · Certification and deprecation**: The life of a metric in a catalogue: certified, deprecated with a successor, followed through lineage to the reports

#### [day1#qamar-case] Qamar Telecom: 300 managers, four business areas, one question each morning

*The case for four days*

- **Usage.** Data, voice and active lines per month, by plan and region.
- **Billing.** One bill per postpaid or fibre account and month, tariffs that change.
- **Collections.** Payments against bills, disputes, late payers in the government segment.
- **Complaints.** Billing, network, service and device complaints, in every region.

Managers want to ask in Arabic and English. Muhsi (مُحصي), the assistant you will test on Day 3, may answer only what this course proves it can answer.

#### [day1#product-not-report] An analytics product has users, owners and releases, not just queries

*What changes at this level*

|  | A report | An analytics product |
| --- | --- | --- |
| Definition | inside one dashboard's formula | a metric file, reviewed, versioned |
| Owner | whoever built it | a named business owner and a steward |
| Proof | it looked right last month | tests against source totals, in CI |
| Consumers | one audience | dashboards, notebooks, tools and an assistant |
| Change | edited in place | announced, approved, deprecated with a successor |

### Session 1: One metric, three owners

#### [day1#s1] One metric, three owners

*Session 1*

- Compute one metric as each of its owners defines it
- Separate a data error from a definition choice with a walk
- Write a certified definition with an owner and its choices

#### [day1#three-rates] Three owners report three collection rates for the same month

*March 2026, one meeting*

- **94.1%** Finance: cash received in March over March's billing
- **93.8%** Collections: March bills paid within 60 days of due, net of disputes
- **73.5%** Customer care: share of March bills paid in full by the due date

Each is computed correctly from its own definition. None of them is "the" collection rate yet.

#### [day1#what-differs] Four choices separate the three definitions

*Read the definitions, not the numbers*

| Choice | Finance | Collections | Customer care |
| --- | --- | --- | --- |
| Population | cash that arrived in March | March's bills | March's bills |
| Window | the calendar month | 60 days after due | by the due date |
| Disputes | in the denominator | out | out |
| Unit | value | value | count of bills |

> **And one thing that is not a choice.** The finance figure reads the payments table as loaded.

#### [day1#walk] A walk turns one argument into four separate decisions

*A bridge, one change at a time*

| Item | Value |
| --- | --- |
| Finance as reported | 94.1% |
| Duplicate batch removed | 90.2% |
| Cohort, 60 days, gross | 92.9% |
| Disputes out | 93.8% |
| Window 30 days | 86.5% |

Each row changes one thing. The council decides each row on its own merit.

#### [day1#data-error] A payment batch loaded twice is a data error, fixed once in the data

*Lab 1.1, step 2*

```sql
-- file: Lab 1.1
SELECT batch_id,
       COUNT(*) - COUNT(DISTINCT (bill_id, paid_date, amount)) AS extra_rows,
       SUM(amount) FILTER (WHERE load_no > 1)                  AS extra_amount
FROM fct_payment
GROUP BY batch_id HAVING extra_rows > 0;
-- B20260317 | 80 | 24802.51
```

> **Not in a report formula.** Fix it in the payment mart, so every metric built on payments is right at once.

#### [day1#council-criteria] Agree on criteria first; the definition follows from them

*How the council decides*

- **Comparable month to month:** a cohort of bills, not whatever cash arrived
- **Closes in time:** before the second month-end close after the due date
- **Owed now:** disputed amounts out until the dispute is decided
- **Value, not count:** the board manages cash

- **Certified collection rate.** Value paid within 30 days of the due date on the month's bills, over the amount due net of open disputes, deduplicated, reported once the window has closed. March 2026: **86.5%**.

#### [day1#maturity] A cohort metric is not reported until its window has closed

*A rule that looks like a detail*

- **Without the rule.** May 2026 bills are due on 24 June; with data to 30 June, almost no 30-day window has closed. The rate looks like a collapse.
- **With the rule.** The metric reports a cohort only when due date plus 30 days is on or before the cut-off. May waits for August.

> **An assistant will not know this.** Unless the layer enforces it, "what was the collection rate last month?" gets a wrong but plausible answer.

#### [day1#checkpoint-1] The meeting wants one number by tomorrow

*Checkpoint*

**Question:** The chief financial officer asks you to "just average the three collection rates" for the board pack until the council meets. What do you do?

- A. Report the average, 87.1%, with a footnote
- B. Report the walk, and the certified definition's value once the council agrees it
- C. Report the finance figure, since finance owns the board pack
- D. Report the care figure, since it is the most cautious

#### [day1#lab-1-1] Three collection rates, one certified

Lab 1.1 · 25 min

Reconcile the collection rate as finance, collections and customer care define it, find the payment batch loaded twice, walk from one figure to another and agree one certified definition. Done without AI assistance.

[D1_1_collection_rate.ipynb](https://sdaiaacademy.github.io/ds-408/labs/D1_1_collection_rate.ipynb)

- [ ] Three rates for March 2026 (8 min)
- [ ] The payment batch loaded twice (5 min)
- [ ] Walk from the finance figure to the collections figure (7 min)
- [ ] The certified definition (5 min)
- [ ] ✱ Stretch: The government segment under each definition

### Session 2: Metrics as code with tests

#### [day1#s2] Metrics as code with tests

*Session 2*

- Write simple, ratio, cumulative and derived metrics as code
- Explain why a ratio is computed after aggregation
- Prove a metric against an independent total from the marts

#### [day1#recap-307] You know the anatomy of a metric; here it becomes a file with a lifecycle

*Recap from DS-307*

- Grain, aggregation, filter, time logic: DS-307 Day 1
- Ratios and distinct counts that do not add up: DS-307 Day 1
- Metrics in an open specification: DS-307 Lab 2.4

- **New here.** Owner, version, status and tests in the same file; review rules; deprecation; one catalogue for four areas.

#### [day1#metric-file] A metric file holds the definition and the promise around it

*data/metrics/collections.yml*

```yaml
# file: collections.yml
- name: collection_rate
  type: ratio
  numerator: collected_30
  denominator: net_due_30
  owner: Majdi Bawazir
  version: 1.0.0
  status: certified
  description: Share of the net amount due on the period's bills paid
    within 30 days of the due date (certified)
  ai: {synonyms: {ar: [نسبة التحصيل, معدل التحصيل]}}
  tests:
    - reconcile: "SELECT ... FROM fct_payment ... / ... FROM fct_bill"
```

#### [day1#four-types] Four types cover the metrics of all four areas

*Metric types in the course layer*

- **Simple.** An aggregate of one dataset, with an optional filter. `billed_amount`
- **Ratio.** Two metrics, divided after aggregation. `collection_rate`
- **Cumulative.** A simple metric summed to date in the fiscal year. `cash_collected_fytd`
- **Derived.** An expression over other metrics. `complaints_per_1k_lines`

The same four exist, under other names, in MetricFlow (simple, ratio, cumulative, derived) and in Cube's measures.

#### [day1#ratio-of-sums] A ratio is divided after aggregation, never averaged across parts

*Lab 1.2, step 3*

| FY2025-26 | Collection rate | Net due (SAR) |
| --- | --- | --- |
| Business | 85.6% | 2,035,219 |
| Consumer | 91.1% | 3,524,157 |
| Government | 50.6% | 545,839 |
| Company: ratio of sums | 85.6% |  |
| Plain average of the three | 75.8% |  |

#### [day1#cumulative] "To date" needs an order in time and a year that restarts in April

*Fiscal year to date*

| Month | Cash | FYTD |
| --- | --- | --- |
| Feb 2026 | 540,627 | 5,105,422 |
| Mar 2026 | 568,579 | 5,674,001 |
| Apr 2026 | 590,927 | 590,927 |
| May 2026 | 622,025 | 1,212,952 |

- Qamar's fiscal year runs April to March
- The layer refuses a cumulative query without months
- The test: March to date equals April to March from the marts

#### [day1#reconcile-tests] A reconciliation test compares the metric with SQL that bypasses the layer

*Proof against the source*

**1 · Metric** through the semantic layer → **2 · Independent SQL** on the marts → **3 · Equal?** to a tolerance

> **Lab 1.2.** Drop the maturity filter from `net_due_30` and its test fails: SAR 9,249,163 against 7,935,267.

#### [day1#checkpoint-2] A regional rate for the scorecard

*Checkpoint*

**Question:** The regional scorecard needs one collection rate for the year. A colleague computes each month's rate, then averages the twelve. Where does that go wrong first?

- A. When a month has a duplicated payment batch
- B. When the fiscal year starts in April
- C. When months, or the parts averaged, differ much in size
- D. When rates are rounded to one decimal place

#### [day1#lab-1-2] Five metrics as code

Lab 1.2 · 25 min

Implement five metrics, including the certified collection rate as a ratio and cash collected fiscal year to date, with reconciliation tests against the marts; then break one and watch its test fail.

[D1_2_metrics_as_code.ipynb](https://sdaiaacademy.github.io/ds-408/labs/D1_2_metrics_as_code.ipynb)

- [ ] Read one metric file (3 min)
- [ ] Three simple metrics (7 min)
- [ ] The ratio: a ratio of sums (6 min)
- [ ] The cumulative metric (4 min)
- [ ] Run the tests, then break one (5 min)
- [ ] ✱ Stretch: A derived metric for the collection gap, with its test

### Session 3: Ownership and change control

#### [day1#s3] Ownership and change control

*Session 3*

- Distinguish the owner, the steward and the approver of a metric
- Version a metric change as major, minor or patch
- Take a change through review rules that run in continuous integration

#### [day1#three-roles] An owner answers for the meaning; a steward answers for the file

*Who does what*

- **Owner.** A business lead. Approves every change of meaning. Majdi Bawazir for the collection rate.
- **Steward.** The data platform team. Edits the file, runs the tests. Zeyad Al-Juraisy's team.
- **Requester.** Anyone. Opens a change request with the reason and the reports affected.

> **One owner per metric.** Two owners means nobody decides when they disagree.

#### [day1#semver] The version says whether a reader's number will move

*Semantic versioning for metrics*

| Change | Example | Bump |
| --- | --- | --- |
| Meaning: expression, filter, inputs | billed amount without VAT | **major** 1.0.0 → 2.0.0 |
| New field or status | certified after tests pass | minor 0.9.0 → 0.10.0 |
| Words only | an Arabic synonym, a clearer description | patch 2.0.0 → 2.0.1 |

A major change keeps the old meaning reachable under a new name until its reports have moved.

#### [day1#rules-as-code] Six review rules run on every pull request, so memory is not the control

*labs/ci/check_metrics.py*

1. Owner, version, status and description on every metric
2. A certified simple metric has a test
3. A changed metric has the right version bump
4. The changelog names the metric and its new version
5. The owner approves the new version, and is not its author
6. Nothing is removed unless it was deprecated first

#### [day1#cr-07-trace] The steward changes one expression; CI stops it three times

*Lab 1.3: the quick edit*

- commit: CR-07: billed amount without VAT (expr: amount_due / 1.15)
- R3: a major change needs a major version bump (was 1.0.0, now 1.0.0)
- R4: CHANGELOG.md has no line for billed_amount 1.0.0
- R5: no approval of version 1.0.0
- fixed: 2.0.0, changelog line, approval by Jood Al-Muhaisen: metrics check passed, merged

#### [day1#notice-period] A breaking change is announced before it takes effect

*The human part*

- **Announce.** Two monthly closes ahead, to every report owner the lineage finds.
- **Run both.** The old meaning under a new name, deprecated, beside the new version.
- **Retire.** After the sunset date, when no report reads the old one.

> **CR-07 moves ARPA too.** ARPA is derived from the billed amount: its owner must hear about the change even though nobody touched ARPA's file.

#### [day1#checkpoint-3] A fix to the maturity rule

*Checkpoint*

**Question:** The steward finds that `net_due_30` counted cohorts one day early and fixes the filter. The certified figure for March moves by 0.1 point. Which version and approval does the change need?

- A. Major version, approved by the owner, with a changelog line
- B. Patch version, since the effect is small
- C. Minor version, approved by the steward who found it
- D. No version, since it corrects a bug

#### [day1#lab-1-3] A change taken through review

Lab 1.3 · 25 min

Write the change process for a metric and take one change, the billed amount without VAT, through a local git repository whose review rules stop it until the version, the changelog and the owner's approval are right.

[D1_3_change_control.ipynb](https://sdaiaacademy.github.io/ds-408/labs/D1_3_change_control.ipynb)

- [ ] Read the review rules (4 min)
- [ ] Write the change process (6 min)
- [ ] Make the change on a branch (5 min)
- [ ] Run the check and read why it fails (4 min)
- [ ] Fix, pass and merge (6 min)
- [ ] ✱ Stretch: A words-only change: which bump does it need?

### Session 4: Certification and deprecation

#### [day1#s4] Certification and deprecation

*Session 4*

- Check a metric catalogue for owners and tests
- Deprecate a metric with a successor and a sunset date
- Find every report that depends on a deprecated metric, directly or through lineage

#### [day1#lifecycle] Draft, certified, deprecated, retired: each status is a promise

*The life of a metric*

1. **Draft** anyone may use it, nobody may rely on it
2. **Certified** owner, tests, reviewed changes
3. **Deprecated** successor and sunset date named
4. **Retired** removed after the sunset

Muhsi answers only from certified metrics (Day 4). The status is how it knows.

#### [day1#catalogue-health] Qamar's 40-metric catalogue keeps fewer promises than its labels say

*Lab 1.4, step 1*

- **2** certified metrics without an owner
- **1** certified simple metric without a test
- **10** certified derived metrics with no test of their own

#### [day1#deprecate-with-successor] Deprecate with a successor and a date, and rename what was never a duplicate

*Lab 1.4, step 2*

| Metric | Version | Replaced by | Sunset |
| --- | --- | --- | --- |
| `collection_rate_finance` | 1.3.0 → 1.4.0 | `collection_rate` | 2026-08-31 |
| `collection_rate_60d` | 2.1.0 → 2.2.0 | `collection_rate` | 2026-08-31 |
| `paid_on_time_rate` | 1.0.0 → 1.1.0 | `on_time_payment_share` | 2026-08-31 |

#### [day1#lineage] Nine of twelve reports must move, and eight never typed a deprecated name

*Lab 1.4, steps 3 and 4*

- **By alias:** "collection %", "collections rate", "on-time payers %", "cash collection rate"
- **Through lineage:** `collections_score`, then `region_health_index` ("RHI" on the board pack)
- **Directly:** one report, the data platform health page

> **A text search finds one report.** Resolving aliases and following `depends_on` finds nine.

#### [day1#checkpoint-4] Cleaning up after the sunset

*Checkpoint*

**Question:** It is 1 September 2026. `collection_rate_60d` is past its sunset, and the Collections weekly still reads it under the alias "collections rate". What happens next?

- A. Remove the metric: the date has passed
- B. Extend the sunset by a quarter without telling anyone
- C. Edit the report to read the certified rate yourself
- D. Escalate to the report's owner with the date the removal will happen

#### [day1#lab-1-4] Deprecate in a 40-metric catalogue

Lab 1.4 · 25 min

Version and deprecate metrics in a 40-metric catalogue, follow the lineage to the metrics built on them, and list the reports that still use a deprecated one, by name, by alias or through another metric.

[D1_4_catalogue_lifecycle.ipynb](https://sdaiaacademy.github.io/ds-408/labs/D1_4_catalogue_lifecycle.ipynb)

- [ ] The catalogue's health (5 min)
- [ ] Deprecate three metrics (6 min)
- [ ] Everything built on a deprecated metric (6 min)
- [ ] Reports that still use one (8 min)
- [ ] ✱ Stretch: One notice per report owner

#### [day1#wrap-up] Three things to keep

*Day 1 · Wrap-up*

- **Walk, then certify.** Split a disagreement into one change per row; fix data errors in the data.
- **A metric is a file.** Definition, owner, version, status and tests together, reviewed by rules in CI.
- **Lineage finds the reader.** Aliases and dependencies, not a text search, tell you who a change will hurt.

#### [day1#next] Day 2: design the semantic layer

*Next*

- Four business areas on one customer, one region and one calendar
- Bring a question your managers ask that crosses two areas
- Unfinished labs can be finished at home: each starts from supplied files
