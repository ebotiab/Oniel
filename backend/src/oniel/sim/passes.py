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
* Si esa parada está en otra línea cargada (un tren que cambia de línea a mitad de recorrido),
  la asignación puede traer la distancia real desde la salida hasta la parada por la otra línea;
  entonces el reparto la usa en vez de la línea recta, con el mismo margen del 30 %.
* Si la parada está fuera de la red cargada pero una fuente dice cuántos kilómetros de vía hay
  hasta ella desde la salida (de la bifurcación de Albacete a Elche AV), el
  reparto usa esa distancia en vez de la línea recta, con el mismo margen del 30 %.
* Si las dos paradas están fuera de la línea y a una de ellas, al menos, se llega por otra línea
  cargada o por un camino de longitud conocida, el tren cruza la línea sin parar: entra por un
  nodo y sale por otro. Si la otra parada está fuera de la red cargada, su distancia es la línea recta, como
  arriba (hacen falta sus coordenadas). El paso es estimado y el margen es el 30 % del mayor de los dos tiempos que pasa
  fuera de la línea.
* Si no podemos saber por dónde circula el tren (dos paradas fuera de la red cargada, o una
  parada que no se sabe situar), el paso queda **indeterminado**.
* Si la línea tiene un **baipás** (otra línea cargada que une dos de sus nodos y evita lo que hay
  entre ellos, como los que rodean Zaragoza y Lleida) y el tren no para ni sale de la línea entre
  esos dos nodos, va por el baipás: no pasa por los tramos que quedan entre ellos, pasa por los
  del baipás y el reparto del tiempo usa los kilómetros de ese camino.
* Si la línea es un **enlace** (una vía corta entre un nodo de una línea y un nodo de otra, como
  el de Monforte del Cid), el tren la cruza entre una parada de cada lado, y la explicación del
  paso empieza por la parada del lado de la otra línea, que es el motivo por el que va por él:
  «Viene de Alicante-Terminal: por eso va por aquí.»
