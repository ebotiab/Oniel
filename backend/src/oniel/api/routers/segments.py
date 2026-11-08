from __future__ import annotations

import datetime as dt
from typing import Annotated

import asyncpg
from fastapi import APIRouter, HTTPException, Query

from oniel.api.deps import ConnectionDep
from oniel.domain.schemas import SegmentOut, SegmentPassOut, SegmentServicesOut
from oniel.repo import network_repo, services_repo
from oniel.sim.service import direction_label, shifted_times

router = APIRouter(prefix="/segments", tags=["tramos"])

DateQuery = Annotated[
    dt.date | None,
    Query(description="Día de servicio; por defecto, el día de referencia del horario"),
]


async def _segment_or_404(conn: asyncpg.Connection, segment_id: str) -> SegmentOut:
    segment = await network_repo.fetch_segment(conn, segment_id)
    if segment is None:
        raise HTTPException(404, f"No hay ningún tramo con id {segment_id}")
    return segment


async def resolve_date(conn: asyncpg.Connection, date: dt.date | None) -> dt.date:
    if date is not None:
        return date
    _, _, ref = await network_repo.feed_bounds(conn)
    return ref or dt.date.today()


@router.get("/{segment_id}")
async def get_segment(segment_id: str, conn: ConnectionDep) -> SegmentOut:
    return await _segment_or_404(conn, segment_id)


@router.get("/{segment_id}/services")
async def get_segment_services(
    segment_id: str, conn: ConnectionDep, date: DateQuery = None
) -> SegmentServicesOut:
    segment = await _segment_or_404(conn, segment_id)
    day = await resolve_date(conn, date)
    dated = await services_repo.passes_on_segment(conn, segment.id, day)
    passes = []
    counts: dict[str, int] = {"publicado": 0, "estimado": 0, "indeterminado": 0}
    for d in dated:
        enter, exit_ = shifted_times(d.segment_pass, d.from_previous_day)
        counts[d.segment_pass.kind] += 1
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
    return SegmentServicesOut(segment=segment, date=day, passes=passes, counts=counts)
