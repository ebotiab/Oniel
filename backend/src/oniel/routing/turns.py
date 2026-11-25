"""De qué lado de cada nodo sale cada tramo: lo que dice qué giros permiten las vías.

En un nodo que no es una estación (una bifurcación, un puesto de banalización, un PAET) un tren
no puede dar la vuelta: entra por un lado y sale por el otro. Dos tramos solo se pueden encadenar
allí si salen del nodo hacia lados opuestos. El lado se saca del trazado: se mira hacia dónde va
cada tramo a ``REACH_M`` metros del nodo y se compara con los demás. Sobre la red cargada los
ángulos no dejan dudas (más de ``OPPOSITE_DEG`` o menos de ``SAME_DEG``); un nodo de tres tramos o
más en el que alguna pareja quede en medio no se clasifica, y ``oniel-data validate`` lo da por
error.

En las estaciones no hay lados: un tren puede invertir la marcha y salir por donde entró. El
método y sus medidas están en ``docs/simulacion.md``, «Giros en las bifurcaciones».
"""

from __future__ import annotations

import math
from collections.abc import Iterable, Mapping, Sequence
from dataclasses import dataclass
from typing import Any, Protocol

from oniel.geo import Coord, haversine_km

#: Distancia al nodo, por el trazado, a la que se mira hacia dónde va un tramo.
REACH_M = 500.0
#: Dos tramos que forman menos de estos grados salen del nodo por el mismo lado.
SAME_DEG = 30.0
#: Dos tramos que forman más de estos grados salen del nodo por lados opuestos.
OPPOSITE_DEG = 150.0
#: Un tramo cuyo trazado empieza a más de estos metros del de otro en el mismo nodo no se compara.
JOIN_M = 250.0

#: Por cada nodo que no es estación, el lado (0 o 1) por el que sale cada uno de sus tramos.
Turns = dict[str, dict[str, int]]


class TurnSegment(Protocol):
    """Lo que hace falta de un tramo (``SegmentOut`` lo cumple)."""

    @property
    def id(self) -> str: ...
    @property
    def from_node_id(self) -> str: ...
    @property
    def to_node_id(self) -> str: ...
    @property
    def status(self) -> str: ...


@dataclass(frozen=True)
class TurnProblem:
    """Un nodo cuyos tramos no se dejan repartir en dos lados."""

    node_id: str
    detail: str


def _heading(coords: Sequence[Coord]) -> tuple[Coord, float]:
    """El primer punto del trazado y el rumbo, en grados, hacia el que está a ``REACH_M`` de él."""
    origin = coords[0]
    target = coords[-1]
    walked = 0.0
    for a, b in zip(coords, coords[1:], strict=False):
        step = haversine_km(a, b) * 1000
        if step > 0 and walked + step >= REACH_M:
            t = (REACH_M - walked) / step
            target = (a[0] + (b[0] - a[0]) * t, a[1] + (b[1] - a[1]) * t)
            break
        walked += step
    east = (target[0] - origin[0]) * math.cos(math.radians(origin[1]))
    north = target[1] - origin[1]
    return origin, math.degrees(math.atan2(east, north))


def _between(a: float, b: float) -> float:
    """El ángulo entre dos rumbos, de 0 a 180 grados."""
    return abs((a - b + 180) % 360 - 180)


def turn_sides(
    segments: Iterable[tuple[TurnSegment, Mapping[str, Any]]], station_ids: Iterable[str]
) -> tuple[Turns, list[TurnProblem]]:
    """Los lados de cada nodo que no es estación y los nodos que no se han podido clasificar.

    ``segments`` trae cada tramo con su geometría (un ``LineString`` GeoJSON que va de su nodo de
    origen al de destino). Solo cuentan los tramos disponibles, que son los del grafo.
    """
    stations = set(station_ids)
    at_node: dict[str, list[tuple[str, Coord, float]]] = {}
    for segment, geometry in segments:
        if segment.status != "disponible":
            continue
        coords = [(float(c[0]), float(c[1])) for c in geometry["coordinates"]]
        if len(coords) < 2:
            continue
        for node_id, line in (
            (segment.from_node_id, coords),
            (segment.to_node_id, coords[::-1]),
        ):
            if node_id not in stations:
                origin, heading = _heading(line)
                at_node.setdefault(node_id, []).append((segment.id, origin, heading))
    turns: Turns = {}
    problems: list[TurnProblem] = []
    for node_id, leaving in sorted(at_node.items()):
        leaving.sort()
        _, first_origin, first_heading = leaving[0]
        sides: dict[str, int] = {}
        trouble: str | None = None
        for segment_id, origin, heading in leaving:
            apart = haversine_km(first_origin, origin) * 1000
            if apart > JOIN_M:
                trouble = (
                    f"el trazado de {segment_id} empieza a {apart:.0f} m del de {leaving[0][0]}"
                )
                break
            angle = _between(first_heading, heading)
            if angle < SAME_DEG:
                sides[segment_id] = 0
            elif angle > OPPOSITE_DEG or len(leaving) == 2:
                # Con dos tramos no hay nada que elegir: si no salen juntos, uno sigue al otro,
                # aunque la vía haga una curva cerrada junto al nodo.
                sides[segment_id] = 1
            else:
                trouble = f"{segment_id} y {leaving[0][0]} forman {angle:.0f}°"
                break
        if trouble is None:
            # Entre sí también: dos tramos del mismo lado van juntos y dos de lados distintos, no.
            for i, (a_id, _, a_heading) in enumerate(leaving):
                for b_id, _, b_heading in leaving[i + 1 :]:
                    angle = _between(a_heading, b_heading)
                    same = sides[a_id] == sides[b_id]
                    if len(leaving) > 2 and (
                        (same and angle >= SAME_DEG) or (not same and angle <= OPPOSITE_DEG)
                    ):
                        trouble = f"{a_id} y {b_id} forman {angle:.0f}°"
        if trouble is None:
            turns[node_id] = sides
        else:
            problems.append(TurnProblem(node_id, trouble))
    return turns, problems
