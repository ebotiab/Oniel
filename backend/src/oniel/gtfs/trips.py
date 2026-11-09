"""Qué viajes del GTFS recorren una línea y con qué paradas se resuelve cada uno.

Un viaje se resuelve línea a línea con la asignación de paradas de cada especificación. Las
reglas de recorrido (``route_overrides``) cubren los trenes que cambian de línea a mitad de
camino: dicen entre qué paradas el viaje va por esta línea y, si hace falta, por qué nodo sale
hacia la otra. Las demás líneas cargadas (``OtherLine``) sirven para medir la distancia por
ellas y para explicar en el visor por dónde sigue el tren.
"""

from __future__ import annotations

from collections.abc import Mapping, Sequence
from dataclasses import dataclass

from oniel.geo import haversine_km
from oniel.gtfs.reader import GtfsFeed, GtfsTrip, select_corridor_trips
from oniel.network.spec import NetworkSpec, RouteOverride, StopMapping
from oniel.sim.passes import ExitDistance, LineNode, StopCall


@dataclass(frozen=True)
class LoadedLine:
    """Una línea cargada: su especificación y sus nodos con kilómetro y coordenadas."""

    spec: NetworkSpec
    nodes: Mapping[str, LineNode]

    @property
    def line_id(self) -> str:
        return self.spec.line.id

    def node_of_stop(self, stop_id: str) -> LineNode | None:
        mapping = self.spec.stop_mappings.get(stop_id)
        if mapping is None or mapping.node is None:
            return None
        return self.nodes.get(mapping.node)


@dataclass(frozen=True)
class MatchedRoute:
    """Una regla de recorrido aplicada a un viaje concreto."""

    override: RouteOverride
    reversed: bool

    @property
    def first_stop_id(self) -> str | None:
        """Parada en la que el viaje empieza a ir por la línea, en el sentido del viaje."""
        return self.override.to_stop_id if self.reversed else self.override.from_stop_id

    @property
    def last_stop_id(self) -> str | None:
        return self.override.from_stop_id if self.reversed else self.override.to_stop_id


def match_override(override: RouteOverride, stop_ids: Sequence[str]) -> bool | None:
    """``None`` si el viaje no encaja; si encaja, si lo hace en sentido inverso al declarado."""
    pattern = list(override.consecutive_stop_ids)
    ids = list(stop_ids)
    n = len(pattern)
    for i in range(len(ids) - n + 1):
        window = ids[i : i + n]
        if window == pattern:
            return False
        if window == pattern[::-1]:
            return True
    return None


def route_for_trip(spec: NetworkSpec, trip: GtfsTrip) -> MatchedRoute | None:
    """La primera regla de recorrido de la línea que encaja con el viaje, si hay alguna."""
    stop_ids = [st.stop_id for st in trip.stop_times]
    for override in spec.route_overrides:
        reversed_ = match_override(override, stop_ids)
        if reversed_ is not None:
            return MatchedRoute(override, reversed_)
    return None


def select_trips_for_spec(feed: GtfsFeed, spec: NetworkSpec) -> list[GtfsTrip]:
    """Viajes que recorren la línea: los del filtro de corredor más los de las reglas de recorrido."""
    f = spec.corridor_filter
    selected = select_corridor_trips(
        feed,
        f.required_stop_ids,
        f.any_of_stop_ids,
        min_node_stops=f.min_node_stops,
        node_stop_ids=spec.node_stop_ids,
        exclude_stop_ids=f.exclude_stop_ids,
    )
    if spec.route_overrides:
        chosen = {t.trip_id for t in selected}
        for trip in feed.trips.values():
            if trip.trip_id not in chosen and route_for_trip(spec, trip) is not None:
                selected.append(trip)
        selected.sort(key=lambda t: (t.train_number, t.trip_id))
    return selected


