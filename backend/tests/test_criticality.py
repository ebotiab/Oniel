"""Trenes por tramo y alternativa en la red cargada, sobre la red de la instantánea del visor."""

from __future__ import annotations

import json
from pathlib import Path
from typing import Any

import pytest

from oniel.analysis.criticality import (
    SCOPE_NOTE,
    ServicePath,
    corridor,
    other_way,
    segment_alternatives,
)
from oniel.domain.schemas import (
    AlternativesOut,
    LineSummary,
    NetworkIndexOut,
    SegmentAlternativesOut,
    SegmentOut,
)
from oniel.routing import (
    DEFAULT_MAX_RATIO,
    Graph,
    Scenario,
    ScenarioError,
    build_graph,
    find_routes,
    route_along,
)

DATA = Path(__file__).resolve().parents[2] / "frontend" / "public" / "data"

LAV, CONV, MZCR, JAEN, LBMG, ALBACETE = (
    "lav-madrid-sevilla",
    "convencional-madrid-alcazar-cordoba",
    "manzanares-ciudad-real",
    "espeluy-jaen",
    "linares-baeza-moreda-granada",
    "alcazar-albacete",
)
LAV_MALAGA, LAV_GRANADA = "lav-cordoba-malaga", "lav-antequera-granada"
BCN = "lav-madrid-barcelona"
LAV_VALENCIA = "lav-madrid-valencia"
LAV_ALICANTE = "lav-albacete-alicante"
LAV_MURCIA = "lav-monforte-murcia"
MEDITERRANEO = "valencia-castello-tarragona"
LAV_VALLADOLID = "lav-madrid-valladolid"
MADRID, CORDOBA, SEVILLA = "madrid-puerta-de-atocha", "cordoba", "sevilla-santa-justa"
ADAMUZ_CORDOBA = f"{LAV}:adamuz:cordoba"
CORDOBA_BIF_MALAGA = f"{LAV}:cordoba:bif-malaga"
ALMAGRO_CIUDAD_REAL = f"{MZCR}:almagro:ciudad-real"
ALBACETE_NODES = [
    "alcazar-de-san-juan",
    "campo-de-criptana",
    "socuellamos",
    "villarrobledo",
    "minaya",
    "la-roda-de-albacete",
    "la-gineta",
    "albacete-los-llanos",
]
ALBACETE_SEGMENTS = [
    f"{ALBACETE}:{a}:{b}" for a, b in zip(ALBACETE_NODES, ALBACETE_NODES[1:], strict=False)
]


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
    assert (group.length_km, group.time_min, group.line_ids) == (343.6, 80, [LAV])
    alternative = group.alternative
    assert alternative is not None
    # con Adamuz – Córdoba cerrado queda la línea convencional entera: 440,7 km frente a 343,6
    assert alternative.line_ids == [CONV]
    assert (alternative.length_km, alternative.extra_km) == (440.7, 97.1)
    assert alternative.time_min is not None and alternative.extra_min == alternative.time_min - 80
    assert alternative.single_track_km == 194.1
    assert alternative.via[:2] == ["Aranjuez", "Alcázar de San Juan"]


def test_towards_sevilla_there_is_no_other_way_in_the_loaded_lines(graph: Graph) -> None:
    trains = [ServicePath("ave-1", "renfe", _path(graph, MADRID, SEVILLA))]
    result = segment_alternatives(graph, trains)
    south = _of(result, f"{LAV}:bif-malaga:majarabique")
    assert (south.trains, south.with_alternative, south.without_alternative) == (1, 0, 1)
    assert south.groups[0].alternative is None
    # entre Córdoba y la bifurcación de Málaga sí lo hay desde que Granada está unida por los dos
    # lados: por Linares-Baeza, Moreda, Granada y Antequera, 340 km más largo
    first = _of(result, CORDOBA_BIF_MALAGA)
    assert (first.with_alternative, first.without_alternative) == (1, 0)
    assert first.groups[0].alternative is not None
    assert first.groups[0].alternative.line_ids == [CONV, LBMG, LAV_GRANADA, LAV_MALAGA, LAV]
    assert first.groups[0].alternative.extra_km == 340.2
    # el mismo tren, al norte de Córdoba, sí tiene otro camino
    north = _of(result, ADAMUZ_CORDOBA)
    assert north.without_alternative == 0
    assert north.groups[0].to_node_id == SEVILLA


