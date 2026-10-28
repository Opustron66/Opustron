# Remaining work before the 29 Oct deadline

Written 28 Oct. Pick up a task by putting your name next to it in the PR thread. Background is in
`docs/next-phase-handoff.md` and `docs/next-phase-results.md`.

## Where the code is

| Where | What | State |
|---|---|---|
| `main` (`452b38a`, 18 Oct) | P1 ingest, P2 memory, P3 reasoning fixes (#18–#21), P4 guard + UI | Merged |
| #24 `p4/pin-preshed` | `preshed<3.0.14` (a fresh pip install otherwise turns name masking off silently) | Open, CI green |
| #22 `p1/next-phase` | Topic timelines, hybrid retrieval, agentic answers, redaction fixes (0.602 → 0.922) | Open, CI green, **needs P2 (@nabz121) and P3 (@Starishine) review** |
| #23 `p4/surrogate-names` | Stand-in names, spending cap, run 1 masking fixes, unmasked URLs, as-of sees later docs | Open, stacked on #22, **`1498b57` needs P3 review** |

**Merge order: #24 → #22 → #23.** None of the next-phase work is on `main` yet.

## Accuracy so far (corpus A, Nemotron-3-Ultra)

| Config | Overall |
|---|---|
| NVIDIA agentic RAG (reference) | 0.828 |
| NVIDIA self-model (reference) | 0.909 |
| Chronicle Phase 0, redaction off | 0.602 |
| Chronicle final, redaction off (2 trials) | 0.930, 0.914 (mean 0.922) |
| Chronicle, redaction on, tokens + placeholder note | 0.871 |
| Run 1 (27 Oct, redaction on, tokens) | 0.871; 24 misses; disambiguation 10/15 |
| Run 2 (after run 1's masking fixes) | 17 misses (about 0.91 if the question count matches run 1). **Score not recorded anywhere.** as_of 2/6 |

Not benchmarked yet: stand-in names (`CHRONICLE_PSEUDONYMS=surrogate`) and `1498b57` (as-of
questions see later documents). The 22 Oct runs listed in the hand-off are invalid (401s).

**What we can honestly claim.** +1.3 over 0.909 is within run-to-run noise (2–3 questions), so
don't say "beats NVIDIA". Aim for: *roughly level with NVIDIA's best with privacy on, +9 over their
agentic RAG, plus a per-category breakdown.* NVIDIA's numbers have no privacy layer at all.

## Tasks

### 1. Check the key and cap spending — owner: ___
- Free check: `curl -s https://api.tokenfactory.nebius.com/v1/models -H "Authorization: Bearer $OPENAI_API_KEY"`.
- Use promo credits with no card attached. Token Factory only alerts, and charges the card at $0.
- Set `CHRONICLE_SPEND_LIMIT_USD` and `CHRONICLE_SPEND_SINCE` (ISO timestamp) in `.env` (#23, see README).
- **Done when** the curl lists models and the cap is set.

### 2. Privacy-on headline run — owner: ___
- Check out #23's branch (`p4/surrogate-names`) and run `uv sync`. Then confirm masking actually works:
  `uv run python -c "from chronicle.guard.pii_detector import ner_available; print(ner_available())"` → `True`.
- Clone the benchmark, `NVIDIA/nemoclaw-community` at `f4b0a73`. `scripts/bench_run.sh` defaults to Sara's
  local paths, so set `BENCH`, `VENV` and `ENV_FILE` yourself:
  ```bash
  BENCH=<nemoclaw>/examples/tools/agent-memory-benchmark VENV=$PWD/.venv ENV_FILE=$PWD/.env \
  CHRONICLE_LLM_CACHE=off CONSOLIDATE_MODEL=nvidia/Nemotron-3-Ultra-550b-a55b \
  nohup scripts/bench_run.sh t1-a-ultra-on a ultra on --trial-index 1 --trial-count 2 > t1.log 2>&1 &
  ```
  Then the same with `t2` / `--trial-index 2`.
- **Done when** both trials finish, `grep -c "answering failed" t*.log` is about 0, and the scores are posted in the PR.

### 3. Stand-ins vs tokens — owner: ___
- Answer-only run with `CHRONICLE_PSEUDONYMS=surrogate` on task 2's redaction-on ingest state. The gap is at
  answer time, so a full ingest isn't needed.
- **Done when** 2 trials have run. Make `surrogate` the default only if it beats tokens by 2+ points.

### 4. Write the numbers down — owner: ___
- Use `scripts/bench_compare.py RUN_DIR... --names ...` with the reference dirs `agentic-rag_corpus-a_nemotron`
  and `self-model_corpus-a_nemotron`. Include the **per-category** table, especially as_of (NVIDIA: 66.7%).
- Fill the `<!-- RESULTS -->` and `<!-- REDACTION -->` placeholders in `docs/next-phase-results.md`, and
  replace the stub `docs/benchmark-results.md`. Record run 2's real score.

### 5. Stop tuning after one fix round
At most one more "fix from the misses, re-run" cycle. Each round fits to the benchmark's own
questions, which makes the number less trustworthy.

### 6. Submission material — owner: ___
- `docs/devpost.md` is a stub. It needs: what Chronicle does (below), architecture (`docs/architecture.md`),
  results (task 4) and the privacy story (egress log, masking, spending cap).
- `docs/demo-script.md` has 3 bullets. Expand it into a shot list for the video using `data/demo/`.

### 7. Optional (probably no time)
Lightning and corpus B re-runs (about 4 h per B run, 8 h per A run). Corpus B's best valid score is
0.625 (Lightning, Phase 0, off).

## What Chronicle does (for the write-up)

1. The user runs ingest on a folder of emails, Slack threads, merge requests and notes.
2. P1 extracts claims, each with a verbatim quote (claims that fail the check are dropped), plus a dated
   timeline per topic and a page per person.
3. P2 stores every fact with two dates, when it was true and when it was said. Changes add versions;
   nothing is deleted.
4. The user asks in the UI chat or through Hermes. P3 routes by question type: an as-of question only sees
   what was known by then. It searches facts, timelines, person pages and documents, can search again or
   open a document (up to 3 calls), and answers with sources or "not in the corpus".
5. P4 masks names, emails, phones and IDs on every model call and restores them in the reply. The UI egress
   log shows exactly what left the machine. Tavily lookups with personal data are blocked.

## Gotchas
- Never read `corpus_*/questions/answers.jsonl` or the reference runs' verdict details; only our own `correct` flags.
- The response cache replays identical prompts across runs. Use `CHRONICLE_LLM_CACHE=off` for independent trials.
- Consolidation uses Ultra in every Phase 1+ run, including Lightning rows. Say so in the write-up.
- A pip install made in the last few days may have masking off. Run `uv sync` (see #24).
