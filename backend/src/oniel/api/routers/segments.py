from __future__ import annotations

import datetime as dt
from typing import Annotated

import asyncpg
from fastapi import APIRouter, HTTPException, Query

from oniel.api.deps import ConnectionDep
from oniel.domain.schemas import (
    SegmentOut,
    SegmentServicesOut,
    ServiceHistoryOut,
)
from oniel.repo import network_repo, services_repo
from oniel.sim.service import public_passes

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
    passes, counts = public_passes(
        segment, await services_repo.passes_on_segment(conn, segment.id, day)
    )
    return SegmentServicesOut(
        segment=segment,
        date=day,
        passes=passes,
        counts=counts,
        interruptions=await network_repo.fetch_interruptions(conn, day=day, segment_id=segment.id),
    )


@router.get("/{segment_id}/history")
async def get_segment_history(segment_id: str, conn: ConnectionDep) -> ServiceHistoryOut:
    """Trenes que recorren el tramo según cada fichero de horarios, en el día de referencia de cada uno."""
    segment = await _segment_or_404(conn, segment_id)
    return ServiceHistoryOut(
        id=segment.id, points=await services_repo.segment_history(conn, segment.id)
    )
