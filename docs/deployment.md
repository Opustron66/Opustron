# Hosted Chronicle demo

The production entry point serves the built React UI and memory API on one
origin. It never ingests documents or starts model calls on startup. This is a
shared, password-protected demo over one memory state, not a multi-user account
system. Everyone given the login sees the same facts and egress log.

Chat is disabled by default. Browsing saved facts, timelines and entities does
not use Nebius credits. Enabling chat allows paid calls for new questions.

## Verify locally from Windows PowerShell

Run each command separately from the repository root:

```powershell
Set-Location 'C:\Github Projects\Opustron'
Push-Location ui
npm.cmd ci
npm.cmd run build
Pop-Location

$env:CHRONICLE_WEB_USERNAME = 'viewer'
# Choose a password for this local test; do not commit or share it in logs.
$LoginPassword = Read-Host 'Demo password' -AsSecureString
$env:CHRONICLE_WEB_PASSWORD = [System.Net.NetworkCredential]::new('', $LoginPassword).Password
$env:CHRONICLE_WEB_CHAT_ENABLED = '0'
$env:CHRONICLE_STATE_DIR = "$PWD\data\hosted-state"
$env:PORT = '8000'

& .\.venv\Scripts\python.exe -m chronicle.web
```

Open <http://localhost:8000> and enter the login. `/healthz` is the only public
endpoint. It reports `memory_loaded: false` until facts have been imported.
An empty memory is valid while waiting for a state transfer. Missing UI build
files or login settings stop startup rather than expose a partially configured app.

The hosted entry point binds to all interfaces. Use HTTPS through the hosting
provider for remote access: HTTP Basic authentication must not be sent over
unencrypted public connections. The local commands above use HTTP for localhost.

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
docker run --rm --name chronicle-web -p 127.0.0.1:8000:8000 --mount source=chronicle-data,target=/data --env CHRONICLE_WEB_USERNAME --env CHRONICLE_WEB_PASSWORD --env CHRONICLE_WEB_CHAT_ENABLED=0 chronicle-web
```

This forwards the login variables set in the current PowerShell session. The
image runs as UID 10001, builds the UI in a separate stage, and excludes local
credentials, state and caches. The named volume preserves `/data/state` and
`/data/.chronicle` (the egress log and response cache) across container restarts.
Existing bind mounts or imported files must be writable by UID 10001.

In another terminal, import the archive's contents into the stopped service's
volume. For a local container with an empty state, you can stop it, then run a
temporary container to copy files; for Render use its shell as described below.
Do not include state in the container image.

## Render deployment

`render.yaml` describes one Docker web service with a 1 GB persistent disk at
`/data`. The standard instance is selected for headroom for the Python and spaCy
dependencies; this is a paid hosting resource. Nothing is provisioned by merely
adding these files. Review the current plan and disk price in Render before
creating the service. Do not enable multiple instances or Uvicorn workers: the
demo uses one SQLite database and a process-local chat limit.

1. Push the reviewed deployment changes to the branch you want to host.
2. In Render, create a Blueprint from that repository and branch.
3. Supply `CHRONICLE_WEB_USERNAME` and a strong `CHRONICLE_WEB_PASSWORD` when
   prompted. Keep `CHRONICLE_WEB_CHAT_ENABLED=0`; no model key is needed yet.
4. Review the paid resources, then deploy. The service uses the provider's `PORT`
   and `/healthz` health check. Open the HTTPS URL and verify login and the empty
   memory screen. Automatic redeploys are disabled in the blueprint.
5. Transfer the friend's state archive to the service through Render's shell
   using a temporary private download URL or your chosen secure file transfer.
   Extract only the expected state files into a fresh directory on `/data`.
   Never expose the archive through the UI's static directory or commit it to Git.
6. Set `CHRONICLE_STATE_DIR` to that directory and restart the service. Verify
   `memory_loaded: true`, visible facts and the expected date span.

Render's persistent disk survives restarts and redeploys; its ordinary container
filesystem does not. Keep state, cache and accounting logs on `/data`. Disk-backed
services have deployment availability limits; review Render's documentation
before promising uninterrupted availability.

References: [Docker services](https://render.com/docs/docker),
[persistent disks](https://render.com/docs/disks),
[Blueprint configuration](https://render.com/docs/blueprint-spec).

## Enable paid chat later

Only do this after approving model spending. In the hosting dashboard set:

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

The UI currently shows its generic error message when chat is disabled or rate
limited. It does not invent an answer. Chat history/UI improvements in other PRs
can be integrated separately; the hosted wrapper reuses the memory API router.

## Offline validation

```powershell
& .\.venv\Scripts\python.exe -m pytest tests/deploy tests/memory/test_server.py tests/memory/test_ask.py tests/guard/test_egress_boundary.py -q
Push-Location ui
npm.cmd test
npm.cmd run build
Pop-Location
```

The production-server tests replace model calls with a failing mock. They verify
login, static assets, state import, health, disabled chat, budget prerequisites and
request limits. They do not validate a live Render deployment or provider call.
