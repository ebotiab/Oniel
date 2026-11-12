"""Grafo de rutas y escenarios, sobre la red de la instantánea del visor (la misma que importa la base)."""

from __future__ import annotations

import json
import os
from dataclasses import dataclass
from pathlib import Path
from typing import Any

import pytest

from oniel.domain.schemas import LineSummary, NetworkIndexOut, NodeIndexOut, SegmentOut
from oniel.routing import (
    DEFAULT_MAX_CHANGES,
    DEFAULT_MAX_RATIO,
    Graph,
    Scenario,
    ScenarioError,
    SketchLink,
    SpeedChange,
    build_graph,
    closure_detours,
    find_routes,
)
from oniel.sim.closure import alternatives

REPO = Path(__file__).resolve().parents[2]
#: El índice de la instantánea lleva todas las líneas, nodos y tramos: el grafo entero.
SNAPSHOT = REPO / "frontend" / "public" / "data" / "index.json"
#: Casos que el cliente (``frontend/e2e/rutas.spec.ts``) tiene que resolver igual que el servidor.
PARITY = REPO / "frontend" / "e2e" / "fixtures" / "rutas-paridad.json"

LAV, CONV, MZCR = (
    "lav-madrid-sevilla",
    "convencional-madrid-alcazar-cordoba",
    "manzanares-ciudad-real",
)
MADRID, CIUDAD_REAL, MANZANARES, CORDOBA = (
    "madrid-puerta-de-atocha",
    "ciudad-real",
    "manzanares",
    "cordoba",
)
URDA_CIUDAD_REAL = f"{LAV}:urda:ciudad-real"


@dataclass(frozen=True)
class Red:
    """Lo que el grafo necesita de la red, leído del índice de la instantánea."""

    lines: list[LineSummary]
    nodes: list[NodeIndexOut]
    segments: list[SegmentOut]


@pytest.fixture(scope="module")
def network() -> Red:
    index = NetworkIndexOut.model_validate(json.loads(SNAPSHOT.read_text(encoding="utf-8")))
    segments = [SegmentOut(id=f.id, **f.properties) for f in index.segment_features.features]
    return Red(lines=index.lines, nodes=index.nodes, segments=segments)


@pytest.fixture(scope="module")
def graph(network: Red) -> Graph:
    return build_graph(network.lines, network.nodes, network.segments)


def test_graph_joins_the_lines_at_their_shared_nodes(graph: Graph, network: Red) -> None:
    assert len(graph.edges) == len(network.segments) == 48
    # un nodo común a dos líneas es uno solo, con un kilómetro en cada una
    assert len(graph.nodes) == len({n.id for n in network.nodes})
    assert {e.line_id for e in graph.edges_at(MANZANARES)} == {CONV, MZCR}
    assert {e.line_id for e in graph.edges_at(CIUDAD_REAL)} == {LAV, MZCR}
    assert graph.line_km[MZCR][MANZANARES] == 0 and graph.line_km[CONV][MANZANARES] > 196


DEFAULTS: dict[str, Any] = {"max_changes": DEFAULT_MAX_CHANGES, "max_ratio": DEFAULT_MAX_RATIO}
#: El criterio anterior al comparador: un solo paso de una línea a otra y ningún descarte por largo.
ONE_CHANGE: dict[str, Any] = {"max_changes": 1, "max_ratio": None}


def test_madrid_cordoba_has_two_routes(graph: Graph) -> None:
    fast, slow = find_routes(graph, MADRID, CORDOBA, **ONE_CHANGE)
    assert (fast.line_ids, fast.length_km, fast.single_track_km) == ([LAV], 343.6, 0)
    assert (slow.line_ids, slow.length_km, slow.single_track_km) == ([CONV], 440.7, 194.1)
    assert "Alcázar de San Juan" in slow.via and "Ciudad Real" in fast.via
    assert fast.time_min is not None and slow.time_min is not None
    assert fast.time_min < slow.time_min
    assert fast.node_ids[0] == MADRID and fast.node_ids[-1] == CORDOBA
    assert len(fast.segment_ids) == len(fast.node_ids) - 1


