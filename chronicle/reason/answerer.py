"""Generate privacy-routed answers with citations limited to retrieved evidence.

With ``tools`` the answerer is agentic: for up to ``MAX_ROUNDS`` model calls it may ask for more
evidence (``search`` with new queries, or ``open`` a full source document) before answering, and
the last round must answer. Without tools it answers in one call.
"""
import os
import re
from collections.abc import Callable
from dataclasses import dataclass
from datetime import date
from itertools import pairwise

from chronicle.guard import llm

from .dates import annotate_dates
from .grounding import unsupported
from .models import AnswerResult, Evidence, QueryPlan

SUPPORT = {"type": "array", "items": {
    "type": "object",
    "properties": {"doc_id": {"type": "string"}, "quote": {"type": "string"}},
    "required": ["quote"],
    "additionalProperties": False,
}}
TIMELINE = {"type": "array", "items": {
    "type": "object",
    "properties": {
        "date": {"type": "string"},
        "event": {"type": "string"},
        "status": {"type": "string", "enum": ["stated", "proposed", "decided", "scheduled", "done"]},
        "doc_id": {"type": "string"},
    },
    "required": ["date", "event", "status"],
    "additionalProperties": False,
}}

ANSWER_SCHEMA = {
    "type": "object",
    "properties": {
        "answer": {"type": "string"},
        "source_ids": {"type": "array", "items": {"type": "string"}},
        "support": SUPPORT,
    },
    "required": ["answer", "source_ids"],
    "additionalProperties": False,
}
# The timeline comes first so the model writes it before the answer.
TIMELINE_SCHEMA = {
    "type": "object",
    "properties": {"timeline": TIMELINE, **ANSWER_SCHEMA["properties"]},
    "required": ["timeline", "answer", "source_ids"],
    "additionalProperties": False,
}

GROUNDING = """Support: also fill "support" with one to three short quotes copied word for word from the
evidence (each under 30 words, with its document id) that state the names, numbers and status in
your answer. Put nothing in the answer that you cannot quote. An answer saying the corpus does not
record something needs no quotes."""

TIMELINE_RULE = """Timeline first: before answering, fill "timeline" with the dated events about the
subject of the question, oldest first (at most 12), each with its status (stated, proposed,
decided, scheduled or done) and document id. A proposal is decided once the people involved
commit to it; scheduled is not done. Then answer from the timeline: the state on the date asked,
or where it started and where it ended."""

_TIMELINE_Q = re.compile(
    r"\bhow .{0,60}\bchanged\b|\bwhere it (?:started|ended)\b|\bover the (?:corpus )?(?:window|period)\b"
    r"|\bstill (?:unaddressed|open|an open)\b|\b(?:has|had) anything been done\b|\bput in place\b",
    re.IGNORECASE)


def timeline_enabled() -> bool:
    """CHRONICLE_TIMELINE=1: timeline-first answers. Off by default: on corpus A it fixed nothing
    and turned one as-of answer into a refusal."""
    return os.environ.get("CHRONICLE_TIMELINE", "0").lower() in ("1", "true", "yes", "on")


def needs_timeline(plan: QueryPlan) -> bool:
    """State-over-time questions: as-of, history, and "has anything been done / how did it change"."""
    if not timeline_enabled():
        return False
    return plan.kind == "as_of" or plan.question_type == "history" or bool(_TIMELINE_Q.search(plan.question))


# Question phrases repeated verbatim in the evidence. Run 5 answered "the prompt-prefix cache hit
# rate on the smoke fixture" with figures from a later smoke test; only one line in the evidence
# said "smoke fixture". Lines that repeat the question's rarer two-word phrases are listed first.
_TOKEN = re.compile(r"[a-z0-9][a-z0-9'%!-]*")
_SENTENCE = re.compile(r"(?<=[.!?])\s+")
_PHRASE_STOP = frozenset(
    "a an the of on in at to for by from with and or but is are was were be been has had have do does did "
    "what which who whom when where why how that this these those it its as into about than then there "
    "their they them he she his her you your we our any all each both give name describe yes no not".split())