def calls_for_trip(
    trip: GtfsTrip,
    feed: GtfsFeed,
    spec: NetworkSpec,
    *,
    nodes: Mapping[str, LineNode] | None = None,
    others: Sequence[LoadedLine] = (),
    route: MatchedRoute | None = None,
) -> list[StopCall]:
    """Todas las paradas del viaje, con la asignación que les da esta línea.

    Si el viaje encaja con una regla de recorrido, sus asignaciones particulares mandan sobre las
    generales. Una parada que es salida hacia otra línea cargada (``via``) lleva una nota que lo
    explica y, si se conocen los nodos de las dos líneas, la distancia por la otra línea.
    """
    general = spec.stop_mappings
    calls = []
    for st in trip.stop_times:
        stop = feed.stops.get(st.stop_id)
        mapping = (
            route.override.mapping_for(st.stop_id, general)
            if route is not None
            else general.get(st.stop_id)
        )
        distances: dict[str, ExitDistance] = {}
        note = None
        if mapping is not None and mapping.via is not None:
            distances, note = _via_other_line(
                st.stop_id, stop.name if stop else st.stop_id, mapping, nodes or {}, others
            )
        calls.append(
            StopCall(
                seq=st.seq,
                stop_id=st.stop_id,
                stop_name=stop.name if stop else st.stop_id,
                arrival_s=st.arrival_s,
                departure_s=st.departure_s,
                lon=stop.lon if stop else None,
                lat=stop.lat if stop else None,
                node_id=mapping.node if mapping else None,
                exit_node_ids=tuple(mapping.exits) if mapping else (),
                exit_distances=distances,
                exit_note=note,
            )
        )
    return calls


def _via_other_line(
    stop_id: str,
    stop_name: str,
    mapping: StopMapping,
    own: Mapping[str, LineNode],
    others: Sequence[LoadedLine],
) -> tuple[dict[str, ExitDistance], str | None]:
    """Nota que explica dónde está la parada y, por cada salida, la distancia hasta ella.

    La distancia se compone de la línea recta entre la salida y el nodo de enlace más el
    kilometraje por la otra línea desde ahí hasta la parada. Si el enlace es la propia parada
    no hay nada que medir por la otra línea y se deja la línea recta de siempre.
    """
    assert mapping.via is not None
    other = next((o for o in others if o.line_id == mapping.via.line), None)
    if other is None:
        return {}, None  # la otra línea no está cargada en esta ejecución: línea recta
    join = other.nodes.get(mapping.via.node)
    target = other.node_of_stop(stop_id)
    if join is None or target is None:
        return {}, None
    name = other.spec.line.name
    note = f"está en la {name[0].lower()}{name[1:]}"
    if join.id == target.id:
        return {}, note
    note += f", con la que este tren enlaza en {join.label}"
    by_other = abs(join.km - target.km)
    distances = {}
    for exit_id in mapping.exits:
        exit_node = own.get(exit_id)
        if exit_node is None:
            continue
        if exit_node.id == join.id:
            how = f"{by_other:.0f} km por esa línea hasta {stop_name}"
            distances[exit_id] = ExitDistance(by_other, how)
            continue
        link = haversine_km((exit_node.lon, exit_node.lat), (join.lon, join.lat))
        how = (
            f"{link:.0f} km en línea recta hasta {join.label} y {by_other:.0f} km por esa línea"
            f" hasta {stop_name}"
        )
        distances[exit_id] = ExitDistance(link + by_other, how)
    return distances, note


def calls_on_line(calls: Sequence[StopCall], route: MatchedRoute | None) -> list[StopCall]:
    """Las paradas con las que se resuelve esta línea: todas, o el tramo que marca la regla."""
    ordered = sorted(calls, key=lambda c: c.seq)
    if route is None:
        return ordered
    ids = [c.stop_id for c in ordered]
    start = ids.index(route.first_stop_id) if route.first_stop_id is not None else 0
    end = ids.index(route.last_stop_id) if route.last_stop_id is not None else len(ids) - 1
    return ordered[start : end + 1]
