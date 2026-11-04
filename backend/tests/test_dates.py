from datetime import date

from app.nlp.dates import find_dates, parse_meeting_date

MON = date(2025, 3, 10)  # a Monday


def one(text, ref=MON):
    found = find_dates(text, ref)
    assert found, text
    return found[0]


def test_weekday_resolves_to_next_occurrence_after_meeting():
    d = one("finish it by Friday")
    assert d.resolved and d.date == date(2025, 3, 14)
    assert one("by Monday").date == date(2025, 3, 17)  # not "today"


def test_next_weekday_means_following_week():
    assert one("next Friday").date == date(2025, 3, 21)


def test_tomorrow_today_and_in_n_days():
    assert one("tomorrow").date == date(2025, 3, 11)
    assert one("today").date == MON
    assert one("in 3 days").date == date(2025, 3, 13)
    assert one("in two weeks").date == date(2025, 3, 24)


def test_relative_dates_stay_unresolved_without_reference_date():
    d = one("by Friday", ref=None)
    assert not d.resolved and d.date is None and d.kind == "relative"
    assert "Friday" in d.normalized


def test_absolute_dates():
    assert one("on 14 March").date == date(2025, 3, 14)
    assert one("March 14th, 2026").date == date(2026, 3, 14)
    assert one("2025-04-01").date == date(2025, 4, 1)
    d = one("on 14 March", ref=None)
    assert not d.resolved and "year unknown" in d.normalized


def test_ambiguous_numeric_date_is_not_guessed():
    d = one("by 03/04")
    assert not d.resolved and "Ambiguous" in (d.note or "")
    assert one("by 25/03").date == date(2025, 3, 25)


def test_event_and_urgency_deadlines_are_unresolved():
    assert one("before the demo").kind == "event"
    assert not one("ASAP").resolved


def test_end_of_week_and_month():
    assert one("by end of week").date == date(2025, 3, 14)
    assert one("by end of the month").date == date(2025, 3, 31)


def test_meeting_date_validation():
    assert parse_meeting_date("2025-03-10") == MON
    assert parse_meeting_date("") is None
    try:
        parse_meeting_date("10 March")
        assert False
    except ValueError:
        pass


def test_no_dates_in_plain_sentence():
    assert find_dates("We should talk about the architecture", MON) == []
