# Next phase: closing the gap to NVIDIA's 90.9%

Experiment branch `claude/exp-next-phase-567359` (cut from `p1/run4`). Nothing is merged upstream;
each owner section below lists the changes in their area for review.

## Results

<!-- RESULTS -->

How these were run: `scripts/bench_run.sh LABEL CORPUS MODEL REDACT` benchmarks one committed revision
from a snapshot (benchmark `NVIDIA/nemoclaw-community` @ f4b0a73, the same revision as Run 4).
Ladder revisions are tagged `ladder/p0` … `ladder/p3` and `final`; `p1` and `p2` carry the
consolidation tuning commit cherry-picked so each rung differs from the previous one by one phase.
Tables come from `scripts/bench_compare.py`, which reads only the `correct` flag of our own runs'
verdicts and the reference runs' aggregate `report.json`. No gold answers were read.

Caveats:
- **Consolidation model.** Every run from Phase 1 on builds topic timelines with
  `CHRONICLE_CONSOLIDATE_MODEL=nvidia/Nemotron-3-Ultra-550b-a55b`, including Lightning runs. The
  plan allows a stronger model for this one-time ingest pass. With Lightning the merge step
  over-merged (a fire-drill date with "marshals needed") or missed links (the Camden pour window
  stayed split), while Ultra chained the pour window correctly (24th → 2 Sep → 7 Sep). A Lightning
  row is therefore "Lightning answers, Ultra consolidation".
- **Cost axis.** As in Run 4, the proxy reports no countable usage, so `report.json` marks runs
  invalid on cost. Scores are unaffected.
