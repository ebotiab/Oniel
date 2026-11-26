"""Orquesta una simulación de cierre con datos de la base."""

from __future__ import annotations

from collections import Counter
from typing import Any

import asyncpg
import logfire

from oniel.domain.schemas import (
    ClosureRequest,
    ClosureResult,
    ClosureResultItem,
    SegmentOut,
    SegmentPassOut,
)
from oniel.repo.datasets_repo import fetch_datasets
from oniel.repo.network_repo import fetch_graph, fetch_interruptions, fetch_operators, fetch_sources
from oniel.repo.services_repo import DatedPass, fmt_time, passes_on_segment
from oniel.routing import Scenario
from oniel.sim.closure import DAY_S, ClosureWindow, alternatives, classify
from oniel.sim.passes import SegmentPass

METHOD = (
    "Para cada tren que recorre el tramo ese día comparamos la ventana de cierre con el intervalo"
    " en que ocupa el tramo. Si el tren para en las dos estaciones que lo delimitan, el intervalo"
    " sale del horario publicado. Si no, lo estimamos repartiendo el tiempo entre sus paradas en"
    " proporción a la distancia, con un margen del 15 % (mínimo 3 minutos), o del 30 % (mínimo"
    " 5 minutos) cuando una parada está fuera de la línea: en otra línea cargada, y entonces la"
    " distancia se mide por ella, o fuera de la red, y se mide en línea recta. Un tren cuenta"
    " como afectado si el solape existe incluso descontando el margen; si solo coincide dentro"
    " del margen, o no se puede fijar su recorrido, queda indeterminado."
)

CAVEATS = [
    "El cálculo usa horarios planificados de viajeros. Quedan fuera los trenes de mercancías y"
    " los cambios de última hora por obras o interrupciones.",
    "El cierre se supone de todas las vías del tramo y no se calcula ningún desvío ni"
    " reordenación de trenes.",
]

INTERRUPTED_CAVEAT = (
    "En la fecha simulada el tramo ya tiene una interrupción real registrada: los trenes de la"
    " lista figuran en el horario publicado, pero no circulan por él."
)

ALTERNATIVE_CAVEAT = (
    "Cuando otras líneas cargadas, una sola o varias encadenadas, unen dos nodos situados a ambos"
    " lados del tramo, Oniel señala ese recorrido alternativo, pero no estima qué trenes podrían"
    " desviarse ni con qué horario."
)


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


async def timetable_credits(conn: asyncpg.Connection, used: set[tuple[str, str]]) -> list[str]:
    """Cita la fuente del conjunto de cada servicio que aparece en la simulación."""
    if not used:
        return ["No hay servicios en los horarios consultados para este tramo y esta fecha."]
    dataset_sources = {d.id: d.source_id for d in await fetch_datasets(conn)}
    source_names = {s.id: s.name for s in await fetch_sources(conn)}
    operator_names = {o.id: o.name for o in await fetch_operators(conn)}
    # Dos versiones del mismo horario pueden intervenir a uno y otro lado de la medianoche.
    credits = {
        (operator_names[operator_id], source_names[dataset_sources[dataset_id]])
        for operator_id, dataset_id in used
    }
    return [f"El horario de {name} procede de «{source}»." for name, source in sorted(credits)]


def public_passes(
    segment: SegmentOut, dated: list[DatedPass]
) -> tuple[list[SegmentPassOut], dict[str, int]]:
    """La ficha y la API cuentan los recorridos del día y comparten el mismo detalle horario."""
    passes = []
    counts: dict[str, int] = {"publicado": 0, "estimado": 0, "indeterminado": 0}
    for d in dated:
        counts[d.segment_pass.kind] += 1
        if segment.station_closure:
            continue
        enter, exit_ = shifted_times(d.segment_pass, d.from_previous_day)
        passes.append(
            SegmentPassOut(
                service=d.service,
                kind=d.segment_pass.kind,
                enter=enter,
                exit=exit_,
                enter_margin_min=round(d.segment_pass.enter_margin_s / 60, 1),
                exit_margin_min=round(d.segment_pass.exit_margin_s / 60, 1),
                km_increasing=d.segment_pass.km_increasing,
                direction_label=direction_label(segment, d.segment_pass.km_increasing),
                basis=d.segment_pass.basis,
            )
        )
    return passes, counts


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
        dated: list[DatedPass] = await passes_on_segment(
            conn,
            segment.id,
            req.date,
            with_previous_day=True,
            next_day_until_s=max(0, window.end_s - DAY_S),
        )
        # El cierre es un escenario de una modificación sobre el grafo de todas las líneas.
        active = await fetch_interruptions(conn, day=req.date)
        detours, omitted = alternatives(
            await fetch_graph(conn), segment.id, active, Scenario.from_code(req.scenario)
        )
        interruptions = [i for i in active if segment.id in i.segment_ids]
        items: list[ClosureResultItem] = []
        counts: Counter[str] = Counter()
        used_timetables: set[tuple[str, str]] = set()
        for d in dated:
            verdict = classify(d.segment_pass, window, DAY_S * d.day_offset)
            # La ficha cuenta los trenes que salen el día elegido. De los días contiguos solo
            # se añaden los pasos que alcanza la franja, incluidos sus márgenes de incertidumbre.
            if d.day_offset and verdict.status == "no_afectado":
                continue
            used_timetables.add((d.service.operator_id, d.dataset_id))
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
                    from_next_day=d.day_offset == 1,
                )
            )
        order = {
            "afectado_publicado": 0,
            "afectado_estimado": 1,
            "indeterminado": 2,
            "no_afectado": 3,
        }
        # Los pasos ya vienen en orden cronológico, incluidas las horas de los días contiguos.
        items.sort(key=lambda i: order[i.status])
        for key in order:
            counts.setdefault(key, 0)
        summary: dict[str, Any] = {
            **counts,
            "trains": len(items),
            "interrupted": bool(interruptions),
        }
        logfire.info("closure simulated", **summary)
        end_label = req.end.strftime("%H:%M") + (
            " del día siguiente" if window.end_s >= 86400 else ""
        )
        return ClosureResult(
            request=req,
            segment=segment,
            window_label=f"{req.date.strftime('%d/%m/%Y')} de {req.start.strftime('%H:%M')} a {end_label}",
            counts=dict(counts),
            items=items,
            alternatives=detours,
            omitted_alternatives=omitted,
            interruptions=interruptions,
            method=METHOD,
            caveats=[
                *await timetable_credits(conn, used_timetables),
                *CAVEATS,
                *([INTERRUPTED_CAVEAT] if interruptions else []),
                *([ALTERNATIVE_CAVEAT] if detours else []),
            ],
        )
