from datetime import date

import pytest

from chronicle.reason.planner import InvalidQueryDate, plan_query


@pytest.mark.parametrize("question", [
    "Who owned billing on June 9?", "Who owned billing on 9 June?",
    "Who owned billing on June 9th, 2026?", "Who owned billing on 2026-06-09?",
])
def test_question_date_overrides_slider(question):
    plan = plan_query(question, as_of=date(2026, 6, 20))
    assert plan.reference_date == date(2026, 6, 9)
    assert plan.kind == "as_of"


def test_named_date_uses_slider_year():
    assert plan_query("Who owned billing on June 9?", as_of=date(2025, 6, 20)).reference_date == date(2025, 6, 9)


def test_slider_used_without_explicit_date():
    assert plan_query("Who owns billing?", as_of=date(2026, 6, 20)).reference_date == date(2026, 6, 20)


def test_history_does_not_drop_old_owner():
    plan = plan_query("Who owned billing before June 10?", as_of=date(2026, 6, 20))
    assert plan.kind == "ordering_or_history"
    assert plan.reference_date is None


def test_invalid_date_is_explicit_error():
    with pytest.raises(InvalidQueryDate):
        plan_query("Who owned billing on June 31?", as_of=date(2026, 6, 20))
