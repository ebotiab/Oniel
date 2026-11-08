"""Orquesta una simulación de cierre con datos de la base."""

from __future__ import annotations

from collections import Counter

import asyncpg
import logfire

from oniel.domain.schemas import ClosureRequest, ClosureResult, ClosureResultItem, SegmentOut
from oniel.repo.services_repo import DatedPass, fmt_time, passes_on_segment
from oniel.sim.closure import ClosureWindow, classify
from oniel.sim.passes import SegmentPass

METHOD = (
    "Para cada tren que recorre el tramo ese día comparamos la ventana de cierre con el intervalo"
    " en que ocupa el tramo. Si el tren para en las dos estaciones que lo delimitan, el intervalo"
    " sale del horario publicado. Si no, lo estimamos repartiendo el tiempo entre sus paradas en"
    " proporción a la distancia, con un margen del 15 % (mínimo 3 minutos), o del 30 % (mínimo"
    " 5 minutos) cuando una parada está fuera de la red cargada. Un tren cuenta como afectado si"
    " el solape existe incluso descontando el margen; si solo coincide dentro del margen, o no se"
    " puede fijar su recorrido, queda indeterminado."
)

CAVEATS = [
    "Los horarios son los publicados por Renfe en su GTFS; no incluyen interrupciones, obras ni"
    " cambios de última hora.",
    "Se consideran solo los servicios de Renfe importados en esta versión; no aparecen otros"
    " operadores ni mercancías.",
    "El cierre se supone de las dos vías y no se calcula ningún desvío ni reordenación de trenes.",
]


def direction_label(segment: SegmentOut, km_increasing: bool | None) -> str:
    if km_increasing is None:
        return "sentido desconocido"
    return (
        f"{segment.from_name} → {segment.to_name}"
        if km_increasing
        else f"{segment.to_name} → {segment.from_name}"
    )


def shifted_times(p: SegmentPass, from_previous_day: bool) -> tuple[str | None, str | None]:
    off = -86400 if from_previous_day else 0
    return (
        fmt_time(p.enter_s + off) if p.enter_s is not None else None,
        fmt_time(p.exit_s + off) if p.exit_s is not None else None,
    )


async def simulate_closure(
    conn: asyncpg.Connection, segment: SegmentOut, req: ClosureRequest
) -> ClosureResult:
    window = ClosureWindow.from_times(req.start, req.end)
    with logfire.span(
        "simulate closure {segment_id} {date} {start}-{end}",
        segment_id=segment.id,
        date=req.date.isoformat(),
        start=req.start.isoformat(),
        end=req.end.isoformat(),
    ):
        dated: list[DatedPass] = await passes_on_segment(conn, segment.id, req.date)
        items: list[ClosureResultItem] = []
        counts: Counter[str] = Counter()
        for d in dated:
            verdict = classify(d.segment_pass, window, -86400 if d.from_previous_day else 0)
            counts[verdict.status] += 1
            enter, exit_ = shifted_times(d.segment_pass, d.from_previous_day)
            items.append(
                ClosureResultItem(
                    service=d.service,
                    status=verdict.status,
                    kind=d.segment_pass.kind,
                    enter=enter,
                    exit=exit_,
                    direction_label=direction_label(segment, d.segment_pass.km_increasing),
                    explanation=verdict.explanation,
                    from_previous_day=d.from_previous_day,
                )
            )
        order = {
            "afectado_publicado": 0,
            "afectado_estimado": 1,
            "indeterminado": 2,
            "no_afectado": 3,
        }
        items.sort(key=lambda i: (order[i.status], i.enter or "", i.service.train_number))
        for key in order:
            counts.setdefault(key, 0)
        logfire.info("closure simulated", **dict(counts), trains=len(items))
        end_label = req.end.strftime("%H:%M") + (
            " del día siguiente" if window.end_s >= 86400 else ""
        )
        return ClosureResult(
            request=req,
            segment=segment,
            window_label=f"{req.date.strftime('%d/%m/%Y')} de {req.start.strftime('%H:%M')} a {end_label}",
            counts=dict(counts),
            items=items,
            method=METHOD,
            caveats=CAVEATS,
        )
