from __future__ import annotations

from fastapi import APIRouter, HTTPException

from oniel.api.deps import ConnectionDep
from oniel.domain.schemas import ClosureRequest, ClosureResult
from oniel.repo import network_repo
from oniel.routing import ScenarioError
from oniel.sim.service import simulate_closure

router = APIRouter(prefix="/simulations", tags=["simulaciones"])


@router.post("/closure")
async def post_closure(req: ClosureRequest, conn: ConnectionDep) -> ClosureResult:
    segment = await network_repo.fetch_segment(conn, req.segment_id)
    if segment is None:
        raise HTTPException(404, f"No hay ningún tramo con id {req.segment_id}")
    try:
        return await simulate_closure(conn, segment, req)
    except ScenarioError as exc:
        raise HTTPException(422, f"Escenario no válido: {exc}") from exc
