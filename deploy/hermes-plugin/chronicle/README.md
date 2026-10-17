# Chronicle memory provider for Hermes Agent

Gives Hermes a bi-temporal long-term memory: every fact keeps the dates it was
true, and replaced facts are closed rather than deleted.

## Install

From the repo root, in the environment that runs Hermes (inside the NemoClaw
sandbox, connect first with `nemoclaw <sandbox> connect`):

```bash
./deploy/install.sh
hermes memory setup        # choose "chronicle"
```

Or set it directly in `$HERMES_HOME/config.yaml`:

```yaml
memory:
  provider: chronicle
```

## What it does

| Hermes hook | Chronicle behaviour |
|---|---|
| `prefetch` | Recalls matching facts valid now and injects them before each turn |
| `sync_turn` | Stores the user's message in a background thread (assistant replies are not stored) |
| `on_memory_write` | Mirrors built-in memory: `replace` supersedes the old fact, `remove` closes it |
| `chronicle_recall` tool | Search memory; pass `as_of: YYYY-MM-DD` to see what was true on that date |
| `chronicle_remember` tool | Store an explicit fact, optionally with the date it became true |
| `chronicle_web_search` tool | Public web search via Tavily; only offered when `TAVILY_API_KEY` is set |

## Privacy

Emails, phone numbers, SSNs, card numbers and IP addresses in recalled memory
are replaced with stable tokens (`EMAIL_1`, ...) before Hermes sends them to its
model. Names are kept. Set `CHRONICLE_REDACT_RECALL=0` to turn this off.

Chronicle's own LLM calls always go through `chronicle.guard.llm`, which
pseudonymises everything and writes `~/.chronicle/egress.log`.

Web searches are refused, and nothing is sent, when the query contains an
email, phone number, ID or a person's name. The agent gets
`{"blocked": true, "pii_types": [...]}` back. Sent queries are logged too.

## Storage

Memory lives in Chronicle's SQLite bi-temporal store at
`$HERMES_HOME/chronicle/memory.sqlite3`, one database per Hermes profile, so it
survives restarts and profiles stay separate. Set `CHRONICLE_MEMORY_DB` to share
one database, e.g. with the memory server the UI reads.
