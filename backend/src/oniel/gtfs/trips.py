"""Qué viajes del GTFS recorren una línea y con qué paradas se resuelve cada uno.

Un viaje se resuelve línea a línea con la asignación de paradas de cada especificación. Las
reglas de recorrido (``route_overrides``) cubren los trenes que cambian de línea a mitad de
camino: dicen entre qué paradas el viaje va por esta línea y, si hace falta, por qué nodo sale
hacia las otras. Las demás líneas cargadas (``LoadedLine``) sirven para medir la distancia por
ellas, aunque el camino hasta la parada cruce más de una, y para explicar en el visor por dónde
sigue el tren.
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


def match_run(pattern: Sequence[str], stop_ids: Sequence[str]) -> bool | None:
    """``None`` si el viaje no lleva esas paradas seguidas; si las lleva, si es en sentido inverso."""
    pattern = list(pattern)
    ids = list(stop_ids)
    n = len(pattern)
    for i in range(len(ids) - n + 1):
        window = ids[i : i + n]
        if window == pattern:
            return False
        if window == pattern[::-1]:
            return True
    return None


def match_override(override: RouteOverride, stop_ids: Sequence[str]) -> bool | None:
    """``None`` si el viaje no encaja; si encaja, si lo hace en sentido inverso al declarado."""
    return match_run(override.consecutive_stop_ids, stop_ids)


def route_for_trip(spec: NetworkSpec, trip: GtfsTrip) -> MatchedRoute | None:
    """La primera regla de recorrido de la línea que encaja con el viaje, si hay alguna."""
    stop_ids = [st.stop_id for st in trip.stop_times]
    for override in spec.route_overrides:
        reversed_ = match_override(override, stop_ids)
        if reversed_ is not None:
            return MatchedRoute(override, reversed_)
    return None


def select_trips_for_spec(feed: GtfsFeed, spec: NetworkSpec) -> list[GtfsTrip]:
    """Viajes que recorren la línea: los del filtro de corredor, los que llevan seguidas las paradas
    que el filtro declara y los de las reglas de recorrido."""
    f = spec.corridor_filter
    selected = select_corridor_trips(
        feed,
        f.required_stop_ids,
        f.any_of_stop_ids,
        min_node_stops=f.min_node_stops,
        node_stop_ids=spec.node_stop_ids,
        exclude_stop_ids=f.exclude_stop_ids,
    )
    if spec.route_overrides or f.consecutive_stop_ids:
        chosen = {t.trip_id for t in selected}
        excluded = set(f.exclude_stop_ids)
        for trip in feed.trips.values():
            if trip.trip_id in chosen:
                continue
            stop_ids = [st.stop_id for st in trip.stop_times]
            in_a_row = not excluded.intersection(stop_ids) and any(
                match_run(run, stop_ids) is not None for run in f.consecutive_stop_ids
            )
            if in_a_row or route_for_trip(spec, trip) is not None:
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
    explica y, si se conocen los nodos de las líneas del camino, la distancia por ellas.
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
        if mapping is not None and mapping.via:
            distances, note = _via_other_lines(
                st.stop_id, stop.name if stop else st.stop_id, mapping, nodes or {}, others
            )
        elif mapping is not None and mapping.track_km is not None:
            # distancia por vía que da una fuente, hasta una parada a la que no llega ninguna
            # línea cargada: vale para todas las salidas de la asignación
            name = stop.name if stop else st.stop_id
            how = f"{_km(mapping.track_km)} km de vía hasta {name}"
            distances = {e: ExitDistance(mapping.track_km, how) for e in mapping.exits}
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


def _km(value: float) -> str:
    return f"{value:.0f}"


@dataclass(frozen=True)
class ViaLeg:
    """Un trecho del camino hasta una parada de otra línea: por qué línea y entre qué nodos."""

    line: LoadedLine
    #: Nodo por el que el tren entra en la línea.
    join: LineNode
    #: Nodo en el que la deja: el enlace con el trecho siguiente o, en el último, la parada.
    end: LineNode

    @property
    def km(self) -> float:
        return abs(self.join.km - self.end.km)

    @property
    def line_name(self) -> str:
        """Nombre de la línea para ir en mitad de una frase («línea convencional…»)."""
        name = self.line.spec.line.name
        return f"{name[0].lower()}{name[1:]}"


def via_legs(
    stop_id: str, mapping: StopMapping, others: Sequence[LoadedLine]
) -> list[ViaLeg] | str:
    """El camino ``via`` de una parada, trecho a trecho; si no se puede seguir, por qué no.

    Cada trecho entra en su línea por el nodo que declara y la deja en el nodo del trecho
    siguiente, que por tanto tiene que ser común a las dos; el último llega a la parada, que
    tiene que ser un nodo de esa línea.
    """
    legs: list[ViaLeg] = []
    for i, hop in enumerate(mapping.via):
        line = next((o for o in others if o.line_id == hop.line), None)
        if line is None:
            return f"la línea {hop.line} no está entre las líneas cargadas"
        join = line.nodes.get(hop.node)
        if join is None:
            return f"{hop.node} no es un nodo de la línea {hop.line}"
        if i + 1 < len(mapping.via):
            next_node = mapping.via[i + 1].node
            end = line.nodes.get(next_node)
            if end is None:
                return f"{next_node} no es un nodo de la línea {hop.line}"
        else:
            end = line.node_of_stop(stop_id)
            if end is None:
                return f"la parada no es un nodo de la línea {hop.line}"
        legs.append(ViaLeg(line, join, end))
    return legs


def _via_other_lines(
    stop_id: str,
    stop_name: str,
    mapping: StopMapping,
    own: Mapping[str, LineNode],
    others: Sequence[LoadedLine],
) -> tuple[dict[str, ExitDistance], str | None]:
    """Nota que explica dónde está la parada y, por cada salida, la distancia hasta ella.

    La distancia suma el kilometraje de cada trecho por su línea; si la salida no es el propio
    nodo de enlace con la primera, se añade la línea recta entre los dos. Si el enlace es la
    propia parada no hay nada que medir por la otra línea y se deja la línea recta de siempre.
    """
    legs = via_legs(stop_id, mapping, others)
    if isinstance(legs, str) or not legs:
        return {}, None  # el camino no se puede seguir en esta ejecución: línea recta
    first, last = legs[0], legs[-1]
    note = f"está en la {last.line_name}"
    by_lines = sum(leg.km for leg in legs)
    if by_lines == 0:
        return {}, note
    exits = [own[e] for e in mapping.exits if e in own]
    if len(legs) == 1 and any(e.id != first.join.id for e in exits):
        note += f", con la que este tren enlaza en {first.join.label}"
    distances = {}
    for exit_node in exits:
        parts = []
        link = 0.0
        if exit_node.id != first.join.id:
            link = haversine_km((exit_node.lon, exit_node.lat), (first.join.lon, first.join.lat))
            parts.append(f"{link:.0f} km en línea recta hasta {first.join.label}")
        if len(legs) == 1:
            parts.append(f"{first.km:.0f} km por esa línea hasta {stop_name}")
        else:
            parts.extend(
                f"{leg.km:.0f} km por la {leg.line_name} hasta"
                f" {stop_name if leg is last else leg.end.label}"
                for leg in legs
            )
        how = ", ".join(parts[:-1]) + f" y {parts[-1]}" if len(parts) > 1 else parts[0]
        distances[exit_node.id] = ExitDistance(link + by_lines, how)
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
