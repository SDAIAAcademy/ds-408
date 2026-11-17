---
course: "Analytics Products: Semantic Layers and Conversational Analytics"
code: "DS-408"
version: "2027.1.0"
deck: "day3"
day: 3
language: "en"
view: "trainee"
source: "https://sdaiaacademy.github.io/ds-408/slides/day3.html"
---

# Analytics Products: Semantic Layers and Conversational Analytics

## Day 3: Test the assistant

Certified questions, context, accuracy and stability

#### [day3#title] Test the assistant

*SDAIA Academy · Analytics Products: Semantic Layers and Conversational Analytics*

Day 3: Certified questions, context, accuracy and stability

Data Science Track · 4 teaching days + capstone day · 4 sessions · 4 labs · DS-408

#### [day3#agenda] Test the assistant

*Today*

- **Session 1 · A certified set for a platform**: Questions with certified answers, covering every area, difficulty and language, including those the assistant must refuse
- **Session 2 · Which context helps**: Synonyms, descriptions and examples removed one at a time, with everything else fixed
- **Session 3 · A scoring harness**: Execution accuracy, wrong but plausible answers and refusals, in a report a reviewer can re-run
- **Session 4 · Ask it again**: The same question three times: agreement, and the cell that matters most, stable and wrong

#### [day3#review-day2] A new dataset arrives on Thursday

*Review of Day 2*

**Question:** A roaming dataset is added to the layer on Thursday without a row rule. On Sunday the Eastern regional manager asks for roaming data by region. With deny by default on, what happens?

- A. The layer refuses the query and names the missing rule
- B. All five regions come back
- C. Only the Eastern region comes back
- D. The rows come back with every value masked

### Session 1: A certified set for a platform

#### [day3#s1] A certified set for a platform

*Session 1*

- Write a certified answer as value, metric, filters and grain
- Cover areas, difficulty levels and both languages
- Include questions the assistant must refuse

#### [day3#why-certified] A leaderboard score says little about your metrics; a certified set says a lot

*Before 300 managers ask*

- Public text-to-SQL benchmarks use other schemas and other definitions
- Enterprise benchmarks show **real warehouses stay hard**: Spider 2.0 (ICLR 2025)
- Your managers ask about **your** collection rate, fiscal year and Hijri months
- DS-307 ended with ten certified answers and a go or no-go memo; a platform needs more

- **Qamar's set.** 60 questions: four areas, three difficulties, 30 in Arabic and 30 in English, 8 that Muhsi must refuse.

#### [day3#certified-answer] A certified answer is a figure and the four things that produce it

*What is certified*

```yaml
# file: certified_60.yaml
- id: C05
  lang: en
  area: collections
  difficulty: 1
  question: What was the collection rate for government
    customers for December 2025 bills?
  query:
    metrics: [collection_rate]
    where: ["customer.segment = 'government'",
            "time.month = DATE '2025-12-01'"]
  expect: {kind: value, value: 0.560764, unit: ratio,
           metric_version: 1.0.0}
```

- **Metric and version.** Which definition, and which version of it.
- **Filters and grain.** Which customers, which period, grouped how.
- **Value.** Run through the layer, never typed from a report.

#### [day3#coverage] The supplied 44 questions leave two cells empty and almost no refusals

*Lab 3.1, step 1*

| Area | Difficulty 1 | Difficulty 2 | Difficulty 3 | Refusals |
| --- | --- | --- | --- | --- |
| Usage | 5 | 4 | 3 | 1 |
| Billing | 5 | 4 | 3 | 1 |
| Collections | 5 | 4 | 0 | 0 |
| Complaints | 5 | 4 | 0 | 0 |

Difficulty 1: one filter. 2: two filters or a fiscal period. 3: a ranking, a Hijri period or a cumulative figure.

#### [day3#refusals] A refusal is a right answer, and the set must test five kinds of it

*The questions Muhsi must refuse*

- **Restricted.** Names, national IDs or mobile numbers of customers.
- **Forecast.** Next year's revenue: the layer holds facts, not predictions.
- **Not matured.** May 2026's collection rate: its 30-day window has not closed.

