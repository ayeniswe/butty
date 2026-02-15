import datetime

from apps.web.main import _format_balance_last_updated, _seconds_until_next_daily_sync


def test_seconds_until_next_daily_sync_is_24_hours():
    now = datetime.datetime(2024, 5, 10, 14, 0)  # Friday
    assert _seconds_until_next_daily_sync(now) == 24 * 3600


def test_seconds_until_next_daily_sync_is_24_hours_after_any_time():
    now = datetime.datetime(2024, 5, 10, 16, 0)  # Friday
    assert _seconds_until_next_daily_sync(now) == 24 * 3600


def test_format_balance_last_updated_uses_just_now_within_same_minute():
    now = datetime.datetime(2024, 5, 10, 16, 0, 45)
    last_updated = datetime.datetime(2024, 5, 10, 16, 0, 1)

    assert _format_balance_last_updated(last_updated, now) == "Updated just now"


def test_format_balance_last_updated_uses_timestamp_for_older_updates():
    now = datetime.datetime(2024, 5, 10, 16, 1, 0)

    assert (
        _format_balance_last_updated("2024-05-10 16:00:01", now)
        == "Updated May 10, 2024 04:00 PM"
    )
