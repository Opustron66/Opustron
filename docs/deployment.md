# Hosted Chronicle demo

The production entry point serves the built React UI and memory API on one
origin. It never ingests documents or starts model calls on startup. This is a
public demo over one approved synthetic memory state, not a multi-user account
system. Everyone can see the same facts and egress log. Only use NVIDIA's
published synthetic artifacts; do not upload private memories or personal logs.

Chat is disabled by default. Browsing saved facts, timelines and entities does
not use Nebius credits. Enabling chat allows paid calls for new questions.
The supplied Render blueprint uses the Free plan, with no paid disk. It can
restore the same saved-memory ZIP after every restart without model calls.

## Verify locally from Windows PowerShell

Run each command separately from the repository root:

```powershell
Set-Location 'C:\Github Projects\Opustron'
Push-Location ui
npm.cmd ci
npm.cmd run build
Pop-Location

$env:CHRONICLE_WEB_CHAT_ENABLED = '0'
$env:CHRONICLE_STATE_DIR = "$PWD\data\hosted-state"
$env:PORT = '8000'

& .\.venv\Scripts\python.exe -m chronicle.web
```

Open <http://localhost:8000>; no login is needed. `/healthz` reports
`memory_loaded: false` until facts have been imported. An empty memory is valid
while waiting for a state transfer. Missing UI build files stop startup.

The hosted entry point binds to all interfaces. Use HTTPS through the hosting
provider for remote access. The local commands above use HTTP for localhost.

## Transfer an existing memory without re-ingesting

Ask the sender for the Chronicle commit and corpus revision, plus a separate
state archive for each corpus:

- `claims.jsonl`: extracted facts
- `docs.jsonl`: source text used by hybrid retrieval
- `pages.jsonl`: topic timelines and entity pages
- `memory.sqlite3`: optional consistent database backup

The sender must stop processes using SQLite before copying its files, or use
SQLite's backup API. Do not copy only the main database file while it is being
written in WAL mode. Do not include `.env`, provider keys, or the sender's home
directory. Caches are optional and are not needed to browse or answer.

Put the state files directly inside `CHRONICLE_STATE_DIR`. Keep Corpus A and B
in separate directories; point the service at one corpus at a time. On startup,
the hosted entry point synchronizes both claims and pages into SQLite without
model calls. No SQLite backup is needed if you have all three JSONL files: a new
database can be built locally from them. Keep an untouched copy of the archive.

Restart after importing or switching state. The hosted service opens a snapshot
at startup; it does not watch for later changes to the JSONL files. Inspect the
timeline for malformed dates in older states; deploying newer code does not
rewrite extracted dates. Prefer a separate volume directory for each replacement
state rather than mixing files from different archives.

## Build and run the production container

From the repo root, with Docker Desktop running in Linux-container mode:

```powershell
docker build -f deploy/Dockerfile -t chronicle-web .
docker volume create chronicle-data
docker run --rm --name chronicle-web -p 127.0.0.1:8000:8000 --mount source=chronicle-data,target=/data --env CHRONICLE_WEB_CHAT_ENABLED=0 chronicle-web
```

The image runs as UID 10001, builds the UI in a separate stage, and excludes local
credentials, state and caches. The named volume preserves `/data/state` and
`/data/.chronicle` (the egress log and response cache) across container restarts.
Existing bind mounts or imported files must be writable by UID 10001.

In another terminal, import the archive's contents into the stopped service's
volume. For a local container with an empty state, you can stop it, then run a
temporary container to copy files. Render Free has no shell access: use the
startup snapshot download described below instead.
Do not include state in the container image.

## Render deployment

`render.yaml` describes one Free Docker web service in Singapore, without a paid
disk or database. Nothing is provisioned by adding these files. It is a demo
configuration, not a guarantee of availability. Render Free sleeps after 15
minutes without traffic and can take about a minute to wake. SQLite, logs and
caches on its filesystem disappear on restart, redeploy or sleep. It has no SSH
or dashboard shell. The snapshot loader rebuilds SQLite from saved JSONL files;
it never reruns model extraction.

Do not enable multiple instances or Uvicorn workers. Paid chat is explicitly
blocked while `CHRONICLE_WEB_EPHEMERAL=1` unless the verified external Upstash
budget is configured, because losing the local log would reset its accounting.
For optional chat without upgrading Render, follow [the Free chat guide](free-chat.md).

### Prepare the friend's saved memory

Create a ZIP with exactly these three files at its root (no enclosing directory):
`claims.jsonl`, `docs.jsonl`, `pages.jsonl`. Do not include SQLite files, caches,
credentials, or gold answers. This format can rebuild the memory without a
database backup. Keep the original archive unchanged.

In PowerShell, after receiving the state folder:

```powershell
$State = 'C:\path\to\friends-state'
Compress-Archive -LiteralPath "$State\claims.jsonl", "$State\docs.jsonl", "$State\pages.jsonl" -DestinationPath "$PWD\.tmp\memory-state.zip"
Get-FileHash "$PWD\.tmp\memory-state.zip" -Algorithm SHA256
```

Store that archive at a stable HTTPS download URL that returns ZIP bytes, not
a file-sharing preview page. Use private access where appropriate; the URL can
contain a download token and must be set as a server-side secret. The URL must
remain valid for future cold starts. Do not commit the archive or URL to Git,
or place it under the public UI assets. Confirm you have permission to host
the transferred state.

