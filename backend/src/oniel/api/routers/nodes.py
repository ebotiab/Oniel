from __future__ import annotations

from fastapi import APIRouter, HTTPException

from oniel.api.deps import ConnectionDep
from oniel.api.routers.segments import DateQuery, resolve_date
from oniel.domain.schemas import NodeOut, NodeServicesOut
from oniel.repo import network_repo, services_repo

router = APIRouter(prefix="/nodes", tags=["nodos"])


@router.get("/{node_id}")
async def get_node(node_id: str, conn: ConnectionDep) -> NodeOut:
    node = await network_repo.fetch_node(conn, node_id)
    if node is None:
        raise HTTPException(404, f"No hay ningún nodo con id {node_id}")
    return node


@router.get("/{node_id}/services")
async def get_node_services(
    node_id: str, conn: ConnectionDep, date: DateQuery = None
) -> NodeServicesOut:
    node = await network_repo.fetch_node(conn, node_id)
    if node is None:
        raise HTTPException(404, f"No hay ningún nodo con id {node_id}")
    day = await resolve_date(conn, date)
    return NodeServicesOut(
        node=node, date=day, calls=await services_repo.calls_at_node(conn, node_id, day)
    )