def test_another_way_counts_even_if_it_changes_line_more_often_than_the_comparator_allows(
    graph: Graph,
) -> None:
    """Un tren de Valencia a Valladolid cruza Madrid por Chamartín. Con un tramo cerrado entre
    Torrejón de Velasco y la bifurcación de Albacete, su otro camino baja a Albacete, sube por
    Alcázar de San Juan a Madrid-Puerta de Atocha y vuelve a Torrejón de Velasco para tomar el
    túnel: seis cambios de línea, uno más de los que el comparador enumera por defecto."""
    valencia, valladolid = "valencia-joaquin-sorolla", "valladolid-campo-grande"
    closed_segment = f"{LAV_VALENCIA}:horcajada:cuenca-fernando-zobel"
    own = _path(graph, valencia, valladolid)
    assert closed_segment in own
    assert not find_routes(graph, valencia, valladolid, Scenario(closures=[closed_segment]))
    segment = _of(segment_alternatives(graph, [ServicePath("ave-1", "renfe", own)]), closed_segment)
    assert (segment.with_alternative, segment.without_alternative) == (1, 0)
    alternative = segment.groups[0].alternative
    assert alternative is not None
    assert ALBACETE in alternative.line_ids and CONV in alternative.line_ids
    assert alternative.extra_km == pytest.approx(167.1, abs=0.2)


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


def test_a_way_round_of_more_than_twice_the_journey_is_not_another_way(graph: Graph) -> None:
    """El tope del comparador y de los rodeos de un cierre vale también aquí, medido contra el
    recorrido del propio tren: con la red en anillo siempre existe la vuelta entera."""
    # de Madrid a Córdoba, 343,6 km por la alta velocidad y 440,7 por la convencional: cuenta
    own, other = find_routes(graph, MADRID, CORDOBA, max_changes=0)
    assert other_way(own, [other], DEFAULT_MAX_RATIO) is other
    assert other_way(own, [other], 1.2) is None and other_way(own, [other], None) is other
    assert other_way(own, [], DEFAULT_MAX_RATIO) is None
    # un tren que solo recorre Urda – Ciudad Real: el rodeo por Manzanares pasa del doble
    short = route_along(graph, "urda", [f"{LAV}:urda:ciudad-real"])
    round_about = find_routes(
        graph, "urda", "ciudad-real", Scenario(closures=[short.segment_ids[0]]), max_ratio=None
    )
    assert round_about and round_about[0].length_km > 2 * short.length_km
    assert other_way(short, round_about, DEFAULT_MAX_RATIO) is None
    assert other_way(short, round_about, None) is round_about[0]