"""

from __future__ import annotations

from collections.abc import Mapping, Sequence
from dataclasses import dataclass, field
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
    name: str = ""

    @property
    def label(self) -> str:
        return self.name or self.id


@dataclass(frozen=True)
class LineSegment:
    id: str
    km_from: float
    km_to: float


@dataclass(frozen=True)
class BypassPiece:
    """Un tramo de un baipás, medido desde el nodo en el que el baipás se separa de la línea."""

    segment_id: str
    km_from: float
    km_to: float
    #: El kilometraje de la línea del baipás crece en el mismo sentido que el de la línea.
    same_direction: bool = True


@dataclass(frozen=True)
class Bypass:
    """Otro camino entre dos nodos de la línea, por una línea aparte que evita lo que hay entre ellos.

    Lo toma el tren que recorre la línea de un nodo al otro sin parar ni salir de ella entre los
    dos: el que no tiene motivo para entrar en la estación que el baipás rodea.
    """

    #: Kilómetros, en la línea, de los dos nodos que el baipás une.
    km_from: float
    km_to: float
    #: Sus tramos, en el orden en que se recorren desde ``km_from``.
    pieces: tuple[BypassPiece, ...]
    #: Frase que explica por qué el tren va por él («No para en Zaragoza-Delicias: …»).
    note: str = ""

    @property
    def length_km(self) -> float:
        return self.pieces[-1].km_to if self.pieces else 0.0

    @property
    def saved_km(self) -> float:
        """Lo que el baipás acorta respecto al camino por la línea entre los mismos dos nodos."""
        return (self.km_to - self.km_from) - self.length_km


@dataclass(frozen=True)
class ExitDistance:
    """Distancia conocida desde un nodo de salida hasta una parada que está en otra línea cargada."""

    km: float
    #: Cómo se compone, para explicarlo («47 km en línea recta hasta Ciudad Real y 173 km por esa
    #: línea hasta Córdoba»).
    how: str


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
    #: Distancia conocida desde cada nodo de salida hasta la parada (por otra línea cargada, o
    #: por vía según una fuente); si falta, se usa la línea recta.
    exit_distances: Mapping[str, ExitDistance] = field(default_factory=dict)
    #: Dónde está la parada cuando no es de esta línea pero sí de otra cargada, para explicarlo
    #: («está en la línea de alta velocidad Madrid – Sevilla, con la que enlaza en Ciudad Real»).
    exit_note: str | None = None


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
    extra_km: float  # distancia desde el nodo de salida hasta la parada exterior
    #: Nodo por el que el tren sale o entra, si la parada es exterior.
    exit_node: LineNode | None = None
    #: De dónde sale extra_km cuando no es la línea recta.
    extra_how: str | None = None

    @property
    def measured(self) -> bool:
        """Se sabe cuánto hay hasta la parada: está en la línea, se llega por líneas cargadas o
        tiene coordenadas con las que medir la línea recta."""
        located = self.call.lon is not None and self.call.lat is not None
        return self.on_line or self.extra_how is not None or located

    @property
    def along_loaded_lines(self) -> bool:
        """La parada es exterior, pero se sabe cuánta vía hay hasta ella: por otras líneas
        cargadas o porque una fuente da la distancia."""
        return not self.on_line and self.exit_node is not None and self.extra_how is not None


def resolve_passes(
    calls: Sequence[StopCall],
    nodes: Mapping[str, LineNode],
    segments: Sequence[LineSegment],
    bypasses: Sequence[Bypass] = (),
    link_far_node: str | None = None,
) -> tuple[list[SegmentPass], Literal["completa", "parcial"]]:
    """Calcula el paso del servicio por cada tramo que recorre.

    Con ``bypasses``, el resultado lleva también los pasos por los tramos de los baipases que el
    tren toma, que son de otra línea: van detrás de los de esta. ``link_far_node`` es, si la línea
    es un enlace, el nodo por el que se une a la línea de la que no cuelga: la parada por la que
    el tren entra o sale por él abre la explicación del paso.
    """
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
        for p in _leg_passes(a, b, ordered, unknown_between, bypasses, link_far_node):
            passes.setdefault(p.segment_id, p)
        i = j
    own = [passes.pop(s.id) for s in ordered if s.id in passes]
    return [*own, *passes.values()], resolution


def _overall_direction(calls: Sequence[StopCall], nodes: Mapping[str, LineNode]) -> bool | None:
    kms = [nodes[c.node_id].km for c in calls if c.node_id and c.node_id in nodes]
    if len(kms) >= 2 and kms[0] != kms[-1]:
        return kms[-1] > kms[0]
    return None


def _anchor_for(
    call: StopCall, nodes: Mapping[str, LineNode], direction: bool | None, prev_km: float | None
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
    known = call.exit_distances.get(chosen.id)
    if known is not None:
        return _Anchor(call, chosen.km, False, known.km, chosen, known.how)
    extra = 0.0
    if call.lon is not None and call.lat is not None:
        extra = haversine_km((call.lon, call.lat), (chosen.lon, chosen.lat))
    return _Anchor(call, chosen.km, False, extra, chosen)


def _fmt(seconds: float) -> str:
    seconds = int(round(seconds))
    h, rem = divmod(seconds, 3600)
    return f"{h:02d}:{rem // 60:02d}"


def _leg_passes(
    a: _Anchor,
    b: _Anchor,
    segments: Sequence[LineSegment],
    unknown_between: bool,
    bypasses: Sequence[Bypass] = (),
    link_far_node: str | None = None,
) -> list[SegmentPass]:
    lo, hi = min(a.km, b.km), max(a.km, b.km)
    if hi - lo < KM_TOLERANCE:
        return []
    km_increasing = b.km > a.km
    inside = [
        s for s in segments if s.km_from >= lo - KM_TOLERANCE and s.km_to <= hi + KM_TOLERANCE
    ]
    # Las dos paradas fuera de la línea: el recorrido se puede fijar si al menos a una se llega
    # por otra línea cargada (el tren cruza esta de un nodo a otro sin parar en ella) y de la otra
    # se sabe a qué distancia queda. Con las dos fuera de la red cargada no hay nada que ancle
    # por dónde va.
    crossing = not a.on_line and not b.on_line
    anchored = (a.along_loaded_lines or b.along_loaded_lines) and a.measured and b.measured
    if unknown_between or (crossing and not anchored):
        why = (
            "El horario incluye una parada que Oniel no sabe situar en la red, así que no se puede"
            " fijar el recorrido entre "
            f"{a.call.stop_name} y {b.call.stop_name}."
        )
        return [
            SegmentPass(s.id, "indeterminado", None, None, 0.0, 0.0, km_increasing, why)
            for s in inside
        ]

    # Baipases que quedan enteros entre las dos paradas: el tren no para ni sale de la línea
    # entre sus dos nodos, así que va por ellos y no por los tramos que rodean.
    taken = [
        bp for bp in bypasses if bp.km_from >= lo - KM_TOLERANCE and bp.km_to <= hi + KM_TOLERANCE
    ]

    def along(km: float) -> float:
        """Kilómetros recorridos desde ``lo`` hasta ese kilómetro de la línea, por donde va el tren."""
        return km - lo - sum(bp.saved_km for bp in taken if bp.km_to <= km + KM_TOLERANCE)

    t0 = float(a.call.departure_s)
    t1 = float(b.call.arrival_s)
    leg_time = max(t1 - t0, 0.0)
    on_line_km = along(hi)
    total_km = on_line_km + a.extra_km + b.extra_km
    # tiempo estimado entre los dos puntos de la línea (si una parada está fuera, parte del
    # tiempo se consume fuera de la red)
    share = 1.0 if total_km == 0 else on_line_km / total_km
    t_enter_line = t0 + leg_time * (a.extra_km / total_km if total_km else 0.0)
    t_exit_line = t_enter_line + leg_time * share
    both_on_line = a.on_line and b.on_line
    ratio = IN_NETWORK_MARGIN_RATIO if both_on_line else EXIT_MARGIN_RATIO
    min_margin = IN_NETWORK_MARGIN_MIN_S if both_on_line else EXIT_MARGIN_MIN_S
    # Con una parada en la línea, el margen crece con el tiempo que el tren pasa en ella desde esa
    # parada. Si cruza sin parar, la hora publicada más cercana queda fuera: cuenta el mayor de
    # los dos tiempos exteriores, que es el margen que las líneas vecinas dan a esos enlaces.
    uncertain_s = (
        max(t_enter_line - t0, t1 - t_exit_line) if crossing else t_exit_line - t_enter_line
    )
    margin = max(min_margin, ratio * uncertain_s)

    def time_at(done_km: float) -> float:
        frac = 0.0 if on_line_km == 0 else done_km / on_line_km
        if not km_increasing:
            frac = 1.0 - frac
        return t_enter_line + frac * (t_exit_line - t_enter_line)

    # Lo que el tren recorre entre las dos paradas, tramo a tramo: su id, los kilómetros hechos
    # desde ``lo`` a su principio y a su final, si su kilometraje va en el sentido del de la línea
    # y, en los de un baipás, la frase que lo explica.
    stretches: list[tuple[str, float, float, bool, str]] = [
        (s.id, along(s.km_from), along(s.km_to), True, "")
        for s in inside
        if not any(
            s.km_from >= bp.km_from - KM_TOLERANCE and s.km_to <= bp.km_to + KM_TOLERANCE
            for bp in taken
        )
    ]
    for bp in taken:
        base = along(bp.km_from)
        stretches.extend(
            (p.segment_id, base + p.km_from, base + p.km_to, p.same_direction, bp.note)
            for p in bp.pieces
        )
    done_a, done_b = (0.0, on_line_km) if km_increasing else (on_line_km, 0.0)
    # En un enlace, la parada del lado de la otra línea es el motivo de que el tren vaya por él.
    why_link = ""
    if link_far_node is not None:
        if a.exit_node is not None and a.exit_node.id == link_far_node:
            why_link = f"Viene de {a.call.stop_name}: por eso va por aquí."
        elif b.exit_node is not None and b.exit_node.id == link_far_node:
            why_link = f"Va a {b.call.stop_name}: por eso va por aquí."

    passes = []
    for segment_id, done_lo, done_hi, same_direction, note in stretches:
        first, last = (done_lo, done_hi) if km_increasing else (done_hi, done_lo)
        enter, exit_ = time_at(first), time_at(last)
        enter_pub = a.on_line and abs(first - done_a) <= KM_TOLERANCE
        exit_pub = b.on_line and abs(last - done_b) <= KM_TOLERANCE
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
            elif crossing:
                basis = _crossing_basis(a, b, on_line_km, margin)
            else:
                basis = _outside_basis(a, b, on_line_km, margin)
        passes.append(
            SegmentPass(
                segment_id=segment_id,
                kind=kind,
                enter_s=enter,
                exit_s=exit_,
                enter_margin_s=0.0 if enter_pub else margin,
                exit_margin_s=0.0 if exit_pub else margin,
                km_increasing=km_increasing if same_direction else not km_increasing,
                basis=f"{note or why_link} {basis}" if note or why_link else basis,
            )
        )
    return passes


def _outside_basis(a: _Anchor, b: _Anchor, on_line_km: float, margin: float) -> str:
    """Explica un reparto en el que una de las dos paradas no está en esta línea."""
    outside = b if not b.on_line else a
    t0, t1 = _fmt(a.call.departure_s), _fmt(b.call.arrival_s)
    minutes = int(margin // 60)
    if outside.exit_node is not None and outside.call.exit_note is None and outside.extra_how:
        verb = "sale de" if outside is b else "entra en"
        return (
            f"Estimado: {outside.call.stop_name} está fuera de la red cargada; el tren {verb}"
            f" esta línea por {outside.exit_node.label}. El reparto entre {a.call.stop_name}"
            f" ({t0}) y {b.call.stop_name} ({t1}) usa {on_line_km:.0f} km por la línea y, desde"
            f" {outside.exit_node.label}, {outside.extra_how}; margen de ±{minutes} min."
        )
    if outside.call.exit_note is None or outside.exit_node is None:
        return (
            f"Estimado: {outside.call.stop_name} está fuera de la red cargada, así que el reparto"
            f" entre {a.call.stop_name} ({t0}) y {b.call.stop_name} ({t1}) usa la distancia en"
            f" línea recta; margen de ±{minutes} min."
        )
    verb = "sale de" if outside is b else "entra en"
    how = outside.extra_how or (
        f"{outside.extra_km:.0f} km en línea recta hasta {outside.call.stop_name}"
    )
    return (
        f"Estimado: {outside.call.stop_name} {outside.call.exit_note}; el tren {verb} esta línea"
        f" por {outside.exit_node.label}. El reparto entre {a.call.stop_name} ({t0}) y"
        f" {b.call.stop_name} ({t1}) usa {on_line_km:.0f} km por la línea y, desde"
        f" {outside.exit_node.label}, {how}; margen de ±{minutes} min."
    )


def _crossing_basis(a: _Anchor, b: _Anchor, on_line_km: float, margin: float) -> str:
    """Explica el paso de un tren que cruza la línea sin parar, entre paradas de otras líneas."""
    assert a.exit_node is not None and b.exit_node is not None
    t0, t1 = _fmt(a.call.departure_s), _fmt(b.call.arrival_s)
    where = " y ".join(
        f"{x.call.stop_name} {x.call.exit_note}" for x in (a, b) if x.call.exit_note is not None
    )
    outside = " y ".join(
        f"{x.call.stop_name} está fuera de la red cargada"
        for x in (a, b)
        if not x.along_loaded_lines
    )
    before = "" if a.along_loaded_lines else " en línea recta"
    after = "" if b.along_loaded_lines else " en línea recta"
    return (
        f"Estimado: este tren recorre la línea sin parar en ella; entra por {a.exit_node.label}"
        f" y sale por {b.exit_node.label}.{f' {where}.' if where else ''}"
        f"{f' {outside}.' if outside else ''} El reparto entre"
        f" {a.call.stop_name} ({t0}) y"
        f" {b.call.stop_name} ({t1}) usa {a.extra_km:.0f} km{before} antes de"
        f" {a.exit_node.label}, {on_line_km:.0f} km por la línea y {b.extra_km:.0f} km{after}"
        f" después de {b.exit_node.label}; margen de ±{int(margin // 60)} min."
    )
