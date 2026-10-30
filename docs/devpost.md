# Devpost submission

Copy each section into the matching Devpost field. Fill in the two links marked `TODO` before
submitting.

## Form fields

| Field | Answer |
|---|---|
| Project name | Chronicle |
| Tagline | A personal AI agent whose memory keeps up: it knows what was true *when*, cites its sources, and never sends your private data out unmasked. |
| Track | Personal AI |
| Public repo | https://github.com/Opustron66/Opustron (MIT) |
| Working demo | TODO: hosted Render URL |
| Video | TODO: YouTube link (public, under 3 minutes) |
| NVIDIA models | NVIDIA Nemotron 3 Ultra (`nvidia/Nemotron-3-Ultra-550b-a55b`) for answering, consolidation and benchmark runs; Nemotron 3.5 Lightning (`nvidia/Nemotron-3_5-Lightning`) for extraction and development |
| Nebius services | Nebius Token Factory (every model call, OpenAI-compatible endpoint) |
| Other NVIDIA tools | NVIDIA Agent Memory Benchmark (`NVIDIA/nemoclaw-community`), OpenShell egress policy, NemoClaw preset |
| Built with | python, sqlite, react, vite, nvidia-nemotron, nebius-token-factory, hermes-agent, openshell, nemoclaw, presidio, spacy, tavily, render, upstash |
| Existed before the submission period? | No. The repo was created on 14 Oct 2026 during the hackathon, and all code was written during the submission period. |

## About the project

### Inspiration

Ask an assistant "who owns the payments service?" In April the answer was Alex; since 15 May it
has been Blake. Most memory systems store both emails as text and return whichever one scores
highest, so you get a stale answer stated with confidence. A personal agent that runs all the time
over your email, chat and notes has to know *when* each thing was true. It also has to keep that
private data private, even though the model runs in the cloud.

### What it does

Chronicle is a memory and reasoning layer for a personal AI agent.

1. **Ingest.** Point it at a folder of emails, Slack threads, calendar files and notes. Nemotron
   extracts facts ("Blake Shore owns payments service, from 15 May"). Each fact carries a verbatim
   quote from its document, and facts whose quote isn't really in the document are dropped. It also
   builds a dated timeline for every tracked topic and a page for every person.
2. **Remember in two dimensions of time.** Every fact records when it was true in the world
   (valid time) and when Chronicle learned it (recorded time). Nothing is ever deleted: when Blake
   takes over, Alex's fact is closed, not overwritten. So "who owned payments on 3 May?" and "what
   did we believe on 20 April?" both have correct answers.
3. **Answer with evidence.** A question is classified (current state, as-of a date, history,
   ordering…) and routed: an as-of question only sees facts true then and documents written by
   then. Chronicle searches facts, timelines, person pages and raw documents, may search again or
   open a document, and answers with citations. Each answer has to quote its evidence, and code
   checks every quote. When the evidence isn't there it says "the corpus does not record that"
   instead of guessing.
4. **Keep private data private.** Every model call goes through one guard that pseudonymises
   names, organisations, places, emails, phone numbers and IDs before the request leaves the
   machine, and restores them in the reply. An egress log shows exactly what left, and the UI
   displays it live. Web searches that would identify a person are blocked, and a hard spending
   cap stops runaway costs.
5. **Use it.** The Memory Time Machine UI lets you drag a date slider and watch facts change,
   compare two dates, chat with citations, and inspect the egress log. Chronicle also ships as a
   Hermes Agent memory plugin (`chronicle_recall` with `as_of`, `chronicle_remember`), with an
   OpenShell policy that locks the sandbox down to Token Factory and Tavily only.

### How we built it

Four people, four layers, connected by one shared `Claim` schema:

- **P1 Ingest** (`chronicle/ingest`): parsers for email, chat, calendar and markdown; Nemotron
  extraction with a closed predicate vocabulary and JSON-schema output; entity resolution; date
  normalisation; a consolidation pass that merges topic names and writes per-topic timelines.
- **P2 Memory** (`chronicle/memory`): a bi-temporal SQLite store with half-open validity
  intervals, versioned facts, supersession rules per predicate, and BM25 search with
  reciprocal-rank fusion over facts, timelines and document chunks.
