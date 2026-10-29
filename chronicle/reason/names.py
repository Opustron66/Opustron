"""Give people their full names in the final answer.

With names masked, "Jin" and "Jin Oh" reach the model as two different stand-ins, so an answer
can come back as "Jin." where the evidence (and the grader) has "Jin Oh". Run 9 (privacy on) lost
"Jin." and "Sam." this way; the same answers with privacy off said "Jin Oh." and "Sam Iverson.".
A lone first name is expanded when exactly one known person has it: the people ingest put in
``roster.json``, plus every full name written as an email sender, recipient or chat speaker.
"""
import json
import re
from functools import lru_cache
from pathlib import Path

ROSTER_FILE = "roster.json"
DOCS_FILE = "docs.jsonl"
# A full name written where only people appear: an email sender or recipient ("Jin Oh <jin.oh@...>",
# "Jin Oh (@jin)") or a chat speaker ("Alex Chen (U200AC3F7E12)"). Free-form capitalised pairs
# also catch "Hello Alex" and "View Merge".
_PERSON = re.compile(r"\b([A-Z][a-z]+(?:-[A-Z][a-z]+)?) ([A-Z][a-z]+(?:-[A-Z][a-z]+)?)\s+(?:<|\(@|\(U[0-9A-F]{6,})")
# "Platform Eng Ops <eng-ops@...>" is a team: a capitalised word right before the pair.
_WORD_BEFORE = re.compile(r"[A-Z][A-Za-z]*\s$")


def _person_names(text: str) -> set[str]:
    return {f"{m.group(1)} {m.group(2)}" for m in _PERSON.finditer(text)
            if not _WORD_BEFORE.search(text[max(0, m.start() - 40):m.start()])}


@lru_cache(maxsize=8)
def _state_people(state: str) -> tuple[str, ...]:
    people: set[str] = set()
    try:
        roster = json.loads((Path(state) / ROSTER_FILE).read_text())
        listed = roster.get("people") if isinstance(roster, dict) else None
        people |= {p for p in listed if isinstance(p, str) and " " in p.strip()} if isinstance(listed, list) else set()
    except (OSError, ValueError):
        pass
    try:
        with open(Path(state) / DOCS_FILE) as f:
            for line in f:
                people |= _person_names(line)
    except OSError:
        pass
    return tuple(sorted(people))


def load_people(state: str | Path | None) -> list[str]:
    """Full names of people in the state: ingest's roster plus every sender, recipient and chat
    speaker in its documents. None without a state."""
    return list(_state_people(str(state))) if state is not None else []


def known_people(people: list[str], evidence_texts: list[str]) -> dict[str, str]:
    """First name -> full name, for first names that belong to exactly one known person."""
    names = set(people) | {name for t in evidence_texts for name in _person_names(t)}
    by_first: dict[str, set[str]] = {}
    for name in names:
        by_first.setdefault(name.split()[0], set()).add(name)
    return {first: next(iter(full)) for first, full in by_first.items() if len(full) == 1}


def expand(text: str, first_names: dict[str, str]) -> str:
    """``text`` with each lone first name in ``first_names`` written out in full. A name already
    followed by a capitalised word ("Jin Oh") or a hyphen ("Wen-Qing") is left alone."""
    for first, full in first_names.items():
        text = re.sub(rf"\b{re.escape(first)}\b(?!['’]?\s+[A-Z][a-z])(?!-)", full, text)
    return text


def full_names(answer: str, people: list[str], evidence_texts: list[str]) -> str:
    """``answer`` with each lone first name of a known person written out in full."""
    first_names = known_people(people, evidence_texts)
    return expand(answer, {f: full for f, full in first_names.items() if full not in answer})
