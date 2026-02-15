import datetime

from apps.web.main import _seconds_until_next_daily_sync


def test_seconds_until_next_daily_sync_is_24_hours():
    now = datetime.datetime(2024, 5, 10, 14, 0)  # Friday
    assert _seconds_until_next_daily_sync(now) == 24 * 3600


def test_seconds_until_next_daily_sync_is_24_hours_after_any_time():
    now = datetime.datetime(2024, 5, 10, 16, 0)  # Friday
    assert _seconds_until_next_daily_sync(now) == 24 * 3600