- **P3 Reason** (`chronicle/reason`): question planning, hybrid time-routed retrieval, an agentic
  answer loop (up to 3 calls), "key lines" that surface the evidence repeating the question's
  wording, claim-based voting on flip-prone questions, a code-checked quote requirement, a wider
  second look before giving up, and computed relative dates ("by Mon EOD" → 2026-05-25).
- **P4 Guard, UI and deploy** (`chronicle/guard`, `ui/`, `deploy/`): Presidio + spaCy PII
  detection, consistent pseudonyms (or realistic stand-in names), the single LLM client every
  module must use (CI fails if any other code imports an HTTP library), a response cache, the
  egress log, the React + Vite UI, the Hermes plugin, the OpenShell policy and a Render deployment.

### How we used NVIDIA Nemotron and Nebius Token Factory

Every model call in Chronicle goes to **Nemotron on Nebius Token Factory** through its
OpenAI-compatible endpoint.

- **Nemotron 3.5 Lightning** for day-to-day development ingests. Extracting facts from 425
  benchmark documents took about 8 minutes and cost under $1, so we could re-ingest after every
  prompt change.
- **Nemotron 3 Ultra (550B)** for answering, topic consolidation and every reported benchmark run,
  including that run's ingest.
  Its 1M-token context also let us test answering over the whole corpus in one prompt, with the
  shared prefix served from Token Factory's prompt cache.
- **Structured output.** Extraction uses `json_schema` response formats with thinking turned off;
  answering uses reasoning mode with a 16k token budget.
- **Token Factory sped up our iteration.** There was nothing to host: we changed one environment
  variable to switch between Lightning and Ultra, and ran 10 full benchmark runs of 186
  questions each in the final three days.
- We evaluated on **NVIDIA's Agent Memory Benchmark** with the same model, corpus and grader as
  NVIDIA's own reference runs.

### Results

Corpus A of NVIDIA's Agent Memory Benchmark: 186 questions, Nemotron 3 Ultra, NVIDIA's grader.

| System | Overall |
|---|---:|
| NVIDIA agentic RAG (reference) | 0.828 |
| NVIDIA self-model (reference) | 0.909 |
| Chronicle, first full pipeline | 0.602 |
| **Chronicle, privacy on** (every name masked; run 10) | **0.946** (176/186) |
| **Chronicle, privacy off** (runs 7 and 8) | **0.957** (178/186) |

- Same model, same corpus, same grader as NVIDIA's reference runs. NVIDIA's runs have no privacy
  layer at all, and ours scores higher even with every name masked.
- With the final answer pipeline, masking cost about 6 points (0.898 in run 9 against 0.957 with
  privacy off). Writing first names out in full before masking, so that "Jin" and "Jin Oh" share
  one pseudonym, closed most of the gap (0.946 in run 10).
- **Efficiency:** about 29k answering tokens per question with privacy off (runs 7 and 8) and 33k
  with privacy on (run 10), against 241k for NVIDIA's self-model. These are answering tokens only:
  our ingest usage was not recorded, and NVIDIA notes its reference runs' costs are not directly
  comparable.
- **Honesty:** we never read the benchmark's gold answers, only our own right/wrong flags. Results
  vary by about ±2 points between identical runs. NVIDIA describes its reference runs as "not a
  ranking", so we present this as a comparison, not a win. Our fixes were driven by corpus A's
  misses; corpus B (a different domain) has not been re-run with the final pipeline.

### How we got there

Every row is a full 186-question run on corpus A with Nemotron 3 Ultra. Scores come from the
benchmark's grader; we only ever read our own right/wrong flags.

