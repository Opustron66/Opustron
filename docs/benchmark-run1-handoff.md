# Benchmark Run 1 — Handoff Notes

**Date**: 2026-10-17  
**Branch**: `p1/ingest-skeleton`  
**Goal**: Run NVIDIA mnemo benchmark (corpus B) and get scores.

---

## What Was Done

All scaffolding is in place and working:

| Step | Status | Detail |
|------|--------|--------|
| Clone `nemoclaw-community` | ✅ | at `/tmp/nemoclaw` |
| `pip install -e .` (Chronicle) | ✅ | installs cleanly; ignores axolotl version noise |
| Fix `adapter.json` model ID | ✅ | `nvidia/Nemotron-3_5-Lightning` |
| Fix `adapter.json` python → python3 | ✅ | committed |
| Fix `llm_client.py` env var fallback | ✅ | now reads `OPENAI_API_KEY` / `OPENAI_BASE_URL` as fallback for `NEBIUS_*` |
| SSL cert fix | ✅ | `SSL_CERT_FILE=$(python3 -c "import certifi; print(certifi.where())")` |
| Correct `--upstream` flag | ✅ | `https://api.tokenfactory.nebius.com` |

**Run command that worked up to ingest**:

```bash
cd /tmp/nemoclaw/examples/tools/agent-memory-benchmark
set -a; source /Users/sara/Desktop/Opustron/.env; set +a
export SSL_CERT_FILE=$(python3 -c "import certifi; print(certifi.where())")
export REQUESTS_CA_BUNDLE=$SSL_CERT_FILE
export CHRONICLE_MAX_TOKENS=8192
python3 -m bench.runner \
  --adapter /Users/sara/Desktop/Opustron/adapters/chronicle \
  --corpus corpus_b/corpus \
  --questions corpus_b/questions/questions.jsonl \
  --gold corpus_b/questions/answers.jsonl \
  --upstream https://api.tokenfactory.nebius.com \
  2>&1 | tee /Users/sara/Desktop/Opustron/data/benchmark/results_run1.txt
```

---

## The Bug Blocking Scores

**Error**: `[chronicle] FAILED <doc>: no JSON claims list in reply`  
**Scope**: 66 of 90 corpus_b part_a documents; 79 of 90 part_b. 24 part_a documents DO succeed.

### Diagnosis

`chronicle/guard/llm_client.py:231` (in `_call_api`):

```python
content = resp.choices[0].message.content or ""
```

When `message.content` is `None`, this silently becomes `""`. Then `parse_llm_json("")` in `extractor.py:187` finds no JSON object and raises `ValueError("no JSON claims list in reply")`.

**Why is content `None`?**  
Direct API test confirms: the model (`nvidia/Nemotron-3_5-Lightning`) is a reasoning model. It puts its thinking in `message.model_extra['reasoning_content']` and the actual JSON answer in `message.content`. For larger/more complex documents the reasoning trace is very long. At `max_tokens=8192` (shared between reasoning + output), the reasoning alone can exhaust the budget, leaving the model no tokens to emit the JSON answer → `content = None`, `finish_reason = "length"`.

Confirmed with a direct API call — simple prompt returns `content: '{"claims": []}'` fine; the 66 failing documents are larger channel/DM conversations.

### Fix Options

**Option A — raise `max_tokens` further** (quick try, may not be enough):  
Set `CHRONICLE_MAX_TOKENS=32768` or higher. Nemotron Lightning supports up to ~128k context. Risk: cost goes up; some docs might still fail.

**Option B — separate reasoning from output tokens** (correct fix):  
Pass `max_tokens` only for output and let reasoning run uncapped. With the Nebius/NIM API, check if it supports a separate `reasoning_effort` or `thinking_budget` parameter. Otherwise restructure to not use structured output (`response_format: json_schema`) — instead ask for plain JSON in the prompt and parse the raw text (Chronicle already has `parse_json_reply` for this in `llm_client.py`).

