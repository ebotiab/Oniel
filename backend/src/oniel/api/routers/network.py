from __future__ import annotations

import datetime as dt
from typing import Annotated

from fastapi import APIRouter, HTTPException, Query

from oniel.api.deps import ConnectionDep
from oniel.domain.schemas import (
    CoverageOut,
    InterruptionOut,
    LineDetailOut,
    NetworkIndexOut,
    NetworkOut,
    Source,
)
from oniel.repo import network_repo, services_repo

router = APIRouter(tags=["red"])


@router.get("/network")
async def get_network(conn: ConnectionDep) -> NetworkOut:
    return await network_repo.fetch_network(conn)


@router.get("/lines")
async def get_lines(conn: ConnectionDep) -> NetworkIndexOut:
    """Índice ligero de la red: líneas, nodos sin textos y tramos con la geometría simplificada."""
    return await network_repo.fetch_index(conn)


@router.get("/lines/{line_id}")
async def get_line(
    conn: ConnectionDep,
    line_id: str,
    date: Annotated[
        dt.date | None,
        Query(description="Día de los recuentos por tramo; por defecto el de referencia"),
    ] = None,
) -> LineDetailOut:
    """El detalle de una línea: nodos, tramos, geometría completa y pasos por tramo."""
    detail = await network_repo.fetch_line_detail(conn, line_id, date)
    if detail is None:
        raise HTTPException(status_code=404, detail="Línea no encontrada")
    return detail


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
    """Pasos por tramo un día: el total (``counts``) y su reparto por operador (``by_operator``)."""
    day = date
    if day is None:
        _, _, day = await network_repo.feed_bounds(conn)
    day = day or dt.date.today()
    return {
        "date": day.isoformat(),
        "counts": await services_repo.daily_counts(conn, day),
        "by_operator": await services_repo.daily_counts_by_operator(conn, day),
    }