def test_madrid_ciudad_real_has_three_routes_one_of_them_through_manzanares(
    graph: Graph,
) -> None:
    direct, detour, long_way = find_routes(graph, MADRID, CIUDAD_REAL, **ONE_CHANGE)
    assert (direct.line_ids, direct.length_km) == ([LAV], 170.8)
    # el desvío de los Intercity y Alvia tras Urda: convencional hasta Manzanares y línea 522
    assert detour.line_ids == [CONV, MZCR]
    assert detour.length_km == 260.5 and detour.single_track_km == 64.4
    assert [(leg.to_node_id, leg.length_km) for leg in detour.legs] == [
        (MANZANARES, 196.1),
        (CIUDAD_REAL, 64.4),
    ]
    assert detour.via[-3:] == ["Manzanares", "Daimiel", "Almagro"]
    # y la vuelta larga: convencional hasta Córdoba y alta velocidad de vuelta
    assert long_way.line_ids == [CONV, LAV] and long_way.length_km == 613.5


def test_more_line_changes_find_the_route_of_the_diverted_alvia(graph: Graph) -> None:
    """Con dos cambios de línea aparece Madrid – Manzanares – Ciudad Real – Córdoba (433,3 km)."""
    routes = find_routes(graph, MADRID, CORDOBA, max_changes=2)
    assert [r.length_km for r in routes] == [343.6, 433.3, 440.7, 479.8]
    assert routes[1].line_ids == [CONV, MZCR, LAV]
    assert [r.length_km for r in find_routes(graph, MADRID, CORDOBA, max_changes=None)] == [
        343.6,
        433.3,
        440.7,
        479.8,
    ]
    assert [r.line_ids for r in find_routes(graph, MADRID, CORDOBA, max_changes=0)] == [
        [LAV],
        [CONV],
    ]


def test_by_default_routes_are_not_capped_by_lines_but_by_length(graph: Graph) -> None:
    """El criterio del comparador: sin tope útil de líneas y sin rodeos de más del doble."""
    # Madrid – Córdoba: entra el recorrido de los Alvia desviados, por tres líneas
    to_cordoba = find_routes(graph, MADRID, CORDOBA)
    assert [r.length_km for r in to_cordoba] == [343.6, 433.3, 440.7, 479.8]
    assert [len(r.legs) for r in to_cordoba] == [1, 3, 1, 3]
    # Madrid – Ciudad Real: la vuelta por Córdoba (613,5 km frente a 170,8 km) se descarta
    assert [r.length_km for r in find_routes(graph, MADRID, CIUDAD_REAL)] == [170.8, 260.5]
    assert [r.length_km for r in find_routes(graph, MADRID, CIUDAD_REAL, max_ratio=None)] == [
        170.8,
        260.5,
        613.5,
    ]
    # Madrid – Andújar: hay un recorrido que pasa tres veces de una línea a otra
    to_andujar = find_routes(graph, MADRID, "andujar")
    assert [r.length_km for r in to_andujar] == [361.9, 401.0, 422.4, 512.1]
    assert [leg.line_id for leg in to_andujar[3].legs] == [CONV, MZCR, LAV, CONV]
    # la proporción se mide contra el más corto de los que quedan en el escenario
    closed = Scenario(closures=[URDA_CIUDAD_REAL])
    assert [r.length_km for r in find_routes(graph, MADRID, CIUDAD_REAL, closed)] == [260.5]
    assert [r.length_km for r in find_routes(graph, MANZANARES, CIUDAD_REAL)] == [64.4]


def test_time_is_length_over_typical_speed(graph: Graph, network: Red) -> None:
    (route,) = find_routes(graph, MANZANARES, CIUDAD_REAL, max_changes=0)
    segments = [s for s in network.segments if s.line_id == MZCR]
    assert all(s.typical_speed_kmh == 140 for s in segments)
    minutes = sum(s.length_km / 140 * 60 for s in segments)
    assert route.time_min == round(minutes) == 28
    assert route.legs[0].time_min == route.time_min


