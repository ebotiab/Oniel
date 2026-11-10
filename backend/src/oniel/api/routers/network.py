from __future__ import annotations

import datetime as dt
from typing import Annotated

from fastapi import APIRouter, Query

from oniel.api.deps import ConnectionDep
from oniel.domain.schemas import CoverageOut, InterruptionOut, NetworkOut, Source
from oniel.repo import network_repo, services_repo

router = APIRouter(tags=["red"])


@router.get("/network")
async def get_network(conn: ConnectionDep) -> NetworkOut:
    return await network_repo.fetch_network(conn)


@router.get("/coverage")
async def get_coverage(conn: ConnectionDep) -> CoverageOut:
    return await network_repo.fetch_coverage(conn)


@router.get("/sources")
async def get_sources(conn: ConnectionDep) -> list[Source]:
    return await network_repo.fetch_sources(conn)


@router.get("/interruptions")
async def get_interruptions(
    conn: ConnectionDep,
    date: Annotated[
        dt.date | None,
        Query(description="Solo las vigentes ese día; sin él, todas las registradas"),
    ] = None,
) -> list[InterruptionOut]:
    """Interrupciones del servicio registradas, con sus tramos, fechas y fuentes."""
    return await network_repo.fetch_interruptions(conn, day=date)


@router.get("/segment-counts")
async def get_segment_counts(
    conn: ConnectionDep,
    date: Annotated[
        dt.date | None, Query(description="Día de servicio; por defecto el de referencia")
    ] = None,
) -> dict[str, object]:
    day = date
    if day is None:
        _, _, day = await network_repo.feed_bounds(conn)
    day = day or dt.date.today()
    return {"date": day.isoformat(), "counts": await services_repo.daily_counts(conn, day)}
