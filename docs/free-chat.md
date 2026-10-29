# Chat on Render Free with a durable budget

Render Free can host the app while Nebius bills for model inference. The
existing memory ZIP is reused: this setup does not ingest or train anything.
The shared budget is stored in Upstash Redis, separately from Render's temporary
disk. Use the Free database plan and keep its ID and spending limit unchanged
across deployments unless deliberately raising the limit with the command below.
Never give it a TTL or enable eviction of the budget key.

Code deployment and budget initialization do not call a model. Keep
`CHRONICLE_WEB_CHAT_ENABLED=0` until spending is explicitly approved. A real
question after setting it to `1` can incur charges.

## 1. Deploy the integration with chat disabled

Merge this change and deploy that commit in Render. Keep the existing snapshot
URL/checksum, `CHRONICLE_WEB_EPHEMERAL=1`, and `CHRONICLE_WEB_CHAT_ENABLED=0`.
You should already have `UPSTASH_REDIS_REST_URL` and
`UPSTASH_REDIS_REST_TOKEN` as private Render environment variables. Use the
regular write-capable token, not the read-only one. No Upstash connections are
made at startup while chat is disabled.

## 2. Initialize the $0.25 ledger once, from Windows PowerShell

Update your local checkout to the merged commit first. Run each line separately
from the repository root. Enter the Upstash values directly in the prompts;
the token prompt is hidden and its value is not placed in shell command history.
No Nebius key is needed for initialization.

```powershell
$Py = Join-Path (Get-Location).Path '.venv\Scripts\python.exe'
$env:UPSTASH_REDIS_REST_URL = Read-Host 'Upstash REST URL'
$RedisSecret = Read-Host 'Upstash REST token' -AsSecureString
$env:UPSTASH_REDIS_REST_TOKEN = [System.Net.NetworkCredential]::new('', $RedisSecret).Password
$env:CHRONICLE_MODEL = 'nvidia/Nemotron-3_5-Lightning'
$env:CHRONICLE_SPEND_BUDGET_ID = 'demo-v1'
$env:CHRONICLE_SPEND_LIMIT_USD = '0.25'
& $Py -m chronicle.budget init
```

Expected output includes `limit_microusd: 250000` and
`spent_or_reserved_microusd: 0`. A nonzero exit or an error means stop and fix the
configuration. An existing ledger is never reset by `init`; inspect it instead:

```powershell
& $Py -m chronicle.budget status
Remove-Item Env:UPSTASH_REDIS_REST_TOKEN
Remove-Variable RedisSecret
```

This sends only budget commands to your Upstash database. It makes no model
requests. The ledger stores numbers and random reservation IDs, not questions,
memory contents, or provider credentials.

## 3. Add the matching Render environment settings

| Variable | Value |
| --- | --- |
| `CHRONICLE_SPEND_BACKEND` | `upstash` |
| `CHRONICLE_SPEND_BUDGET_ID` | `demo-v1` |
| `CHRONICLE_SPEND_LIMIT_USD` | `0.25` |
| `CHRONICLE_MODEL` | `nvidia/Nemotron-3_5-Lightning` |
| `CHRONICLE_WEB_ASKS_PER_MINUTE` | `2` |
| `CHRONICLE_VOTE` | `0` |
| `CHRONICLE_MAX_TOKENS` | `16384` |
| `CHRONICLE_WEB_EPHEMERAL` | `1` |
| `CHRONICLE_WEB_CHAT_ENABLED` | **`0` until spending is approved** |

Keep the existing snapshot settings and Upstash credentials. The remote guard
supports Lightning ($0.06/M input, $0.24/M output) and Ultra ($1/M input, $3/M
output), using the repository's pinned prices. It refuses other models. Leave
thinking at the model default to preserve reasoning quality; smaller output
limits can truncate reasoning and trigger additional answer attempts.

## 4. Enable chat only when ready for paid questions

Enter `NEBIUS_API_KEY` privately in Render and use
`NEBIUS_BASE_URL=https://api.tokenfactory.nebius.com/v1/`.
Then set `CHRONICLE_WEB_CHAT_ENABLED=1` and save/redeploy. Startup validates the
configuration locally. Every actual provider attempt must first reserve funds
against the existing remote ledger; it is never initialized, replenished or reset
by startup. A temporary Redis outage blocks model calls without preventing memory
browsing from starting. Asking a question can incur charges. The UI should switch from
the browse-only panel to live chat.

Start with one known question and inspect the answer's sources and the budget
status before further use. All visitors share the same $0.25 allowance. To turn
off spending again, set `CHRONICLE_WEB_CHAT_ENABLED=0` and redeploy.

## How reservations behave