def test_scenario_round_trips_through_json_and_the_short_code() -> None:
    scenario = Scenario(
        closures=[URDA_CIUDAD_REAL],
        links=[
            SketchLink(
                from_node_id="mora", to_node_id="alcazar-de-san-juan", length_km=62.5, speed_kmh=200
            )
        ],
        speeds=[SpeedChange(segment_id=f"{MZCR}:almagro:ciudad-real", speed_kmh=160)],
    )
    code = scenario.to_code()
    assert code == (
        "c~lav-madrid-sevilla:urda:ciudad-real;e~mora~alcazar-de-san-juan~62.5~200"
        ";v~manzanares-ciudad-real:almagro:ciudad-real~160"
    )
    assert Scenario.from_code(code) == scenario
    assert Scenario.model_validate_json(scenario.model_dump_json()) == scenario
    assert Scenario.from_code("").is_empty and Scenario().to_code() == ""


@pytest.mark.parametrize("code", ["x~algo", "c~", "c~Tramo Raro", "e~a~b~0~100", "v~a:b:c~rápido"])
def test_unreadable_scenarios_are_rejected(code: str) -> None:
    with pytest.raises(ScenarioError):
        Scenario.from_code(code)


def test_scenario_that_does_not_fit_the_network_is_rejected(graph: Graph) -> None:
    with pytest.raises(ScenarioError, match="tramo"):
        graph.apply(Scenario(closures=["no-existe:a:b"]))
    with pytest.raises(ScenarioError, match="nodo"):
        graph.apply(Scenario.from_code("e~madrid-puerta-de-atocha~atlantida~10~100"))
    with pytest.raises(ScenarioError, match="nodo"):
        find_routes(graph, MADRID, "atlantida")


def test_closing_a_segment_removes_the_routes_that_use_it(graph: Graph) -> None:
    routes = find_routes(
        graph, MADRID, CIUDAD_REAL, Scenario(closures=[URDA_CIUDAD_REAL]), **ONE_CHANGE
    )
    assert [r.line_ids for r in routes] == [[CONV, MZCR], [CONV, LAV]]
    assert all(URDA_CIUDAD_REAL not in r.segment_ids for r in routes)
    # el grafo original no cambia
    assert len(find_routes(graph, MADRID, CIUDAD_REAL, **ONE_CHANGE)) == 3


def test_changing_a_speed_changes_the_time_and_not_the_length(graph: Graph) -> None:
    (base,) = find_routes(graph, MANZANARES, CIUDAD_REAL, max_changes=0)
    faster = Scenario(speeds=[SpeedChange(segment_id=s, speed_kmh=280) for s in base.segment_ids])
    (changed,) = find_routes(graph, MANZANARES, CIUDAD_REAL, faster, max_changes=0)
    assert changed.length_km == base.length_km
    assert changed.time_min == 14 and base.time_min == 28


def test_a_sketched_link_opens_a_new_route(graph: Graph) -> None:
    """Un enlace esbozado entre Alcázar de San Juan y Ciudad Real, de 110 km a 200 km/h."""
    link = SketchLink(
        from_node_id="alcazar-de-san-juan", to_node_id=CIUDAD_REAL, length_km=110, speed_kmh=200
    )
    routes = find_routes(graph, MADRID, CIUDAD_REAL, Scenario(links=[link]), **ONE_CHANGE)
    sketched = next(r for r in routes if link.id in r.segment_ids)
    assert [leg.line_id for leg in sketched.legs] == [CONV, None]
    assert sketched.legs[1].line_name == "Enlace esbozado"
    assert (sketched.legs[1].length_km, sketched.legs[1].time_min) == (110, 33)
    assert sketched.length_km == round(graph.line_km[CONV]["alcazar-de-san-juan"] + 110, 1)
    assert sketched.line_ids == [CONV]
    assert len(routes) == 4


def test_detours_of_a_closure_between_madrid_and_ciudad_real(graph: Graph) -> None:
    """Cierre de Urda – Ciudad Real: el rodeo por Manzanares (dos líneas) y la convencional entera."""
    short, long = closure_detours(graph, URDA_CIUDAD_REAL)
    assert short.route.line_ids == [CONV, MZCR]
    assert (short.route.from_node_id, short.route.to_node_id) == (MADRID, CIUDAD_REAL)
    assert (short.route.length_km, short.closed_line_length_km) == (260.5, 170.8)
    assert long.route.line_ids == [CONV]
    assert (long.route.from_node_id, long.route.to_node_id) == (MADRID, CORDOBA)
    assert (long.route.length_km, long.closed_line_length_km) == (440.7, 343.6)


