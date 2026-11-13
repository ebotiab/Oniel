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
#: El lazo que cierran la convencional de Moreda y las dos de alta velocidad de Córdoba a Granada.
LBMG, LAV_GRANADA, LAV_MALAGA = (
    "linares-baeza-moreda-granada",
    "lav-antequera-granada",
    "lav-cordoba-malaga",
)
BY_GRANADA = [CONV, LBMG, LAV_GRANADA, LAV_MALAGA]
#: La alta velocidad de Barcelona y sus dos baipases, que cuentan como parte de ella.
BCN, BARCELONA, ZARAGOZA = "lav-madrid-barcelona", "barcelona-sants", "zaragoza-delicias"
AROUND_ZARAGOZA = "baipas-zaragoza:bif-moncasi:bif-canal-imperial"
AROUND_LLEIDA = "baipas-lleida:bif-les-torres-de-sanui:bif-artesa-de-lleida"
#: Los dos caminos de Madrid a Albacete: el convencional por Alcázar y el de alta velocidad por Cuenca.
ALBACETE, LAV_VALENCIA, LAV_ALICANTE = (
    "alcazar-albacete",
    "lav-madrid-valencia",
    "lav-albacete-alicante",
)
#: La alta velocidad que sigue hasta Murcia desde la bifurcación de Murcia, antes de Alicante.
LAV_MURCIA, MURCIA = "lav-monforte-murcia", "murcia-del-carmen"
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
    # los dos baipases, los nueve tramos de la línea de Albacete a Alicante, los ocho de la de
    # Monforte del Cid a Murcia y los 35 de la de Valencia a Camp de Tarragona
    # y los ocho de la de Monforte del Cid a Murcia
    assert len(graph.edges) == len(network.segments) == 54 + 8 + 8 + 20 + 2 + 14 + 2 + 9 + 8 + 35 + 5
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
        558.0,  # por Cuenca hasta Albacete y vuelta por Alcázar de San Juan y Manzanares
        613.5,
        704.6,  # lo mismo al revés: por Alcázar a Albacete y vuelta por Cuenca
        885.6,  # por Linares-Baeza, Moreda, Granada, Antequera y Córdoba
        910.9,  # por Cuenca, Albacete y Alcázar, y de allí por Linares-Baeza y Córdoba
        1289.1,  # por Barcelona, la costa y Valencia
    ]
    # Madrid – Andújar: hay un recorrido que pasa tres veces de una línea a otra
    to_andujar = find_routes(graph, MADRID, "andujar")
    assert [r.length_km for r in to_andujar] == [361.9, 401.0, 422.4, 512.1]
    assert [leg.line_id for leg in to_andujar[3].legs] == [CONV, MZCR, LAV, CONV]
    # la proporción se mide contra el más corto de los que quedan en el escenario
    closed = Scenario(closures=[URDA_CIUDAD_REAL])
    assert [r.length_km for r in find_routes(graph, MADRID, CIUDAD_REAL, closed)] == [260.5]
    assert [r.length_km for r in find_routes(graph, MANZANARES, CIUDAD_REAL)] == [64.4]


def test_madrid_to_albacete_goes_two_ways_and_alicante_is_reached(graph: Graph) -> None:
    """El objetivo de la etapa de Levante: Madrid – Albacete por la línea convencional de Alcázar
    y por la alta velocidad de Cuenca, con kilómetros y tiempo de cada uno, y Madrid – Alicante."""
    conventional, high_speed, *others = find_routes(graph, MADRID, "albacete-los-llanos")
    assert conventional.line_ids == [CONV, ALBACETE]
    assert (conventional.length_km, conventional.time_min) == (277.6, 106)
    assert "Alcázar de San Juan" in conventional.via
    assert high_speed.line_ids == [LAV, LAV_VALENCIA, LAV_ALICANTE]
    assert (high_speed.length_km, high_speed.time_min) == (313.6, 65)
    assert high_speed.via == ["Cuenca-Fernando Zóbel"]
    # queda un tercero, por Ciudad Real y Manzanares hasta Alcázar: 415,2 km, menos del doble
    assert [r.length_km for r in others] == [415.2]
    to_alicante = find_routes(graph, MADRID, "alicante-terminal")
    assert [(r.length_km, r.time_min) for r in to_alicante] == [
        (442.5, 143),
        (478.4, 102),
        (580.0, 167),
    ]
    # el más corto junta la línea convencional hasta Albacete con la alta velocidad desde allí: el
    # comparador une líneas sin mirar el ancho de vía. El de alta velocidad entero es el segundo
    assert to_alicante[0].line_ids == [CONV, ALBACETE, LAV_ALICANTE]
    assert to_alicante[1].line_ids == [LAV, LAV_VALENCIA, LAV_ALICANTE]
    assert to_alicante[1].via == [
        "Cuenca-Fernando Zóbel",
        "Albacete-Los Llanos",
        "Villena Alta Velocidad",
    ]