- **Uncertified.** Bills paid on time: only a draft metric fits.
- **Causal.** "Why did complaints rise?": a figure is not a cause.

#### [day3#screening] Four rules screen a candidate question before it is certified

*Lab 3.1, step 2*

| Rule | Reject when | Candidate |
| --- | --- | --- |
| Period | an answer with no time condition | "What is the collection rate?" |
| Certified | only a draft metric fits the draft | "Cash to billing ratio in March" |
| Duplicate | same metrics, groups and filters as one in the set | January's rate, in other words |
| Restricted | groups or filters on a Restricted field | "Which customer had the largest bill?" |

24 candidates: 16 kept, 8 rejected.

#### [day3#hijri-caveat] A Hijri question about monthly facts certifies a labelling choice

*Lab 3.1, step 3*

- Ramadan 1447 runs from about 18 February to 19 March 2026
- Bills and monthly usage are dated on the first day of the service month
- So "data in Ramadan 1447" counts the **March 2026** service month
- Complaints are dated by day, so "complaints in Rajab 1447" is exact

> **Say it in the question.** The certified answer must state the convention, or two analysts certify different figures and both are right.

#### [day3#checkpoint-1] Two analysts, two certified figures

*Checkpoint*

**Question:** Two analysts certify "the collection rate for January bills" and record 0.8495 and 0.8645. Both ran the semantic layer. What must the certified answer also record so a reviewer can settle it?

- A. The value to more decimal places
- B. The analysts' names and the date
- C. The metric and its version, the filters and the grain they ran
- D. The assistant's answer to the same question

#### [day3#lab-3-1] From 44 to 60 certified questions

Lab 3.1 · 25 min

Extend the supplied certified set to cover each business area and difficulty level in Arabic and English, including questions the assistant must refuse, certifying each new answer through the semantic layer.

