from __future__ import annotations

from fastapi import APIRouter, HTTPException

from oniel.api.deps import ConnectionDep
from oniel.domain.schemas import ServiceDetail
from oniel.repo import services_repo

router = APIRouter(prefix="/services", tags=["servicios"])


@router.get("/{service_id}")
async def get_service(service_id: str, conn: ConnectionDep) -> ServiceDetail:
    found = await services_repo.fetch_service(conn, service_id)
    if found is None:
        raise HTTPException(404, f"No hay ningún servicio con id {service_id}")
    service, stops = found
    return ServiceDetail(**service.model_dump(), stops=stops)
