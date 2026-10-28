"""Check that an answer's names, numbers and short values are backed by verbatim evidence quotes.

The answer call also returns ``support``: short quotes copied from the evidence. Here the code (not
the model) checks each quote really occurs in the evidence, then that every name ("Morgan Lee"),
merge request (!342), percentage or multi-digit number, and a short answer's own words appear in
those quotes. What is left over is "unsupported", and the pipeline sends the answer back once.
Run 5 answered "ready to merge" for a merge request that was only a reserved placeholder, and named
the person who approved a proposal instead of the one who made it.
"""
import re

_SPACE = re.compile(r"\s+")
_MARKUP = re.compile(r"[*`_]+")
_DATE = re.compile(r"\b\d{4}-\d{2}-\d{2}\b|\b\d{1,2}:\d{2}\b")
_NUMBER = re.compile(r"!\d+|(?<![\w.!#])\d+(?:[.,]\d+)?\s?%|(?<![\w.!#])\d+\.\d+(?![\w.])|(?<![\w.!#-])\d{2,}(?![\w.%-])")
_NAME = re.compile(r"\b[A-Z][a-z]+(?:[- ][A-Z][a-z]+)+\b")
_NAME_STOP = frozenset({"the", "a", "an", "in", "on", "by", "as", "it", "yes", "no", "as of", "from", "to",
                        "monday", "tuesday", "wednesday", "thursday", "friday", "saturday", "sunday"})
_WORD = re.compile(r"[a-z][a-z'-]{3,}")
_STOPWORDS = frozenset({"that", "this", "with", "from", "into", "were", "have", "been", "will", "they",
                        "their", "there", "about", "which", "while", "also", "only", "still", "then",
                        # Units are written many ways ("30 days" for "30d"); the number carries the claim.
                        "days", "weeks", "hours", "minutes", "seconds", "months", "percent", "per"})
_YES_NO = re.compile(r"^\W*(yes|no)\b", re.IGNORECASE)
_GAVE_UP = re.compile(r"\bdoes not record\b|\bnot in the corpus\b", re.IGNORECASE)
SHORT_ANSWER_WORDS = 6
MIN_QUOTE = 8


def norm(text: str) -> str:
    text = text.replace("’", "'").replace("‘", "'").replace("“", '"').replace("”", '"')
    text = text.replace("–", "-").replace("—", "-")
    return _SPACE.sub(" ", _MARKUP.sub("", text)).strip().lower()


def _names(text: str) -> list[str]:
    out = []
    for m in _NAME.finditer(text):
        words = m.group(0).split()
        while words and words[0].lower() in _NAME_STOP:
            words = words[1:]
        if len(words) >= 2:
            out.append(" ".join(words))
    return out


def claims(answer: str, question: str) -> list[str]:
    """The checkable parts of ``answer`` that the question did not already supply."""
    asked = norm(question)
    text = _DATE.sub(" ", answer)
    found = [m.group(0) for m in _NUMBER.finditer(text)] + _names(text)
    first = re.split(r"[.!?](?:\s|$)|\n", answer.strip(), maxsplit=1)[0]
    if len(first.split()) <= SHORT_ANSWER_WORDS and not _YES_NO.match(first):
        found += [w for w in _WORD.findall(norm(_DATE.sub(" ", first))) if w not in _STOPWORDS]
    return list(dict.fromkeys(c for c in found if norm(c) not in asked))


def unsupported(answer: str, support, question: str, evidence_texts: list[str]) -> list[str]:
    """Claims in ``answer`` that no verified quote in ``support`` contains. Refusals need none."""
    if not answer.strip() or _GAVE_UP.search(answer):
        return []
    wanted = claims(answer, question)
    if not wanted:
        return []
    haystack = norm("\n".join(evidence_texts))
    quotes = []
    for item in support if isinstance(support, list) else []:
        quote = item.get("quote") if isinstance(item, dict) else item if isinstance(item, str) else None
        if isinstance(quote, str) and len(norm(quote)) >= MIN_QUOTE and norm(quote) in haystack:
            quotes.append(norm(quote))
    backed = "\n".join(quotes)
    return [c for c in wanted if norm(c) not in backed]
