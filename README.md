# Chronicle

A personal AI agent whose memory keeps up. Built for the Nebius x NVIDIA Global
AI Hackathon.

Chronicle's memory is **bi-temporal**: every fact records when it was true
(`valid_from` / `valid_to`) and when Chronicle learned it. Facts are never
deleted. When Bob takes over the payments service from Alice, Alice's fact is
closed rather than overwritten, so "who owned payments on 3 May?" still has the
right answer. Personal data is pseudonymised before any call leaves the machine.

| Piece | What it does |
|---|---|
| Ingest (P1) | Parses email, chat, calendar and markdown into events and facts |
| Memory (P2) | Bi-temporal store with `as_of()` queries |
| Reason (P3) | Plans, retrieves and answers with citations; abstains when unsure |
| Guard (P4) | PII detection, pseudonymisation, the shared LLM client, egress log |
| UI (P4) | Memory Time Machine: drag a date slider and watch facts change |
| Deploy (P4) | Hermes Agent plugin, OpenShell egress lockdown, one-command install |

## Quick start

Needs Python 3.10+, [uv](https://docs.astral.sh/uv/) and Node 18+.

```bash
git clone https://github.com/Opustron66/Opustron.git
cd Opustron
uv sync --extra dev
cp .env.example .env        # then fill in NEBIUS_API_KEY
uv run pytest
```

Chronicle reads keys from environment variables and does not load `.env` by
itself yet, so export it in your shell before running anything that calls a
model:

```bash
set -a; source .env; set +a
```

| Variable | Used for |
|---|---|
| `NEBIUS_API_KEY` | Nebius Token Factory (all model calls) |
| `NEBIUS_BASE_URL` | Defaults to `https://api.tokenfactory.nebius.com/v1/` |
| `CHRONICLE_MODEL` | Defaults to `nvidia/Nemotron-3_5-Lightning`; use `nvidia/Nemotron-3-Ultra-550b-a55b` only for official benchmark runs |
| `CHRONICLE_MAX_TOKENS` | Default completion budget for `chronicle.guard.llm` (16384). Reasoning tokens count toward it, so small budgets return empty or truncated replies |
| `CHRONICLE_PSEUDONYMS` | `surrogate` shows the model realistic stand-in names ("Jordan Okafor") in place of `PERSON_1` tokens. Unset = tokens |
| `CHRONICLE_SPEND_LIMIT_USD` / `CHRONICLE_SPEND_SINCE` | Hard spending cap: model calls are refused once the egress log shows this many USD spent since the ISO timestamp (Token Factory itself only alerts, and charges the card at $0) |
| `CHRONICLE_LLM_CACHE` | `off` disables the response cache in `~/.chronicle/llm_cache` (independent benchmark trials). Unset = on |
| `TAVILY_API_KEY` | Web enrichment |
| `CHRONICLE_REDACT_RECALL` | Hermes plugin: `0` stops masking emails/phones/IDs in recalled memory |
| `CHRONICLE_REDACT_NAMES` | Benchmark runs only: `off` stops pseudonymising names, organisations and places (emails/phones/IDs stay masked); `person` masks people only, leaving organisations and places. Unset = on |

## Calling a model: always use `chronicle.guard.llm`

Every teammate calls models through one client. Never import `openai`
directly.

CI enforces this: `tests/guard/test_egress_boundary.py` fails if code outside
`chronicle/guard/` imports `openai`, `requests`, `httpx`, `aiohttp`,
`urllib.request` or `http.client`, or hard-codes the Token Factory / Tavily URLs.
The only exception is the Tavily client, which has its own PII gate. The sandbox
policy can't catch this, because it sees one Python process.

```python
from chronicle.guard import llm

text = llm.complete([{"role": "user", "content": "Summarise Alice's email"}])
data = llm.complete(messages, schema={"type": "object", "properties": {...}})  # returns a dict
raw = llm.complete(messages, schema={"name": "claims", "schema": {...}})      # returns the reply text
```

Pass a bare JSON Schema to get a parsed dict back. The parser tolerates
reasoning-model noise (`<think>` blocks, code fences, a draft before the final
answer) and takes the last complete JSON value; it raises `ValueError` if the
reply has none. The same parser is available as
`chronicle.guard.llm_client.parse_json_reply`. Pass an OpenAI `json_schema`
envelope (`{"name": ..., "schema": ...}`) to get the raw reply text and parse
it yourself.
If the endpoint rejects `response_format`, the client retries without it and
stops sending it. For your own settings, build a client:
`LLMClient(default_model=..., max_tokens=8192, timeout=180)`.

What it does for you:

- **Pseudonymises** names, emails, phone numbers and other PII (`Alice Tan` →
  `PERSON_1`) before the request leaves the machine, and restores them in the
  reply.
- **Caches** responses in `~/.chronicle/llm_cache/`, so reruns cost nothing.
- **Logs** every outbound call (model, tokens, which PII types were redacted,
  a redacted preview) to `~/.chronicle/egress.log`. The UI shows this log.

Response-cache keys include the endpoint, model, schema, effective token budget
and temperature. Changing the budget makes a fresh request. Empty, incomplete
and unparseable structured replies are not cached; unusable existing entries
are bypassed. Structured cache admission also checks required top-level fields
and their declared types, while callers remain responsible for full validation.
Only pseudonymised replies are stored. The versioned key ignores older entries
without deleting them. Incomplete replies raise a safe error with finish reason
and token budget after usage is logged; retries remain caller-controlled.

Ingestion uses this client too, so corpus text is pseudonymised before it
reaches Nebius and quotes come back with the real values restored:

```bash
python -m chronicle.ingest --corpus DIR --state DIR [--model ID] [--timeout 180] [--max-tokens 8192]
```

What gets detected:

| Masked | How |
|---|---|
| Emails, phones, SSNs, cards, IPs, URLs | Regex, always on |
| People, organisations, places | Presidio + spaCy `en_core_web_sm`, installed by `uv sync` |
| **Not masked: dates and times** | Deliberately. Chronicle reasons about when facts were true; a model shown `DATE_1` can't order them |

The first call takes ~15s while spaCy loads. If the model can't load, a warning
says `Name detection is OFF` and only the regex tier runs. Check with
`uv run python -c "from chronicle.guard.pii_detector import ner_available; print(ner_available())"`.
The small model misses some lone first names ("Priya") and sometimes flags
non-names ("Nebius AI" as a person).

## Web enrichment (Tavily)

```python
from chronicle.integrations.tavily import TavilyClient, PrivacyBlocked

results = TavilyClient().search("Nebius Token Factory pricing", max_results=5)
```

Needs `TAVILY_API_KEY`. A search query can't be pseudonymised (nobody can search
for `PERSON_1`), so a query that identifies a person is refused instead:
emails, phone numbers, IDs and people's names raise `PrivacyBlocked` and
nothing is sent. Organisations, places and links are
allowed. Every query that is sent goes to the egress log as provider `tavily`.