**Option C — strip reasoning via model_extra** (defensive fix):  
In `_call_api`, after the API call:
```python
content = resp.choices[0].message.content
if not content:
    # reasoning model exhausted its output budget; reasoning is in model_extra
    # try to recover JSON from reasoning_content as a last resort
    reasoning = (resp.choices[0].message.model_extra or {}).get('reasoning_content', '')
    content = reasoning  # parse_llm_json will strip <think> blocks and find JSON
content = content or ""
```
This is a fallback — the reasoning trace sometimes contains the JSON before the model ran out of tokens.

**Option D — skip `response_format: json_schema`** (most robust):  
The endpoint may not handle structured output reliably. Disable it: set `self._structured = False` at construction, or add a `CHRONICLE_STRUCTURED=false` env var check. The model will return plain text; `parse_json_reply` already handles stripping `<think>` blocks.

### Recommended order of attempts

1. Try **Option D** first (disable json_schema) — one-line change, already coded, zero risk.  
2. If that fixes parse failures but output quality drops, try **Option B** (uncapped reasoning).

---

## Files Changed This Session

| File | Change |
|------|--------|
| `adapters/chronicle/adapter.json` | model ID set; `python` → `python3` |
| `chronicle/guard/llm_client.py` | `OPENAI_API_KEY`/`OPENAI_BASE_URL` fallback added to `__init__` |

---

## LLM Cache Note

The LLM cache at `~/.chronicle/llm_cache/` may contain partial/empty responses from this run's failed calls. The cache key does **not** include `max_tokens`, so raising the token limit alone won't bypass stale cache entries. **Clear the cache before re-running**:

```bash
rm -rf ~/.chronicle/llm_cache
```

---

## Next Session Prompt (copy this)

> I'm working on Chronicle, a bi-temporal memory agent at `/Users/sara/Desktop/Opustron`, branch `p1/ingest-skeleton`. I need to fix the NVIDIA mnemo benchmark ingest so it can actually produce scores.
>
> **The problem**: Running the benchmark against corpus B fails with `no JSON claims list in reply` for ~73% of documents. Root cause: `nvidia/Nemotron-3_5-Lightning` is a reasoning model; its reasoning trace consumes the token budget, leaving `message.content = None`. `LLMClient._call_api` in `chronicle/guard/llm_client.py:231` has `content = resp.choices[0].message.content or ""` which silently becomes an empty string.
>
> **The fix to try first (Option D)**: Disable `response_format: json_schema` for this model. In `LLMClient.__init__`, set `self._structured = False` when the model name contains "Lightning" or "nemotron" (or add a `CHRONICLE_STRUCTURED=false` env var). The extractor's `parse_llm_json` already handles plain-text JSON replies.
>
> **After fixing**, clear the LLM cache (`rm -rf ~/.chronicle/llm_cache`) and re-run the benchmark with:
>
> ```bash
> cd /tmp/nemoclaw/examples/tools/agent-memory-benchmark
> set -a; source /Users/sara/Desktop/Opustron/.env; set +a
> export SSL_CERT_FILE=$(python3 -c "import certifi; print(certifi.where())")
> export REQUESTS_CA_BUNDLE=$SSL_CERT_FILE
> export CHRONICLE_MAX_TOKENS=32768
> python3 -m bench.runner \
>   --adapter /Users/sara/Desktop/Opustron/adapters/chronicle \
>   --corpus corpus_b/corpus \
>   --questions corpus_b/questions/questions.jsonl \
>   --gold corpus_b/questions/answers.jsonl \
>   --upstream https://api.tokenfactory.nebius.com \
>   2>&1 | tee /Users/sara/Desktop/Opustron/data/benchmark/results_run1.txt
> ```
>
> **Target**: >91% overall accuracy, ≥83% on `as_of`. NVIDIA baselines: agentic RAG 82.8%, self model 90.9%.
>
> The benchmark runner lives at `/tmp/nemoclaw/examples/tools/agent-memory-benchmark` (already cloned). Chronicle is installed as an editable package (`pip install -e .` already run). The `.env` has `OPENAI_API_KEY` (Nebius key), `OPENAI_BASE_URL=https://api.tokenfactory.nebius.com/v1/`, `CHRONICLE_MODEL=nvidia/Nemotron-3_5-Lightning`.
>
> Read `docs/benchmark-run1-handoff.md` for full context before starting.
