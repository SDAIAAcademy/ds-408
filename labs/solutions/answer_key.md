# Answer key for trainers

All data is synthetic (`prepare_data.py`, seed 408; `_tools/make_case_files.py`). Figures are from full-size solution
runs; quick mode (`QAMAR_QUICK=1`) changes only the figures of the session table in Lab 2.2.

## Planted problems

| Where | Problem | Found by |
|---|---|---|
| `fct_payment` | payments batch B20260317 loaded twice (`load_no` 2): 80 rows, SAR 24,802.51 | Lab 1.1 |
| `dim_tariff` | Qamar Postpaid M and Qamar Fibre 100 change price on 2025-10-01 (two history rows each) | Lab 2.1 |
| `fct_complaint` | network complaints spike in the Eastern region in January 2026; billing complaints after the price change (November 2025) | Labs 2.1, 3.3 |
| `data/definitions/collection_rate_three.yaml` | three teams' collection rates (finance, collections, care) | Lab 1.1 |
| `data/metrics/` | averaging monthly ratios; a change that skips the version bump and approval | Labs 1.2, 1.3 |
| `data/catalogue/` | certified metrics with no owner, untested derived metrics, reports on deprecated metrics through aliases | Lab 1.4 |
| `data/semantic/model_starter.yaml` | complaints not conformed; tariff join without validity dates | Lab 2.1 |
| `data/semantic/query_log.csv` | ten question shapes are 91% of the log | Lab 2.2 |
| `data/access/policy.yaml` | no row rule for complaints (allow by default); `contact_name` derived from the Restricted full name, untagged | Lab 2.3 |
| `qamar_model.yaml` | DuckDB-only SQL (`strftime`, `split_part`, `date_diff`) | Lab 2.4 |
| `data/assistant/supplied_44.yaml` | no difficulty 3 for collections and complaints; two refusals, both about personal data | Lab 3.1 |
| `data/assistant/candidates.yaml` | eight flawed drafts: X01, X04, X08 no period; X02, X05 duplicates; X03, X06 draft metrics; X07 Restricted field | Lab 3.1 |
| `data/assistant/replies.jsonl` | stand-in error model (stated in `make_case_files.py`): Arabic needs synonyms, collections need descriptions, fiscal and Hijri periods need examples; C13 and Q11 stable and wrong; C15 answers a draft metric; five unstable questions | Labs 3.2 to 3.4, 4.2 |
| `data/review/` | Team B: tariff fan-out, complaint leak, readable first names, collection rate defined as finance's ratio with a self-confirming test, 30 English questions in one run, routes on point rates, README claim without a re-run | Lab 4.4 |

## Expected results

**Lab 1.1.** Rates for March 2026: finance 94.1%, collections 93.8%, care 73.5%, certified 86.5%. Without the
duplicate batch, finance 90.2%. Walk 94.1 → 90.2 → 92.9 → 93.8 → 86.5. Government: 46.2% at 30 days, 78.2% at 60.

**Lab 1.2.** FY2025-26 ratio of sums 85.65%; average of monthly ratios 85.64%; average of segment ratios 75.75%
(business 85.6%, consumer 91.1%, government 50.6%). Cash collected FYTD to March: SAR 5,674,001. The broken test
reads 9,249,163 against 7,935,267.

**Lab 1.4.** 2 certified metrics with no owner, 1 simple metric untested, 10 derived untested; 3 metrics downstream
of the deprecated ones; 9 of 12 reports must move.

**Lab 2.1.** Wide join 1.48 times the billed amount and 13.33 times the complaints. Eastern complaints per 1,000
lines: 30.6, 42.3, 98.1, 39.9 (November to February). Data by plan 4,769,001 GB before the as-of join, 3,043,658 after.

**Lab 2.2.** Rows scanned 36,539,620 → 2,815,154; latency about 1,426 ms → 225 ms on a laptop (full size).
Pre-aggregation rows 540, 48, 504, 17. Lines with a session: 3,253 for the year against 31,226 summed by month.

**Lab 2.3.** 3 of 21 access tests fail first (complaint rows, contact_name), 0 after the fix. Central complaints 612.

**Lab 2.4.** 24 metrics exported, `cash_collected_fytd` left behind. On SQLite: `strftime` fails silently (one row,
empty month), `split_part` and `date_diff` fail loudly. `MEDIAN` still fails after the three dialect entries.

**Lab 3.1.** Two empty cells, two refusals in the 44. 16 candidates kept, 8 rejected. 60 questions, 30 per language,
8 refusals of five kinds in all four areas.

**Lab 3.2.** Full context 95.0%. Without synonyms 83.3% (Arabic 73.3%, English 93.3%, unchanged). Without
descriptions 80.0% (collections 40%). Without examples 71.7% (difficulty 1 unchanged). Contribution order:
examples (23.3 points), descriptions (15.0), synonyms (11.7; 23.4 in Arabic).

**Lab 3.3.** 50 right, 7 refused right, 2 wrong but plausible (C13, Q11), 1 missed refusal (C15): 95.0% accuracy,
5.0% wrong but plausible. The reviewer's re-run gives the same.

**Lab 3.4.** Runs 95%, 90%, 90%. 91.7% of questions agree over three runs: 52 stable right, 5 unstable (C09, C12,
Q13, Q15, U13), 3 stable wrong (C13, C15, Q11). A cache of run 1 hides all five. A vote of three: 56 of 60 against 57.

**Lab 4.1.** MCP 2025-11-25, three tools. Eastern manager: billed rows EAS only, complaints also under WES (raised in
EAS by Western customers: the policy, not a leak). Three attempts to raise the role return no other region. Six tests pass.

**Lab 4.2.** Guard verdicts: X01 no_period, X06 uncertified, X07 restricted, contact_name restricted, May 2026
collection rate not_matured, C01 none. Full context, three runs: accuracy 91.7% → 93.3%, wrong but plausible
8.3% → 6.7%. Without descriptions: 80.0% → 83.3%, 20.0% → 6.7%.

**Lab 4.3.** 180 answers, 12 wrong figures. Upper bounds: lookup 9.3%, Hijri 29.9%, must refuse 20.2%, ranking
31.0%, fiscal 32.5%, cumulative 56.4%. Routes at 10%: lookup to the assistant; Hijri and must-refuse with review;
fiscal, ranking and cumulative to an analyst. At 5% lookups move to review.

**Lab 4.4.** 14 of 14 reconciliation tests pass. Checks: tariff fan-out, complaint leak, readable first names,
three DuckDB-only fields, four evaluation findings, three routing findings. Reading adds the collection-rate
definition and its self-confirming test. Top two at risk 9; ten findings fixed before release; verdict not ready.

## Checkpoint answers in the decks

Day 1: B, C, A, D. Day 2: review A; sessions D, B, C, A. Day 3: review A; sessions C, B, C, B.
Day 4: review C; sessions B, C, B, A.
