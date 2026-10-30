# Privacy guard and egress

Every model call and web search leaves the machine through `chronicle/guard/`. Design notes are in
[architecture.md](architecture.md#privacy-guard-p4).

## Calling a model: `chronicle.guard.llm`

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

## Masking names in benchmark runs

The guard pseudonymises names, organisations and places before every model
call, and gives one entity the same token everywhere in a request ("Camden Row"
and "camden's" both become `LOC_1`). Placeholders still cost some answer
accuracy, so a benchmark run may set `CHRONICLE_REDACT_NAMES=off` to send real
names. Emails, phones, IDs and URLs stay masked either way, and a warning is
logged while names are off. Redaction is on by default: set the switch per run,
not in `adapter.json` or `.env`, and report scores both with and without it.

## Live egress log

```bash
uv run python -m chronicle.guard.egress_server     # http://127.0.0.1:8001/api/egress
```

The bottom panel then shows `● LIVE` and every model call and web search as it
leaves the machine, refreshed every 2s, with redaction badges and PII types.
Without the server it shows `sample data` (made-up entries), and if the server
stops after being live it shows `offline` with the last real entries. The
server only listens on 127.0.0.1 and only serves `GET /api/egress?n=30`.
Polls while it's down show up as 500s in the browser console; that is expected.
