import datetime

from apps.web.main import _seconds_until_next_daily_sync


def test_seconds_until_next_daily_sync_is_24_hours():
    now = datetime.datetime(2024, 5, 10, 14, 0)  # Friday
    assert _seconds_until_next_daily_sync(now) == 24 * 3600


def test_seconds_until_next_daily_sync_is_24_hours_after_any_time():
    now = datetime.datetime(2024, 5, 10, 16, 0)  # Friday
    assert _seconds_until_next_daily_sync(now) == 24 * 3600


def test_format_last_updated_label_shows_now_within_same_utc_minute():
    from datetime import datetime, timezone

    from apps.web.main import _format_last_updated_label

    updated_at = datetime(2024, 5, 10, 14, 0, 4, tzinfo=timezone.utc)
    now = datetime(2024, 5, 10, 14, 0, 59, tzinfo=timezone.utc)

    assert _format_last_updated_label(updated_at, now) == "Last updated now"


def test_format_last_updated_label_parses_naive_utc_and_formats_time():
    from datetime import datetime, timezone

    from apps.web.main import _format_last_updated_label

    updated_at = "2024-05-10 14:00:00"
    now = datetime(2024, 5, 10, 14, 2, 0, tzinfo=timezone.utc)

    assert _format_last_updated_label(updated_at, now) == "Last updated May 10, 2024 02:00 PM UTC"


def test_format_last_updated_label_normalizes_non_utc_timezone():
    from datetime import datetime, timedelta, timezone

    from apps.web.main import _format_last_updated_label

    pacific = timezone(timedelta(hours=-7))
    updated_at = datetime(2024, 5, 10, 7, 0, 22, tzinfo=pacific)
    now = datetime(2024, 5, 10, 14, 0, 45, tzinfo=timezone.utc)

    assert _format_last_updated_label(updated_at, now) == "Last updated now"