## Memory (P2): bi-temporal store

`chronicle.memory` stores P1's claims in SQLite (`state/memory.sqlite3`). Facts are never
deleted: a newer value closes the old fact's `valid_to`, and every change is kept as a
version, so you can ask both what was true on a day and what Chronicle believed at the time.
Design notes are in [docs/architecture.md](docs/architecture.md).

```python
from chronicle.memory import MemoryAPI

memory = MemoryAPI.from_state(".tmp/chronicle")   # loads new lines from state/claims.jsonl
memory.holder_at("owns", "payments service", "2026-05-03").subject   # "Alice Chen"
memory.search("who owns payments", as_of="2026-05-20")               # ranked Facts with doc_id + quote
memory.history("payments service")                                   # every owner, oldest first
memory.as_of("2026-06-01", known_at="2026-04-20")                    # what we believed on 20 Apr
```

```bash
python -m chronicle.memory sync  --state .tmp/chronicle   # load claims.jsonl into SQLite
python -m chronicle.memory serve --state .tmp/chronicle   # UI API on http://localhost:8000/api
```

| Endpoint | Returns |
|---|---|
| `GET /api/entities` | Entities with `entity_id`, `name`, `entity_type`, `aliases`, `fact_count` |
| `GET /api/entities/{id}/history` | `{entity, facts}`, superseded facts included |
| `GET /api/facts?as_of=YYYY-MM-DD` | Facts true that day (all facts without `as_of`); optional `known_at`, `subject`, `predicate` |
| `GET /api/facts/{fact_id}/versions` | Every recorded version of one fact |
| `GET /api/timeline?start=&end=` | Facts starting or ending in the window |
| `GET /api/search?q=&as_of=&k=` | Ranked facts |
| `GET /api/span` | First and last day in memory (slider range) |
| `POST /api/ask` | `{answer, source_ids, citations}` for `{question, as_of?}`; answers through the privacy guard |

