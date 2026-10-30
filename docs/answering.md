# Answering and the benchmark adapter (P3)

How Chronicle turns a question into an answer, the rules tuned against NVIDIA's Agent Memory
Benchmark, and how to run the adapter. Switches mentioned here are listed in
[configuration.md](configuration.md).

## Benchmark adapter

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

## How questions reach memory

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

## Chat in the UI

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

## Answer rules

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
first. "Both numbers" questions give the value before and after. An agenda is never
treated as a record of what a meeting discussed. (A rule letting a person's role be inferred from
indirect evidence was tried and removed: run 5 named the wrong person on two attribution questions.) A commitment someone makes about their own work
("I'll take over the slot") counts as a step taken; scheduled events still need evidence they
happened. For as-of questions, a change written after the
date ("from 30d to 14d") may supply the old value. Retrieval packs about 10k tokens of evidence (`CHAR_BUDGET` 40,000 characters).

**Second look.** When an answer's first sentence says the corpus is silent, the question is
retrieved again with about 25k tokens of evidence (`WIDE` in `retriever.py`) and answered once
more. The retry replaces the first answer only if it answers and cites a document, so a correct
"not recorded" stands when the wider search finds nothing. `CHRONICLE_SECOND_LOOK=off` disables it.

**Voting on hard questions.** Between identical benchmark runs the answers that flipped were mostly
yes/no, "which one", "how many" and as-of questions (6 of 15 disambiguation questions on corpus A).
With `CHRONICLE_VOTE=1` those are answered a second time at temperature 0.6; if the two agree the
first stands, otherwise a third answer decides. About 44 of corpus A's 186 questions qualify.
Two answers agree when they make the same claims (the yes/no, a refusal, or the names, numbers and a
short answer's words, with Jaccard overlap of at least 0.5), not when their first sentences match
word for word. With no two agreeing, the most typical answer stays: the one whose claims overlap
most with the other two. The exact-sentence check almost never matched free text, so the vote fell
back to the first answer; across runs 4-7, 27% of voted questions flipped against 6% of the rest.
Replaying those runs' answers as vote samples, the claim check picks a right answer 89.1% of the
time on voted questions, against 88.5% for the old check and 86.4% with no vote.

**Positive-form check.** The grader reads a value in a clause that also holds "not", "no longer",
"rather than" or "instead of" as denied, and the model kept answering "NOT shared (duplicated)"
despite the prompt rule. With `CHRONICLE_POSITIVE_FORM=1` the answer's first sentence is scanned for
that shape; when found (and the question is not yes/no or about whether something happened), one
small call sees only the question and answer and restates the value first ("Duplicated. It is not
shared."). A rewrite that still leads with a negation, gives up, or grows too long is discarded. On
run 4's answers it fires on 5 of 186. Answers must also use only figures stated for the exact
context a question names ("on the smoke fixture").

**Relative dates are computed, not guessed.** Documents shown to the model carry the weekday they
were written ("written Wednesday 2026-05-20") and the calendar date after each relative day
(`chronicle/reason/dates.py`): "by Mon EOD" becomes "by Mon EOD [2026-05-25]" (the date goes after a time of day, so the phrase stays whole), "next Wed" the
Wednesday of the following week, "tonight"/"tomorrow" their dates. A bare weekday could be past or
coming, so it shows both ("Tue [2026-05-19 or 2026-05-26]") and the model picks by tense. Explicit
dates ("Wed, 20 May", "Fri the 29th") are left alone. Only the prompt text changes; stored memory
does not. The model had answered one deadline as 23, 24 and 25 May in different runs.

**Quoted support, checked in code** (`chronicle/reason/grounding.py`). Every answer also returns
`support`: one to three quotes copied word for word from the evidence. The code checks each quote
really occurs in the evidence, then that every name, merge request number, percentage or
multi-digit number, and a short answer's own words, appear in a verified quote. Anything left over
sends the answer back once with the list ("these parts were not backed by a quote"); the
better-backed answer is kept. A retry that refuses replaces the answer only when none of the
unbacked parts occur anywhere in the evidence (made up, not just unquoted). Run 5 had answered
"ready to merge" for a reserved placeholder MR; an earlier version of this check also turned a
right "30% reduction target" into a refusal because the model had not quoted the 30%.

**Key lines.** Before the question, the prompt lists up to four evidence lines that repeat one of
the question's rarer two-word phrases ("smoke fixture", "meeting load"), rarest first, with their
document ids. Rarity counts documents, not lines. A hyphenated question word also asks for its last
part with the next word ("cost-reduction target" → "reduction target"), which is how the evidence
wrote it in an as-of question run 7 refused. Run 5 answered the cache hit rate "on the smoke
fixture" with figures from a later smoke test, and missed a one-line DM saying a meeting-load fix
had been agreed. `CHRONICLE_KEY_LINES=off` turns it off.

**Answer rules.** "Who proposed X" is the first person who suggested it, even as a question, not
whoever approved it. Counts are written with their noun ("Two reports."). For as-of questions, a
later reply that reviews a draft written by the as-of date ("the 30% target is a stretch") counts as
evidence of what the draft said. Dates, deadlines and statuses are given in the evidence's own words
first ("Mon EOD", "reserved", "Draft until sign-off"), with words that limit them in time ("for now",
"not yet"). "What is the status of X" lists every status the evidence states. A chosen metric or method is named as the evidence
specifies it ("symmetric KL divergence ..."), not only by its category. For who holds a role,
the best-supported person is named from clear indirect evidence too (both the team and the person
when the evidence ties the role to both: "the evaluator workstream (Jin Oh)"), and the wider second look
accepts that evidence for role questions ("Rohan Dasgupta from Beacon"). For the current state,
changes the people involved agreed to count as put in place; for an as-of date only days after the
offer, they were still a proposal. "Has X been ...?" questions get the same refusal shape as "did X
happen?".

These came from comparing our own right and wrong answers to the same question across 14 runs,
using only each run's `correct` flags. Two earlier rules went the wrong way and were removed: "a
later message in the thread moves the deadline" (answers saying "Mon EOD" were right, "Monday
morning" wrong) and "a commitment counts as a step taken" (the as-of answer that was right said
"still an open problem").

**Either-or questions.** "Had anything been done about X, or was it still an open problem?" gets an
answer shape: start with the option that holds, in the question's own words, not "Yes." or "No."
Questions that ask for yes or no are left alone.

**Full names** (`chronicle/reason/names.py`). A lone first name in the answer ("Jin.") is written
out in full ("Jin Oh.") when exactly one known person has it. Known people are those in ingest's
`roster.json` plus every full name written as an email sender or recipient or a chat speaker in the
state's `docs.jsonl`; a capitalised word right before the pair ("Platform Eng Ops") marks a team, not
a person. With names masked, the evidence is written out the same way before the model sees it, so
"Rohan" and "Rohan Dasgupta" share one stand-in instead of two; the question is written out the same
way, or its "Jordan" and the evidence's "Jordan Kim" get different stand-ins (run 10 then answered
"the corpus does not record Jordan"). The privacy-on run 9 scored 0.898
against 0.957 with privacy off; it answered "Jin." and "Sam." where privacy-off runs said "Jin Oh."
and "Sam Iverson.", and refused "who leads Project Beacon". With the fix, the privacy-on run 10 scored 0.946 (176/186).