| Run | Privacy | Overall | What changed |
|---|---|---:|---|
| Phase 0 | off | 0.602 | First end-to-end pipeline: extraction, bi-temporal memory, retrieval, answers |
| Next phase (2 trials) | off | 0.930, 0.914 | Topic timelines, hybrid retrieval, agentic answers (search again or open a document) |
| 1 | on | 0.871 | First run with every name masked |
| 2 | on | 0.909 | Masking fixes after run 1: less over-masking, URLs left readable |
| 4 | off | 0.914 | Privacy off from here on, to measure answer accuracy on its own |
| 5 | off | 0.941 | Bare value first, a wider second look before giving up, voting on flip-prone questions, computed relative dates |
| 6 | off | 0.946 | Key lines (evidence that repeats the question's wording), quotes checked in code |
| 7 | off | 0.957 | Answers in the evidence's own words, either-or answer shape, both-numbers check |
| 8 | off | 0.957 | Claim-based voting, named methods and owners; a second run at the same score |
| 9 | on | 0.898 | Run 8's code with every name masked |
| 10 | on | **0.946** | First names written out in full before masking ("Jin" → "Jin Oh") |

Run 3 (0.898, privacy on) was a repeat of run 2's code. Per-question-type results are in
`docs/benchmark-results.md`.

### Challenges we ran into

- **Run-to-run noise.** Identical code moved ±2 points between runs. We added claim-based voting
  on yes/no, "which one", "how many" and as-of questions, the types that flipped most.
- **Masking without losing accuracy.** With names replaced by `PERSON_1`, the model lost track of
  who was who. Privacy-on scores rose from 0.871 (run 1) to 0.946 (run 10) as the whole pipeline
  improved; writing names out in full before masking took the same code from 0.898 to 0.946.
- **Reasoning models and structured output.** With thinking on, Nemotron sometimes wrote its
  reasoning into the content field, and reasoning tokens used up small token budgets, which
  produced empty replies. We extract with thinking off and retry truncated answers.
- **Stale facts.** "Moved to 1 May" has to close "due 24 Apr" from the day it was said, not the
  day it was due. Supersession rules per predicate, recomputed on every write, made the answers
  independent of ingestion order.

### Accomplishments that we're proud of

- 0.946 on NVIDIA's benchmark **with every name masked**, above NVIDIA's best reference run
  (0.909), which has no masking.
- Every quote an answer gives is checked against the source text in code, and an answer with
  names or numbers no quote backs gets a correction pass.
- An architecture where nothing can bypass the privacy guard: CI enforces it.
- A memory you can see: drag the slider and watch Alex's ownership end on 15 May.

### What we learned

Most of the accuracy came from what the model is shown and when, not from a bigger model:
time-routing the evidence, surfacing the lines that repeat the question's wording, and checking
quotes in code. Measure everything: two of our "obvious" prompt rules lowered the score and were
removed.

### What's next

- Re-run corpus B with the final pipeline to check that it generalises.
- Learned routing per question type, and making stand-in names the default if they hold up.
- An on-device masking model so even the detection step never needs the network.
- Continuous ingest from live mailboxes and calendars through the Hermes plugin.

## Feedback on Nebius Token Factory and NVIDIA tools

**What worked well**

- The OpenAI-compatible endpoint was a drop-in replacement: one base URL and key, no SDK changes.
- Nemotron 3.5 Lightning is fast and cheap enough to re-run full extraction after every prompt
  change (425 documents in about 8 minutes, under $1).
- Nemotron 3 Ultra's 1M context and prompt caching made whole-corpus experiments affordable.
- The Agent Memory Benchmark's published reference runs made it easy to compare our system with
  NVIDIA's on the same model and corpus.

**What could be better**

- **No hard spending cap.** Token Factory sends alerts but keeps charging the card. We built our
  own cap (`CHRONICLE_SPEND_LIMIT_USD`) on top of the egress log. A per-key hard limit would help
  teams on shared keys.
- **Reasoning tokens count toward `max_tokens`.** With a small budget, Nemotron returns an empty
  or cut-off reply and no clear error. A note in the docs, or a separate reasoning budget, would
  have saved us debugging time.
- **Thinking with structured output.** When `json_schema` was off, Nemotron 3.5 Lightning in
  thinking mode wrote its reasoning into `content`. Documenting how thinking interacts with
  `response_format` would help.
- **Usage accounting.** The benchmark's accounting proxy counted our answering tokens but recorded
  none for ingest, so we cannot compare ingest cost with NVIDIA's runs. A usage endpoint per key
  would make cost comparisons possible.
- **Key errors.** A night of benchmark runs failed with 401s and we only noticed afterwards. A
  clearer error body for an invalid or expired key would help.
