from __future__ import annotations

import datetime as dt
from typing import Annotated

from fastapi import APIRouter, HTTPException, Query

from oniel.api.deps import ConnectionDep
from oniel.domain.schemas import RouteOut, RoutesOut
from oniel.repo import network_repo
from oniel.routing import DEFAULT_MAX_CHANGES, Scenario, ScenarioError, find_routes

router = APIRouter(tags=["rutas"])

METHOD = (
    "Oniel une todas las líneas cargadas en un solo grafo, aplica las modificaciones del"
    " escenario (tramos cerrados, enlaces esbozados, velocidades cambiadas) y busca los recorridos"
    " que no pasan dos veces por el mismo nodo ni cambian de línea más veces de las pedidas. Los"
    " kilómetros se miden por cada línea. El tiempo es el de recorrer cada tramo a su velocidad"
    " habitual, sin paradas, sin acelerar ni frenar y sin esperar cruces en vía única: sirve para"
    " comparar recorridos, no es un horario."
)


@router.get("/routes")
async def get_routes(
    conn: ConnectionDep,
    from_: Annotated[str, Query(alias="from", description="Id del nodo de origen")],
    to: Annotated[str, Query(description="Id del nodo de destino")],
    scenario: Annotated[
        str,
        Query(
            description="Escenario como cadena corta (c~tramo;e~nodo~nodo~km~kmh;v~tramo~kmh)"
            " o como JSON; vacío, la red tal como está cargada"
        ),
    ] = "",
    date: Annotated[
        dt.date | None,
        Query(description="Día para señalar las interrupciones vigentes en cada recorrido"),
    ] = None,
    avoid_interruptions: Annotated[
        bool,
        Query(description="Con fecha: cierra además los tramos interrumpidos ese día"),
    ] = False,
    max_changes: Annotated[
        int, Query(ge=0, le=6, description="Cambios de línea admitidos en un recorrido")
    ] = DEFAULT_MAX_CHANGES,
) -> RoutesOut:
    """Recorridos entre dos nodos con la red de un escenario, del más corto al más largo."""
    graph = await network_repo.fetch_graph(conn)
    for node_id in (from_, to):
        if node_id not in graph.nodes:
            raise HTTPException(404, f"No hay ningún nodo con id {node_id}")
    try:
        parsed = (
            Scenario.model_validate_json(scenario)
            if scenario.lstrip().startswith("{")
            else Scenario.from_code(scenario)
        )
    except ValueError as exc:  # ScenarioError y los errores de validación de Pydantic
        raise HTTPException(422, f"Escenario no válido: {exc}") from exc
    active = await network_repo.fetch_interruptions(conn, day=date) if date else []
    if avoid_interruptions:
        parsed = parsed.with_closures(s for i in active for s in i.segment_ids)
    try:
        routes = find_routes(graph, from_, to, parsed, max_changes=max_changes)
    except ScenarioError as exc:
        raise HTTPException(422, f"Escenario no válido: {exc}") from exc
    return RoutesOut(
        from_node_id=from_,
        to_node_id=to,
        scenario=parsed,
        scenario_code=parsed.to_code(),
        date=date,
        max_changes=max_changes,
        routes=[
            RouteOut(
                **r.model_dump(),
                interruptions=[i for i in active if set(r.segment_ids).intersection(i.segment_ids)],
            )
            for r in routes
        ],
        method=METHOD,
    )
