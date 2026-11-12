"""Trenes por tramo y alternativa en la red cargada, sobre la red de la instantánea del visor."""

from __future__ import annotations

import json
from pathlib import Path
from typing import Any

import pytest

from oniel.analysis.criticality import SCOPE_NOTE, ServicePath, corridor, segment_alternatives
from oniel.domain.schemas import (
    AlternativesOut,
    LineSummary,
    NetworkIndexOut,
    SegmentAlternativesOut,
    SegmentOut,
)
from oniel.routing import Graph, ScenarioError, build_graph, find_routes, route_along

DATA = Path(__file__).resolve().parents[2] / "frontend" / "public" / "data"

LAV, CONV, MZCR, JAEN, LBMG = (
    "lav-madrid-sevilla",
    "convencional-madrid-alcazar-cordoba",
    "manzanares-ciudad-real",
    "espeluy-jaen",
    "linares-baeza-moreda-granada",
)
MADRID, CORDOBA, SEVILLA = "madrid-puerta-de-atocha", "cordoba", "sevilla-santa-justa"
ADAMUZ_CORDOBA = f"{LAV}:adamuz:cordoba"
CORDOBA_BIF_MALAGA = f"{LAV}:cordoba:bif-malaga"
ALMAGRO_CIUDAD_REAL = f"{MZCR}:almagro:ciudad-real"


def _read(name: str) -> Any:
    return json.loads((DATA / name).read_text(encoding="utf-8"))


@pytest.fixture(scope="module")
def lines() -> list[LineSummary]:
    return NetworkIndexOut.model_validate(_read("index.json")).lines


@pytest.fixture(scope="module")
def graph(lines: list[LineSummary]) -> Graph:
    index = NetworkIndexOut.model_validate(_read("index.json"))
    segments = [SegmentOut(id=f.id, **f.properties) for f in index.segment_features.features]
    return build_graph(lines, index.nodes, segments)


def _path(graph: Graph, from_node: str, to_node: str, nth: int = 0) -> frozenset[str]:
    """Los tramos del recorrido número ``nth`` entre dos nodos, del más corto al más largo."""
    return frozenset(find_routes(graph, from_node, to_node)[nth].segment_ids)


def _of(result: list[SegmentAlternativesOut], segment_id: str) -> SegmentAlternativesOut:
    return next(s for s in result if s.segment_id == segment_id)


def test_the_conventional_line_is_the_alternative_to_high_speed_between_madrid_and_cordoba(
    graph: Graph,
) -> None:
    trains = [
        ServicePath("ave-1", "renfe", _path(graph, MADRID, CORDOBA)),
        ServicePath("ave-2", "renfe", _path(graph, MADRID, CORDOBA)),
        ServicePath("ouigo-1", "ouigo", _path(graph, MADRID, CORDOBA)),
    ]
    segment = _of(segment_alternatives(graph, trains), ADAMUZ_CORDOBA)
    assert (segment.trains, segment.with_alternative, segment.without_alternative) == (3, 3, 0)
    assert segment.by_operator == {"ouigo": 1, "renfe": 2}
    [group] = segment.groups
    assert (group.from_node_id, group.to_node_id, group.trains) == (MADRID, CORDOBA, 3)
    assert (group.length_km, group.time_min, group.line_ids) == (343.6, 81, [LAV])
    alternative = group.alternative
    assert alternative is not None
    # con Adamuz – Córdoba cerrado queda la línea convencional entera: 440,7 km frente a 343,6
    assert alternative.line_ids == [CONV]
    assert (alternative.length_km, alternative.extra_km) == (440.7, 97.1)
    assert alternative.time_min is not None and alternative.extra_min == alternative.time_min - 81
    assert alternative.single_track_km == 194.1
    assert alternative.via[:2] == ["Aranjuez", "Alcázar de San Juan"]


def test_south_of_cordoba_there_is_no_other_way_in_the_loaded_lines(graph: Graph) -> None:
    trains = [ServicePath("ave-1", "renfe", _path(graph, MADRID, SEVILLA))]
    result = segment_alternatives(graph, trains)
    south = _of(result, CORDOBA_BIF_MALAGA)
    assert (south.trains, south.with_alternative, south.without_alternative) == (1, 0, 1)
    assert south.groups[0].alternative is None
    # el mismo tren, al norte de Córdoba, sí tiene otro camino
    north = _of(result, ADAMUZ_CORDOBA)
    assert north.without_alternative == 0
    assert north.groups[0].to_node_id == SEVILLA


def test_trains_are_grouped_by_their_way_through_the_loaded_lines(graph: Graph) -> None:
    direct = _path(graph, MADRID, CORDOBA)
    # los desviados: convencional hasta Manzanares, Manzanares – Ciudad Real y alta velocidad
    diverted = _path(graph, MADRID, CORDOBA, nth=1)
    assert ALMAGRO_CIUDAD_REAL in diverted
    trains = [
        ServicePath("ave-1", "renfe", direct),
        ServicePath("ave-2", "renfe", direct),
        ServicePath("alvia-1", "renfe", diverted),
    ]
    segment = _of(segment_alternatives(graph, trains), ADAMUZ_CORDOBA)
    assert [(g.trains, g.length_km) for g in segment.groups] == [(2, 343.6), (1, 433.3)]
    assert [g.alternative.extra_km for g in segment.groups if g.alternative] == [97.1, 7.4]
    # para los desviados, el otro camino de Manzanares a Ciudad Real es la alta velocidad: más corto
    detour = _of(segment_alternatives(graph, trains), ALMAGRO_CIUDAD_REAL)
    [group] = detour.groups
    assert group.alternative is not None
    assert group.alternative.line_ids == [LAV]
    assert group.alternative.extra_km == -89.7