def test_detours_leave_the_closed_line_and_only_come_back_past_the_closure(graph: Graph) -> None:
    for edge in graph.edges:
        assert edge.line_id is not None
        km = graph.line_km[edge.line_id]
        lo, hi = sorted((km[edge.a], km[edge.b]))
        for detour in closure_detours(graph, edge.id):
            route = detour.route
            assert edge.line_id not in route.line_ids
            assert km[route.from_node_id] <= lo and km[route.to_node_id] >= hi
            assert not set(route.node_ids[1:-1]) & set(km)
            assert detour.closed_line_length_km == round(
                km[route.to_node_id] - km[route.from_node_id], 1
            )


def test_closure_south_of_cordoba_has_no_detour(graph: Graph) -> None:
    assert closure_detours(graph, f"{LAV}:bif-malaga:majarabique") == []


def test_closure_between_almagro_and_ciudad_real_goes_round_through_madrid(graph: Graph) -> None:
    by_madrid, by_cordoba = closure_detours(graph, f"{MZCR}:almagro:ciudad-real")
    assert by_madrid.route.line_ids == by_cordoba.route.line_ids == [CONV, LAV]
    assert (by_madrid.route.length_km, by_madrid.closed_line_length_km) == (366.9, 64.4)
    assert "Madrid-Puerta de Atocha" in by_madrid.route.via
    assert by_cordoba.route.length_km == 417.4 and "Córdoba" in by_cordoba.route.via


def test_other_closures_of_the_scenario_also_cut_the_detours(graph: Graph) -> None:
    scenario = Scenario(closures=[f"{MZCR}:daimiel:almagro"])
    (only,) = closure_detours(graph, URDA_CIUDAD_REAL, scenario)
    assert only.route.line_ids == [CONV]


def test_alternatives_of_a_closure_keep_the_single_line_wording(graph: Graph) -> None:
    """La alternativa de una sola línea se describe como antes de pasar por el grafo."""
    two_lines, one_line = alternatives(graph, f"{LAV}:villanueva-de-cordoba:adamuz")
    assert (one_line.line_id, one_line.line_ids) == (CONV, [CONV])
    assert (one_line.from_node_id, one_line.to_node_id) == (MADRID, CORDOBA)
    assert (one_line.length_km, one_line.closed_line_length_km) == (440.7, 343.6)
    assert one_line.single_track_km == 194.1
    assert one_line.note == (
        "Recorrido alternativo cargado en Oniel entre Madrid-Puerta de Atocha y Córdoba: 441 km"
        " por la línea convencional Madrid – Alcázar de San Juan – Córdoba frente a 344 km por la"
        " línea cerrada. Incluye 194 km de vía única. Oniel no reasigna los trenes afectados a"
        " esta alternativa; solo señala que existe."
    )
    assert (two_lines.from_node_id, two_lines.to_node_id) == (CIUDAD_REAL, CORDOBA)
    assert two_lines.line_ids == [MZCR, CONV] and two_lines.line_id == MZCR
    assert (
        "309 km por la línea convencional Manzanares – Ciudad Real hasta Manzanares y por la"
        " línea convencional Madrid – Alcázar de San Juan – Córdoba frente a 173 km"
    ) in two_lines.note


