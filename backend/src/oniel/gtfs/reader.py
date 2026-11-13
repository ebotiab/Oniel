"""Lectura de un fichero GTFS (zip): el de Renfe y el de Ouigo.

El fichero de Renfe rellena los campos con espacios hasta una anchura fija y usa un trip_id por
ventana de validez; aquí se normaliza todo y se expande el calendario a fechas concretas.
"""

from __future__ import annotations

import csv
import datetime as dt
import io
import re
import zipfile
from collections import defaultdict
from dataclasses import dataclass, field
from pathlib import Path

WEEKDAY_COLUMNS = ("monday", "tuesday", "wednesday", "thursday", "friday", "saturday", "sunday")


@dataclass(frozen=True)
class GtfsStop:
    stop_id: str
    name: str
    lon: float
    lat: float


@dataclass(frozen=True)
class GtfsStopTime:
    seq: int
    stop_id: str
    arrival_s: int
    departure_s: int
    pickup_type: int | None
    drop_off_type: int | None


@dataclass
class GtfsTrip:
    trip_id: str
    route_id: str
    service_id: str
    train_number: str
    product: str
    stop_times: list[GtfsStopTime] = field(default_factory=list)


@dataclass
class GtfsFeed:
    agency_name: str
    stops: dict[str, GtfsStop]
    trips: dict[str, GtfsTrip]
    service_dates: dict[str, set[dt.date]]
    feed_start: dt.date
    feed_end: dt.date
    #: Viajes que trae el fichero, antes de juntar los que repiten un tren el mismo día.
    trips_in_file: int = 0
    #: Números de tren que el fichero trae en más de un viaje algún día.
    merged_train_numbers: int = 0

    def stop_ids_of(self, trip: GtfsTrip) -> set[str]:
        return {s.stop_id for s in trip.stop_times}


def parse_gtfs_time(value: str) -> int:
    """'8:30:00' o '25:10:00' → segundos desde la medianoche del día de servicio."""
    h, m, s = value.strip().split(":")
    return int(h) * 3600 + int(m) * 60 + int(s)


def parse_gtfs_date(value: str) -> dt.date:
    return dt.datetime.strptime(value.strip(), "%Y%m%d").date()


def _rows(zf: zipfile.ZipFile, name: str) -> list[dict[str, str]]:
    with zf.open(name) as fh:
        text = io.TextIOWrapper(fh, encoding="utf-8-sig")
        reader = csv.DictReader(text)
        return [
            {k.strip(): (v or "").strip() for k, v in row.items() if k is not None}
            for row in reader
        ]


def expand_calendar(
    calendar: list[dict[str, str]], calendar_dates: list[dict[str, str]]
) -> dict[str, set[dt.date]]:
    dates: dict[str, set[dt.date]] = defaultdict(set)
    for row in calendar:
        start, end = parse_gtfs_date(row["start_date"]), parse_gtfs_date(row["end_date"])
        weekdays = [row.get(col, "0") == "1" for col in WEEKDAY_COLUMNS]
        day = start
        while day <= end:
            if weekdays[day.weekday()]:
                dates[row["service_id"]].add(day)
            day += dt.timedelta(days=1)
    for row in calendar_dates:
        day = parse_gtfs_date(row["date"])
        if row["exception_type"] == "1":
            dates[row["service_id"]].add(day)
        else:
            dates[row["service_id"]].discard(day)
    return dict(dates)


def train_number(short_name: str, product: str) -> str:
    """Número de tren sin el producto delante: el fichero de Ouigo escribe «TGV 6477»."""
    prefix = f"{product} "
    return short_name[len(prefix) :] if product and short_name.startswith(prefix) else short_name


#: Palabras que van en minúscula dentro del nombre de una estación.
_LOWERCASE_WORDS = {"de", "del", "la", "las", "el", "los", "y"}


def stop_name(name: str) -> str:
    """Nombre de parada legible: uno escrito todo en mayúsculas pasa a mayúscula inicial.

    «MADRID-PUERTA DE ATOCHA» → «Madrid-Puerta de Atocha». Los demás se dejan como están.
    """
    if not name.isupper():
        return name
    words = re.split(r"([ /-])", name.lower())
    return "".join(
        w if i and w in _LOWERCASE_WORDS else w[:1].upper() + w[1:] for i, w in enumerate(words)
    )


