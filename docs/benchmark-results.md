# Benchmark results

NVIDIA Agent Memory Benchmark (`NVIDIA/nemoclaw-community` @ `f4b0a73`), corpus A, 186 questions,
Nemotron 3 Ultra (`nvidia/Nemotron-3-Ultra-550b-a55b`) on Nebius Token Factory, graded by the
benchmark's own grader. NVIDIA's reference runs use the same model and corpus.

Tables come from `scripts/bench_compare.py`, which reads only the `correct` flag of our own runs'
verdicts and the reference runs' aggregate `report.json`. No gold answers were read.

## Headline

| System | Privacy | Overall |
|---|---|---:|
| NVIDIA agentic RAG (reference) | none | 0.828 |
| NVIDIA self-model (reference) | none | 0.909 |
| Chronicle, run 10 | every name masked | **0.946** (176/186) |
| Chronicle, runs 7 and 8 | off | **0.957** (178/186) |

## Run history

| Run | Privacy | Overall | What changed |
|---|---|---:|---|
| Phase 0 | off | 0.602 | First end-to-end pipeline (claims only) |
| Next phase, 2 trials | off | 0.930, 0.914 | Topic timelines, hybrid retrieval, agentic answers |
| 1 | on (tokens) | 0.871 | First privacy-on run; 24 misses |
| 2 | on | 0.909 | Fixed masking bugs that garbled the answer prompt |
| 3 | on | 0.898 | |
| 4 | off | 0.914 | Privacy-off baseline for the answer-side fix rounds |
| 5 | off | 0.941 | Bare value first, positive-form rewrite, voting, wider second look |
| 6 | off | 0.946 | Key lines, quote-checked answers, refusal and deadline rules |
| 7 | off | 0.957 | Answers in the evidence's words, either-or shape, both-numbers check |
| 8 | off | 0.957 | Claim-based voting, hyphen-aware key lines |
| 9 | on | 0.898 | Answered "Jin." where privacy-off runs said "Jin Oh." |
| 10 | on | 0.946 | Full names written out in the evidence before masking |

## Per question type

Per-type numbers were recorded up to run 6. Later runs' per-type tables are on P4's machine.

| Type | NVIDIA agentic RAG | NVIDIA self-model | Run 4 | Run 5 | Run 6 |
|---|---:|---:|---:|---:|---:|
| abstention (13) | 1.000 | 0.923 | 1.000 | 0.923 | 1.000 |
| as_of (6) | 0.333 | 0.667 | 0.333 | 0.667 | 0.667 |
| attribution (5) | 0.800 | 0.800 | 1.000 | 0.600 | 0.800 |
| chain_freshness (5) | 0.600 | 1.000 | 0.800 | 0.800 | 0.800 |
| citation (12) | 0.917 | 1.000 | 0.917 | 0.833 | 0.917 |
| constraint (5) | 0.800 | 1.000 | 1.000 | 1.000 | 1.000 |
| disambiguation (15) | 0.667 | 0.867 | 0.800 | 0.933 | 0.867 |
| freshness (12) | 0.750 | 0.917 | 0.833 | 1.000 | 0.917 |
| multi_source (73) | 0.877 | 0.945 | 0.986 | 0.986 | 0.986 |
| ordering (4) | 0.750 | 1.000 | 1.000 | 1.000 | 1.000 |
| set_difference (6) | 0.833 | 0.833 | 0.667 | 1.000 | 1.000 |
| single_hop (30) | 0.867 | 0.833 | 0.933 | 0.967 | 0.967 |
| **overall (186)** | **0.828** | **0.909** | **0.914** | **0.941** | **0.946** |
| tokens / question | 14.5k | 241k (+183M ingest) | 12.9k | 19.9k | 29.1k |

## Caveats

- Identical code varies by about ±2 points (2–4 questions) between runs. Treat single runs as
  approximate.
- NVIDIA calls its reference runs "not a ranking". Read this as same model, same corpus, same
  grader, not as a leaderboard.
- Fix rounds were driven by corpus A's misses (our own answers and right/wrong flags only). Corpus B,
  a different domain, has not been re-run with the final pipeline; its best valid score is 0.625
  (Lightning, Phase 0, privacy off).
- Topic consolidation uses Ultra in every run from the next phase on.
- The accounting proxy could not read gzipped responses, so ingest token counts were not recorded.
  We make no claim about ingest cost.
