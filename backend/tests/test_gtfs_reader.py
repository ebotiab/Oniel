import datetime as dt

from oniel.gtfs.reader import GtfsFeed, expand_calendar, parse_gtfs_time, select_corridor_trips
from oniel.network.spec import NetworkSpec


def test_parse_gtfs_time_after_midnight() -> None:
    assert parse_gtfs_time("8:30:00") == 8 * 3600 + 30 * 60
    assert parse_gtfs_time("25:10:00") == 25 * 3600 + 10 * 60


def test_expand_calendar_with_exceptions() -> None:
    cal = [
        {
            "service_id": "s",
            "monday": "1",
            "tuesday": "0",
            "wednesday": "0",
            "thursday": "0",
            "friday": "0",
            "saturday": "0",
            "sunday": "0",
            "start_date": "20261102",
            "end_date": "20261116",
        }
    ]
    exc = [
        {"service_id": "s", "date": "20261109", "exception_type": "2"},
        {"service_id": "s", "date": "20261111", "exception_type": "1"},
    ]
    dates = expand_calendar(cal, exc)["s"]
    assert dates == {dt.date(2026, 11, 2), dt.date(2026, 11, 11), dt.date(2026, 11, 16)}


def test_feed_has_the_madrid_sevilla_sample(feed: GtfsFeed, spec: NetworkSpec) -> None:
    trips = select_corridor_trips(
        feed, spec.corridor_filter.required_stop_ids, spec.corridor_filter.any_of_stop_ids
    )
    assert len(trips) > 300
    numbers = {t.train_number for t in trips}
    assert "02070" in numbers  # AVE Madrid 7:00 → Sevilla 9:48, el caso calculado a mano
    for t in trips:
        assert t.stop_times == sorted(t.stop_times, key=lambda s: s.seq)
        assert all(s.arrival_s <= s.departure_s for s in t.stop_times)