The server reloads `claims.jsonl` when P1 appends to it. Intervals are half-open: on a
handover day the new owner holds. `chronicle.memory.backend.SQLiteBackend` implements the
Hermes `ChronicleBackend` protocol (`$CHRONICLE_MEMORY_DB`, default
`~/.chronicle/memory.sqlite3`).

## P3: benchmark adapter and ingestion handoff

The benchmark adapter now runs P1's `python -m chronicle.ingest`. It uses the
same extraction, entity resolution, incremental ingestion and `Claim` schema
as normal ingestion. UI chat and benchmark answering both retrieve evidence
through P2's temporal search, retaining source document IDs, verbatim quotes,
observation dates and validity fields. The benchmark opens `state/memory.sqlite3`
and syncs P1's `state/claims.jsonl` on each question, then closes its connection.
There is no separate raw-document SQLite ingestion path.

P1 and P2 normalize literal email values to the `email` predicate rather than
`status`; email addresses are values, not separate entities, and multiple contact
addresses may coexist. Deadline placeholder aliases (`due`, `deadline`, `due date`)
normalize to `due`. P1 emits the new date for rescheduling and discards a redundant
closing-only dated claim when that same document contains a validated replacement
for the same subject/predicate; P2 closes the old schedule at the replacement's
observation date. Ownership endings and standalone closing claims remain intact.
Re-ingest into a fresh state to apply this to previously processed documents:
the extraction prompt/cache version changed, but existing done markers and stored
facts are not rewritten. Baseline evaluation state and reports should be retained.

```powershell
uv run python -m chronicle.ingest --corpus tests/fixtures/corpus/part_a --state .tmp/chronicle
uv run python -m chronicle.ingest --corpus tests/fixtures/corpus/part_b --state .tmp/chronicle
'{"id":"q1","question":"Who owns payments?"}' | uv run python adapters/chronicle/answer.py --state .tmp/chronicle
uv run pytest tests/reason tests/ingest tests/guard
```

Set `NEBIUS_API_KEY` and `CHRONICLE_MODEL` before starting either process.
Extraction and answering both use the shared privacy guard. For reasoning
models, set `CHRONICLE_MAX_TOKENS` to a sufficient answer budget (for example,
8192); P1's CLI defaults to 8192 for extraction. The legacy adapter ingest
script forwards to P1's CLI for existing callers, including its exit status.
Existing `chronicle_adapter.sqlite3` state must be re-ingested into a fresh
state directory. It is never used as a fallback. Malformed question records
are skipped with a line-number diagnostic on stderr; stdout stays JSONL.

### P1/P2/P3 integration status

P1 ingestion is shared. P2 provides persistent claim storage and temporal search.
UI chat and benchmark answering use the same P2 `MemoryAPI.search`, evidence
conversion and privacy-routed answerer. Existing `claims.jsonl` state is loaded
into P2 automatically, and subsequent questions pick up appended claims.
An existing P2 database also works without the claims file.

- P1 owns extraction and the shared `Claim` contract.
- P2 owns durable claim storage, supersession and temporal search.
- P3 uses P2 for both UI chat and benchmark retrieval.
  Ingestion continues to use P1's entry point.

Both paths apply P2's supersession and as-of filters. The benchmark JSONL input
optionally accepts `"as_of":"2026-06-20"` to supply the same date context as
the UI slider. Explicit dates in the question override that context; malformed
`as_of` values are skipped with a diagnostic. Without `as_of` or an explicit
question date, historical evidence remains searchable. Match the state and date
context when comparing UI and benchmark answers. Output remains
`{id, answer, source_ids}`.

