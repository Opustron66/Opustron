# Strict answer and citation review

These are manually reviewed development verdicts against the frozen synthetic corpus, not a model-judge score or an official benchmark. Warm repeats are not counted as additional accuracy samples.

| Case | Expected | Actual cold answer | Strict answer | Cited sources | Citation assessment |
|---|---|---|---|---|---|
| owner-before | Maya Patel | Maya Patel | PASS | DEMO:billing-owner-0601, DEMO:billing-handover-0610 | Both opening and handover sources support the prior owner; extra handover citation is outside frozen source whitelist but substantively valid |
| owner-boundary | Noah Williams | Noah Williams | PASS | DEMO:billing-handover-0610 | Supported |
| owner-slider | Noah Williams | Noah Williams | PASS | DEMO:billing-handover-0610 | Supported |
| owner-named | Maya Patel | Maya Patel | PASS | DEMO:billing-owner-0601 | Supported |
| owner-history | Maya Patel | Maya Patel | PASS | DEMO:billing-handover-0610, DEMO:billing-owner-0601 | Supported |
| deadline-old | 2026-06-18 | 2026-06-18 | PASS | DEMO:export-deadline-0603 | Supported |
| deadline-new | 2026-06-25 | 2026-06-25 | PASS | DEMO:export-rescheduled-0612 | Supported |
| search-owner | Iris Chen | Iris Chen | PASS | DEMO:search-owner-0615 | Supported |
| email | maya.patel@example.test | maya.patel@example.test | PASS | DEMO:billing-owner-0601 | Supported |
| scheduled | 2026-06-30 | 2026-06-30 | PASS | DEMO:demo-scheduled-0620 | Supported |
| not-completed | No completion established; scheduled only | No, the customer demo is scheduled for 2026-06-30 and has not been completed as of 2026-06-20. | FAIL | DEMO:demo-scheduled-0620 | Source establishes schedule only; absence of completion is not established |
| unknown | Not in the corpus | Not in the corpus | PASS | none | Correct abstention; no citations |
| before-corpus | Not in the corpus | The corpus does not contain any record of who owned the billing service as of 2026-05-31. | PASS | none | Correct abstention; no citations |

## Accuracy by category

| Category | Supported / total |
|---|---|
| ownership | 4/4 |
| date parsing | 1/1 |
| history | 1/1 |
| deadline | 2/2 |
| PII recall | 1/1 |
| scheduling | 1/1 |
| abstention | 2/3 |

Strict supported-answer result: **12/13 (92.3%)**. All thirteen cold HTTP requests returned 200: twelve used a provider call, and the unknown-menu question abstained without one. The failure is epistemic: “has not been completed” is stronger than “the corpus does not confirm completion.” A lenient reading of the scheduled future demo might accept that answer, but the frozen expectation deliberately requires avoiding this overclaim.

All 11 answers that returned citations used real source document IDs. Ten of those 11 answers are fully supported by their citations under this strict review; the scheduling overclaim is not. The owner-before answer cites an additional handover document beyond its frozen whitelist: it fails a mechanical whitelist-only check, but manual review confirms that document also supports the prior owner. This distinction is recorded instead of silently changing the frozen source list. The two unknown/before-corpus answers correctly return no citations.

The before-corpus answer is correct, but retrieval sent an unrelated deadline record to the model due to a date-token match; it therefore made an avoidable provider call. Ownership, historical deadline and email values were correct in this run. These 13 cases are too small to estimate general accuracy.
