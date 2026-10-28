# Hand-off: submission work (no benchmark credits needed)

Written 28 Oct (evening SGT). P4 (@shrad1601) keeps working on accuracy (benchmark runs, which cost
credits). Everything below can run without benchmark credits and is split between **Sara** and
**Sania**. The demo recording needs a few cents of model calls on your own key; that's marked where
it applies.

**Deadline: 30 Oct, 10:00 PT = 31 Oct, 01:00 SGT.** Aim to have everything merged by
**30 Oct, 18:00 SGT**, so there's time to record, upload and submit.

Judging is on four criteria: **Technological Implementation, Design, Potential Impact, Quality of
the Idea**. The benchmark score isn't a criterion by itself; it backs up "Technological
Implementation". Track: **Personal AI** (always-on private assistant with persistent memory). For
that track, Devpost suggests NemoClaw, OpenShell, Hermes Agent and Nebius Serverless. We already
ship a Hermes plugin and an OpenShell policy (`deploy/`), so show them.

## Where things stand

- `main` = run 6 code (`a5e3ab4`, PR #25): **0.946 on corpus A with Nemotron 3 Ultra, privacy off.**
- Results, same corpus and same model as NVIDIA's reference runs (from `scripts/bench_compare.py`,
  our own `correct` flags only):

| Type | NVIDIA agentic RAG | NVIDIA self-model | Run 2 (privacy on) | Run 4 | Run 5 | Run 6 |
|---|---:|---:|---:|---:|---:|---:|
| abstention (13) | 1.000 | 0.923 | | 1.000 | 0.923 | 1.000 |
| as_of (6) | 0.333 | 0.667 | | 0.333 | 0.667 | 0.667 |
| attribution (5) | 0.800 | 0.800 | | 1.000 | 0.600 | 0.800 |
| chain_freshness (5) | 0.600 | 1.000 | | 0.800 | 0.800 | 0.800 |
| citation (12) | 0.917 | 1.000 | | 0.917 | 0.833 | 0.917 |
| constraint (5) | 0.800 | 1.000 | | 1.000 | 1.000 | 1.000 |
| disambiguation (15) | 0.667 | 0.867 | | 0.800 | 0.933 | 0.867 |
| freshness (12) | 0.750 | 0.917 | | 0.833 | 1.000 | 0.917 |
| multi_source (73) | 0.877 | 0.945 | | 0.986 | 0.986 | 0.986 |
| ordering (4) | 0.750 | 1.000 | | 1.000 | 1.000 | 1.000 |
| set_difference (6) | 0.833 | 0.833 | | 0.667 | 1.000 | 1.000 |
| single_hop (30) | 0.867 | 0.833 | | 0.933 | 0.967 | 0.967 |
| **overall (186)** | **0.828** | **0.909** | **0.909** | **0.914** | **0.941** | **0.946** |
| tokens / question | 14.5k | 241k (+183M ingest) | 11.6k | 12.9k | 19.9k | 29.1k |

Run 2's per-type numbers weren't copied here; P4 can add them. Our ingest token counts
weren't recorded (proxy accounting), so **don't claim an ingest-cost win**.

**What we can honestly claim**
- Same model as NVIDIA's reference runs (Nemotron 3 Ultra on Nebius Token Factory), better memory
  system: **0.946 vs 0.828 (agentic RAG) and 0.909 (self-model).**
- **With every name masked (privacy on) we still match NVIDIA's best (0.909)**, and NVIDIA's runs have
  no privacy layer at all.
- **Efficiency:** run 4 (0.914) used 12.9k tokens per question; NVIDIA's self-model used 241k.
- Two runs of nearly the same code: 0.941 and 0.946 (mean 0.944). Runs vary by about ±2 points, so
  don't present one run as exact.
- NVIDIA's README says its reference runs are "not a ranking", so say "same model, same corpus,
  same grader", not "we beat NVIDIA".
- No gold answers were read. We used only our own right/wrong flags. Say so; it's a credibility point.
- Caveat to mention in the write-up: several fix rounds were driven by corpus A's misses. Corpus B
  (a different domain) hasn't been re-run yet.

---

## Sara: write-up, numbers and architecture

### S1. Devpost write-up (`docs/devpost.md`, currently a one-line stub)
The project page judges read first. Suggested sections, about 600–900 words:
1. **One-line pitch.** "Chronicle: a personal AI agent whose memory keeps up. It knows what was true
   *when*, and it never lets your private data leave unmasked."
2. **The problem.** Assistants forget, or remember stale facts. "Who owns payments?" has a different
   answer in May than in April. Plain RAG returns whichever document scores highest, not what is
   currently true.