def read_feed(path: Path, *, stop_id_prefix: str | None = None) -> GtfsFeed:
    """Lee un GTFS y deja un viaje por número de tren y día (``oniel.gtfs.variants``).

    Con ``stop_id_prefix`` se quita ese prefijo de los ``stop_id`` que lo llevan.
    """
    from oniel.gtfs.variants import merge_same_day_trips

    def stop_id(value: str) -> str:
        return value.removeprefix(stop_id_prefix) if stop_id_prefix else value

    with zipfile.ZipFile(path) as zf:
        agency = _rows(zf, "agency.txt")
        stops = {
            stop_id(r["stop_id"]): GtfsStop(
                stop_id(r["stop_id"]),
                stop_name(r["stop_name"]),
                float(r["stop_lon"]),
                float(r["stop_lat"]),
            )
            for r in _rows(zf, "stops.txt")
        }
        routes = {r["route_id"]: r for r in _rows(zf, "routes.txt")}
        trips: dict[str, GtfsTrip] = {}
        for r in _rows(zf, "trips.txt"):
            route = routes.get(r["route_id"], {})
            product = route.get("route_short_name") or route.get("route_long_name") or ""
            trips[r["trip_id"]] = GtfsTrip(
                trip_id=r["trip_id"],
                route_id=r["route_id"],
                service_id=r["service_id"],
                train_number=train_number(r.get("trip_short_name") or r["trip_id"], product),
                product=product,
            )
        for r in _rows(zf, "stop_times.txt"):
            trip = trips.get(r["trip_id"])
            if trip is None:
                continue
            trip.stop_times.append(
                GtfsStopTime(
                    seq=int(r["stop_sequence"]),
                    stop_id=stop_id(r["stop_id"]),
                    arrival_s=parse_gtfs_time(r["arrival_time"]),
                    departure_s=parse_gtfs_time(r["departure_time"]),
                    pickup_type=int(r["pickup_type"]) if r.get("pickup_type") else None,
                    drop_off_type=int(r["drop_off_type"]) if r.get("drop_off_type") else None,
                )
            )
        for trip in trips.values():
            trip.stop_times.sort(key=lambda s: s.seq)
        calendar = _rows(zf, "calendar.txt")
        calendar_dates = (
            _rows(zf, "calendar_dates.txt") if "calendar_dates.txt" in zf.namelist() else []
        )
    service_dates = expand_calendar(calendar, calendar_dates)
    all_dates = {d for ds in service_dates.values() for d in ds}
    feed = GtfsFeed(
        agency_name=agency[0]["agency_name"] if agency else "",
        stops=stops,
        trips=trips,
        service_dates=service_dates,
        feed_start=min(all_dates),
        feed_end=max(all_dates),
        trips_in_file=len(trips),
    )
    feed.merged_train_numbers = merge_same_day_trips(feed)
    return feed


def select_corridor_trips(
    feed: GtfsFeed,
    required_stop_ids: list[str],
    any_of_stop_ids: list[str],
    *,
    min_node_stops: int = 0,
    node_stop_ids: frozenset[str] = frozenset(),
    exclude_stop_ids: list[str] | None = None,
) -> list[GtfsTrip]:
    """Viajes que recorren la línea según el filtro de corredor de su especificación.

    Un viaje entra si para en todas las ``required_stop_ids``, en alguna de ``any_of_stop_ids``
    (si se dan), en al menos ``min_node_stops`` paradas distintas que sean nodos de la línea y en
    ninguna de ``exclude_stop_ids``.
    """
    required, any_of = set(required_stop_ids), set(any_of_stop_ids)
    excluded = set(exclude_stop_ids or ())
    selected = []
    for trip in feed.trips.values():
        ids = feed.stop_ids_of(trip)
        if not required <= ids or (any_of and not ids & any_of) or ids & excluded:
            continue
        if min_node_stops and len(ids & node_stop_ids) < min_node_stops:
            continue
        selected.append(trip)
    selected.sort(key=lambda t: (t.train_number, t.trip_id))
    return selected