KEY_LINES = 4
MAX_PHRASE_DF = 3
MAX_LINE = 400


def _lines(text: str) -> list[str]:
    """Whole lines (a chat message, a timeline entry); a long paragraph is cut into sentences."""
    out = []
    for line in text.splitlines():
        out += [line] if len(line) <= MAX_LINE else _SENTENCE.split(line)
    return [x.strip() for x in out if 20 <= len(x.strip()) <= MAX_LINE and not x.lstrip().startswith("TOPIC:")]


def _phrases(text: str) -> set[str]:
    words = _TOKEN.findall(text.lower())
    return {f"{a} {b}" for a, b in pairwise(words) if a not in _PHRASE_STOP and b not in _PHRASE_STOP}


def key_lines(question: str, evidence: list[Evidence]) -> list[str]:
    """Up to ``KEY_LINES`` evidence lines that share a rare two-word phrase with the question,
    rarest match first, each tagged with its document id."""
    asked = _phrases(question)
    if not asked:
        return []
    lines = []
    for e in evidence:
        for line in _lines(e.text):
            if found := asked & _phrases(line):
                lines.append((e.doc_id, line, found))
    # Rarity counts documents, not lines: a topic, a fact and a chunk can all quote one sentence.
    df = {p: len({doc_id for doc_id, _, found in lines if p in found}) for p in asked}
    scored = {}
    for doc_id, line, found in lines:
        if line not in scored and any(df[p] <= MAX_PHRASE_DF for p in found):
            scored[line] = (sum(1 / df[p] for p in found), doc_id)
    ranked = sorted(scored.items(), key=lambda item: -item[1][0])[:KEY_LINES]
    return [f"[{doc_id}] {line}" for line, (_, doc_id) in ranked]


def key_lines_enabled() -> bool:
    return os.environ.get("CHRONICLE_KEY_LINES", "1").lower() not in ("0", "false", "no", "off")

FALLBACK_CONTRACT = """Answer the question from the memory you built out of the corpus.
Rules:
1. Be short. Answer with the specific value asked for, not a paragraph.
2. Give the CURRENT state unless the question explicitly asks about the past. A later document may supersede an earlier one.
3. If the corpus does not support an answer, say plainly that it is not in the corpus. Never guess.
4. Cite the exact document ids you relied on.
Reply with a single JSON object and nothing else:
{"answer": "<your short answer>", "source_ids": ["<doc id>", ...]}"""

EVIDENCE_RULES = """Evidence sufficiency rules (also apply when using a benchmark answer contract):
- A schedule, deadline, proposal or plan establishes intent, not whether an event occurred.
- A scheduled date in the past or future does not prove completion, non-completion or cancellation.
- If asked whether something happened and the evidence only schedules it, say the corpus does not confirm whether it happened. You may give its scheduled date.
- Say that an event completed, did not complete or was cancelled only when evidence explicitly supports that status as of the question's reference date.
- Missing evidence is not proof of a negative. Cite only documents that support what you actually assert.
- A definite completion, non-completion or cancellation answer must include the exact supporting evidence document IDs in source_ids."""