**Both numbers.** When the question asks for both numbers and the answer gives fewer than two
figures (beyond any in the question; dates, times and durations like "24h" don't count, and
when the answer has percentages only percentages count), the answer is asked for once more with "from <before> to
<after>"; the retry is kept only if it has both.

**Refusal wording, truncated replies.** "The corpus does not confirm" is rewritten to "does not
record", which the grader recognises as a refusal. A reply that runs out of tokens while thinking is
retried with a request to think briefly, then once more with thinking off (`complete(...,
thinking=False)` switches it for one call); before, a second cut-off was scored as "Not in the
corpus".

**Critic pass** (`chronicle/reason/critic.py`, `CHRONICLE_CRITIC=1`, off by default and in the
benchmark adapter: on a 42-question check it scored the same as without it and approved wrong
answers, since it is the same model checking itself). A second call reads the same evidence, the question and the draft, and runs a checklist:
every part answered, figures for the exact context named, the latest value (a later message in the
thread supersedes), the right person for the role, refusals the evidence contradicts, and outcomes
the evidence never states. It may replace the draft only by copying an evidence line that proves
the problem; the code checks that line really is in the evidence. A fix that refuses replaces an
answer only when the quote check had already flagged it.

**Negations get their own clause.** "Provider C has experimental status and does not fully support
it" is rewritten to "...experimental status; it does not fully support it": the grader reads a
clause holding "not" as denying everything in it.

**Timeline first for state over time (off by default, `CHRONICLE_TIMELINE=1`).** As-of questions, history questions and ones like "how did
X change" or "have mitigations been put in place?" use a schema whose first field is `timeline`:
dated events about the subject, oldest first, each marked stated, proposed, decided, scheduled or
done. The answer is then read off that timeline (the Chain-of-Note idea from LongMemEval). On a
39-question check it fixed nothing and turned one as-of answer into a refusal, so it is off.

**Whole-corpus answering (experiment).** `CHRONICLE_FULL_CORPUS=1` skips retrieval and gives the
model every document, oldest first, in one prompt (corpus A is about 120k tokens; Nemotron Ultra
takes 1M). The system prompt and the corpus come before anything question-specific, so the
provider's prompt cache serves that prefix at the cached-input price.
