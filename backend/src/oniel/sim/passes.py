"""Paso de un servicio por los tramos de una línea.

Reglas, en lenguaje llano:

* Si el tren para en las dos estaciones que delimitan un tramo, el paso es **publicado**: entra
  a la hora de salida de la primera y sale a la hora de llegada de la segunda.
* Si el tren no para en uno de los extremos, el paso es **estimado**: repartimos el tiempo entre
  sus dos paradas publicadas en proporción a la distancia recorrida, y le damos un margen del
  15 % de ese tiempo (mínimo 3 minutos).
* Si una de las paradas está fuera de la red cargada (por ejemplo Málaga), el tren sale o entra
  por un nodo de la línea (una bifurcación o un cambiador). Estimamos cuándo con la distancia en
  línea recta hasta esa parada y damos un margen mayor: 30 % (mínimo 5 minutos).
* Si no podemos saber por dónde circula el tren, el paso queda **indeterminado**.
"""

from __future__ import annotations

from dataclasses import dataclass
from typing import Literal

from oniel.geo import haversine_km

PassKind = Literal["publicado", "estimado", "indeterminado"]

KM_TOLERANCE = 0.05
IN_NETWORK_MARGIN_RATIO = 0.15
IN_NETWORK_MARGIN_MIN_S = 180.0
EXIT_MARGIN_RATIO = 0.30
EXIT_MARGIN_MIN_S = 300.0


@dataclass(frozen=True)
class LineNode:
    id: str
    km: float
    lon: float
    lat: float


@dataclass(frozen=True)
class LineSegment:
    id: str
    km_from: float
    km_to: float


@dataclass(frozen=True)
class StopCall:
    """Una parada del servicio tal y como la publica el horario."""

    seq: int
    stop_id: str
    stop_name: str
    arrival_s: int
    departure_s: int
    lon: float | None = None
    lat: float | None = None
    node_id: str | None = None  # la parada es un nodo de la línea
    exit_node_ids: tuple[
        str, ...
    ] = ()  # la parada está fuera; el tren entra o sale por uno de estos


@dataclass(frozen=True)
class SegmentPass:
    segment_id: str
    kind: PassKind
    enter_s: float | None
    exit_s: float | None
    enter_margin_s: float
    exit_margin_s: float
    km_increasing: bool | None
    basis: str

    @property
    def earliest_s(self) -> float | None:
        return None if self.enter_s is None else self.enter_s - self.enter_margin_s

    @property
    def latest_s(self) -> float | None:
        return None if self.exit_s is None else self.exit_s + self.exit_margin_s


@dataclass(frozen=True)
class _Anchor:
    call: StopCall
    km: float
    on_line: bool  # True si el tren para en este punto de la línea
    extra_km: float  # distancia en línea recta desde el nodo de salida hasta la parada exterior


def resolve_passes(
    calls: list[StopCall], nodes: dict[str, LineNode], segments: list[LineSegment]
) -> tuple[list[SegmentPass], Literal["completa", "parcial"]]:
    """Calcula el paso del servicio por cada tramo que recorre."""
    ordered = sorted(segments, key=lambda s: s.km_from)
    calls = sorted(calls, key=lambda c: c.seq)
    direction = _overall_direction(calls, nodes)
    anchors: list[_Anchor | None] = [_anchor_for(c, nodes, direction, prev_km=None) for c in calls]
    # segunda pasada: las salidas se eligen con el km de la parada anterior en la línea
    last_km: float | None = None
    for i, call in enumerate(calls):
        a = anchors[i]
        if a is not None and a.on_line:
            last_km = a.km
        elif call.exit_node_ids:
            anchors[i] = _anchor_for(call, nodes, direction, prev_km=last_km)

    resolution: Literal["completa", "parcial"] = "completa"
    if any(a is None for a in anchors):
        resolution = "parcial"

    passes: dict[str, SegmentPass] = {}
    i = 0
    while i < len(anchors) - 1:
        a = anchors[i]
        if a is None:
            i += 1
            continue
        # busca la siguiente ancla conocida; si hay paradas desconocidas en medio, indeterminado
        j = i + 1
        while j < len(anchors) and anchors[j] is None:
            j += 1
        if j >= len(anchors):
            break
        b = anchors[j]
        assert b is not None
        unknown_between = j > i + 1
        for p in _leg_passes(a, b, ordered, unknown_between):
            passes.setdefault(p.segment_id, p)
        i = j
    return [passes[s.id] for s in ordered if s.id in passes], resolution


def _overall_direction(calls: list[StopCall], nodes: dict[str, LineNode]) -> bool | None:
    kms = [nodes[c.node_id].km for c in calls if c.node_id and c.node_id in nodes]
    if len(kms) >= 2 and kms[0] != kms[-1]:
        return kms[-1] > kms[0]
    return None