For chat response-time settings, see [Faster Ultra chat](#faster-ultra-chat).

Each actual provider attempt atomically reserves the price of the model's full
1,048,576-token input context plus its configured output limit. For Lightning
with 16,384 output tokens, that is about $0.067 per attempt. This deliberately
overestimates input rather than guessing token counts. A confirmed response
settles to reported token usage and returns unused funds. There must be enough
headroom for a whole reservation, so the demo can stop before every cent is used.

Automatic SDK retries are disabled. An explicit schema fallback or reasoning
retry needs its own reservation. A timeout, crash, rejected request, missing
usage or failed settlement retains the reservation: ambiguous requests are
never assumed free. This may consume the *app allowance* faster than actual
provider spending. No automatic refunds, expiry or resets are performed.

## Raise an existing allowance to $5 and switch to Ultra

Keep chat disabled while updating the database and Render configuration. Deploy
the Ultra-supporting code first. The model is
`nvidia/Nemotron-3-Ultra-550b-a55b`, the same model ID used for benchmark runs;
using the same model does not itself reproduce all benchmark pipeline settings.

In local PowerShell, re-enter the private Upstash credentials and use the
**existing** budget ID and **old** limit to authorize the increase:

```powershell
$Py = Join-Path (Get-Location).Path '.venv\Scripts\python.exe'
$env:UPSTASH_REDIS_REST_URL = Read-Host 'Upstash REST URL'
$RedisSecret = Read-Host 'Upstash REST token' -AsSecureString
$env:UPSTASH_REDIS_REST_TOKEN = [System.Net.NetworkCredential]::new('', $RedisSecret).Password
$env:CHRONICLE_SPEND_BUDGET_ID = 'demo-v1'
$env:CHRONICLE_SPEND_LIMIT_USD = '0.25'
$env:CHRONICLE_MODEL = 'nvidia/Nemotron-3-Ultra-550b-a55b'
& $Py -m chronicle.budget raise-limit --to 5
Remove-Item Env:UPSTASH_REDIS_REST_TOKEN
Remove-Variable RedisSecret
```

Expected output has `limit_microusd: 5000000`. Spent/reserved funds remain
unchanged: $5 is the new **total allowance**, not an extra $5. This command only
updates the existing Redis ledger; it never calls a model or changes Render.
The old-limit comparison prevents an accidental repeated increase or a stale
configuration overwriting the database. Do not delete the key or rerun `init`.

After a successful increase, set these matching values in Render:

```text
CHRONICLE_SPEND_LIMIT_USD=5
CHRONICLE_MODEL=nvidia/Nemotron-3-Ultra-550b-a55b
CHRONICLE_SPEND_BUDGET_ID=demo-v1
```

Keep `CHRONICLE_SPEND_BACKEND=upstash`, `CHRONICLE_WEB_EPHEMERAL=1`, the Upstash
credentials and memory snapshot settings. Use `CHRONICLE_WEB_CHAT_ENABLED=0`
until ready for paid questions, then follow step 4 above.

Ultra reserves about $1.10 per provider attempt at a 16,384 output-token limit,
settling to actual reported usage afterward. This is headroom, not a flat price
per question. An ambiguous failed request retains its larger reservation, so
the demo can stop with unspent provider credit remaining. Unknown models are
still blocked. Each receipt records its reserved model so mixed-model requests
are settled using the correct rate even when the default model changes.

For future status checks, set the local `CHRONICLE_SPEND_LIMIT_USD=5` too.

If the ledger is unavailable, malformed, deleted, expired or its limit does not
match the configuration, new model calls are blocked. The local spending log
is no longer the source of budget authorization in Upstash mode. The egress log
is still available, but Render can lose its local history on restart.

This is an application guard based on the pinned model prices, not a provider
billing guarantee. Pricing changes, other uses of the same Nebius account, or
manually resetting/replacing the ledger are outside its accounting. Keep a
margin below your remaining account balance. Do not reset a ledger while a
request is in flight, or change the budget ID to bypass an exhausted allowance.

## Faster Ultra chat

The UI waits for a complete JSON answer; it does not stream tokens. A question
can include a query-interpretation call, up to three evidence-gathering rounds,
and conditional grounding or second-look passes. Thus one question is not
necessarily one provider request. Model reasoning time and these extra calls
both contribute to response time, independently of a Render cold start.

Keep the current Ultra model, thinking configuration, output-token allowance,
retrieval settings and all existing verification/retry passes. Disabling
thinking, shortening output limits or removing answer checks can change accuracy,
so these are not the recommended response to a latency complaint when accuracy
must be preserved.

The budget client reuses HTTPS connections between Redis reservations and
settlements, reducing repeated connection setup without changing prompts, model
parameters, retrieval or budget authorization. No fixed speedup is claimed: live
latency has not been measured, and model generation can still dominate.

The UI shows elapsed request time instead of only saying thinking, and explains
that a complete answer can involve multiple evidence checks. This makes waiting
clearer; it does not stream intermediate text or reveal model reasoning.
Existing exact-request caching can help repeated identical requests while the
instance stays alive; Render Free can discard that local cache on restart. A
Render cold start can add latency before the app responds. None of these changes
reduce the reasoning or checking performed for an uncached question.

The chat's suggested questions are exact published Corpus A prompts: Atlas's
GitLab path (`fact-031`), Quillon's current launch target
(`fresh-quillon-launch-date`), Beacon eval ownership (`attrib-eval-owners`), and
the historical backfill window (`asof-backfill-window`). At the end of Corpus A,
expected answers are `platform-eng/atlas`, 14 July 2026, Anya Volkov / Jin Oh,
and 30 days as of 20 May. Set the Time Machine to 27 May 2026 for this sample set.
Viewing suggestions costs nothing; clicking a suggestion in enabled chat sends
a real paid question.

## Offline verification

The development dependency `fakeredis[lua]` executes the actual Lua locally;
tests use fake model transports, never your Redis credentials or model key.

```powershell
& .\.venv\Scripts\python.exe -m pytest tests/guard/test_remote_budget.py tests/guard/test_spend_limit.py tests/guard/test_llm_client.py tests/deploy/test_web.py tests/memory/test_ask.py -q
Push-Location ui
npm.cmd test
npm.cmd run build
Pop-Location
```

References: [Upstash REST API](https://upstash.com/docs/redis/features/restapi),
[Free plan](https://upstash.com/pricing/redis).
