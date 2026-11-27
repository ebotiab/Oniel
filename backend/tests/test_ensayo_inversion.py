"""Ensayo de cinco nodos de #322. Como script entrega al visor las respuestas de GET /api/routes."""

from __future__ import annotations

import asyncio
import json
from dataclasses import dataclass, replace
from typing import Any, Literal
from unittest.mock import AsyncMock, patch

from fastapi import FastAPI
from httpx import ASGITransport, AsyncClient
from pydantic import BaseModel

from oniel.api.deps import get_connection
from oniel.api.routers import routes
from oniel.domain.schemas import LineSummary, NodeOut, SegmentOut
from oniel.repo import network_repo
from oniel.routing import build_graph

# PK en metros. Las velocidades son ficticias y solo sirven para comprobar la paridad.
LINES = {
    "entrada": [("origen", 0), ("este", 85702), ("parada", 87840)],
    "salida": [("parada", 0), ("oeste", 2102), ("destino", 93801)],
    "atajo": [("este", 0), ("oeste", 1011)],
}
SEGMENTS = {
    "entrada": [("acceso", 200), ("anden-este", 90)],
    "salida": [("anden-oeste", 90), ("salida", 200)],
    "atajo": [("directo", 50)],
}


class Red(BaseModel):
    lines: list[LineSummary]
    nodes: list[NodeOut]
    segments: list[SegmentOut]
    turns: dict[str, dict[str, int]]


def red(variante: str) -> Red:
    lines = []
    nodes = []
    segments = []
    for line_id, stops in LINES.items():
        options: dict[str, str] = {}
        if line_id == "atajo":
            options["link_of"] = "salida"
            if variante == "orientado":
                options["link_towards"] = "destino"
            elif variante != "sin permiso":
                options["link_reversal_at"] = "parada"
        lines.append(
            LineSummary.model_validate(
                dict(
                    id=line_id,
                    name=line_id,
                    mode="convencional",
                    status="disponible",
                    length_km=stops[-1][1] / 1000,
                    node_count=len(stops),
                    segment_count=len(stops) - 1,
                    **options,
                )
            )
        )
        for seq, (node_id, metres) in enumerate(stops):
            kind: Literal["estacion", "bifurcacion"] = "estacion"
            if node_id in ("este", "oeste") or (node_id == "parada" and variante == "bifurcación"):
                kind = "bifurcacion"
            nodes.append(
                NodeOut(
                    id=node_id,
                    name=node_id.capitalize(),
                    kind=kind,
                    lon=0,
                    lat=0,
                    line_id=line_id,
                    km=metres / 1000,
                    seq=seq,
                )
            )
            if seq:
                previous, start = stops[seq - 1]
                segment, speed = SEGMENTS[line_id][seq - 1]
                segments.append(
                    SegmentOut(
                        id=segment,
                        line_id=line_id,
                        seq=seq,
                        from_node_id=previous,
                        to_node_id=node_id,
                        from_name=previous.capitalize(),
                        to_name=node_id.capitalize(),
                        km_from=start / 1000,
                        km_to=metres / 1000,
                        length_km=(metres - start) / 1000,
                        typical_speed_kmh=speed,
                        tracks=1,
                        status="disponible",
                    )
                )
    turns = {
        "este": {"acceso": 0, "anden-este": 1, "directo": 1},
        "oeste": {"salida": 0, "anden-oeste": 1, "directo": 1},
    }
    if variante == "bifurcación":
        turns["parada"] = {"anden-este": 0, "anden-oeste": 0}
    return Red(lines=lines, nodes=nodes, segments=segments, turns=turns)


@dataclass(frozen=True)
class Camino:
    nodos: str
    tramos: str
    km: float
    minutos: int
    inversiones: tuple[str, ...] = ()