3. **What it does.** Use "What Chronicle does" from `docs/remaining-work.md` (ingest → bi-temporal
   memory → reasoning with citations → privacy guard → UI and Hermes).
4. **How we built it.** One short paragraph per layer, P1–P4 (see S3 for the diagram). Mention:
   - Every fact has two clocks (valid time and recorded time); nothing is deleted.
   - As-of questions only see what was known then.
   - Every answer quotes its evidence, and code checks each quote is real.
   - The prompt surfaces the evidence lines that repeat the question's wording.
   - Voting on flip-prone questions; a second, wider look before giving up.
   - Names, emails, phones and IDs are pseudonymised on every model call; the egress log shows
     exactly what left the machine.
   - Spending cap.
5. **Results.** The table above plus the "honest claims" bullets. A small bar chart (overall:
   NVIDIA agentic 0.828, NVIDIA self-model 0.909, Chronicle privacy-on 0.909, Chronicle 0.946)
   reads well.
6. **Built with.** NVIDIA Nemotron 3 Ultra (550B) on Nebius Token Factory (1M context), Hermes
   Agent plugin, OpenShell egress policy, Python, SQLite, React and Vite.
7. **Challenges.** Run-to-run noise (±2 pts); a grader that treats "not X" in a clause as denying
   X; masking names without losing accuracy (0.871 → 0.909 with privacy on).
8. **What's next.** Corpus B, learned routing per question type, on-device masking model.

**Done when** `docs/devpost.md` is complete, reviewed by one teammate, and pasted into the
Devpost form. Check the form's required fields yourself: repo link, video link, track, and which
NVIDIA model and Nebius service were used.

### S2. Results doc (`docs/benchmark-results.md`, currently a stub)
- Put in the table above, plus the run history: run 1 0.871 (privacy on) → run 2 0.909 (on) →
  run 3 0.898 (on) → run 4 0.914 (off) → run 5 0.941 → run 6 0.946. Add one line per run on what
  changed; commit messages and the README sections have the details.
- Fill the `<!-- RESULTS -->` and `<!-- REDACTION -->` placeholders in `docs/next-phase-results.md`.
- Run dirs are on P4's machine (`nemoclaw-community/examples/tools/agent-memory-benchmark/results/runs/`).
  Ask P4 for `report.json` and `verdicts.jsonl` if you want to regenerate the table with
  `scripts/bench_compare.py`. Never open `answers.jsonl` under `corpus_*/questions/`.
- P4 will add later runs' rows.

**Done when** both files have real numbers and no placeholders.

### S3. Architecture diagram (`docs/architecture.md` + one image for Devpost and the video)
The current diagram stops at "P3 reason". Add the answer pipeline, since that's where most of the
accuracy came from:
```
question → plan (question type, as-of date) → retrieve (facts, topic timelines, person pages,
documents) → key lines (evidence repeating the question's wording) → answer with quotes →
vote on flip-prone questions → quote check (code) → wider second look if it gave up →
wording fixes (bare value first, negations in their own clause) → answer + citations
```
Plus the privacy guard around every model call (mask → Nebius → restore → egress log). Export
one clean PNG (Excalidraw is fine) for the Devpost gallery and the video.

**Done when** the PNG is in `docs/` and `docs/architecture.md` links it.