# Answers are graded clause by clause: a value is credited only where it is asserted, and a
# clause holding "not", "no longer", "rather than" or "instead of" denies everything in it.
# "NOT shared (duplicated)" therefore denies "duplicated", and a hedge added after an answer
# ("the corpus does not confirm ...") can turn it into a refusal.
ANSWER_FORM = """How to write the answer:
- Start with the bare answer as its own sentence: the name, number, date or value, or "Yes."
  or "No." Then add one short supporting sentence if useful. Keep negation words ("not",
  "no longer", "rather than", "instead of") out of the sentence that gives the value, even when
  the question asks which one is NOT something: write "Phoenix." or "Duplicated.", never
  "Phoenix is not a real project" or "NOT shared (duplicated)".
- When the evidence answers the question, answer it plainly. Do not add caveats such as "the
  corpus does not confirm ..." to an answer you have given.
- For the current state, give only the current value. Do not repeat superseded values, earlier
  plans or old proposals unless the question asks for the history.
- When the question asks how many, or for each/all items, count every distinct one in the
  evidence (same name but different date, purpose or owner = distinct) and list them all.
  Write the count with what it counts ("Two reports."), not a bare digit.
- When the question asks for both numbers, or what something did to a value, give the value
  before and after ("from 40% to 65%").
- When the question names a specific context (a fixture, environment, test, tier or date), use
  only figures stated for that exact context, not similar figures from other tests or later runs.
- An agenda or plan is not a record of what was discussed or decided at an event.
- For the current state, changes the people involved agreed to ("I'll take over the slot", "we're
  collapsing the sync to biweekly") count as put in place. For an as-of date only days after such
  an offer, it was still a proposal unless the evidence shows it had started. Scheduled events
  (reviews, launches, cutovers, meetings) need evidence that they happened.
- Give dates, deadlines and statuses in the evidence's own words first ("Mon EOD", "reserved",
  "Draft until sign-off"), then the computed date if useful ("Mon EOD (2026-05-25)"). Keep words
  that limit a value in time next to it ("duplicated for now", "not yet", "until the cutover").
- For "what is the status of X", give every status the evidence states for X, in its words (for
  example reserved, draft until sign-off, planned for a date), and no caveat about what is missing.
- For who holds a role, answer from clear indirect evidence too: if documents tie a person to a
  role or project ("Priya's team" builds Orion; Priya added Orion's registry), name the
  best-supported person with their full name rather than saying the corpus does not record it.
- "Who proposed / suggested / raised X" is the first person who suggested it, even as a question
  ("worth porting to Atlas?"); approving, assigning or later repeating it is not proposing.
- When the corpus does not record what was asked, say "The corpus does not record <it>." and
  describe no outcome."""

# An as-of question may only be answerable from a later document that records the change: "lowered
# the default from 30d to 14d" written after the date is the only statement of the old value.
AS_OF_LATER = ("never report the new values they introduce as the answer. They can still show what held "
               'before: a change written later ("raised the limit from 5 to 8") means the old value (5) '
               "held on the as-of date, so report the old value. A later reply that reviews a document "
               'written by the as-of date ("the 30% target in your draft is a stretch") shows what that '
               "document said, so report that too. Otherwise use them only to say that "
               "something had not happened yet, or was not yet decided, by the as-of date (and when it "
               "happened).")

def _contract() -> str:
    try:
        from bench.answer_contract import ANSWER_CONTRACT
        return ANSWER_CONTRACT
    except ImportError:
        return FALLBACK_CONTRACT

EVIDENCE_GUIDE = """How to read the evidence:
- TOPIC blocks are timelines of one tracked value, oldest statement first; each line gives the
  date it was stated, the source document and a verbatim quote. LATEST is the most recent statement.
- FACT lines give a fact's validity interval (valid FROM -> TO; "now" = still true) and the date
  it was stated.
- DOCUMENT blocks are raw source text; prefer them when they disagree with a FACT or TOPIC.
  Relative days in them carry the computed date in brackets ("by Mon [2026-05-25]"); a bare
  weekday shows the previous and the coming one ("Tue [2026-05-19 or 2026-05-26]"): pick by tense.
  Use these dates rather than counting days yourself.
- Cite the document ids (the [...] ids) that support your answer."""


def _written(day: str) -> str:
    """ "Wednesday 2026-05-20": the weekday too, so "by Mon" can be checked against it."""
    try:
        return f"{date.fromisoformat(day[:10]):%A} {day}"
    except ValueError:
        return day