def test_snapshot_says_which_segments_leave_their_trains_without_alternative(
    lines: list[LineSummary],
) -> None:
    """La instantánea, con los trenes del día de referencia (13 de noviembre de 2026)."""
    exported = AlternativesOut.model_validate(_read("alternatives.json"))
    assert exported.scope_note == SCOPE_NOTE and "líneas que Oniel tiene cargadas" in SCOPE_NOTE
    assert exported.line_ids == [
        LAV,
        CONV,
        MZCR,
        JAEN,
        LBMG,
        ALBACETE,
        LAV_MALAGA,
        LAV_GRANADA,
        BCN,
        LAV_VALENCIA,
        "baipas-zaragoza",
        "baipas-lleida",
        LAV_ALICANTE,
        LAV_MURCIA,
        MEDITERRANEO,
        LAV_VALLADOLID,
    ]
    assert exported.missing_operator_ids == ["iryo"]
    # los trenes de cada tramo son los mismos pasos que cuenta su línea, por operador
    counts: dict[str, int] = {}
    by_operator: dict[str, dict[str, int]] = {}
    for line in lines:
        detail = _read(f"lines/{line.id}.json")
        assert detail["date"] == str(exported.date)
        counts |= detail["counts"]
        by_operator |= detail["counts_by_operator"]
    # los dos baipases, los nueve de la línea de Albacete a Alicante, los ocho de la de Monforte
    # del Cid a Murcia y los 35 de la de Valencia a Camp de Tarragona
    # Monforte del Cid a Murcia
    assert len(exported.segments) == 54 + 8 + 8 + 20 + 2 + 14 + 2 + 9 + 8 + 35 + 5
    for s in exported.segments:
        assert s.trains == counts.get(s.segment_id, 0) == sum(g.trains for g in s.groups)
        assert s.by_operator == by_operator.get(s.segment_id, {})
        assert s.with_alternative + s.without_alternative == s.trains
    # no queda otro camino hacia Sevilla, adonde Oniel solo llega por la alta velocidad, ni en
    # el ramal de Jaén, que acaba en una estación término
    # Un camino de más del doble que el recorrido del tren no cuenta como otro camino. «Sin otro
    # camino» es el tramo en el que ningún tren lo tiene (`none`); en otros se queda sin él solo
    # una parte de los trenes, los de recorrido corto
    without = {
        s.segment_id: s.without_alternative for s in exported.segments if s.without_alternative
    }
    none = {k: n for k, n in without.items() if n == _of(exported.segments, k).trains}
    assert (len(none), len(without)) == (48, 115)
    apart = (
        f"{BCN}:",
        f"{LAV_VALENCIA}:",
        f"{LAV_ALICANTE}:",
        f"{LAV_MURCIA}:",
        f"{MEDITERRANEO}:",
        f"{LAV_VALLADOLID}:",
    )
    assert {k: n for k, n in none.items() if not k.startswith(apart)} == {
        f"{LAV}:bif-malaga:majarabique": 83,
        f"{LAV}:majarabique:sevilla-santa-justa": 81,
        f"{JAEN}:espeluy:mengibar-artichuela": 26,
        f"{JAEN}:mengibar-artichuela:jaen": 26,
        # a Málaga solo llega la alta velocidad de Córdoba, y el enlace de la bifurcación Gobantes
        # hacia Granada no está cargado
        f"{LAV_MALAGA}:antequera-santa-ana:bif-gobantes": 57,
        f"{LAV_MALAGA}:bif-gobantes:pb-alora": 63,
        f"{LAV_MALAGA}:pb-alora:paet-los-prados": 63,
        f"{LAV_MALAGA}:paet-los-prados:malaga-maria-zambrano": 63,
        # los dos trenes de Linares-Baeza a Almería: la vuelta por Córdoba, Antequera y Granada
        # mide más del doble
        f"{LBMG}:linares-baeza:jodar-ubeda": 2,
        f"{LBMG}:jodar-ubeda:cabra-del-santo-cristo": 2,
        f"{LBMG}:cabra-del-santo-cristo:moreda": 2,
    }
    # desde que Albacete está unida a Madrid por dos caminos, el convencional por Alcázar de San
    # Juan y el de alta velocidad por Cuenca, cada uno es el otro camino del otro: los 13 trenes
    # de Alcázar de San Juan a Albacete, los 86 de la línea de Valencia hasta la bifurcación de
    # Albacete (84 en el primer tramo) y los 44 de esa bifurcación a Albacete tienen alternativa
    for segment_id in ALBACETE_SEGMENTS:
        assert _of(exported.segments, segment_id).trains == 13
    trunk = [s for s in exported.segments if s.segment_id.startswith(f"{LAV_VALENCIA}:")]
    # los dos primeros tramos son el túnel y el acceso desde Madrid-Chamartín: 74 trenes, los que
    # salen de Chamartín; los 10 que faltan hasta 84 entran por la bifurcación de Torrejón de
    # Velasco desde Madrid-Puerta de Atocha
    assert [s.trains for s in trunk[:10]] == [74, 74, 84] + [86] * 7
    assert all(s.without_alternative == 0 for s in trunk[2:10])
    # La línea de Valencia a Camp de Tarragona cierra un anillo con la de Madrid a Valencia y la de
    # Madrid a Barcelona, pero dar la vuelta entera no cuenta: de la bifurcación de Albacete a
    # València solo tienen otro camino los 4 AVE de Madrid a Castelló; los de Madrid a València,
    # no. Y a Madrid-Chamartín no llega ninguna otra línea cargada: sus dos tramos, sin otro camino
    valencia = [s for s in exported.segments if s.segment_id.startswith(f"{LAV_VALENCIA}:")]
    assert [(s.trains, s.without_alternative) for s in valencia[10:]] == [
        (42, 38),
        (42, 38),
        (52, 48),
        (52, 48),
    ]
    assert {s: n for s, n in none.items() if s.startswith(f"{LAV_VALENCIA}:")} == {
        f"{LAV_VALENCIA}:madrid-chamartin:paso-bajo-atocha": 74,
        f"{LAV_VALENCIA}:paso-bajo-atocha:bif-torrejon-de-velasco": 74,
    }
    # y en la de Albacete a Alicante, los siete que van de Albacete a Alicante: 42 trenes hasta
    # la bifurcación de Murcia, 36 de allí a Monforte del Cid (los 6 de Madrid a Murcia que no
    # entran en Alicante ya han salido) y 56 de Monforte del Cid a Alicante, con los 20 Avant de
    # Alicante a Murcia. De la bifurcación a Albacete, 44, con otro camino
    alicante = [s for s in exported.segments if s.segment_id.startswith(f"{LAV_ALICANTE}:")]
    assert [(s.trains, s.without_alternative) for s in alicante] == [
        (44, 0),
        (44, 0),
        (42, 42),
        (42, 42),
        (42, 42),
        (42, 42),
        (42, 42),
        (36, 36),
        (56, 56),
    ]
    # a Murcia solo llega la alta velocidad de Monforte del Cid: ninguno de sus ocho tramos tiene
    # otro camino. Por el primero solo pasan los 6 trenes de Madrid que no entran en Alicante; en
    # la bifurcación Vinalopó se suman los que vienen de Alicante por el enlace, que no está
    # cargado, y son 36 hasta Murcia
    murcia = [s for s in exported.segments if s.segment_id.startswith(f"{LAV_MURCIA}:")]
    assert [(s.trains, s.without_alternative) for s in murcia] == [(6, 6)] + [(36, 36)] * 7
    assert murcia[0].by_operator == {"ouigo": 2, "renfe": 4}
    assert all(s.by_operator == {"ouigo": 6, "renfe": 30} for s in murcia[1:])
    # De la alta velocidad de Barcelona solo quedan los tres tramos de Camp de Tarragona a
    # Barcelona-Sants, fuera del anillo, con sus 108 trenes
    # la de Madrid a Valladolid entera: es la única cargada al norte de Madrid. 122 trenes hasta
    # Segovia, 111 hasta la bifurcación Medina, donde salen los de Galicia, y 81 hasta Valladolid
    valladolid = [s for s in exported.segments if s.segment_id.startswith(f"{LAV_VALLADOLID}:")]
    assert [(s.trains, s.without_alternative) for s in valladolid] == [
        (122, 122),
        (122, 122),
        (111, 111),
        (111, 111),
        (81, 81),
    ]
    # tampoco en la alta velocidad de Barcelona, que solo comparte con las demás la cabecera de
    # Madrid: quince de sus veinte tramos no tienen otro camino cargado
    barcelona = [s for s in exported.segments if s.segment_id.startswith(f"{BCN}:")]
    assert len(barcelona) == 20
    assert {s: n for s, n in none.items() if s.startswith(f"{BCN}:")} == {
        f"{BCN}:camp-de-tarragona:l-arboc": 108,
        f"{BCN}:l-arboc:vilafranca-del-penedes": 108,
        f"{BCN}:vilafranca-del-penedes:barcelona-sants": 108,
    }
    assert _of(exported.segments, f"{BCN}:madrid-puerta-de-atocha:bif-vallecas-av").trains == 74
    # los cinco que entran y salen de Zaragoza-Delicias y de Lleida-Pirineus sí lo tienen: el
    # baipás. Y solo llevan los trenes que paran en la estación o salen de la línea por ella
    stations = {
        f"{BCN}:bif-moncasi:zaragoza-delicias": 56,
        f"{BCN}:zaragoza-delicias:bif-huesca": 55,
        f"{BCN}:bif-huesca:bif-canal-imperial": 51,
        f"{BCN}:bif-les-torres-de-sanui:lleida-pirineus": 31,
        f"{BCN}:lleida-pirineus:bif-artesa-de-lleida": 47,
    }
    for s in barcelona:
        if s.segment_id in stations:
            assert (s.trains, s.without_alternative) == (stations[s.segment_id], 0)
    # los baipases llevan los que no paran: 22 el de Zaragoza y 42 el de Lleida. Con el baipás
    # cortado entrarían en la estación, 4,9 km y 6 minutos más en Zaragoza
    around_zaragoza = _of(exported.segments, "baipas-zaragoza:bif-moncasi:bif-canal-imperial")
    assert (around_zaragoza.trains, around_zaragoza.without_alternative) == (22, 0)
    assert around_zaragoza.by_operator == {"ouigo": 4, "renfe": 18}
    (direct,) = around_zaragoza.groups
    assert (direct.from_node_id, direct.to_node_id) == (MADRID, "barcelona-sants")
    assert (direct.length_km, direct.line_ids) == (620.1, [BCN])
    assert direct.alternative is not None and direct.alternative.line_ids == [BCN]
    assert (direct.alternative.extra_km, direct.alternative.extra_min) == (4.9, 6)
    around_lleida = _of(
        exported.segments, "baipas-lleida:bif-les-torres-de-sanui:bif-artesa-de-lleida"
    )
    assert (around_lleida.trains, around_lleida.without_alternative) == (42, 0)
    # lo que llega a cada bifurcación sale de ella por la estación o por el baipás
    before = _of(exported.segments, f"{BCN}:cambiador-plasencia-de-jalon:bif-moncasi").trains
    assert before == 78 == stations[f"{BCN}:bif-moncasi:zaragoza-delicias"] + 22
    after = _of(exported.segments, f"{BCN}:bif-artesa-de-lleida:l-espluga-de-francoli").trains
    assert after == 89 == stations[f"{BCN}:lleida-pirineus:bif-artesa-de-lleida"] + 42
    # De la línea nueva, el primer tramo, porque a València-Estació del Nord solo se llega por
    # él, y los dieciséis de Castelló a Camp de Tarragona: la vuelta por Madrid mide más del doble
    # para todos sus trenes. De Joaquín Sorolla a Castelló solo la tienen los 4 AVE de Madrid
    coast_none = {s: n for s, n in none.items() if s.startswith(f"{MEDITERRANEO}:")}
    assert len(coast_none) == 17
    assert coast_none[f"{MEDITERRANEO}:valencia-estacio-del-nord:valencia-joaquin-sorolla"] == 54
    assert coast_none[f"{MEDITERRANEO}:cambiador-la-boella:camp-de-tarragona"] == 19
    partly = _of(exported.segments, f"{MEDITERRANEO}:almassora:castello-de-la-plana")
    assert (partly.trains, partly.without_alternative) == (52, 48)
    # un regional de València a Vinaròs (151,0 km) no tiene otro camino: los 1.026 km por Madrid
    # no cuentan
    coast = _of(exported.segments, f"{MEDITERRANEO}:castello-de-la-plana:benicassim")
    regional = next(
        g
        for g in coast.groups
        if (g.from_node_id, g.to_node_id) == ("valencia-estacio-del-nord", "vinaros")
    )
    assert (regional.trains, regional.length_km) == (22, 151.0)
    assert regional.alternative is None
    # Granada queda unida por los dos lados (la convencional de Moreda y la alta velocidad de
    # Antequera), así que ni la alta velocidad de Granada ni Córdoba – bifurcación de Málaga
    # figuran ya: sus trenes de largo recorrido tienen otro camino, aunque sea por una línea de
    # otro ancho. Los de recorrido corto (los Avant de Sevilla, Málaga y Granada), no
    first = _of(exported.segments, CORDOBA_BIF_MALAGA)
    assert (first.trains, first.without_alternative) == (140, 22)
    loja = _of(exported.segments, f"{LAV_GRANADA}:loja:bif-tocon")
    assert (loja.trains, loja.without_alternative) == (24, 14)
    # para los 6 trenes de Madrid a Granada (los dos Alvia que siguen a Almería cuentan con
    # ese destino, no con Granada), el otro camino, por Moreda, es 81,7 km más corto
    to_granada = next(
        g for g in loja.groups if (g.from_node_id, g.to_node_id) == (MADRID, "granada")
    )
    assert to_granada.trains == 6 and to_granada.alternative is not None
    assert to_granada.alternative.line_ids == [CONV, LBMG]
    assert to_granada.alternative.extra_km == -81.7
    assert _of(exported.segments, f"{LAV_MALAGA}:bif-malaga:la-marota").trains == 77
    # entre la estación de Moreda y la bifurcación no pasa ningún tren de los horarios
    assert _of(exported.segments, f"{LBMG}:moreda:bif-almeria").trains == 0
    # el grupo más numeroso de Adamuz – Córdoba: los 41 trenes entre Madrid y Sevilla
    top = _of(exported.segments, ADAMUZ_CORDOBA).groups[0]
    assert (top.trains, top.from_node_id, top.to_node_id) == (41, MADRID, SEVILLA)
    assert top.alternative is not None
    assert (top.alternative.extra_km, top.alternative.extra_min) == (97.0, 106)