def test_a_route_that_strays_far_from_a_shorter_one_is_dropped(graph: Graph) -> None:
    """Sevilla – Manzanares: el camino que llega a Ciudad Real y sube hasta Madrid para volver.

    Mide 666,4 km frente a 363,9 km, menos del doble, pero desde Ciudad Real, donde se aparta del
    más corto, recorre 366,9 km para lo que el otro hace en 64,4 km.
    """
    sevilla = "sevilla-santa-justa"
    assert [r.length_km for r in find_routes(graph, sevilla, MANZANARES)] == [363.9, 371.2]
    unfiltered = find_routes(graph, sevilla, MANZANARES, max_ratio=None)
    assert [r.length_km for r in unfiltered][:3] == [363.9, 371.2, 666.4]
    assert MADRID in unfiltered[2].node_ids and CIUDAD_REAL in unfiltered[2].node_ids
    # los dos caminos que se apartan en Córdoba se conservan: 244,6 km frente a 237,2 km
    assert [r.length_km for r in find_routes(graph, MADRID, CORDOBA)] == [
        343.6,
        433.3,
        440.7,
        479.8,
    ]


def test_inverting_the_direction_gives_the_same_routes(graph: Graph) -> None:
    for a, b in [(MADRID, CORDOBA), ("sevilla-santa-justa", MANZANARES), (MADRID, "andujar")]:
        there = [r.segment_ids for r in find_routes(graph, a, b)]
        back = [list(reversed(r.segment_ids)) for r in find_routes(graph, b, a)]
        assert sorted(there) == sorted(back)


def _parity_cases(graph: Graph) -> dict[str, Any]:
    routes: list[dict[str, Any]] = [
        {"from": MADRID, "to": CORDOBA, "scenario": "", **ONE_CHANGE},
        {"from": MADRID, "to": CIUDAD_REAL, "scenario": "", **ONE_CHANGE},
        {
            "from": MADRID,
            "to": "sevilla-santa-justa",
            "scenario": "",
            "max_changes": 2,
            "max_ratio": None,
        },
        {
            "from": MADRID,
            "to": CIUDAD_REAL,
            "scenario": f"c~{URDA_CIUDAD_REAL};e~alcazar-de-san-juan~ciudad-real~110.5~200"
            f";v~{MZCR}:almagro:ciudad-real~95",
            "max_changes": 2,
            "max_ratio": None,
        },
        # el criterio por defecto, el del comparador: sin tope útil de líneas y hasta el doble
        {"from": MADRID, "to": CORDOBA, "scenario": "", **DEFAULTS},
        {"from": MADRID, "to": CIUDAD_REAL, "scenario": "", **DEFAULTS},
        {"from": MADRID, "to": "andujar", "scenario": "", **DEFAULTS},
        # un rodeo que no llega al doble del total, pero sí donde se aparta del más corto
        {"from": "sevilla-santa-justa", "to": MANZANARES, "scenario": "", **DEFAULTS},
    ]
    detours: list[dict[str, Any]] = [
        {"segment_id": URDA_CIUDAD_REAL, "scenario": ""},
        {"segment_id": f"{CONV}:venta-de-cardenas:vilches", "scenario": ""},
        {"segment_id": f"{MZCR}:almagro:ciudad-real", "scenario": f"c~{LAV}:adamuz:cordoba"},
    ]
    for case in routes:
        found = find_routes(
            graph,
            case["from"],
            case["to"],
            Scenario.from_code(case["scenario"]),
            max_changes=case["max_changes"],
            max_ratio=case["max_ratio"],
        )
        case["expected"] = [r.model_dump() for r in found]
    for case in detours:
        scenario = Scenario.from_code(case["scenario"])
        case["expected"] = [
            d.model_dump() for d in closure_detours(graph, case["segment_id"], scenario)
        ]
    return {"routes": routes, "detours": detours}


def test_parity_cases_match_the_fixture_shared_with_the_client(graph: Graph) -> None:
    """El cliente resuelve estos mismos casos y los compara con este mismo fichero.

    Si el cálculo cambia a propósito, se regenera con ``ONIEL_UPDATE_FIXTURES=1 uv run pytest
    tests/test_routing.py`` y el cliente tiene que seguir dando lo mismo.
    """
    cases = _parity_cases(graph)
    if os.environ.get("ONIEL_UPDATE_FIXTURES"):
        PARITY.parent.mkdir(parents=True, exist_ok=True)
        PARITY.write_text(json.dumps(cases, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    assert cases == json.loads(PARITY.read_text(encoding="utf-8"))
    assert all(case["expected"] for case in [*cases["routes"], *cases["detours"]])