def _anchor_for(
    call: StopCall, nodes: dict[str, LineNode], direction: bool | None, prev_km: float | None
) -> _Anchor | None:
    if call.node_id and call.node_id in nodes:
        return _Anchor(call, nodes[call.node_id].km, True, 0.0)
    candidates = [nodes[e] for e in call.exit_node_ids if e in nodes]
    if not candidates:
        return None
    chosen = candidates[0]
    if direction is not None and prev_km is not None:
        for cand in candidates:
            ahead = (
                cand.km >= prev_km - KM_TOLERANCE
                if direction
                else cand.km <= prev_km + KM_TOLERANCE
            )
            if ahead:
                chosen = cand
                break
    extra = 0.0
    if call.lon is not None and call.lat is not None:
        extra = haversine_km((call.lon, call.lat), (chosen.lon, chosen.lat))
    return _Anchor(call, chosen.km, False, extra)


def _fmt(seconds: float) -> str:
    seconds = int(round(seconds))
    h, rem = divmod(seconds, 3600)
    return f"{h:02d}:{rem // 60:02d}"


def _leg_passes(
    a: _Anchor, b: _Anchor, segments: list[LineSegment], unknown_between: bool
) -> list[SegmentPass]:
    lo, hi = min(a.km, b.km), max(a.km, b.km)
    if hi - lo < KM_TOLERANCE:
        return []
    km_increasing = b.km > a.km
    inside = [
        s for s in segments if s.km_from >= lo - KM_TOLERANCE and s.km_to <= hi + KM_TOLERANCE
    ]
    if unknown_between or (not a.on_line and not b.on_line):
        why = (
            "El horario incluye una parada que Oniel no sabe situar en la red, así que no se puede"
            " fijar el recorrido entre "
            f"{a.call.stop_name} y {b.call.stop_name}."
        )
        return [
            SegmentPass(s.id, "indeterminado", None, None, 0.0, 0.0, km_increasing, why)
            for s in inside
        ]

    t0 = float(a.call.departure_s)
    t1 = float(b.call.arrival_s)
    leg_time = max(t1 - t0, 0.0)
    on_line_km = hi - lo
    total_km = on_line_km + a.extra_km + b.extra_km
    # tiempo estimado entre los dos puntos de la línea (si una parada está fuera, parte del
    # tiempo se consume fuera de la red)
    share = 1.0 if total_km == 0 else on_line_km / total_km
    t_enter_line = t0 + leg_time * (a.extra_km / total_km if total_km else 0.0)
    t_exit_line = t_enter_line + leg_time * share
    both_on_line = a.on_line and b.on_line
    ratio = IN_NETWORK_MARGIN_RATIO if both_on_line else EXIT_MARGIN_RATIO
    min_margin = IN_NETWORK_MARGIN_MIN_S if both_on_line else EXIT_MARGIN_MIN_S
    margin = max(min_margin, ratio * (t_exit_line - t_enter_line))

    def time_at(km: float) -> float:
        frac = 0.0 if on_line_km == 0 else (km - lo) / on_line_km
        if not km_increasing:
            frac = 1.0 - frac
        return t_enter_line + frac * (t_exit_line - t_enter_line)

    passes = []
    for s in inside:
        first_km, last_km = (s.km_from, s.km_to) if km_increasing else (s.km_to, s.km_from)
        enter, exit_ = time_at(first_km), time_at(last_km)
        enter_pub = a.on_line and abs(first_km - a.km) <= KM_TOLERANCE
        exit_pub = b.on_line and abs(last_km - b.km) <= KM_TOLERANCE
        if enter_pub and exit_pub:
            kind: PassKind = "publicado"
            basis = (
                f"Horario publicado: sale de {a.call.stop_name} a las {_fmt(t0)} y llega a"
                f" {b.call.stop_name} a las {_fmt(t1)}."
            )
        else:
            kind = "estimado"
            if both_on_line:
                basis = (
                    f"Estimado repartiendo los {_fmt(leg_time)} h entre {a.call.stop_name}"
                    f" ({_fmt(t0)}) y {b.call.stop_name} ({_fmt(t1)}) en proporción a la distancia;"
                    f" margen de ±{int(margin // 60)} min."
                )
            else:
                outside = b.call.stop_name if not b.on_line else a.call.stop_name
                basis = (
                    f"Estimado: {outside} está fuera de la red cargada, así que el reparto entre"
                    f" {a.call.stop_name} ({_fmt(t0)}) y {b.call.stop_name} ({_fmt(t1)}) usa la"
                    f" distancia en línea recta; margen de ±{int(margin // 60)} min."
                )
        passes.append(
            SegmentPass(
                segment_id=s.id,
                kind=kind,
                enter_s=enter,
                exit_s=exit_,
                enter_margin_s=0.0 if enter_pub else margin,
                exit_margin_s=0.0 if exit_pub else margin,
                km_increasing=km_increasing,
                basis=basis,
            )
        )
    return passes