Recognized ISO/English calendar dates are removed from the lexical search text
and retained as P2 temporal filters. This avoids matching an unrelated document
solely because it contains the same year. The original question and reference
date still reach the answerer; history comparisons retain historical evidence.
Standalone numeric entity labels such as `Apollo 2026` are preserved. This is
date-token separation, not a general semantic relevance or entailment verifier.

Regression tests compare the exact model prompts, filtered evidence and citations
from UI and JSONL requests. They do not verify live-provider behavior, official
benchmark scores or final ablations. Do not compare legacy raw-document runs
with current temporal-store runs as if they used identical retrieval.

Update `adapters/chronicle/adapter.json`'s `model` to the actual model for an
official run. Launch NVIDIA's `python -m bench.runner --adapter
adapters/chronicle` from its benchmark root with Chronicle importable. If the
runner supplies an accounting proxy, configure the guard's `NEBIUS_BASE_URL`
to that proxy and verify accounting before reporting results. The adapter no
longer reads `OPENAI_BASE_URL`, `OPENAI_API_KEY` or `MNEMO_MODEL`. A proxy run
without model traffic is not an official result. Keep state and gold answers
out of Git, and do not tune on gold answers.

The guard pseudonymises names, organisations and places before every model
call, and gives one entity the same token everywhere in a request ("Camden Row"
and "camden's" both become `LOC_1`). Placeholders still cost some answer
accuracy, so a benchmark run may set `CHRONICLE_REDACT_NAMES=off` to send real
names. Emails, phones, IDs and URLs stay masked either way, and a warning is
logged while names are off. Redaction is on by default: set the switch per run,
not in `adapter.json` or `.env`, and report scores both with and without it.

## Memory Time Machine UI

```bash
cd ui
npm install
npm run dev      # http://localhost:5173
npm test         # Vitest + Testing Library
```

**Real data.** The UI proxies `/api` to the memory server on port 8000. In
another terminal, serve an ingested state dir:

```bash
uv run python -m dotenv -f .env run -- python -m chronicle.memory serve --state DIR
```

The header then shows `● Live memory · N facts`, entity cards and the timeline
use the store's facts, and the slider starts on the latest date. Cards show an
entity on either side of a fact ("Alice Chen: owns → payments service", and
"payments service: who owns → Alice Chen"). As in the store, `valid_to` is the
first day a fact is no longer true, so on a handover day only the new owner is
current. Without the server the memory views show labelled sample data.

**Real chat.** The memory server also serves `POST /api/ask`. Start it with
`NEBIUS_API_KEY`, `CHRONICLE_MODEL` and a sufficient `CHRONICLE_MAX_TOKENS`
(for example, 16384 for testing a reasoning model) loaded into that server
process. Credentials set in another terminal are not inherited. For an existing
Windows virtual environment, run from the repo root:

```cmd
.venv\Scripts\python.exe -m dotenv -f .env run -- .venv\Scripts\python.exe -m chronicle.memory serve --state .tmp/accuracy-smoke
```

Questions without a date use the slider's day. An explicit ISO or English month
date overrides it: with the slider at 20 June 2026, "Who owned billing on June 9?"
retrieves facts valid on 9 June 2026. Yearless dates use the slider's year (or the
current year outside the UI). Before/after/history questions retain historical
evidence instead of applying a single-day filter. Dates are valid-time filters,
not a limit on when Chronicle learned a fact; `known_at` questions, relative dates
and arbitrary date ranges are not implemented in chat's starter planner.

Chat returns source document IDs as citation chips. No matching evidence produces
"Not in the corpus" without calling a model. Invalid requests return 422, invalid
calendar dates in questions return 400, and answer-generation failures return a
generic 502 without provider details. The UI displays an error on failed requests
and never substitutes a sample corpus answer. Answer wording still depends on the
configured model; retrieval does not guarantee answer accuracy.

Answer evidence rules distinguish a plan from an outcome: a scheduled date does
not establish completion, non-completion or cancellation, even when the date is
in the past. Schedule-only evidence should produce "the corpus does not confirm
whether it happened" rather than a definite yes/no. Explicit completed, cancelled
or not-completed evidence can support a definite answer. These rules are appended
even when an external benchmark supplies the answer-format contract; they remain
model instructions, not an independent semantic verifier.

Answer form rules (`ANSWER_FORM`) follow how the benchmark grades: clause by clause,
crediting a value only where it is asserted. So the answer starts with the bare value as its own
sentence ("Phoenix.", "Duplicated.", not "Phoenix is not a real project"), gives
no hedge after an answer it has given, leaves out superseded values unless asked for
the history, counts every distinct instance for "how many" questions, and words a gap
as "The corpus does not record ...". As-of yes/no questions answer "Yes." or "No."
first. Retrieval packs about 10k tokens of evidence (`CHAR_BUDGET` 40,000 characters).

**Live egress log.** In a second terminal, run:

```bash
uv run python -m chronicle.guard.egress_server     # http://127.0.0.1:8001/api/egress
```

The bottom panel then shows `● LIVE` and every model call and web search as it
leaves the machine, refreshed every 2s, with redaction badges and PII types.
Without the server it shows `sample data` (made-up entries), and if the server
stops after being live it shows `offline` with the last real entries. The
server only listens on 127.0.0.1 and only serves `GET /api/egress?n=30`.
Polls while it's down show up as 500s in the browser console; that is expected.

## Running in a sandbox with Hermes Agent

Chronicle plugs into [Hermes Agent](https://hermes-agent.nousresearch.com) as
its memory provider and runs inside an NVIDIA OpenShell sandbox via NemoClaw.

```bash
# Inside the sandbox (nemoclaw <sandbox> connect), or wherever Hermes runs:
./deploy/install.sh
hermes memory setup                  # choose "chronicle"

