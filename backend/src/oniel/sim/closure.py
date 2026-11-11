"""Cierre hipotético de un tramo en una ventana horaria.

Comparamos la ventana con el intervalo en que cada tren ocupa el tramo:

* Si ni siquiera con los márgenes se tocan → **no afectado**.
* Si se solapan incluso descontando los márgenes → **afectado** (publicado o estimado según el
  origen del dato).
* Si solo se tocan dentro del margen de incertidumbre, o el recorrido no se pudo fijar →
  **indeterminado**.

El recorrido alternativo sale del grafo de rutas (``oniel.routing``): un cierre es un escenario
de una modificación, y sus alternativas son los rodeos que salvan el tramo por otras líneas.
"""

from __future__ import annotations

import datetime as dt
from dataclasses import dataclass
from typing import Literal

from oniel.domain.interruptions import alternative_note
from oniel.domain.schemas import ClosureAlternative, InterruptionOut
from oniel.routing import Graph, Route, Scenario, closure_detours
from oniel.sim.passes import SegmentPass

Status = Literal["afectado_publicado", "afectado_estimado", "indeterminado", "no_afectado"]

DAY_S = 86_400


@dataclass(frozen=True)
class ClosureWindow:
    """Ventana en segundos desde la medianoche del día simulado (puede pasar de 86 400)."""

    start_s: int
    end_s: int

    @classmethod
    def from_times(cls, start: dt.time, end: dt.time) -> ClosureWindow:
        s = start.hour * 3600 + start.minute * 60 + start.second
        e = end.hour * 3600 + end.minute * 60 + end.second
        if e <= s:
            e += DAY_S  # la ventana termina al día siguiente
        return cls(s, e)

    @property
    def duration_s(self) -> int:
        return self.end_s - self.start_s


@dataclass(frozen=True)
class Verdict:
    status: Status
    explanation: str


def classify(p: SegmentPass, window: ClosureWindow, day_offset_s: int = 0) -> Verdict:
    """Clasifica el paso de un tren. ``day_offset_s`` desplaza trenes del día anterior (-86400)."""
    if p.kind == "indeterminado" or p.enter_s is None or p.exit_s is None:
        return Verdict("indeterminado", p.basis)
    enter, exit_ = p.enter_s + day_offset_s, p.exit_s + day_offset_s
    outer_lo, outer_hi = enter - p.enter_margin_s, exit_ + p.exit_margin_s
    inner_lo, inner_hi = enter + p.enter_margin_s, exit_ - p.exit_margin_s
    if inner_hi < inner_lo:  # el margen se come el intervalo: usamos el punto medio
        inner_lo = inner_hi = (enter + exit_) / 2
    if outer_hi <= window.start_s or outer_lo >= window.end_s:
        return Verdict(
            "no_afectado",
            f"Ocupa el tramo entre {_fmt(enter)} y {_fmt(exit_)}, fuera de la ventana. {p.basis}",
        )
    if inner_hi > window.start_s and inner_lo < window.end_s:
        status: Status = "afectado_publicado" if p.kind == "publicado" else "afectado_estimado"
        return Verdict(
            status,
            f"Ocupa el tramo entre {_fmt(enter)} y {_fmt(exit_)}, dentro de la ventana. {p.basis}",
        )
    return Verdict(
        "indeterminado",
        f"Su paso ({_fmt(enter)}–{_fmt(exit_)}) solo coincide con la ventana dentro del margen de"
        f" incertidumbre. {p.basis}",
    )


def _fmt(seconds: float) -> str:
    seconds = int(round(seconds)) % (2 * DAY_S)
    h, rem = divmod(seconds, 3600)
    return f"{h % 24:02d}:{rem // 60:02d}"


def alternatives(
    graph: Graph,
    segment_id: str,
    interruptions: list[InterruptionOut] | None = None,
    scenario: Scenario | None = None,
) -> list[ClosureAlternative]:
    """Recorridos alternativos al tramo cerrado, del más corto al más largo.

    Cada uno sale de la línea del tramo por un nodo anterior al cierre y vuelve a ella por uno
    posterior, por una línea o por varias encadenadas (``closure_detours``). ``interruptions``
    son las vigentes el día simulado: cada alternativa lleva las que caen en su recorrido.
    """
    out: list[ClosureAlternative] = []
    for detour in closure_detours(graph, segment_id, scenario):
        route = detour.route
        used = set(route.segment_ids)
        blocking = [i for i in interruptions or [] if used.intersection(i.segment_ids)]
        note = (
            f"Recorrido alternativo cargado en Oniel entre {route.from_name} y {route.to_name}:"
            f" {route.length_km:.0f} km {_by_lines(route)} frente a"
            f" {detour.closed_line_length_km:.0f} km por la línea cerrada."
        )
        if route.single_track_km > 0:
            note += f" Incluye {route.single_track_km:.0f} km de vía única."
        note += (
            " Oniel no reasigna los trenes afectados a esta alternativa; solo señala que existe."
        )
        for i in blocking:
            publisher = i.sources[0].publisher if i.sources else "fuente sin registrar"
            note += alternative_note(i.from_name, i.to_name, i.start_date, publisher)
        first = route.legs[0]
        out.append(
            ClosureAlternative(
                line_id=first.line_id or "",
                line_name=first.line_name,
                from_node_id=route.from_node_id,
                from_name=route.from_name,
                to_node_id=route.to_node_id,
                to_name=route.to_name,
                length_km=route.length_km,
                closed_line_length_km=detour.closed_line_length_km,
                via=route.via,
                single_track_km=route.single_track_km,
                note=note,
                interruptions=blocking,
                line_ids=route.line_ids,
                legs=route.legs,
                time_min=route.time_min,
                segment_ids=route.segment_ids,
            )
        )
    return out


def _by_lines(route: Route) -> str:
    """«por la línea X» o «por la línea X hasta N y por la línea Y»."""
    parts = [
        f"por {_article(leg.line_name)}"
        + (f" hasta {leg.to_name}" if i < len(route.legs) - 1 else "")
        for i, leg in enumerate(route.legs)
    ]
    return ", ".join(parts[:-1]) + (" y " if len(parts) > 1 else "") + parts[-1]


def _article(line_name: str) -> str:
    """«la línea convencional…» para una línea; «un enlace esbozado» para un enlace."""
    lowered = line_name[0].lower() + line_name[1:]
    return f"la {lowered}" if lowered.startswith("línea") else f"un {lowered}"