The loader requires the archive's SHA-256, limits downloads to 32 MiB and expanded
contents to 128 MiB, and accepts only the three fixed JSONL filenames. It verifies
the checksum and rows before loading a separate state directory, leaving existing
state untouched. Missing or invalid configured snapshots stop startup. With no
snapshot configured, the app can still start empty while waiting for your friend.

### Create the free service

1. Push the reviewed deployment changes to the branch you want to host.
2. In Render, create a Blueprint from that repository and branch.
3. Keep `CHRONICLE_WEB_CHAT_ENABLED=0` and `CHRONICLE_WEB_EPHEMERAL=1`.
   No username, password or model key is needed. Old `CHRONICLE_WEB_USERNAME`
   and `CHRONICLE_WEB_PASSWORD` settings can be deleted; the app ignores them.
4. Confirm the service plan is **Free** and no paid disk/database is selected,
   then deploy. The service uses the provider's `PORT`
   and `/healthz` health check. Open the HTTPS URL and verify public access and the empty
   memory screen. Automatic redeploys are disabled in the blueprint.
5. When the archive is ready, add `CHRONICLE_STATE_SNAPSHOT_URL` and
   `CHRONICLE_STATE_SNAPSHOT_SHA256` in the service's environment settings.
   These are optional until you receive the files; never substitute a source
   corpus URL, since the loader expects already-extracted memory.
6. Restart the service. Verify
   `memory_loaded: true`, visible facts and the expected date span.

The loader recreates state under `/data/state/snapshot-<sha256>` on a fresh
instance. A previously verified local snapshot can be reused while that instance
exists. Use a new ZIP and checksum to replace the published dataset. This is a
fixed snapshot demo; runtime changes are not saved permanently. Keep A and B in
separate ZIPs and select the one you want to show.

For judging, submit the service's HTTPS URL, explain the possible
cold-start delay, and label the demo as memory browsing with live chat disabled.
An empty state is useful for checking deployment but is not the finished demo.
The friend's actual corpus and the free host's resource limits still need a live
check. Free hosting does not include Nebius inference credits.

Render includes usage allowances for bandwidth and builds. To avoid overage
charges, do not add a payment method for this demo, or configure the applicable
account spending controls. Free services can be suspended when allowances are
exhausted. Do not assume free means unlimited.

References: [Docker services](https://render.com/docs/docker),
[Free plan limits](https://render.com/docs/free),
[Blueprint configuration](https://render.com/docs/blueprint-spec).

## Enable paid chat later

The default Free blueprint keeps chat disabled. To use chat on Free with a durable
external budget, follow [the Free chat guide](free-chat.md). For local-log budgeting, first move
to durable storage for `/data` (including the egress log), explicitly set
`CHRONICLE_WEB_EPHEMERAL=0`, and approve model spending. Then set:

| Variable | Value |
| --- | --- |
| `NEBIUS_API_KEY` | Your provider credential, entered as a server-side secret |
| `NEBIUS_BASE_URL` | `https://api.tokenfactory.nebius.com/v1/` |
| `CHRONICLE_MODEL` | The model ID you intend to pay for |
| `CHRONICLE_SPEND_LIMIT_USD` | Positive USD budget for the period |
| `CHRONICLE_SPEND_SINCE` | UTC ISO timestamp marking the start of that period |
| `CHRONICLE_WEB_CHAT_ENABLED` | `1` |
| `CHRONICLE_WEB_ASKS_PER_MINUTE` | Shared request limit; default `6` |

Restart after configuration changes. Enabled chat refuses startup without a model
credential and finite positive budget. Only one question runs at a time; excess
requests receive HTTP 429. The rate window is shared by all visitors and resets
on restart. It is a demo control, not distributed rate limiting.

The existing spending guard uses estimated token prices and checks before each
model call. It is not a guaranteed provider billing cap: the final call can take
the total past the limit. A question may involve several model calls. Persist the
egress log and use provider-side controls where available. Do not run separate
model jobs against the same budget while hosting the demo.

When chat is disabled, the UI shows a browse-only panel with shortcuts to
ownership, deadlines and past facts. These shortcuts filter saved memory without
calling a model. When enabled chat fails or is rate limited, it shows an error
instead of inventing an answer.

The memory workspace has searchable entities, source quotations, a daily timeline
and a separate date-comparison view. It supports dark and light themes and stacks
the panels on mobile. The reading period uses dates from the source documents
when available, so malformed extracted dates do not stretch the timeline. Stored
claims remain unchanged. `/api/config` exposes only chat availability, document
count and the source date range; it contains no credentials or snapshot URL.

## Offline validation

```powershell
& .\.venv\Scripts\python.exe -m pytest tests/deploy tests/memory/test_server.py tests/memory/test_ask.py tests/guard/test_egress_boundary.py -q
Push-Location ui
npm.cmd test
npm.cmd run build
Pop-Location
```

The production-server tests replace model calls with a failing mock. They verify
public access, egress visibility, static assets, state import, health, disabled chat, budget prerequisites and
request limits. Snapshot tests stub the HTTPS download and verify cold-start
recovery, checksums, archive limits and rejected paths/content. They do not
validate a live Render deployment or provider call.