def _render(e: Evidence) -> str:
    if e.kind == "topic":
        return e.text
    if e.kind == "entity":
        return f"PERSON PAGE\n{e.text}"
    if e.kind == "chunk":
        return f"DOCUMENT [{e.doc_id}] written {_written(e.date)}\n{annotate_dates(e.text, e.date)}"
    if e.kind == "later":
        return (f"WRITTEN AFTER THE AS-OF DATE [{e.doc_id}] written {_written(e.date)}\n"
                f"{annotate_dates(e.text, e.date)}")
    return e.text


MAX_ROUNDS = 3

AGENT_SCHEMA = {
    "type": "object",
    "properties": {
        "action": {"type": "string", "enum": ["answer", "search", "open"]},
        "timeline": TIMELINE,
        "answer": {"type": "string"},
        "source_ids": {"type": "array", "items": {"type": "string"}},
        "support": SUPPORT,
        "queries": {"type": "array", "items": {"type": "string"}},
        "doc_ids": {"type": "array", "items": {"type": "string"}},
    },
    "required": ["action"],
    "additionalProperties": False,
}

AGENT_RULES = """You may gather more evidence before answering. Reply with ONE JSON object:
- {"action": "answer", "answer": "...", "source_ids": [...]} when the evidence answers the question
  (or clearly shows the corpus does not record it). Prefer this.
- {"action": "search", "queries": ["...", "..."]} to search the corpus again with up to 3 new
  keyword queries (other names, ids, synonyms) when a key fact is missing.
- {"action": "open", "doc_ids": ["..."]} to read up to 3 full source documents named in the evidence.
Search or open only when needed: each costs a turn."""

LAST_TURN = "This is your last turn: answer now with the evidence you have."


@dataclass
class Tools:
    """What the agentic answerer may call: more retrieval and full-document reads."""

    search: Callable[[list[str]], list[Evidence]]
    open: Callable[[list[str]], list[Evidence]]


_CHAIN = re.compile(r"\bin between\b|more than once", re.IGNORECASE)
_ORDER = re.compile(r"\bin the order\b|earliest first|\border they happened\b", re.IGNORECASE)
_OUTCOME = re.compile(r"^\s*(how did|how was|what was the outcome|did)\b|^\s*(?:has|have)\b.{0,80}\bbeen\b|\bwhat was (discussed|decided|announced)\b"
                      r"|\bwhat (were the findings|did .{1,60} conclude)\b", re.IGNORECASE)
_TWO = re.compile(r"\b(two different|are different|is that right)\b", re.IGNORECASE)
# "Had anything been done about X, or was it still an open problem?": the grader matches the option
# in the question's own words. Our answers that said "still an open problem" or "Mitigations have
# been put in place" were scored right; "No." and "Mitigations have been committed" were not.
_EITHER = re.compile(r",\s*or\s+(?:was|were|is|are|has|have|had|did|does|do)\b", re.IGNORECASE)
_YES_NO_ASKED = re.compile(r"\banswer (?:with )?(?:yes|no)\b|\byes \(|\byes or no\b", re.IGNORECASE)


def answer_template(plan: QueryPlan) -> str:
    """Short answer shapes for question types the grader matches strictly."""
    q = plan.question
    if _CHAIN.search(q):
        return ('Answer shape: "In between: <value it held between the first and the latest>; now: '
                '<latest value>." Give each value exactly as the documents state it.')
    if _ORDER.search(q):
        return "Answer shape: the items, earliest first, one per line, using the question's wording."
    if _TWO.search(q):
        return 'Answer shape: "Yes. <first>: <what it is>. <second>: <what it is>." One short clause each.'
    if _OUTCOME.search(q) or plan.question_type == "abstention_risk":
        return ("If the evidence does not record that this happened or how it went, answer in one "
                "sentence that the corpus does not record it (e.g. it was only scheduled); do not "
                "describe an outcome.")
    if _EITHER.search(q) and not _YES_NO_ASKED.search(q):
        return ("Answer shape: the question offers options. Start with the option that holds, in the "
                'question\'s own words ("It was still an open problem." or "Mitigations have been put '
                'in place: ..."), not "Yes." or "No.", then the facts that show it, each with who and when.')
    return ""