### S4. README front page
Judges who open the repo see the top of `README.md`. Add, above the "Piece" table:
- a 3-line pitch;
- the overall results line (0.946 vs NVIDIA 0.828 / 0.909, same model);
- a GIF of the UI time slider (from Sania's recording, task N4);
- a link to the Devpost page and the video.

**Done when** the top screen of the README shows the pitch, the numbers and the GIF.

---

## Sania: UI, demo and video

UI code is in `ui/src` (React + Vite): `ChatPanel.jsx`, `CitationPopover.jsx`, `EgressLog.jsx`,
`EntityCard.jsx` and `Timeline.jsx`, with API calls in `services/api.js`. Without a backend, the
UI shows labelled sample data (`MOCK` in `api.js`), so N1–N3 can all be built for free.

Run it:
```bash
cd ui && npm install && npm run dev      # http://localhost:5173
uv run python -m chronicle.memory serve --state DIR   # real data on :8000 (see README "Real data")
```

### N1. "Explain this answer" panel (highest value; it shows off what's unique)
Each chat answer gets an expandable "Why?" section with:
- **the verbatim quote behind each claim**, with its document id and date (the answerer already
  produces these as `support` quotes, see `chronicle/reason/grounding.py`);
- **the as-of date used**, if any;
- **what it replaced**, when a fact was superseded ("Alex Nova → Blake Shore, 15 May"), from
  `getEntityHistory`.

Backend: `POST /api/ask` in `chronicle/memory/server.py` returns `answer` and `source_ids` today.
Add the `support` quotes to the response: pass them through `AnswerResult`, which already holds
`unsupported`. Keep `source_ids` unchanged so the benchmark adapter is unaffected. Add a test in
`ui/src/components/ChatPanel.test.jsx` and one in `tests/` for the API change.

**Done when** clicking "Why?" on an answer shows the quotes, dates and replaced facts, with tests.

### N2. Two-date diff view on the Timeline
Pick two dates and show which facts were **added**, **ended** or **changed** between them. Use
`getFactsAsOf(date1)` and `getFactsAsOf(date2)` and diff by (subject, predicate). This is front-end
only. It makes the bi-temporal memory visible in five seconds of video ("on 1 May Alex owned
payments; on 20 May Blake did").

**Done when** the diff renders against MOCK data and the demo state, with a test.

### N3. Honest refusals in the chat
When the answer is "not in the corpus" or "the corpus does not record…", show it as a distinct
grey "Not in memory" card instead of a normal answer bubble. This shows judges it refuses instead
of guessing.

### N4. Demo script + video (needs a few cents of model calls on your own key)
Expand `docs/demo-script.md` (3 bullets now) into a shot list, then record. Keep it under 3
minutes; check Devpost's limit. Use `data/demo/` (fictional payments-ownership handover from
Alex Nova to Blake Shore on 15 May; no real people).
1. **0:00–0:20 Problem.** "Ask an assistant who owns payments. In April it was Alex, now it's
   Blake. Most memory systems can't tell."
2. **0:20–0:50 Ingest.** Run ingest on `data/demo/part_a`, then `part_b` (README "Quick start").
   Show claims appearing, each with its quote.
3. **0:50–1:30 Time machine.** Drag the date slider across 15 May and watch ownership flip. Show
   the N2 diff view.
4. **1:30–2:10 Ask.** "Who owned payments on 3 May?" → Alex, with a citation. "Who owns it now?"
   → Blake. Open the N1 "Why?" panel. Ask something not in the data to show the N3 refusal.
5. **2:10–2:35 Privacy.** Open the egress log: names and emails left the machine masked.
6. **2:35–2:50 Hermes + OpenShell.** Show Chronicle answering inside Hermes Agent
   (`deploy/hermes-plugin`) with the OpenShell egress policy (`deploy/openshell-policy.yaml`).
   This hits the Personal AI track's suggested tools.
7. **2:50–3:00 Results.** One slide: 0.946 vs NVIDIA 0.828 / 0.909, same Nemotron 3 Ultra model,
   plus 0.909 with privacy on.

Record a 10-second GIF of step 3 for Sara's README (S4).

**Done when** the video is uploaded (YouTube unlisted is fine), its link is in `docs/devpost.md`,
and the GIF is in `docs/`.

### N5. Fresh-clone install check (judges may try it)
On a clean folder, follow the README "Quick start" exactly (`uv sync`, `npm install`, run tests,
serve, open the UI). Fix or note anything that breaks, including `deploy/install.sh`. Test the
install and serve steps; ingest or ask only on the tiny demo set (a few cents).

**Done when** a fresh clone gets to a working UI with only the README's steps.

---

## Other things that help us win
- **Lead with the idea, not the benchmark.** The memory knows *when* things were true, and it keeps
  private data private. The numbers prove the idea works.
- **Show the Personal AI track's tools** (Hermes, OpenShell) in the video: that's free credit on
  "Technological Implementation".
- **Name the privacy trade-off openly:** 0.909 with masking vs 0.946 without. Judges trust teams
  that show their trade-offs.
- **Credibility lines:** "no gold answers read", "same model as NVIDIA's reference runs",
  "results vary ±2 points; mean of two runs 0.944".
- **Polish small things:** the repo description and topics on GitHub, a LICENSE (already there),
  and a clean `main` with green CI.

## Who does what (put your name in the PR thread when you start)

| Task | Owner | Needs credits? |
|---|---|---|
| S1 Devpost write-up | Sara | No |
| S2 Results doc | Sara | No |
| S3 Architecture diagram | Sara | No |
| S4 README front page | Sara | No |
| N1 "Why?" panel | Sania | No (mock); a few cents to test with real asks |
| N2 Two-date diff | Sania | No |
| N3 Refusal card | Sania | No |
| N4 Demo script + video | Sania | A few cents (demo ingest + asks) |
| N5 Fresh-clone check | Sania | A few cents |
| Accuracy runs, final numbers into S2 | P4 (@shrad1601) | Yes |
| Final Devpost submit | P4 (or whoever is awake at 30 Oct 18:00 SGT) | No |
