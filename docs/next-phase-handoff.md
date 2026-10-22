# Hand-off: next-phase experiment (22 Oct 2026)

Spec: `/Users/sara/.claude/plans/can-you-do-the-splendid-kahn.md` (phases 0–4).
Branch `claude/exp-next-phase-567359`, worktree
`/Users/sara/Desktop/Opustron/.claude/worktrees/exp-next-phase-567359`. All commits are local;
nothing has been pushed and there are no PRs. Sara approved local per-phase commits.
`pytest -q` (with `/Users/sara/Desktop/Opustron-fullrun/.venv/bin/python`): 459 passed.

## Status

All four phases are coded, tested and committed. What remains:
1. Collect the Lightning runs that are still going (below).
2. Fill in `docs/next-phase-results.md`. The per-owner sections are written; the `<!-- RESULTS -->`
   and `<!-- REDACTION -->` placeholders need the tables below plus the Lightning numbers.
3. Optional: corpus B ladder rungs p1 and p2 with Lightning (skipped for time; see "Ladder").

## Headline numbers (corpus A, Nemotron-3-Ultra)

| Config | Overall |
|---|---|
| NVIDIA agentic RAG (reference report) | 0.828 |
| NVIDIA self-model (reference report) | 0.909 |
| Chronicle Phase 0, redaction off | 0.602 |
| **Chronicle final, redaction off** (2 fresh trials) | **0.930, 0.914 (mean 0.922)** |
| Chronicle final, redaction on, before the placeholder note (9d5d12a) | 0.839 |
| Chronicle with the placeholder note, redaction on (answer-only on the on-state) | 0.871 |
| Chronicle, person-only redaction | 0.828 |

Ladder, corpus A, Ultra, redaction off: p0 0.602, p1 0.720 (+ topic timelines), p2 0.930 (+ hybrid
retrieval), p3 0.925 (+ agentic answering; no gain on Ultra, within noise).

Redaction cost, split by stage (A, Ultra): ingest on + answer off **0.930**; ingest off + answer on
**0.876**. The cost is at answer time. Two fixes for it are in: 9d5d12a stops masking values that
spaCy tags as names ("0.71¢", "KR3", "Q4"); d6dfc55 adds a placeholder note to the system message.

Corpus B, Lightning, Phase 0, redaction off: 0.625. Run 4 had on 0.542 / off 0.677, so expect
about 5 points of Lightning noise.

Print any table with:
```bash
cd /tmp/nemoclaw/examples/tools/agent-memory-benchmark/results/runs && /Users/sara/Desktop/Opustron-fullrun/.venv/bin/python /Users/sara/Desktop/Opustron/.claude/worktrees/exp-next-phase-567359/scripts/bench_compare.py RUN_DIR... --names ... [--flips --questions ../../corpus_a/questions/questions.jsonl]
```
Reference dirs for comparison: `agentic-rag_corpus-a_nemotron`, `self-model_corpus-a_nemotron`.

## Runs still going (started 22 Oct; Lightning is about 2.5 min per question)

Logs are in `/Users/sara/Desktop/Opustron-bench/logs/`; each ends with `### exit N <run dir>`.

| Log | What | Code |
|---|---|---|
| `p3-b-lightning-off.log` | B ladder p3 = final, redaction off | ladder/p3 |
| `final-b-lightning-on.log` | B final, redaction on | final (d6dfc55) |
| `final-a-lightning-off.log` | A final, redaction off | 9d5d12a (off path identical) |
| `final-a-lightning-on.log` | A final, redaction on | final (d6dfc55) |
| `final-t1-a-ultra-on.log`, `final-t2-a-ultra-on.log` | A Ultra on, 2 fresh trials (about 40 min) | final |

Check progress: `wc -l <run dir>/answers.jsonl`. If the machine reboots, `/tmp` is wiped; the
benchmark now lives at `/Users/sara/Desktop/Opustron-bench/nemoclaw` (NVIDIA/nemoclaw-community @
f4b0a73), and `/tmp/nemoclaw` is only a symlink, so recreate it with
`ln -sfn /Users/sara/Desktop/Opustron-bench/nemoclaw /tmp/nemoclaw`. Run dirs survive a reboot.

## How to run

```bash
cd /Users/sara/Desktop/Opustron/.claude/worktrees/exp-next-phase-567359
CHRONICLE_LLM_CACHE=off REF=final CONSOLIDATE_MODEL=nvidia/Nemotron-3-Ultra-550b-a55b nohup scripts/bench_run.sh LABEL a ultra off > /Users/sara/Desktop/Opustron-bench/logs/LABEL.log 2>&1 &
```
Arguments are `LABEL CORPUS(a|b) MODEL(lightning|ultra) REDACT(on|off|person)`, plus extra runner
arguments such as `--trial-index 1 --trial-count 2`. The script snapshots `REF`'s code, so editing
the worktree mid-run is safe.

## Gotchas

- **Cache replay.** The response cache (`~/.chronicle/llm_cache`) now hits across runs, so a re-run
  replays identical prompts. Use `CHRONICLE_LLM_CACHE=off` for independent trials. Two early
  "trials" were replays and are in `logs/replayed/`; ignore them.
- **Consolidation model.** All Phase 1+ runs use Ultra for consolidation
  (`CONSOLIDATE_MODEL`), including Lightning rows. Say so in the write-up.
- **Bad and incomplete runs.** `*-exp-ingestOFF-answerON` (0.07) and `*-ingestOFF-answerON2` (hit by
  a DNS outage) are invalid; the valid one is `*-ingestOFF-answerON3`. The A Lightning runs lost 3
  of 425 documents to that outage at ingest.
- **Lost data.** Run 4's run directories were lost in a reboot. Its numbers are in this doc and in
  the shared note `…/side-session-notes/local_e1d89aa6-…/next-phase-progress.md`.
- **Gold rule.** Never read `corpus_*/questions/answers.jsonl` or the reference runs' verdict
  details; only use `correct` flags from our runs (`bench_compare.py` does this).

## Commits (oldest first)

865a433 run4 fixes · 90838bc Phase 0 · dd8f303 cache key · 8ccaf95 Phase 1 · 339ad29 Phase 2 ·
cb1cfd7 Phase 3 · 2e6a882 Phase 4 person mode · f73d0c4 consolidation tuning · d0ed887/a282858
bench_run.sh · 42180b6 truncation retry · 28b1881 cache switch + results draft · 9d5d12a value-masking
fix · e8d2690 answer.py network retries · d6dfc55 placeholder note. Tags: `ladder/p0`..`p3`, `final`.