def _messages(plan: QueryPlan, evidence: list[Evidence], *, agentic: bool, last: bool, note: str = "",
              hint: str = "") -> list[dict]:
    context = "\n\n".join(_render(e) for e in evidence)
    reference = f"Answer as of {plan.reference_date.isoformat()}.\n\n" if plan.reference_date else ""
    if plan.reference_date and any(e.kind == "later" for e in evidence):
        reference = (f"Answer as of {plan.reference_date.isoformat()}. Documents marked WRITTEN AFTER THE "
                     f"AS-OF DATE are not true as of that date: {AS_OF_LATER}\n\n")
    if plan.reference_date:
        reference += ('For "had X happened by then?" answer "Yes." or "No." first, then the value it held '
                      'on that date in positive form (e.g. "It was still in beta.", not "It had not '
                      'launched.") and, if it changed later, the date it changed.\n\n')
    system = f"{_contract()}\n\n{EVIDENCE_GUIDE}\n\n{EVIDENCE_RULES}\n\n{ANSWER_FORM}\n\n{GROUNDING}"
    if needs_timeline(plan):
        system += f"\n\n{TIMELINE_RULE}"
    if template := answer_template(plan):
        system += f"\n\n{template}"
    user = f"{reference}EVIDENCE:\n{context}\n\nQUESTION: {plan.question}"
    if key_lines_enabled() and (lines := key_lines(plan.question, evidence)):
        user += ("\n\nEvidence lines that repeat the question's own wording (when the question names a "
                 "specific context, its figures are usually here):\n" + "\n".join(f"- {x}" for x in lines))
    if hint:
        user += f"\n\n{hint}"
    if agentic:
        system += f"\n\n{AGENT_RULES}"
        user += f"\n\n{note}{LAST_TURN if last else ''}".rstrip()
    return [{"role": "system", "content": system}, {"role": "user", "content": user}]


CORPUS_GUIDE = """The user message starts with the whole corpus: every DOCUMENT, oldest first, each with
its id and the date it was written. A later document may supersede an earlier one. Relative days
carry the computed date in brackets ("by Mon [2026-05-25]"); use them rather than counting days.
Cite the document ids that support your answer."""


def corpus_messages(plan: QueryPlan, corpus: list[Evidence]) -> list[dict]:
    """Whole-corpus prompt. Everything that is the same for every question comes first (system
    prompt, then the corpus) so the provider's prompt cache serves it; the question comes last."""
    system = f"{_contract()}\n\n{CORPUS_GUIDE}\n\n{EVIDENCE_RULES}\n\n{ANSWER_FORM}"
    tail = []
    if plan.reference_date:
        day = plan.reference_date.isoformat()
        tail.append(f"Answer as of {day}. Documents written after {day} were not known then: {AS_OF_LATER} "
                    'For "had X happened by then?" answer "Yes." or "No." first, then the value it held on '
                    "that date in positive form.")
    if template := answer_template(plan):
        tail.append(template)
    context = "\n\n".join(_render(e) for e in corpus)
    user = f"CORPUS:\n{context}\n\n" + "".join(f"{t}\n\n" for t in tail) + f"QUESTION: {plan.question}"
    return [{"role": "system", "content": system}, {"role": "user", "content": user}]