DIRECTO = Camino("origen este oeste destino", "acceso directo salida", 178.4, 54)
ESTACION = Camino(
    "origen este parada oeste destino", "acceso anden-este anden-oeste salida", 181.6, 56
)
ENTRADA = Camino("origen este parada", "acceso anden-este", 87.8, 27)
SALIDA = Camino("parada oeste destino", "anden-oeste salida", 93.8, 29)


async def medir(variante: str) -> dict[str, Any]:
    network = red(variante)
    graph = build_graph(network.lines, network.nodes, network.segments, network.turns)
    # Se sustituye solo la lectura del grafo. FastAPI recibe parámetros HTTP y serializa la ruta real.
    app = FastAPI()
    app.include_router(routes.router, prefix="/api")
    app.dependency_overrides[get_connection] = lambda: None
    casos: list[dict[str, Any]] = []

    async def comprobar(desde: str, hasta: str, escenario: str, caminos: list[Camino]) -> None:
        for vuelta in (False, True):
            inicio, fin = (hasta, desde) if vuelta else (desde, hasta)
            params = {"from": inicio, "to": fin}
            if escenario:
                params["scenario"] = escenario
            response = await client.get("/api/routes", params=params)
            response.raise_for_status()
            body = response.json()
            assert (body["max_changes"], body["max_ratio"]) == (None, 2)
            recibidos = body["routes"]
            for ruta in recibidos:
                assert ruta.pop("interruptions") == []
            sentido = -1 if vuelta else 1
            assert [
                (
                    r["node_ids"],
                    r["segment_ids"],
                    r["length_km"],
                    r["time_min"],
                    r["reverse_node_ids"],
                )
                for r in recibidos
            ] == [
                (
                    c.nodos.split()[::sentido],
                    c.tramos.split()[::sentido],
                    c.km,
                    c.minutos,
                    list(c.inversiones),
                )
                for c in caminos
            ], (variante, params, recibidos)
            casos.append(dict(desde=inicio, hasta=fin, escenario=escenario, rutas=recibidos))

    with patch.object(network_repo, "fetch_graph", AsyncMock(return_value=graph)):
        async with AsyncClient(
            transport=ASGITransport(app=app), base_url="http://ensayo"
        ) as client:
            por_estacion = (
                [replace(ESTACION, inversiones=("parada",))] if variante == "habilitada" else []
            )
            await comprobar("origen", "destino", "", [DIRECTO, *por_estacion])
            await comprobar(
                "origen",
                "destino",
                "c~directo",
                [ESTACION] if variante == "orientado" else por_estacion,
            )
            for brazo in ("anden-este", "anden-oeste"):
                await comprobar("origen", "destino", f"c~{brazo}", [DIRECTO])
            if variante == "habilitada":
                # Un viaje entre las propias agujas también excede el doble en el total.
                await comprobar("este", "oeste", "", [Camino("este oeste", "directo", 1.0, 1)])
                # Una vía ajena al triángulo sigue midiendo el rodeo por su parte distinta.
                supuesto = Camino(
                    "origen este oeste destino", "acceso enlace:este:oeste salida", 177.9, 54
                )
                await comprobar("origen", "destino", "e~este~oeste~0.5~100", [supuesto])
                await comprobar("origen", "parada", "", [ENTRADA])
                await comprobar("parada", "destino", "", [SALIDA])
                # Se cierra el brazo legal. Cada aguja queda como única esquina posible hacia el andén.
                await comprobar("este", "parada", "c~anden-este", [])
                await comprobar("oeste", "parada", "c~anden-oeste", [])
    return dict(
        variante=variante,
        red=network.model_dump(),
        casos=casos,
    )


VARIANTES = ("habilitada", "sin permiso", "bifurcación", "orientado")


async def test_consulta_ordinaria_y_cierres_en_ambos_sentidos() -> None:
    for variante in VARIANTES:
        await medir(variante)


if __name__ == "__main__":
    print(json.dumps([asyncio.run(medir(variante)) for variante in VARIANTES]))
