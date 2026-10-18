# P3 answer side: what to change for corpus B, and why

**From**: Sara (P1) · **For**: Sania (P3) · **Date**: 2026-10-18
**Evidence**: mnemo corpus B, run 1, `results/runs/20261017T135109Z-chronicle` (`summary.md`, `verdicts.jsonl`, `answers.jsonl`)

## Where we are

Run 1 scored **0.344 overall** and **0.429 on as_of**. The targets are >0.91 and ≥0.83; NVIDIA's baselines are 0.828 (agentic RAG) and 0.909 (self model).

Most of that gap came from P1. Extraction kept only 91 claims from 173 docs, because the reasoning model's thinking leaked into the reply and got parsed. That's fixed on `p1/ingest-skeleton` (thinking off for ingest, truncated replies rejected). Run 2 will show how far the score moves on extraction alone.

The changes below are the part P1 can't fix. Even with perfect claims, the answer path loses information the grader checks for.

| category | run 1 | what it needs |
|---|---|---|
| single_hop (40) | 13/40 | the exact value from the source text |
| multi_source (19) | 2/19 | evidence from several docs at once |
| freshness (7) / chain_freshness (2) | 0/7, 0/2 | the latest value, with older values recognised as superseded |
| as_of (7) | 3/7 | only what was known by a given date |
| disambiguation (8) | 4/8 | context about which entity is meant |
| abstention (12) | 11/12 | already fine; don't regress it |

31 answers were some form of "Not in corpus", and 29 of those were wrong.

## New input from P1: `state/docs.jsonl`

Ingest now writes one row per document, including documents whose extraction failed:

```json
{"doc_id": "E:2027-07-21T09-07-00__9c0eec80", "date": "2027-07-21", "kind": "email", "part": "part_a",
 "text": "From: Dana Okafor ...\nSubject: Harbor Point steel – HPS-1/HPS-2 ETA 11 Aug\n\n..."}
```

Read it with `chronicle.ingest.pipeline.read_docs(state / DOCS_FILE)`. `text` is the same header-plus-body the extractor saw, with Slack mentions already resolved to names. It's built from the corpus at ingest time, so the answer phase still only reads `--state` and the benchmark's isolation holds.

## Changes, in priority order

### 1. Retrieve over document text, not just claims (`chronicle/reason/retriever.py`)
**What**: Score each doc by term overlap between the question and the doc's `text`, with the subject line weighted higher. Add the claim-overlap score you compute today on top. Return doc-level `Evidence`.
**Why**: Today a fact is findable only if it became a claim *and* the claim's words overlap the question. Example: `b-asof-sup-steel-eta` asks for the HPS-1/HPS-2 ETA. The answer (11 Aug) is in the subject line of `9c0eec80`, but that doc produced no claim, so the answer was "not in corpus". Extraction will always miss some facts. Retrieval over the text means a miss costs a little precision instead of the whole answer.
**Keep**: `terms()` and the stopword list. BM25 would be better than raw overlap, and it's ~20 lines with no new dependency.

### 2. Give the answerer source text (`chronicle/reason/answerer.py`)
**What**: Build the context from the top ~10 docs' full `text`, sorted **oldest → newest**, each headed `[doc_id] date=YYYY-MM-DD`. After that, add a short dated "claims timeline" of the matching claims (`subject | predicate | object | valid_from→valid_to`) as a structured hint.
**Why**: Claim JSON drops qualifiers ("ETA 11 Aug *for HPS-1 and HPS-2 only*"), and the grader does exact-string matching against `accept` values. Cost is small: corpus B averages ~115 words per doc, so 10 docs is roughly 2k tokens. Date order matters because the model reads supersession as a sequence.

### 3. Temporal handling, driven by the planner (`planner.py` → `retriever.py` / `answerer.py`)
`plan_query` already sets `kind` and `reference_date`; nothing downstream uses them yet.
- **as_of** (`reference_date` set): drop docs and claims dated after `reference_date` *before* ranking. Then tell the model: "Answer with the value current on {date}; ignore anything you know from later." Run 1 got 3/7, and the misses gave the later value.
- **current / freshness**: after ranking, make sure the newest matching docs are included even if they score lower. Add: "Later documents supersede earlier ones; give the latest value." Run 1 scored 0/9 across freshness and chain_freshness. Gold notes show the chains (e.g. steel ETA `08-11 → 09-08 → 08-31`), and the latest entry is often a short reply with few keywords, so it ranks low.
- **chain_freshness**: the grader wants the whole chain of values. Tell the model to list every value in date order, ending with the current one.
- The planner's keyword rules miss phrasings like "As of the end of the corpus". Add that phrase, or switch to a cheap LLM planning call.

### 4. Abstain on retrieval, not on the LLM's mood (`abstention.py`, `answerer.py`)
**What**: `should_abstain` should return True only when the best retrieval score is below a threshold (tune it on corpus A). When evidence passes the threshold, tell the answerer to answer from it and say "not in the corpus" only if the documents really don't contain the value.
**Why**: Run 1 abstained 31 times and was wrong on 29 of them. Most of those questions had answers in the corpus that claim-only evidence didn't surface. The 12 real abstention questions mostly ask about things the corpus never mentions, so they'll still score near-zero on retrieval.

### 5. Hand-off to P2 later
`chronicle/memory` (supersession, bi-temporal queries) is the long-term home for steps 1 and 3: P2 would answer "value of X as of D" directly. Until the reason layer calls it, the date-filter-plus-ordering above is a cheap stand-in. Keep that logic behind one function (e.g. `select_evidence(plan, state)`) so P2 can replace it without touching the answerer.

## How to check
- Compare `summary.md` per-category scores against the run 1 table above.
- Read `verdicts.jsonl` → `reason` for the misses. "no accepted value found" means retrieval or wording; "denied" means a stale value was given (temporal).
- Use `--skip-ingest --state <run2 state>` to iterate on P3 without re-paying for ingest.