- **Trials.** Rows are single trials unless marked. Expect a few points of run-to-run noise
  (Run 4's redaction-on claim count moved by about 8% between runs with identical code).
- **Run 4 and Phase 0 rows.** A reboot on 22 Oct wiped `/tmp`, including Run 4's run directories
  and most Phase 0 baselines. The Run 4 numbers and the Phase 0 corpus A / Ultra / off row were
  recorded before that; the other Phase 0 baselines were not re-run, to save Lightning time.

## P1 (Sara): ingestion and consolidation

`chronicle/ingest/*`

- **Quote restore** (`extractor.py`, with a small guard hook). The privacy router restores every
  pseudonym to the entity's full name, so a claim quoting "camden's crew" came back as "Camden Row
  crew" and failed the verbatim check. `restore_quote` re-spells each restored name to the spelling
  the document used (`PseudonymMapping.surfaces()`, exposed per thread by
  `LLMClient.restore_variants()`). `PROMPT_VERSION` v5.
- **Consolidation** (`consolidate.py`, new). Runs after each ingest part and writes
  `state/pages.jsonl`:
  1. *Discover*: one LLM call per document lists every update to a tracked value
     (`{topic, value, effective, quote}`), with quotes checked verbatim against the document.
     Topics come from documents, not claims: claim subjects fragment one thing ("hps-1", "Harbour
     Point steel HPS-1", "Order HPS-1 through HPS-5"), so grouping claims by canonical subject could
     not link them.
  2. *Merge*: topic names that track the same value are grouped by the LLM, in batches of 60 names
     that share a rare word (union-find blocking).
  3. *Write*: one dated timeline per topic (statement date, doc id, value, effective date, quote;
     `VALUES IN ORDER`, `LATEST`), plus a deterministic page per known person from their
     role/assignment claims and roster aliases. Every entry's doc id and quote are re-validated.
  Discovery and merges are cached in the state's LLM cache. `--no-consolidate` /
  `CHRONICLE_CONSOLIDATE=off` disables it; `CHRONICLE_CONSOLIDATE_MODEL` picks its model.
- Tests: `tests/ingest/test_consolidate.py` (alias merge, rare-word blocks, verbatim validation,
  end-to-end pages loaded by P2, cache reuse), `test_extractor.py` (quote restore).

## P2: memory

`chronicle/memory/*`

- **Topic and entity pages** (`database.py` `sync_pages`, `api.py` `sync_pages_file`). Pages are stored
  as `kind="topic"` / `kind="entity"` facts. `kind` is free text, so no migration was needed. A
  changed page gets a new fact version (the old row is replaced in transaction time, never deleted);
  a page that disappears (merged into another topic) is retired the same way. `from_state` syncs
  `pages.jsonl` after `claims.jsonl`, so `memory.search(kind="topic")` finds them.
- **Search** (`search.py`). `bm25()` is factored out of `rank()`. New: `chunk_documents`/`rank_chunks`
  (BM25 over `docs.jsonl`, with as-of filtering by document date; most corpus documents fit in one
  1,600-character chunk) and `rrf()` (reciprocal rank fusion, k=60).
- **`known_at`.** Not used. `recorded_at` is the ingest wall clock, so `known_at` = a 2027 corpus date
  would include everything. The retriever instead drops statements whose `observed_at` is after the
  as-of date, which is what the plan meant.
- Tests: `tests/memory/test_search.py` (RRF order, chunking and date filter),
  `tests/ingest/test_consolidate.py` (`sync_pages` revise/retire).

## P3: reasoning

`chronicle/reason/*`, `adapters/chronicle/answer.py`

- **Per-question error handling** (`answer.py`). An exception logs `<id>: answering failed: …` and
  emits "Not in the corpus" instead of ending the run.
- **Hybrid retrieval** (`retriever.py`). Four channels: claims (k=25), topic timelines (6), person
  pages (2) and raw documents (12). They are fused with RRF and packed to a 28k-character budget, then
  rendered as timelines, then person pages, then `FACT [doc] (valid FROM -> TO; stated D): …` lines
  (Zep-style), then `DOCUMENT` excerpts. Routing: as-of questions see only facts true then,
  statements made by then and documents written by then, and timelines are cut at that date
  (`page_as_of`). History, chain and ordering questions get no date filter.
- **Query understanding** (`planner.py` `understand`). One cheap call returns entities, aliases,
  search terms and a question type. The terms expand BM25, and regex dates stay the source of the
  as-of date. Chain and ordering wording ("in between", "more than once", "earliest first") routes to
  history. `CHRONICLE_QUERY_LLM=off` disables the call.
- **Agentic answering** (`answerer.py`, `pipeline.py`). Up to 3 model calls: the model may `search`
  again (new queries through the same fused, time-routed channels, 10k-character budget) or `open` full
  documents, and the third call must answer. Answer-shape templates cover chain ("In between: X; now:
  Y"), ordering, two-entity disambiguation and outcome / abstention-risk questions. A reply truncated
  by the token limit is retried once with a request to keep the reasoning brief.
  `CHRONICLE_AGENTIC=off` answers in one call.
- Tests: `tests/reason/test_answerer.py` (loop stops at 3 rounds, early stop, templates, truncation
  retry), `test_pipeline.py` (a raising question does not end the run), `test_planner_dates.py`
  (understanding never raises), `test_shared_retrieval.py` (timeline as-of cut). Older tests that
  parsed the JSON evidence format now check the FACT lines.

## P4: guard

`chronicle/guard/*`

- **Consistent pseudonyms, `CHRONICLE_REDACT_NAMES`** (from `p1/run4`, already reviewed there).
- **Surface tracking** (`pseudonymizer.py`). The mapping records how each token's value was spelled
  in the request, for P1's quote restore. Restoration itself is unchanged.
- **Response cache key** (`llm_client.py`). A loopback base URL is keyed as `loopback`, because the
  benchmark's accounting proxy uses a new port each run and every run was a cold cache.
- **`CHRONICLE_REDACT_NAMES=person`** (`pii_detector.py`). Masks people only and lets organisations,
  places and NRP through. In this corpus those are mostly project and site names. The default is
  unchanged (everything masked).
- Tests: `tests/guard/test_pseudonymizer.py`, `test_ner.py`, `test_response_cache.py`.

<!-- REDACTION -->