def test_every_segment_is_listed_even_without_trains(graph: Graph) -> None:
    result = segment_alternatives(graph, [])
    assert [s.segment_id for s in result] == [e.id for e in graph.edges]
    assert all(s.trains == 0 and s.groups == [] for s in result)


def test_corridor_keeps_only_the_stretch_joined_to_the_segment(graph: Graph) -> None:
    lav = find_routes(graph, MADRID, SEVILLA)[0].segment_ids
    # un tren que sale de las líneas cargadas y vuelve: dos trozos sueltos
    broken = [s for s in lav if s != f"{LAV}:ciudad-real:puertollano"]
    start, path = corridor(graph, broken, ADAMUZ_CORDOBA)
    assert start == "puertollano"
    assert [e.id for e in path] == lav[lav.index(f"{LAV}:puertollano:villanueva-de-cordoba") :]
    start, path = corridor(graph, broken, f"{LAV}:urda:ciudad-real")
    assert (start, path[-1].id) == (MADRID, f"{LAV}:urda:ciudad-real")


def test_corridor_falls_back_to_the_segment_when_the_stretch_branches(graph: Graph) -> None:
    # tres tramos que salen de Córdoba no forman un camino
    branching = [ADAMUZ_CORDOBA, CORDOBA_BIF_MALAGA, f"{CONV}:rabanales:cordoba"]
    start, path = corridor(graph, branching, ADAMUZ_CORDOBA)
    assert (start, [e.id for e in path]) == ("adamuz", [ADAMUZ_CORDOBA])
    with pytest.raises(ValueError):
        corridor(graph, branching, "no-existe")


def test_route_along_measures_a_known_way_like_find_routes(graph: Graph) -> None:
    for found in find_routes(graph, MADRID, CORDOBA):
        assert route_along(graph, MADRID, found.segment_ids) == found
    with pytest.raises(ScenarioError):
        route_along(graph, CORDOBA, [f"{LAV}:urda:ciudad-real"])
    with pytest.raises(ScenarioError):
        route_along(graph, MADRID, [])


def test_snapshot_says_which_segments_leave_their_trains_without_alternative(
    lines: list[LineSummary],
) -> None:
    """La instantánea, con los trenes del día de referencia (13 de noviembre de 2026)."""
    exported = AlternativesOut.model_validate(_read("alternatives.json"))
    assert exported.scope_note == SCOPE_NOTE and "líneas que Oniel tiene cargadas" in SCOPE_NOTE
    assert exported.line_ids == [LAV, CONV, MZCR, JAEN, LBMG]
    assert exported.missing_operator_ids == ["iryo"]
    # los trenes de cada tramo son los mismos pasos que cuenta su línea, por operador
    counts: dict[str, int] = {}
    by_operator: dict[str, dict[str, int]] = {}
    for line in lines:
        detail = _read(f"lines/{line.id}.json")
        assert detail["date"] == str(exported.date)
        counts |= detail["counts"]
        by_operator |= detail["counts_by_operator"]
    assert len(exported.segments) == 47
    for s in exported.segments:
        assert s.trains == counts.get(s.segment_id, 0) == sum(g.trains for g in s.groups)
        assert s.by_operator == by_operator.get(s.segment_id, {})
        assert s.with_alternative + s.without_alternative == s.trains
    # no queda otro camino al sur de Córdoba, donde Oniel tiene una sola línea, ni en el ramal
    # de Jaén, que acaba en una estación término, ni en la línea de Linares-Baeza a Granada, una
    # rama unida al resto de la red cargada por un solo extremo
    without = {
        s.segment_id: s.without_alternative for s in exported.segments if s.without_alternative
    }
    assert without == {
        CORDOBA_BIF_MALAGA: 108,
        f"{LAV}:bif-malaga:majarabique": 55,
        f"{LAV}:majarabique:sevilla-santa-justa": 53,
        f"{JAEN}:espeluy:mengibar-artichuela": 50,
        f"{JAEN}:mengibar-artichuela:jaen": 44,
        f"{LBMG}:linares-baeza:jodar-ubeda": 2,
        f"{LBMG}:jodar-ubeda:cabra-del-santo-cristo": 2,
        f"{LBMG}:cabra-del-santo-cristo:moreda": 2,
        f"{LBMG}:bif-almeria:iznalloz": 12,
        f"{LBMG}:iznalloz:granada": 12,
    }
    # entre la estación de Moreda y la bifurcación no pasa ningún tren de los horarios
    assert _of(exported.segments, f"{LBMG}:moreda:bif-almeria").trains == 0
    # el grupo más numeroso de Adamuz – Córdoba: los 43 trenes entre Madrid y Sevilla
    top = _of(exported.segments, ADAMUZ_CORDOBA).groups[0]
    assert (top.trains, top.from_node_id, top.to_node_id) == (43, MADRID, SEVILLA)
    assert top.alternative is not None
    assert (top.alternative.extra_km, top.alternative.extra_min) == (97.0, 104)
