import datetime

from apps.web.main import _seconds_until_next_friday_3pm


def test_seconds_until_next_friday_3pm_before_target_same_day():
    now = datetime.datetime(2024, 5, 10, 14, 0)  # Friday
    assert _seconds_until_next_friday_3pm(now) == 3600


def test_seconds_until_next_friday_3pm_after_target_rolls_to_next_week():
    now = datetime.datetime(2024, 5, 10, 16, 0)  # Friday
    assert _seconds_until_next_friday_3pm(now) == 6 * 24 * 3600 + 23 * 3600