def test_murcia_is_reached_from_madrid_and_from_alicante(graph: Graph) -> None:
    """Madrid – Murcia con sus kilómetros y su tiempo: la alta velocidad entera pasa por Cuenca y
    deja la línea de Alicante en la bifurcación de Murcia, sin entrar en Alicante."""
    to_murcia = find_routes(graph, MADRID, MURCIA)
    assert [(r.length_km, r.time_min) for r in to_murcia] == [
        (485.8, 159),
        (521.7, 118),
        (623.3, 183),
    ]
    # como a Alicante, el más corto junta la línea convencional hasta Albacete con la alta
    # velocidad desde allí; el de alta velocidad entero es el segundo
    assert to_murcia[0].line_ids == [CONV, ALBACETE, LAV_ALICANTE, LAV_MURCIA]
    high_speed = to_murcia[1]
    assert high_speed.line_ids == [LAV, LAV_VALENCIA, LAV_ALICANTE, LAV_MURCIA]
    assert "alicante-terminal" not in high_speed.node_ids
    assert [(leg.from_node_id, leg.to_node_id) for leg in high_speed.legs][-1] == (
        "bif-murcia",
        MURCIA,
    )
    # los últimos 21,5 km, desde Orihuela, son de vía única
    assert high_speed.single_track_km == 21.5
    # desde Madrid-Chamartín, de donde salen casi todos sus trenes, el de alta velocidad entero es
    # el primero: por la línea de Valencia, la de Albacete a Alicante y esta
    from_chamartin = find_routes(graph, "madrid-chamartin", MURCIA)[0]
    assert from_chamartin.line_ids == [LAV_VALENCIA, LAV_ALICANTE, LAV_MURCIA]
    assert (from_chamartin.length_km, from_chamartin.time_min) == (529.5, 123)
    # de Alicante a Murcia el recorrido retrocede hasta la bifurcación de Murcia, porque el
    # enlace de Monforte del Cid no está cargado: 92,2 km, unos 4 más que por el enlace
    (from_alicante,) = find_routes(graph, "alicante-terminal", MURCIA)
    assert from_alicante.line_ids == [LAV_ALICANTE, LAV_MURCIA]
    assert (from_alicante.length_km, from_alicante.time_min) == (92.2, 26)


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
    found = closure_detours(graph, URDA_CIUDAD_REAL)
    short, long = found.detours
    assert short.route.line_ids == [CONV, MZCR]
    assert (short.route.from_node_id, short.route.to_node_id) == (MADRID, CIUDAD_REAL)
    assert (short.route.length_km, short.closed_line_length_km) == (260.5, 170.8)
    assert long.route.line_ids == [CONV]
    assert (long.route.from_node_id, long.route.to_node_id) == (MADRID, CORDOBA)
    assert (long.route.length_km, long.closed_line_length_km) == (440.7, 343.6)
    # desde que Granada está unida por los dos lados existe además la vuelta por Linares-Baeza,
    # Moreda, Granada y Antequera hasta la bifurcación de Málaga; no se lista, pero se cuenta. Y
    # desde que Albacete está unida por dos caminos, otras tres que salen de la bifurcación de
    # Torrejón de Velasco por Cuenca y Albacete y vuelven por Alcázar de San Juan (529,2 km hasta
    # Ciudad Real, 709,4 km hasta Córdoba y 967,0 km hasta la bifurcación de Málaga)
    # Y desde que la línea de València a Camp de Tarragona cierra el anillo con Barcelona, otras
    # tres que suben a Barcelona y bajan por la costa y por Cuenca (de 1.252 a 1.690 km)
    assert found.omitted == 7
    everything = closure_detours(graph, URDA_CIUDAD_REAL, max_ratio=None).detours
    assert [d.route.length_km for d in everything] == [
        260.5,
        440.7,
        529.2,
        698.3,
        709.4,
        967.0,
        1252.2,
        1432.3,
        1690.0,
    ]
    assert (
        LAV_ALICANTE in everything[2].route.line_ids
        and LAV_ALICANTE in everything[5].route.line_ids
    )
    by_granada = everything[3]
    assert by_granada.route.line_ids == BY_GRANADA
    assert (by_granada.route.from_node_id, by_granada.route.to_node_id) == (MADRID, "bif-malaga")
    assert (by_granada.route.length_km, by_granada.closed_line_length_km) == (698.3, 358.0)


