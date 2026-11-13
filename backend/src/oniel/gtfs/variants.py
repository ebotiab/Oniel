"""Un tren por número y día: junta los viajes que un fichero publica repetidos.

El fichero de Renfe trae algunos trenes en varios viajes el mismo día, con el mismo número: dos
recorridos enteros que solo cambian una parada intermedia, el recorrido entero y una parte de él,
o trozos sueltos de dos paradas. Ninguna fuente consultada explica por qué (``docs/datos.md``,
«Trenes repetidos en el horario de Renfe»). Contados uno a uno, el mismo tren salía dos o tres
veces en las fichas y en los recuentos; aquí se juntan en un solo viaje por número de tren y día,
con las paradas de todos.
"""

from __future__ import annotations

import datetime as dt
from collections import defaultdict
from collections.abc import Sequence
from dataclasses import replace

from oniel.gtfs.reader import GtfsFeed, GtfsStopTime, GtfsTrip

#: Separa, en el identificador de un viaje juntado, los de los viajes del fichero que lo forman.
MERGED_ID_SEPARATOR = "+"


def merge_stop_times(variants: Sequence[GtfsTrip]) -> tuple[GtfsTrip, list[GtfsStopTime]]:
    """El viaje que manda y las paradas del tren, con las que solo traen las otras variantes.

    Manda el viaje con más paradas (si empatan, el de identificador menor): sus paradas y sus
    horas se dejan como están. De los demás solo se toman las paradas que faltan, cada una con la
    hora de su viaje y colocada por esa hora. Si dos viajes dan horas distintas para la misma
    parada, vale la del que manda.
    """
    ordered = sorted(variants, key=lambda t: (-len(t.stop_times), t.trip_id))
    primary = ordered[0]
    merged = list(primary.stop_times)
    seen = {s.stop_id for s in merged}
    for other in ordered[1:]:
        for stop in other.stop_times:
            if stop.stop_id in seen:
                continue
            seen.add(stop.stop_id)
            at = next(
                (i for i, s in enumerate(merged) if s.arrival_s > stop.arrival_s), len(merged)
            )
            merged.insert(at, stop)
    return primary, [replace(s, seq=i) for i, s in enumerate(merged, start=1)]


def merge_same_day_trips(feed: GtfsFeed) -> int:
    """Deja en ``feed`` un solo viaje por número de tren y día; devuelve cuántos números cambian.

    Los viajes de un mismo número que nunca coinciden en un día (las ventanas de validez de un
    horario) no se tocan. Si coinciden, cada combinación de viajes que circula junta se convierte
    en un viaje con los días en que se da esa combinación: su identificador es el del viaje que
    manda seguido de los demás, y su ``service_id`` es ese mismo identificador. Un viaje que unos
    días circula solo y otros acompañado conserva su identificador para los días en que va solo.
    """
    by_number: dict[str, list[GtfsTrip]] = defaultdict(list)
    for trip in feed.trips.values():
        by_number[trip.train_number].append(trip)
    changed = 0
    for number in sorted(by_number):
        trips = sorted(by_number[number], key=lambda t: t.trip_id)
        running: dict[dt.date, list[GtfsTrip]] = defaultdict(list)
        for trip in trips:
            for day in feed.service_dates.get(trip.service_id, ()):
                running[day].append(trip)
        if all(len(group) == 1 for group in running.values()):
            continue
        changed += 1
        combos: dict[tuple[str, ...], set[dt.date]] = defaultdict(set)
        for day, group in running.items():
            combos[tuple(t.trip_id for t in group)].add(day)
        originals = {t.trip_id: t for t in trips}
        for trip in trips:
            if feed.service_dates.get(trip.service_id):
                del feed.trips[trip.trip_id]
        for combo in sorted(combos):
            primary, stop_times = merge_stop_times([originals[i] for i in combo])
            rest = [i for i in combo if i != primary.trip_id]
            trip_id = MERGED_ID_SEPARATOR.join([primary.trip_id, *rest])
            feed.trips[trip_id] = replace(
                primary, trip_id=trip_id, service_id=trip_id, stop_times=stop_times
            )
            feed.service_dates[trip_id] = combos[combo]
    return changed