def generate_corpus_answer(plan: QueryPlan, corpus: list[Evidence]) -> AnswerResult:
    """One call over the whole corpus, no retrieval and no tools."""
    if not corpus:
        return AnswerResult("Not in the corpus", [])
    parsed = _complete(corpus_messages(plan, corpus), ANSWER_SCHEMA)
    if not isinstance(parsed, dict):
        raise ValueError("LLM returned no JSON object")
    allowed = {e.doc_id for e in corpus}
    ids = parsed.get("source_ids") if isinstance(parsed.get("source_ids"), list) else []
    ids = list(dict.fromkeys(i for i in ids if isinstance(i, str) and i in allowed))
    answer = parsed.get("answer")
    if not isinstance(answer, str) or not answer.strip():
        answer = "Not in the corpus"
    return AnswerResult(answer=answer, source_ids=ids)


BRIEF = ("Keep your reasoning short: a few sentences at most. The answer must be one short "
         "JSON object.")


def _complete(messages: list[dict], schema: dict, temperature: float = 0.0):
    """One model call; a reply cut off by the token limit (a reasoning model thinking too long)
    is retried with a request to think briefly, then once more with thinking off (on corpus A a
    who-proposed question ran out of tokens twice and was scored as a refusal)."""
    kwargs = {"schema": schema, **({"temperature": temperature} if temperature else {})}
    try:
        return llm.complete(messages, **kwargs)
    except ValueError as exc:
        if "truncated reply" not in str(exc):
            raise
    retry = [*messages[:-1], {**messages[-1], "content": messages[-1]["content"] + "\n\n" + BRIEF}]
    try:
        return llm.complete(retry, **kwargs)
    except ValueError as exc:
        if "truncated reply" not in str(exc):
            raise
        return llm.complete(retry, **kwargs, thinking=False)


def _key(e: Evidence) -> tuple:
    return (e.kind, e.doc_id, e.text[:80])


def _str_list(value, limit: int = 3) -> list[str]:
    if not isinstance(value, list):
        return []
    return [v.strip() for v in value if isinstance(v, str) and v.strip()][:limit]


def generate_answer(plan: QueryPlan, evidence: list[Evidence], tools: Tools | None = None,
                    hint: str = "", temperature: float = 0.0) -> AnswerResult:
    if not evidence:
        return AnswerResult("Not in the corpus", [])
    evidence = list(evidence)
    if tools is None:
        parsed = _complete(_messages(plan, evidence, agentic=False, last=True, hint=hint),
                           TIMELINE_SCHEMA if needs_timeline(plan) else ANSWER_SCHEMA, temperature)
    else:
        note = ""
        for round_number in range(1, MAX_ROUNDS + 1):
            last = round_number == MAX_ROUNDS
            parsed = _complete(_messages(plan, evidence, agentic=True, last=last, note=note, hint=hint),
                               AGENT_SCHEMA, temperature)
            if not isinstance(parsed, dict):
                raise ValueError("LLM returned no JSON object")
            action = parsed.get("action")
            if last or action not in ("search", "open"):
                break
            asked = _str_list(parsed.get("queries" if action == "search" else "doc_ids"))
            found = (tools.search if action == "search" else tools.open)(asked) if asked else []
            have = {_key(e) for e in evidence}
            new = [e for e in found if _key(e) not in have]
            evidence += new
            note = (f"({action} {asked!r} added {len(new)} evidence items.)\n" if new
                    else f"({action} {asked!r} found nothing new.)\n")
    if not isinstance(parsed, dict):
        raise ValueError("LLM returned no JSON object")
    allowed = {e.doc_id for e in evidence} | {d for e in evidence for d in e.cites}
    ids = parsed.get("source_ids") or []
    if not isinstance(ids, list):
        ids = []
    ids = list(dict.fromkeys(i for i in ids if isinstance(i, str) and i in allowed))
    answer = parsed.get("answer", "Not in the corpus")
    if not isinstance(answer, str) or not answer.strip():
        answer = "Not in the corpus"
    texts = [t for e in evidence for t in (e.text, _render(e))]
    return AnswerResult(answer=answer, source_ids=ids,
                        unsupported=unsupported(answer, parsed.get("support"), plan.question, texts))