def test_detours_leave_the_closed_line_and_only_come_back_past_the_closure(graph: Graph) -> None:
    for edge in graph.edges:
        assert edge.line_id is not None
        km = graph.line_km[edge.line_id]
        lo, hi = sorted((km[edge.a], km[edge.b]))
        found = closure_detours(graph, edge.id)
        everything = closure_detours(graph, edge.id, max_ratio=None)
        # lo que se omite son los más largos de los que existen, y el más corto no se omite nunca
        assert len(found.detours) + found.omitted == len(everything.detours)
        assert everything.omitted == 0
        assert found.detours[:1] == everything.detours[:1]
        assert all(d in everything.detours for d in found.detours)
        for detour in everything.detours:
            route = detour.route
            assert edge.line_id not in route.line_ids
            assert km[route.from_node_id] <= lo and km[route.to_node_id] >= hi
            assert not set(route.node_ids[1:-1]) & set(km)
            assert detour.closed_line_length_km == round(
                km[route.to_node_id] - km[route.from_node_id], 1
            )


def test_closure_towards_sevilla_has_no_detour_and_the_first_stretch_goes_round_by_granada(
    graph: Graph,
) -> None:
    """A Sevilla solo se llega por la alta velocidad; hasta la bifurcación de Málaga hay otro
    camino desde que Granada está unida por los dos lados, mucho más largo."""
    none = closure_detours(graph, f"{LAV}:bif-malaga:majarabique")
    assert (none.detours, none.omitted) == ([], 0)
    first, *_ = closure_detours(graph, f"{LAV}:cordoba:bif-malaga").detours
    assert first.route.line_ids == BY_GRANADA
    assert (first.route.from_node_id, first.route.to_node_id) == (CORDOBA, "bif-malaga")
    assert (first.route.length_km, first.closed_line_length_km) == (511.7, 14.4)


def test_closure_between_almagro_and_ciudad_real_goes_round_through_madrid(graph: Graph) -> None:
    found = closure_detours(graph, f"{MZCR}:almagro:ciudad-real")
    by_madrid, by_cordoba = found.detours
    assert by_madrid.route.line_ids == by_cordoba.route.line_ids == [CONV, LAV]
    assert (by_madrid.route.length_km, by_madrid.closed_line_length_km) == (366.9, 64.4)
    assert "Madrid-Puerta de Atocha" in by_madrid.route.via
    assert by_cordoba.route.length_km == 417.4 and "Córdoba" in by_cordoba.route.via
    # la vuelta por Granada y Córdoba (689,5 km) se aparta del de Córdoba en Linares-Baeza y
    # recorre 399,1 km para lo que aquel hace en 127: más del doble, se omite; y lo mismo la
    # vuelta por Alcázar de San Juan, Albacete y Cuenca (606,9 km) y las dos que suben a Barcelona
    # y bajan por la costa y por Valencia
    assert found.omitted == 4
    everything = closure_detours(graph, f"{MZCR}:almagro:ciudad-real", max_ratio=None).detours
    assert [d.route.length_km for d in everything] == [366.9, 417.4, 606.9, 689.5, 1358.6, 1485.2]
    *_, by_granada, _, by_barcelona = everything
    assert by_granada.route.length_km == 689.5 and "Granada" in by_granada.route.via
    assert by_barcelona.route.length_km == 1485.2
    assert {"Calatayud", "Castelló de la Plana"} <= set(by_barcelona.route.via)


def test_other_closures_of_the_scenario_also_cut_the_detours(graph: Graph) -> None:
    scenario = Scenario(closures=[f"{MZCR}:daimiel:almagro"])
    found = closure_detours(graph, URDA_CIUDAD_REAL, scenario)
    (conventional,) = found.detours
    assert conventional.route.line_ids == [CONV]
    # la vuelta por Granada, las dos que salen de Torrejón de Velasco por Cuenca y Albacete y
    # las dos que dan la vuelta por Barcelona y la costa
    assert found.omitted == 5


