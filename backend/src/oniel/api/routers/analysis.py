from __future__ import annotations

import datetime as dt
from typing import Annotated

from fastapi import APIRouter, Query

from oniel.api.deps import ConnectionDep
from oniel.domain.schemas import AlternativesOut
from oniel.repo import network_repo

router = APIRouter(tags=["análisis"])


@router.get("/alternatives")
async def get_alternatives(
    conn: ConnectionDep,
    date: Annotated[
        dt.date | None,
        Query(description="Día de servicio; por defecto, el día de referencia del horario"),
    ] = None,
) -> AlternativesOut:
    """Trenes por tramo y si las líneas cargadas les ofrecen otro camino con el tramo cortado."""
    return await network_repo.fetch_segment_alternatives(conn, date)
