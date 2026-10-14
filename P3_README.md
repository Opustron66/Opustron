# Chronicle P3 baseline — setup and integration

This is a **working P3 scaffold**, not the final Chronicle system. It implements a benchmark-compatible JSONL CLI, persistent raw-document ingestion, keyword retrieval, a starter planner, an OpenAI-compatible model answerer, and unit tests. It does **not** implement bi-temporal validity, P1 claim extraction, P2's memory API, P4's privacy gateway, or final ablations.

## Install into your existing repo

Copy the `chronicle/reason/`, `adapters/chronicle/`, `eval/`, and `tests/reason/` files into matching locations. Review changes before overwriting your own work. The `eval/` files supplied here are starter utilities, not full benchmark analysis. The code requires Python 3.11+; no new third-party dependencies are needed for these files.

Run `uv run pytest tests/reason -v` from your repo root.

## Local smoke test (PowerShell)

Create two test corpus directories, each with Markdown files containing frontmatter `doc_id` and `date`.

```powershell
uv run python adapters/chronicle/ingest.py --corpus tests/fixtures/part_a --state .tmp/chronicle
uv run python adapters/chronicle/ingest.py --corpus tests/fixtures/part_b --state .tmp/chronicle
```

To actually answer non-empty retrievals, set `OPENAI_API_KEY` (or `NEBIUS_API_KEY`) and `MNEMO_MODEL` to a real supported model ID. The default `OPENAI_BASE_URL` is `https://api.tokenfactory.nebius.com/v1`. Under the benchmark, preserve the benchmark-provided `OPENAI_BASE_URL` so calls flow through its accounting proxy.

```powershell
'{"id":"q1","question":"Who manages payments?"}' | uv run python adapters/chronicle/answer.py --state .tmp/chronicle
```

Do not put secrets in source control. The official benchmark runner is invoked **from NVIDIA's benchmark root** and expects the adapter directory to be accessible there. Copy or link the adapter with the appropriate Chronicle import path, or package Chronicle so the benchmark's Python process can import it.

Update `adapters/chronicle/adapter.json` `model` to the actual model used. A `proxy` run with no LLM traffic is **not** a valid official benchmark result. For official runs use NVIDIA's `python -m bench.runner --adapter adapters/chronicle` and its documented A/B flags, then compare matching fingerprint blocks.

## Integration ownership

- P1: replace raw Markdown ingestion with claim extraction.
- P2: replace SQLite `documents` table with bi-temporal fact storage and hybrid search. This baseline **cannot reliably answer as-of questions**.
- P3: expand planner, retrieval, evidence verification, citations, abstention, multi-source synthesis, benchmark adapter, and evaluation.
- P4: route all LLM calls through the shared privacy client. The current direct HTTP client is a **temporary development fallback** and must not be used with private personal data.

Do not tune on the benchmark gold answers. Keep benchmark state out of Git.
