# Frozen development expectations

These 13 synthetic cases are a small development evaluation, not an official benchmark or general accuracy estimate. Expectations were frozen before this run. Grading will be reviewed against the evidence; no model-based judge is used.

| ID | Category | Slider/context | Question | Expected | Allowed supporting sources |
|---|---|---|---|---|---|
| owner-before | ownership | 2026-06-20 | Who owned the billing service on 2026-06-09? | Maya Patel | DEMO:billing-owner-0601 |
| owner-boundary | ownership | 2026-06-20 | Who owned the billing service on 2026-06-10? | Noah Williams | DEMO:billing-handover-0610 |
| owner-slider | ownership | 2026-06-20 | Who owns the billing service? | Noah Williams | DEMO:billing-handover-0610 |
| owner-named | date parsing | 2026-06-20 | Who owned billing on June 9? | Maya Patel | DEMO:billing-owner-0601 |
| owner-history | history | 2026-06-20 | Who owned the billing service before Noah Williams? | Maya Patel | DEMO:billing-owner-0601, DEMO:billing-handover-0610 |
| deadline-old | deadline | 2026-06-05 | What is the invoice export project deadline? | 2026-06-18 | DEMO:export-deadline-0603 |
| deadline-new | deadline | 2026-06-20 | What is the invoice export project deadline? | 2026-06-25 | DEMO:export-rescheduled-0612 |
| search-owner | ownership | 2026-06-20 | Who owns the search service? | Iris Chen | DEMO:search-owner-0615 |
| email | PII recall | 2026-06-20 | What is Maya Patel's work email? | maya.patel@example.test | DEMO:billing-owner-0601 |
| scheduled | scheduling | 2026-06-20 | When is the customer demo scheduled? | 2026-06-30 | DEMO:demo-scheduled-0620 |
| not-completed | abstention | 2026-06-20 | Has the customer demo been completed? | No completion established; scheduled only | DEMO:demo-scheduled-0620 |
| unknown | abstention | 2026-06-20 | What is the cafeteria lunch menu? | Not in the corpus | none |
| before-corpus | abstention | 2026-06-20 | Who owned the billing service on 2026-05-31? | Not in the corpus | none |

Citation grading: a cited document must support the answer, not merely appear in retrieval. Unknown/before-corpus questions should abstain without citations. A scheduling answer must not claim completion. The deadline tests ask which deadline is in force on the context day, not what was known at a historical transaction timestamp.