# On the host: allow Chronicle's two hosts on top of the sandbox's policy (dev)
./deploy/install.sh --sandbox <sandbox>

# On the host: lock the sandbox down to Token Factory + Tavily only (demo)
./deploy/install.sh --sandbox <sandbox> --lockdown
```

Install before `--lockdown`: the lockdown policy blocks PyPI. The install also
downloads spaCy's English model from github.com, so inside a NemoClaw sandbox
add the `github` preset while installing (`install.sh` stops with a clear error
if name detection can't load). To see anything
the policy blocked, run `openshell logs <sandbox> --source sandbox`.

| File | Purpose |
|---|---|
| `deploy/openshell-policy.yaml` | Complete policy. Network reaches only Hermes's inference route, Token Factory and Tavily. Replaces the live policy. |
| `deploy/presets/chronicle.yaml` | Same two Chronicle hosts as a NemoClaw preset that layers on top |
| `deploy/hermes-plugin/chronicle/` | Hermes plugin; see its README for hooks and tools |

In Hermes, the agent gets `chronicle_recall` (with `as_of: YYYY-MM-DD` to ask
about a past date) and `chronicle_remember`, plus `chronicle_web_search` when
`TAVILY_API_KEY` is set. Memory is stored in the SQLite store at
`$HERMES_HOME/chronicle/memory.sqlite3`, one per Hermes profile, so it survives
restarts. Set `CHRONICLE_MEMORY_DB` to a path to share one database instead, for
example the UI's `DIR/memory.sqlite3`, so Hermes memories and ingested
documents are recalled together.

## Tests

```bash
uv run pytest            # Python: guard, memory, ingest, deploy policy, Hermes plugin
cd ui && npm test        # UI
```

CI runs both on every push and pull request. Every PR adds tests for what it
changes and updates this README when setup or behaviour changes.

## Repo layout

```
chronicle/
  ingest/        P1  parsers, extraction, entity resolution, temporal normalisation
  memory/        P2  bi-temporal store, search, supersession
  reason/        P3  planner, retriever, answerer, abstention
  guard/         P4  PII detection, pseudonymiser, privacy router, LLM client, egress log
  integrations/  P4  Hermes memory provider, Tavily
  schema.py          shared models (Event, Entity, Source)
adapters/        NVIDIA Agent Memory Benchmark adapter
eval/            benchmark runner, ablations, failure analysis
ui/              P4  Memory Time Machine (React + Vite)
deploy/          P4  install script, OpenShell policy and preset, Hermes plugin
docs/            architecture, benchmark results, demo script
```

## Working on the repo

- Branch from `main` as `p<N>/<topic>` and open a PR.
- Every PR needs one approving review from someone in a different role before
  merging.
- Never look at the benchmark's gold answers while developing.
