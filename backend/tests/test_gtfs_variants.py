"""Un tren por número y día: los viajes que el fichero publica repetidos se juntan al leerlo."""

from __future__ import annotations

import datetime as dt
from collections import Counter

from oniel.gtfs.reader import GtfsFeed, GtfsStopTime, GtfsTrip
from oniel.gtfs.variants import merge_same_day_trips, merge_stop_times

D1, D2, D3 = dt.date(2026, 11, 13), dt.date(2026, 11, 14), dt.date(2026, 11, 15)


def hm(h: int, m: int) -> int:
    return h * 3600 + m * 60


def trip(trip_id: str, number: str, *stops: tuple[str, int]) -> GtfsTrip:
    return GtfsTrip(
        trip_id=trip_id,
        route_id="r",
        service_id=f"s-{trip_id}",
        train_number=number,
        product="MD",
        stop_times=[GtfsStopTime(i, stop, at, at, 0, 0) for i, (stop, at) in enumerate(stops, 1)],
    )


def feed_of(trips: list[GtfsTrip], dates: dict[str, set[dt.date]]) -> GtfsFeed:
    return GtfsFeed(
        agency_name="prueba",
        stops={},
        trips={t.trip_id: t for t in trips},
        service_dates={f"s-{trip_id}": days for trip_id, days in dates.items()},
        feed_start=D1,
        feed_end=D3,
    )


def stops_of(t: GtfsTrip) -> list[tuple[str, int]]:
    return [(s.stop_id, s.arrival_s) for s in t.stop_times]


def test_the_trip_with_more_stops_leads_and_the_others_add_the_stops_it_lacks() -> None:
    """Dos recorridos enteros que solo cambian una parada y un trozo suelto: un tren con todas."""
    by_b = trip("1", "100", ("A", hm(9, 0)), ("B", hm(10, 0)), ("D", hm(11, 0)))
    by_c = trip("2", "100", ("A", hm(9, 0)), ("C", hm(10, 30)), ("X", hm(10, 45)), ("D", hm(11, 0)))
    piece = trip("3", "100", ("B", hm(10, 5)), ("C", hm(10, 30)))
    primary, merged = merge_stop_times([by_b, by_c, piece])
    assert primary is by_c
    # B entra con la hora de su viaje; C ya estaba y conserva la del viaje que manda
    assert [(s.stop_id, s.arrival_s) for s in merged] == [
        ("A", hm(9, 0)),
        ("B", hm(10, 0)),
        ("C", hm(10, 30)),
        ("X", hm(10, 45)),
        ("D", hm(11, 0)),
    ]
    assert [s.seq for s in merged] == [1, 2, 3, 4, 5]


def test_with_the_same_number_of_stops_the_lower_id_leads() -> None:
    one = trip("1", "100", ("A", hm(9, 0)), ("B", hm(10, 0)))
    two = trip("2", "100", ("A", hm(9, 5)), ("B", hm(10, 5)))
    primary, merged = merge_stop_times([two, one])
    assert primary is one and [s.arrival_s for s in merged] == [hm(9, 0), hm(10, 0)]


def test_trips_of_a_number_that_share_a_day_become_one_trip_for_those_days() -> None:
    """El viaje 1 circula los tres días y el 2, dos de ellos: queda el tren entero los días en que
    coinciden y el viaje 1 solo, con su identificador, el día en que va solo."""
    whole = trip("1", "100", ("A", hm(9, 0)), ("B", hm(10, 0)), ("C", hm(11, 0)))
    part = trip("2", "100", ("B", hm(10, 0)), ("C", hm(11, 0)), ("D", hm(12, 0)))
    other = trip("9", "200", ("A", hm(7, 0)), ("B", hm(8, 0)))
    feed = feed_of([whole, part, other], {"1": {D1, D2, D3}, "2": {D2, D3}, "9": {D1, D2}})
    assert merge_same_day_trips(feed) == 1
    assert set(feed.trips) == {"1", "1+2", "9"}
    assert feed.service_dates[feed.trips["1"].service_id] == {D1}
    assert feed.service_dates[feed.trips["1+2"].service_id] == {D2, D3}
    assert [s for s, _ in stops_of(feed.trips["1+2"])] == ["A", "B", "C", "D"]
    assert stops_of(feed.trips["1"]) == stops_of(whole)
    # el otro número no se toca
    assert feed.trips["9"] is other and feed.trips["9"].service_id == "s-9"
    # nunca dos viajes del mismo número el mismo día
    per_day = Counter(
        (t.train_number, day)
        for t in feed.trips.values()
        for day in feed.service_dates[t.service_id]
    )
    assert set(per_day.values()) == {1}


def test_validity_windows_of_the_same_number_are_left_alone() -> None:
    """Dos viajes del mismo número que nunca coinciden son dos ventanas de un horario."""
    autumn = trip("1", "100", ("A", hm(9, 0)), ("B", hm(10, 0)))
    winter = trip("2", "100", ("A", hm(9, 10)), ("B", hm(10, 10)))
    feed = feed_of([autumn, winter], {"1": {D1}, "2": {D2, D3}})
    assert merge_same_day_trips(feed) == 0
    assert feed.trips == {"1": autumn, "2": winter}


def test_the_renfe_file_has_one_trip_per_train_number_and_day(feed: GtfsFeed) -> None:
    """El fichero del 8 de noviembre de 2026 trae 6.841 viajes y 237 números repetidos algún día."""
    assert (feed.trips_in_file, feed.merged_train_numbers, len(feed.trips)) == (6841, 237, 5961)
    per_day = Counter(
        (t.train_number, day)
        for t in feed.trips.values()
        for day in feed.service_dates.get(t.service_id, ())
    )
    assert set(per_day.values()) == {1}


def test_the_madrid_jaen_train_carries_the_stops_of_all_its_trips(feed: GtfsFeed) -> None:
    """MD 18030 el 13 de noviembre de 2026: el fichero lo trae en cuatro viajes (por Linares-Baeza,
    por Vilches y Mengíbar-Artichuela, y dos trozos de dos paradas) y queda en uno."""
    running = [
        t
        for t in feed.trips.values()
        if t.train_number == "18030" and D1 in feed.service_dates[t.service_id]
    ]
    assert len(running) == 1
    train = running[0]
    assert train.trip_id.count("+") == 3
    names = [feed.stops[s.stop_id].name for s in train.stop_times]
    assert names[0] == "Madrid-Chamartín-Clara Campoamor"
    assert names[-5:] == [
        "Almuradiel-Viso del Marqués",
        "Vilches",
        "Linares-Baeza",
        "Mengíbar-Artichuela",
        "Jaén",
    ]
    times = [s.arrival_s for s in train.stop_times]
    assert times == sorted(times)


def test_trains_with_different_numbers_are_not_joined(feed: GtfsFeed) -> None:
    """Los MD 13079 y 35079 de Jaén a Cádiz circulan los mismos días y coinciden de Córdoba en
    adelante, pero llevan números distintos y el fichero no dice que sean el mismo tren."""
    running = sorted(
        (t.train_number, feed.stops[t.stop_times[0].stop_id].name, t.stop_times[0].departure_s)
        for t in feed.trips.values()
        if t.train_number in ("13079", "35079") and D1 in feed.service_dates[t.service_id]
    )
    assert running == [("13079", "Jaén", hm(7, 18)), ("35079", "Jaén", hm(7, 3))]
