import pytest

from chronicle.reason.answerer import _render
from chronicle.reason.dates import annotate_dates
from chronicle.reason.models import Evidence

WED = "2026-05-20"  # a Wednesday


@pytest.mark.parametrize("text,expected", [
    ("What I need from you by Mon EOD:", "by Mon [2026-05-25] EOD"),
    ("Skip-level with Elena is next Wed.", "next Wed [2026-05-27]"),
    ("Next Friday then", "Next Friday [2026-05-29]"),
    ("this Thursday 14:00", "this Thursday [2026-05-21] 14:00"),
    ("last Fri we cut over", "last Fri [2026-05-15]"),
    ("we shipped it Tue", "Tue [2026-05-19 or 2026-05-26]"),
    ("i'll send a draft tonight", "tonight [2026-05-20]"),
    ("see you tomorrow", "tomorrow [2026-05-21]"),
    ("as of yesterday", "yesterday [2026-05-19]"),
])
def test_relative_days_get_their_calendar_date(text, expected):
    assert expected in annotate_dates(text, WED)


@pytest.mark.parametrize("text", [
    "Date: Wed, 20 May 2026", "Thursday, May 28 works", "Wed 5/27 at 10", "Fri the 29th",
    "I sat down while the sun was out", "no relative days here",
])
def test_explicit_dates_and_ordinary_words_are_left_alone(text):
    assert annotate_dates(text, WED) == text


def test_unknown_written_date_leaves_text_alone():
    assert annotate_dates("by Mon EOD", "") == "by Mon EOD"
    assert annotate_dates("by Mon EOD", "soon") == "by Mon EOD"


def test_documents_are_shown_with_weekday_and_annotated_dates():
    shown = _render(Evidence("E:1", "What I need by Mon EOD", WED, kind="chunk"))
    assert shown.startswith("DOCUMENT [E:1] written Wednesday 2026-05-20\n")
    assert "by Mon [2026-05-25] EOD" in shown
    later = _render(Evidence("E:2", "lands tomorrow", WED, kind="later"))
    assert "written Wednesday 2026-05-20" in later and "tomorrow [2026-05-21]" in later