def test_alternatives_of_a_closure_keep_the_single_line_wording(graph: Graph) -> None:
    """La alternativa de una sola línea se describe como antes de pasar por el grafo."""
    listed, omitted = alternatives(graph, f"{LAV}:villanueva-de-cordoba:adamuz")
    two_lines, one_line = listed
    # no se listan las dos vueltas por Granada hasta la bifurcación de Málaga ni las dos que
    # salen de Torrejón de Velasco por Cuenca y Albacete, ni las dos que dan la vuelta por
    # Barcelona y la costa
    assert omitted == 6
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
    más corto, recorre 366,9 km para lo que el otro hace en 64,4 km. Lo mismo el que baja de la
    bifurcación de Málaga a Granada y vuelve por Moreda (614,4 km).
    """
    sevilla = "sevilla-santa-justa"
    assert [r.length_km for r in find_routes(graph, sevilla, MANZANARES)] == [363.9, 371.2]
    unfiltered = find_routes(graph, sevilla, MANZANARES, max_ratio=None)
    assert [r.length_km for r in unfiltered][:4] == [363.9, 371.2, 614.4, 666.4]
    assert "granada" in unfiltered[2].node_ids
    assert MADRID in unfiltered[3].node_ids and CIUDAD_REAL in unfiltered[3].node_ids
    # los dos caminos que se apartan en Córdoba se conservan: 244,6 km frente a 237,2 km
    assert [r.length_km for r in find_routes(graph, MADRID, CORDOBA)] == [
        343.6,
        433.3,
        440.7,
        479.8,
    ]


def test_a_bypass_counts_as_part_of_its_line(graph: Graph) -> None:
    """De Madrid a Barcelona hay cuatro caminos, según se entre o no en Zaragoza-Delicias y en
    Lleida-Pirineus (620,1 km, 622,0 km, 625,0 km y 627,0 km). Son el mismo recorrido: queda el
    más corto, por los dos baipases, y es de una sola línea."""
    assert graph.bypass_of == {"baipas-zaragoza": BCN, "baipas-lleida": BCN}
    criteria: list[tuple[int | None, float | None]] = [
        (DEFAULT_MAX_CHANGES, DEFAULT_MAX_RATIO),
        (None, None),
        (0, DEFAULT_MAX_RATIO),  # ni un cambio de línea: pasar a un baipás no lo es
    ]
    for max_changes, max_ratio in criteria:
        # el primero; desde que está la línea de València a Camp de Tarragona hay además otros
        # recorridos de Madrid a Barcelona por València y la costa: por Cuenca (755,1 km) y por
        # Alcázar de San Juan y Albacete (864,8 km)
        route, *others = find_routes(
            graph, MADRID, BARCELONA, max_changes=max_changes, max_ratio=max_ratio
        )
        assert all(BCN in r.line_ids and len(r.line_ids) > 1 for r in others)
        assert (route.length_km, route.time_min, route.line_ids) == (620.1, 125, [BCN])
        (leg,) = route.legs
        assert (leg.line_id, leg.length_km, leg.time_min) == (BCN, 620.1, 125)
        assert AROUND_ZARAGOZA in route.segment_ids and AROUND_LLEIDA in route.segment_ids
        assert not any(
            "zaragoza-delicias" in s or "lleida-pirineus" in s for s in route.segment_ids
        )
        assert route.via == ["Guadalajara-Yebes", "Calatayud", "Camp de Tarragona"]
    # en sentido contrario, lo mismo
    there, by_valencia, by_albacete = find_routes(graph, MADRID, BARCELONA)
    back, *_ = find_routes(graph, BARCELONA, MADRID)
    assert by_albacete.length_km == 864.8 and "Albacete-Los Llanos" in by_albacete.via
    assert by_valencia.length_km == 755.1 and "València-Joaquín Sorolla" in by_valencia.via
    assert (back.length_km, back.segment_ids) == (620.1, there.segment_ids[::-1])
    # con el baipás de Zaragoza cerrado el recorrido entra en la estación, 4,9 km más; con un
    # tramo de la estación cerrado, sigue por el baipás
    through, *_ = find_routes(graph, MADRID, BARCELONA, Scenario(closures=[AROUND_ZARAGOZA]))
    assert (through.length_km, through.line_ids) == (625.0, [BCN])
    assert "Zaragoza-Delicias" in through.via and AROUND_LLEIDA in through.segment_ids
    closed = Scenario(closures=[f"{BCN}:zaragoza-delicias:bif-huesca"])
    assert [r.length_km for r in find_routes(graph, MADRID, BARCELONA, closed)] == [
        620.1,
        755.1,
        864.8,
    ]
    # a una estación que el baipás rodea se llega por su ramal, y desde ella se sigue por el otro
    (to_zaragoza,) = find_routes(graph, MADRID, ZARAGOZA)
    assert (to_zaragoza.length_km, to_zaragoza.line_ids) == (306.5, [BCN])
    (onwards,) = find_routes(graph, ZARAGOZA, BARCELONA)
    assert onwards.length_km == 318.5 and AROUND_LLEIDA in onwards.segment_ids
    assert to_zaragoza.length_km + onwards.length_km == pytest.approx(625.0)
    # un trecho que va entero por un baipás es del baipás
    (only,) = find_routes(graph, "bif-moncasi", "bif-canal-imperial")
    assert (only.length_km, only.line_ids, only.segment_ids) == (
        20.7,
        ["baipas-zaragoza"],
        [AROUND_ZARAGOZA],
    )


def test_a_closed_station_stretch_is_saved_by_its_bypass_and_the_other_way_round(
    graph: Graph,
) -> None:
    for segment_id in (
        f"{BCN}:bif-moncasi:zaragoza-delicias",
        f"{BCN}:zaragoza-delicias:bif-huesca",
        f"{BCN}:bif-huesca:bif-canal-imperial",
    ):
        found = closure_detours(graph, segment_id)
        # el baipás y, desde que la línea de València a Camp de Tarragona cierra un anillo, la
        # vuelta de Madrid a Camp de Tarragona por València, por Cuenca o por Albacete; otros
        # seis, más largos, se omiten
        detour, ring, by_albacete = found.detours
        assert found.omitted == 6 and by_albacete.route.length_km == 765.1
        assert (ring.route.from_node_id, ring.route.to_node_id) == (MADRID, "camp-de-tarragona")
        assert ring.route.length_km == 655.3
        assert (detour.route.length_km, detour.closed_line_length_km) == (20.7, 25.6)
        assert detour.route.line_ids == ["baipas-zaragoza"]
        assert [leg.line_name for leg in detour.route.legs] == ["Baipás de Zaragoza"]
    # el baipás cerrado se salva entrando en la estación
    (detour,) = closure_detours(graph, AROUND_LLEIDA).detours  # los del anillo se omiten
    assert (detour.route.length_km, detour.closed_line_length_km) == (16.2, 14.3)
    assert detour.route.line_ids == [BCN] and detour.route.via == ["Lleida-Pirineus"]
    # el resto de la línea, hasta Camp de Tarragona, se salva dando la vuelta por València
    ring, _ = closure_detours(graph, f"{BCN}:calatayud:cambiador-plasencia-de-jalon").detours
    assert (ring.route.from_node_id, ring.route.to_node_id) == (MADRID, "camp-de-tarragona")
    # y de Camp de Tarragona a Barcelona-Sants no hay rodeo: solo llega esta línea
    assert closure_detours(graph, f"{BCN}:l-arboc:vilafranca-del-penedes").detours == []


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
        # los baipases son parte de su línea: un solo recorrido, por ellos o, cerrado uno, por la
        # estación; y a una estación que un baipás rodea se llega por su ramal
        {"from": MADRID, "to": BARCELONA, "scenario": "", **DEFAULTS},
        {"from": MADRID, "to": BARCELONA, "scenario": f"c~{AROUND_ZARAGOZA}", **DEFAULTS},
        {"from": "lleida-pirineus", "to": MADRID, "scenario": "", **DEFAULTS},
    ]
    detours: list[dict[str, Any]] = [
        {"segment_id": URDA_CIUDAD_REAL, "scenario": ""},
        {"segment_id": f"{CONV}:venta-de-cardenas:vilches", "scenario": ""},
        {"segment_id": f"{MZCR}:almagro:ciudad-real", "scenario": f"c~{LAV}:adamuz:cordoba"},
        # los tres salen por nodos distintos y ninguno sobra: cada uno es el más corto desde el suyo
        {"segment_id": f"{LAV}:cordoba:bif-malaga", "scenario": ""},
        # un solo rodeo listado y dos omitidos, que alargan el mismo camino por Ciudad Real o Madrid
        {"segment_id": f"{LBMG}:iznalloz:granada", "scenario": ""},
        # la entrada a una estación se salva por su baipás, y el baipás, por la estación
        {"segment_id": f"{BCN}:bif-moncasi:zaragoza-delicias", "scenario": ""},
        {"segment_id": AROUND_LLEIDA, "scenario": ""},
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
        case["expected"] = closure_detours(graph, case["segment_id"], scenario).model_dump()
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
    assert all(case["expected"] for case in cases["routes"])
    assert all(case["expected"]["detours"] for case in cases["detours"])
