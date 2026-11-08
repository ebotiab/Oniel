"""Cierre hipotético de un tramo en una ventana horaria.

Comparamos la ventana con el intervalo en que cada tren ocupa el tramo:

* Si ni siquiera con los márgenes se tocan → **no afectado**.
* Si se solapan incluso descontando los márgenes → **afectado** (publicado o estimado según el
  origen del dato).
* Si solo se tocan dentro del margen de incertidumbre, o el recorrido no se pudo fijar →
  **indeterminado**.
"""

from __future__ import annotations

import datetime as dt
from dataclasses import dataclass
from typing import Literal

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