[D3_1_certified_set.ipynb](https://sdaiaacademy.github.io/ds-408/labs/D3_1_certified_set.ipynb)

- [ ] Coverage of the supplied set (5 min)
- [ ] Screen the candidate questions (7 min)
- [ ] Certify the answers (7 min)
- [ ] Check coverage, languages and refusals (6 min)
- [ ] ✱ Stretch: Three paraphrases of one question

### Session 2: Which context helps

#### [day3#s2] Which context helps

*Session 2*

- Design an ablation that changes one kind of context at a time
- Score each variant with a fixed model and question set
- Read the contribution of each kind of context by language and area

#### [day3#three-kinds] Each certified metric carries three kinds of context for the assistant

*What Muhsi reads*

- **Synonyms.** In both languages: "collection rate", "نسبة التحصيل", "معدل التحصيل".
- **Description.** "Paid within 30 days of the due date, net of disputes, bill-month cohort."
- **Examples.** A question and its query, such as a fiscal-year filter written correctly.

Muhsi answers with a semantic query, not SQL; the layer computes the figure.

#### [day3#ablation] Remove one kind of context at a time, and keep everything else fixed

*Lab 3.2, the design*

1. **1 · Fix** the model, the 60 questions, run 1
2. **2 · Remove one** synonyms, or descriptions, or examples
3. **3 · Re-score** the same scorer, by language and by area

> **Takeaway.** One change per run, so each drop in accuracy has one cause.

#### [day3#contribution] Examples matter most overall; synonyms matter only in Arabic

*Lab 3.2, step 5*

| Removed | Accuracy drop | Arabic | English | Area hurt most | More wrong but plausible |
| --- | --- | --- | --- | --- | --- |
| Examples | 23.3 pts | 23.4 | 23.3 | collections | +21.7 pts |
| Descriptions | 15.0 pts | 13.4 | 16.6 | collections | +15.0 pts |
| Synonyms | 11.7 pts | 23.4 | 0.0 | billing | 0.0 |

Full context: 95.0% on 60 questions, run 1. Stand-in model (recorded, synthetic).

#### [day3#collections-desc] Without descriptions, collections accuracy falls to 40%, and every miss looks right

*Lab 3.2, step 3*

| Item | Value |
| --- | --- |
| Billing | 100% |
| Usage | 100% |
| Complaints | 80% |
| Collections | 40% |

Muhsi picks the finance ratio (cash over billed) for "collection rate": 0.90 for March instead of 0.86.

#### [day3#standin] A recorded stand-in makes every figure reproducible; a free hosted model makes it real

*How the labs run without a key*

- **Stand-in (default).** 720 recorded replies: 60 questions, 4 contexts, 3 runs. Written from a stated error model in `_tools/make_case_files.py`.
- **Live (stretch).** `QAMAR_MODEL_MODE=live` and a free OpenRouter key: the same prompt to `google/gemma-4-31b-it:free`.

> **Free models change.** Record the model name and the date beside any live figure.

#### [day3#checkpoint-2] One budget, three kinds of context

*Checkpoint*

**Question:** Qamar's managers ask about 80% of their questions in Arabic. With the contribution table above, which kind of context should Zeyad fund first?

- A. Descriptions, because they matter most in English
- B. Examples: the same Arabic drop as synonyms, with plausible errors
- C. Synonyms last, because their overall drop is smallest
- D. Whatever is shortest, to keep prompts small

#### [day3#lab-3-2] Remove one kind of context at a time

Lab 3.2 · 25 min

Remove synonyms, descriptions and examples one at a time from the supplied configuration of Muhsi and re-score each variant with the supplied scorer, by language and by area.

[D3_2_context_ablation.ipynb](https://sdaiaacademy.github.io/ds-408/labs/D3_2_context_ablation.ipynb)

- [ ] The full configuration and its score (4 min)
- [ ] Without synonyms (5 min)
- [ ] Without descriptions (5 min)
- [ ] Without examples (5 min)
- [ ] The contribution table (6 min)
- [ ] ✱ Stretch: Ten questions on a free hosted model

### Session 3: A scoring harness

#### [day3#s3] A scoring harness

*Session 3*

- Score an answer by executing it and comparing with the certified value
- Separate wrong but plausible answers from obvious failures
- Write an evaluation report that a reviewer can re-run

#### [day3#execute] Score the figure the manager sees, not the text of the query

*Lab 3.3, step 1*

- Two different queries can give the same figure: a fiscal year as a label or as a date range
- A reply may come in a code fence, as a sentence, or with a bad date: each is an outcome, never a crash
- Numbers match within a stated relative tolerance (0.5%); group names match exactly

````json
// file: a reply
```json
{"metrics": ["collection_rate"], "by": [],
 "where": ["time.month = DATE '2026-03-01'"]}
```
````

#### [day3#outcomes] Seven outcomes, and the two that reach decisions

*Lab 3.3, step 2*

| Outcome | When | Run 1 |
| --- | --- | --- |
| Right | the certified figure, within tolerance | 50 |
| Refused right | refused a must-refuse question | 7 |
| Wrong but plausible | half to twice the figure, or a valid wrong group | 2 |
| Missed refusal | answered a must-refuse question | 1 |
| Wrong, visible | any other figure | 0 |
| Error | no JSON, the layer failed, nothing came back | 0 |
| Refused wrongly | refused an answerable question | 0 |

#### [day3#three-plausible] Three answers nobody would notice on a slide

*Lab 3.3, step 4*

- **C13 · Riyadh.** Read "Riyadh" as the Central region: 86.0% instead of 81.5%.
- **Q11 · Billing complaints.** Counted all complaints: January 2026 instead of November 2025.
- **C15 · On time.** Answered with a draft metric (73.5%) instead of refusing.

Each looks like a careful answer. Each fails a different safeguard: a field, a metric choice, a certification status.

#### [day3#rerun] A report is evidence only if a reviewer can re-run it and get the same number

*Lab 3.3, step 3*

```bash
# file: from labs/
uv run python harness/score.py \
  --variant full --runs 1
```

- Hashes of every input: the set, the replies, the model, the metric files
- The scorer's version, the tolerance and the plausible band
- The mode, and the model name and date when live

> **First thing to compare when numbers differ:** the hashes, before any code.

#### [day3#checkpoint-3] Same accuracy, different risk

*Checkpoint*

**Question:** Two assistant configurations both score 90% on the certified set. In A, the misses are errors and wrong refusals. In B, the misses are wrong but plausible figures. Which do you put in front of managers, and why?

- A. Either: the accuracy is the same
- B. B, because it always gives a number
- C. A, because its failures are seen and re-asked; B's reach decisions
- D. Neither until accuracy is measured on live traffic

#### [day3#lab-3-3] Accuracy and wrong but plausible

Lab 3.3 · 25 min

Build a harness that executes each reply, reports execution accuracy and the rate of wrong but plausible answers, and writes a report a reviewer can re-run.

[D3_3_scoring_harness.ipynb](https://sdaiaacademy.github.io/ds-408/labs/D3_3_scoring_harness.ipynb)

- [ ] Execute a reply and compare (6 min)
- [ ] Classify every outcome (7 min)
- [ ] The report a reviewer can re-run (7 min)
- [ ] Read the wrong but plausible answers (5 min)
- [ ] ✱ Stretch: A tolerance for rounding: where does it stop being right?

### Session 4: Ask it again

#### [day3#s4] Ask it again

*Session 4*

- Measure answer agreement across repeated runs
- Separate stable right, stable wrong and unstable answers
- Explain what a response cache hides from a stability test

#### [day3#ask-again] The three runs score about the same; the answers are not the same

*Lab 3.4, steps 1 and 2*

- **95%** run 1 accuracy
- **90%** runs 2 and 3
- **91.7%** questions with three agreeing answers

Five questions change answer between runs. A manager who asks twice and gets two figures stops trusting every figure.

#### [day3#stability-cells] Stable and wrong is the worst cell: re-asking never reveals it

*Lab 3.4, step 3*

|  | Questions | Found by |
| --- | --- | --- |
| Stable right | 52 | nothing needed |
| Unstable | 5 | asking again |
| Stable wrong | 3 | only a certified answer |

The stable-wrong three are the plausible errors of Lab 3.3: C13, C15 and Q11. The unstable five are all difficulty 2 or 3.

#### [day3#cache-vote] A cache hides instability; a vote of three does not fix it

*Lab 3.4, step 5 and the stretch*

- **Cache run 1.** All five unstable questions were right on run 1: a cache shows them stable and right, while a fresh ask sometimes is not.
- **Majority of three.** 56 of 60 right against 57 with run 1 alone: C09 is wrong in two runs of three, so the vote picks the wrong one. Triple the cost.

#### [day3#checkpoint-4] A vendor's single run

*Checkpoint*

**Question:** A vendor reports 96% accuracy from one run at temperature zero on your certified set. What do you ask for before trusting it?

- A. A larger question set
- B. Three runs per question: the agreement rate and the stable-wrong questions
- C. Nothing: temperature zero makes it deterministic
- D. A run at a higher temperature

#### [day3#lab-3-4] Three runs per question

Lab 3.4 · 25 min

Run each certified question three times and measure how often the answers agree, which questions are stable but wrong, and how stability differs by area, difficulty and language.

[D3_4_stability.ipynb](https://sdaiaacademy.github.io/ds-408/labs/D3_4_stability.ipynb)

- [ ] Load the three runs (3 min)
- [ ] Agreement per question (6 min)
- [ ] Stable right, stable wrong, unstable (7 min)
- [ ] Stability by area, difficulty and language (6 min)
- [ ] What a cache would hide (3 min)
- [ ] ✱ Stretch: Does a majority vote of three fix the unstable questions?

#### [day3#wrap-up] Three things to keep

*Day 3 · Wrap-up*

- **Certify the query.** Value, metric and version, filters, grain; every area, difficulty and language; refusals.
- **Change one thing.** Ablate one kind of context at a time and read the column that matches your users.
- **Count the plausible.** Report wrong-but-plausible and stable-wrong beside accuracy, in a report anyone can re-run.

#### [day3#next] Day 4: ship and govern

*Next*

- Serve the layer to tools and agents, with the role taken from the credential
- Safeguards that cite the metric and refuse the uncertified
- A routing policy, then a design review of a peer's product
