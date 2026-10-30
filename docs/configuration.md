# Configuration

Chronicle reads settings from environment variables. Copy `.env.example` to `.env`, then load it
into your shell with `set -a; source .env; set +a` (Chronicle does not load `.env` by itself).
Only `NEBIUS_API_KEY` is required.

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
| `CHRONICLE_SECOND_LOOK` | `off` disables the wider retry for answers that say the corpus is silent. Unset = on |
| `CHRONICLE_VOTE` | `1` (set by the benchmark adapter) answers flip-prone questions (yes/no, "which one", "how many", as-of) up to three times and keeps the majority. Unset = off |
| `CHRONICLE_POSITIVE_FORM` | `1` (set by the benchmark adapter) rewrites an answer whose first sentence puts the value next to "not", "rather than" etc., so the value is stated on its own. Unset = off |
| `CHRONICLE_CRITIC` | `1` checks every answer with a second model call. Unset = off (it did not help on corpus A) |
| `CHRONICLE_KEY_LINES` | `off` drops the list of evidence lines that repeat the question's wording. Unset = on |
| `CHRONICLE_TIMELINE` | `1` answers state-over-time questions timeline first. Unset = off |
| `CHRONICLE_GROUNDING` | `off` skips the quote check (each answer quotes evidence for its names and numbers; unbacked ones get one correction pass). Unset = on |
| `CHRONICLE_FULL_CORPUS` | `1` answers every question over the whole corpus (all documents, oldest first) instead of retrieved evidence; for corpora that fit the model context. Unset = off |
