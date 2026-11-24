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
    shortest_route,
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
LAV_LEON = "lav-valladolid-leon"
LAV_OURENSE = "lav-olmedo-ourense"
LAV_BURGOS = "lav-venta-de-banos-burgos"
LEON_GIJON = "leon-oviedo-gijon"
BURGOS_VITORIA = "burgos-miranda-vitoria"
LAV_SANTIAGO = "lav-ourense-santiago"
EJE_ATLANTICO = "eje-atlantico"
SEVILLA_CADIZ = "sevilla-cadiz"
LAV_FIGUERES = "lav-barcelona-figueres"
LINK = "enlace-monforte-del-cid"
#: Las cuatro líneas de Extremadura: de Madrid a Plasencia, la de alta velocidad hasta Badajoz,
#: la de Aljucén a Mérida y el trazado antiguo de Monfragüe a Cáceres.
MADRID_PLASENCIA, LAV_BADAJOZ, RAMAL_MERIDA, MONFRAGUE_CACERES = (
    "madrid-plasencia",
    "lav-plasencia-badajoz",
    "ramal-merida",
    "monfrague-caceres",
)
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
    return build_graph(lines, index.nodes, segments, index.turns)


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
    # entre Córdoba y la bifurcación de Málaga tampoco. Existe la vuelta por Linares-Baeza,
    # Moreda, Granada y Antequera, pero llega a la bifurcación de Málaga por la línea de Málaga,
    # que sale de ella hacia el mismo lado que la de Sevilla: para seguir a Sevilla habría que
    # llegar a Córdoba e invertir la marcha, y ese es el tramo cerrado
    first = _of(result, CORDOBA_BIF_MALAGA)
    assert (first.with_alternative, first.without_alternative) == (0, 1)
    assert first.groups[0].alternative is None
    # un tren a Málaga sí la tiene: llega a su línea sin pasar por la bifurcación hacia Sevilla
    to_malaga = [ServicePath("ave-2", "renfe", _path(graph, MADRID, "malaga-maria-zambrano"))]
    by_granada = _of(segment_alternatives(graph, to_malaga), CORDOBA_BIF_MALAGA)
    assert (by_granada.with_alternative, by_granada.without_alternative) == (1, 0)
    alternative = by_granada.groups[0].alternative
    assert alternative is not None
    assert alternative.line_ids == [CONV, LBMG, LAV_GRANADA, LAV_MALAGA]
    # el mismo tren, al norte de Córdoba, sí tiene otro camino
    north = _of(result, ADAMUZ_CORDOBA)
    assert north.without_alternative == 0
    assert north.groups[0].to_node_id == SEVILLA


def test_another_way_counts_however_many_lines_it_chains(graph: Graph) -> None:
    """El otro camino de un tren es el más corto que hay, encadene las líneas que encadene.

    Un tren de Valencia a Valladolid cruza Madrid por Chamartín. Con un tramo cerrado entre
    Torrejón de Velasco y la bifurcación de Albacete, su otro camino es el más corto que da el
    grafo con ese tramo cerrado, sin tope de cambios de línea (hasta noviembre de 2026 se buscaba
    primero con un tope de cinco)."""
    valencia, valladolid = "valencia-joaquin-sorolla", "valladolid-campo-grande"
    closed_segment = f"{LAV_VALENCIA}:horcajada:cuenca-fernando-zobel"
    own = _path(graph, valencia, valladolid)
    assert closed_segment in own
    shortest = shortest_route(graph, valencia, valladolid, Scenario(closures=[closed_segment]))
    assert shortest is not None and len(shortest.legs) > 2
    segment = _of(segment_alternatives(graph, [ServicePath("ave-1", "renfe", own)]), closed_segment)
    assert (segment.with_alternative, segment.without_alternative) == (1, 0)
    alternative = segment.groups[0].alternative
    assert alternative is not None
    assert (alternative.length_km, alternative.line_ids) == (shortest.length_km, shortest.line_ids)


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


def test_corridor_of_a_train_that_leaves_a_terminus_by_a_link_stops_at_the_station(
    graph: Graph,
) -> None:
    """Un tren de Madrid a Murcia que para en Alicante entra en la estación y vuelve a salir por
    el enlace de Monforte del Cid: pasa dos veces por el tramo de Monforte del Cid a Alicante y
    sus tramos se bifurcan en Monforte del Cid. Su recorrido se toma sin el enlace, como antes de
    cargarlo: hasta Alicante por un lado y, por el otro, desde la bifurcación Vinalopó."""
    link = f"{LINK}:monforte-del-cid-av:bif-vinalopo"
    to_alicante = [
        f"{LAV_ALICANTE}:villena-av:bif-murcia",
        f"{LAV_ALICANTE}:bif-murcia:monforte-del-cid-av",
        f"{LAV_ALICANTE}:monforte-del-cid-av:alicante-terminal",
    ]
    to_murcia = [
        f"{LAV_MURCIA}:bif-vinalopo:elche-av",
        f"{LAV_MURCIA}:elche-av:san-isidro-albatera-catral-av",
    ]
    train = [*to_alicante, link, *to_murcia]
    start, path = corridor(graph, train, to_alicante[0])
    assert (start, [e.id for e in path]) == ("villena-av", to_alicante)
    start, path = corridor(graph, train, to_murcia[1])
    assert (start, [e.id for e in path]) == ("bif-vinalopo", to_murcia)
    # el propio enlace no tiene un trecho sin bifurcaciones: se queda en su tramo
    start, path = corridor(graph, train, link)
    assert (start, [e.id for e in path]) == ("monforte-del-cid-av", [link])
    # un Avant de Alicante a Murcia no se bifurca: su recorrido va entero por el enlace
    avant = [to_alicante[2], link, *to_murcia]
    start, path = corridor(graph, avant, link)
    assert (start, [e.id for e in path]) == ("alicante-terminal", avant)


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


def test_snapshot_alternatives_add_up_with_the_counts_of_each_line(
    lines: list[LineSummary],
) -> None:
    """La instantánea, sea cual sea su día de referencia: lo que no depende del horario cargado.

    El día de referencia se mueve con cada fichero de horarios nuevo, y con él los trenes de cada
    tramo. Los recuentos se comprueban con los ficheros fijos de ``conftest.py``, en
    ``test_integration_db.py``, con :func:`assert_alternatives_of_13_november_2026`.
    """
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
        LINK,
        LAV_VALLADOLID,
        MADRID_PLASENCIA,
        LAV_BADAJOZ,
        RAMAL_MERIDA,
        MONFRAGUE_CACERES,
        LAV_LEON,
        LAV_OURENSE,
        LAV_BURGOS,
        LEON_GIJON,
        BURGOS_VITORIA,
        LAV_SANTIAGO,
        EJE_ATLANTICO,
        SEVILLA_CADIZ,
        LAV_FIGUERES,
        "lav-la-sagra-toledo",
        "lav-zaragoza-huesca",
        "barcelona-girona-portbou",
        "tarragona-barcelona",
        "valencia-xativa-alicante",
        "madrid-avila-valladolid",
        "palencia-santander",
        "zaragoza-castejon-logrono",
        "castejon-pamplona",
        "miranda-bilbao",
        "sevilla-huelva",
        "enlace-soto-de-cerrato",
        "enlace-aljucen-la-garrovilla",
        "enlace-atocha-chamartin",
    ]
    assert exported.missing_operator_ids == []
    # los trenes de cada tramo son los mismos pasos que cuenta su línea, por operador
    counts: dict[str, int] = {}
    by_operator: dict[str, dict[str, int]] = {}
    for line in lines:
        detail = _read(f"lines/{line.id}.json")
        assert detail["date"] == str(exported.date)
        counts |= detail["counts"]
        by_operator |= detail["counts_by_operator"]
    # los dos de después de la línea de Valencia son los baipases; los nueve siguientes, la
    # línea de Albacete a Alicante; los ocho de después, la de Monforte del Cid a Murcia; los 35,
    # la de Valencia a Camp de Tarragona; los 5, la de Madrid a
    # Valladolid; el 1, el enlace de Monforte del Cid; los 13, 14, 2 y 4 del final, las
    # cuatro de Extremadura; los 8, la de Valladolid a León; los 13, la de Olmedo a Ourense, y los
    # 4 siguientes, la de Venta de Baños a Burgos; los 11, la de León a Gijón; los 7, la de Burgos a
    # Vitoria; los 3 y los 15 de después, las dos de Galicia, y los 16 del final, la de Sevilla a Cádiz, y el 1 y
    # los 2 de después, los ramales de Toledo y de Huesca
    assert (
        len(exported.segments)
        == (
            54
            + 8
            + 8
            + 20
            + 2
            + 14
            + 2
            + 9
            + 8
            + 35
            + 5
            + 1
            + 13
            + 14
            + 2
            + 4
            + 8
            + 13
            + 4
            + 11
            + 7
        )
        + (3 + 15)
        + 16
        + 7  # la de Barcelona a Figueres
        + (1 + 2)
        + 26  # la de Barcelona a Portbou
        + 8  # la de Tarragona a Barcelona por la costa
        + 20  # la de València a Alicante por Xàtiva
        + 27  # la de Madrid a Valladolid por Ávila
        + 21  # la de Palencia a Santander
        + (18 + 5)  # las de Zaragoza a Logroño y de Castejón a Pamplona
        + 3  # la de Miranda de Ebro a Bilbao
        + 11  # la de Sevilla a Huelva
        + (1 + 1 + 3)  # los enlaces de Soto de Cerrato y de Aljucén y el túnel de Madrid
    )
    for s in exported.segments:
        assert s.trains == counts.get(s.segment_id, 0) == sum(g.trains for g in s.groups)
        assert s.by_operator == by_operator.get(s.segment_id, {})
        assert s.with_alternative + s.without_alternative == s.trains


def assert_alternatives_of_13_november_2026(exported: AlternativesOut) -> None:
    """Qué tramos dejan a sus trenes sin otro camino, con los trenes del 13 de noviembre de 2026.

    Son los de los ficheros fijos de ``conftest.py``: no cambian cuando se carga un horario nuevo.
    """
    # no queda otro camino hacia Sevilla, adonde Oniel solo llega por la alta velocidad, ni en
    # el ramal de Jaén, que acaba en una estación término
    # Un camino de más del doble que el recorrido del tren no cuenta como otro camino. «Sin otro
    # camino» es el tramo en el que ningún tren lo tiene (`none`); en otros se queda sin él solo
    # una parte de los trenes, los de recorrido corto
    without = {
        s.segment_id: s.without_alternative for s in exported.segments if s.without_alternative
    }
    none = {k: n for k, n in without.items() if n == _of(exported.segments, k).trains}
    # 54 y 121 sin Extremadura, con el enlace de Monforte del Cid. Con sus cuatro líneas, 29 tramos más sin otro camino para ningún
    # tren, y otros 4 en los que se queda sin él una parte: tres junto a sus bifurcaciones y el de
    # la convencional de Madrid-Puerta de Atocha a la bifurcación Planetario
    # y los ocho de la línea de Valladolid a León, la única cargada al norte de Valladolid
    # y los trece de la de Olmedo a Ourense, el único camino cargado a Zamora y a Galicia
    # y los cuatro de la de Venta de Baños a Burgos, el único camino cargado a Burgos
    # la de Burgos, entera: los 18 que dejan la línea de León en Venta de Baños y, desde Soto de
    # Cerrato, 20 con los 2 que llegan de Palencia por el ramal
    burgos = {k: n for k, n in none.items() if k.startswith(f"{LAV_BURGOS}:")}
    assert len(burgos) == 4 and sorted(set(burgos.values())) == [18, 20]
    # y los once de la de León a Gijón, la única cargada al norte de León, y los siete de la de
    # Burgos a Vitoria, el único camino cargado a Miranda de Ebro y a Vitoria
    # y los dieciséis de la de Sevilla a Cádiz, el único camino cargado a Jerez y a Cádiz
    # y los tres de los ramales de Toledo y de Huesca, que acaban en una estación término; con
    # ellos se queda sin otro camino una parte de los trenes en otros catorce: los Avant de Toledo
    # en los cuatro de la línea de Sevilla hasta La Sagra y los 2 de Albacete a Toledo, que cambian
    # de sentido en Atocha, en los diez de la bifurcación de Torrejón de Velasco a Albacete
    # y con la de Tarragona a Barcelona por la costa, los tres de la alta velocidad de Camp de
    # Tarragona a Barcelona-Sants y los dos de la de València de La Feredat a Camp de Tarragona
    # tienen otro camino; en cuatro de la nueva se queda sin él una parte de los trenes: los de
    # Tarragona a Lleida por Reus y los de Lleida por Valls
    # La línea de València a Alicante por Xàtiva cierra un anillo con la alta velocidad de Valencia
    # y la de Albacete a Alicante: dejan de estar sin otro camino los siete tramos de Albacete a
    # Alicante, el primero de la línea de Murcia y los quince que quedaban de la costa, 23 en
    # total, porque sus trenes de largo recorrido tienen la vuelta por València y Xàtiva o por
    # Madrid. De los que se quedan sin él solo en parte salen nueve, en los que ya lo tienen
    # todos, y entran los veinte de la línea nueva
    # La convencional de Madrid a Valladolid por Ávila da otro camino a casi todos los trenes de la
    # alta velocidad de Valladolid: sus cinco tramos dejan de estar sin otro camino para ninguno,
    # y en el último, de la bifurcación Medina a Valladolid, lo tienen todos. De la línea nueva,
    # los cuatro de Chamartín a Pinar de las Rozas quedan sin él para todos, y los veintisiete,
    # sin él para una parte
    # La de Palencia a Santander acaba en Santander, adonde no llega otra línea cargada: sus
    # veintiún tramos quedan sin otro camino para todos sus trenes
    # Las de Zaragoza a Logroño y de Castejón a Pamplona son el único camino cargado entre
    # Zaragoza, Logroño y Pamplona: sus veintitrés tramos quedan sin otro camino para todos
    # La de Miranda de Ebro a Bilbao acaba en Bilbao, adonde no llega otra línea cargada: sus tres
    # tramos quedan sin otro camino para todos sus trenes
    # La de Sevilla a Huelva acaba en Huelva, adonde no llega otra línea cargada: sus once tramos
    # quedan sin otro camino para todos sus trenes
    assert (len(none), len(without)) == (
        54
        + 29
        + 8
        + 13
        + 4
        + 11
        + 7
        + 3
        + 15
        + 16
        + 2
        + 3
        + 12
        - 5
        - 23
        - 5
        + 4
        + 21
        + 23
        + 3
        + 11
        # los enlaces de Soto de Cerrato y de Aljucén quedan sin otro camino para todos, y los dos
        # tramos de la línea de Valencia de Chamartín a Torrejón de Velasco dejan de estarlo: sus
        # trenes tienen el túnel de Atocha a Chamartín y la línea convencional
        + 2
        - 2,
        121
        + 29
        + 4
        + 8
        + 13
        + 4
        + 11
        + 7
        + 3
        + 15
        + 16
        + 2
        + 3
        + 14
        + 12
        - 5
        + 4
        - 9
        + 20
        - 1
        + 27
        + 21
        + 23
        + 3
        + 11
        # los dos enlaces y los tres tramos del túnel, sin él para una parte de sus trenes, menos
        # los dos de la línea de Valencia
        + 5
        - 2
        # con la regla de giro, cuatro en los que antes tenían otro camino todos: los dos de la
        # entrada a Zaragoza-Delicias y el de la salida de Lleida-Pirineus, porque desde el baipás
        # no se entra en la estación sin invertir la marcha, y el de Arroyo de la Herrera a la
        # bifurcación El Palmeral
        + 4,
    )
    # la de Barcelona a Figueres, de Girona al límite: a Figueres-Vilafant solo llega ella. De
    # Barcelona-Sants a Girona tiene otro camino, la convencional de Portbou
    figueres = {k: n for k, n in none.items() if k.startswith(f"{LAV_FIGUERES}:")}
    assert len(figueres) == 2
    # la de Barcelona a Portbou, de Girona a Portbou: a Figueres y a Portbou solo llega ella; 43
    # trenes hasta Flaçà, 42 hasta Figueres y 22 hasta Portbou
    portbou = {k: n for k, n in none.items() if k.startswith("barcelona-girona-portbou:")}
    assert len(portbou) == 12 and sorted(set(portbou.values())) == [22, 42, 43]
    # las dos de Galicia, enteras: a Santiago, A Coruña y Vigo solo llegan ellas
    santiago = {k: n for k, n in none.items() if k.startswith(f"{LAV_SANTIAGO}:")}
    assert len(santiago) == 3 and sorted(set(santiago.values())) == [43, 45]
    eje = {k: n for k, n in none.items() if k.startswith(f"{EJE_ATLANTICO}:")}
    assert len(eje) == 15 and sorted(set(eje.values())) == [35, 36, 51, 53, 55, 64]
    cadiz = {k: n for k, n in none.items() if k.startswith(f"{SEVILLA_CADIZ}:")}
    # la de Sevilla a Cádiz, entera: 56 trenes hasta la bifurcación Utrera y 42 desde allí
    assert len(cadiz) == 16 and sorted(set(cadiz.values())) == [42, 56]
    ramales = {
        k: n
        for k, n in none.items()
        if k.startswith(("lav-la-sagra-toledo:", "lav-zaragoza-huesca:"))
    }
    assert len(ramales) == 3
    vitoria = {k: n for k, n in none.items() if k.startswith(f"{BURGOS_VITORIA}:")}
    # la de Burgos a Vitoria, entera: 29 trenes de Burgos a Miranda de Ebro y 31 de Miranda a Vitoria
    assert len(vitoria) == 7 and sorted(set(vitoria.values())) == [29, 31]
    # la de León a Gijón, entera: 16 trenes donde van también los regionales y 14 en la variante
    # y de Villabona de Asturias a Gijón
    gijon = {k: n for k, n in none.items() if k.startswith(f"{LEON_GIJON}:")}
    assert len(gijon) == 11 and sorted(set(gijon.values())) == [14, 16]
    assert gijon[f"{LEON_GIJON}:la-robla-av:campomanes-av"] == 14
    # la de Olmedo a Ourense, entera: 30 trenes hasta Medina del Campo AV y 22 en los demás
    ourense = {k: n for k, n in none.items() if k.startswith(f"{LAV_OURENSE}:")}
    assert len(ourense) == 13 and sorted(set(ourense.values())) == [22, 30]
    # la de Palencia a Santander, entera: a Santander solo llega ella; los 13 trenes de ese día la
    # recorren de punta a punta
    santander = {k: n for k, n in none.items() if k.startswith("palencia-santander:")}
    assert len(santander) == 21 and set(santander.values()) == {13}
    # las de Zaragoza a Logroño y de Castejón a Pamplona, enteras: son el único camino cargado
    # entre Zaragoza, Logroño y Pamplona; los 28 trenes de Pamplona de ese día recorren la suya
    # de punta a punta
    ebro = {k: n for k, n in none.items() if k.startswith("zaragoza-castejon-logrono:")}
    pamplona = {k: n for k, n in none.items() if k.startswith("castejon-pamplona:")}
    assert len(ebro) == 18 and len(pamplona) == 5 and set(pamplona.values()) == {28}
    # la de Miranda de Ebro a Bilbao, entera: a Bilbao solo llega ella; los trenes de ese día la
    # recorren de punta a punta
    bilbao = {k: n for k, n in none.items() if k.startswith("miranda-bilbao:")}
    assert len(bilbao) == 3 and set(bilbao.values()) == {8}
    # la de Sevilla a Huelva, entera: a Huelva solo llega ella
    huelva = {k: n for k, n in none.items() if k.startswith("sevilla-huelva:")}
    assert len(huelva) == 11
    extremadura_lines = (
        f"{MADRID_PLASENCIA}:",
        f"{LAV_BADAJOZ}:",
        f"{RAMAL_MERIDA}:",
        f"{MONFRAGUE_CACERES}:",
    )
    apart = (
        f"{LAV_LEON}:",
        f"{LAV_OURENSE}:",
        f"{LAV_BURGOS}:",
        f"{LEON_GIJON}:",
        f"{BURGOS_VITORIA}:",
        f"{LAV_SANTIAGO}:",
        f"{EJE_ATLANTICO}:",
        f"{SEVILLA_CADIZ}:",
        f"{LAV_FIGUERES}:",
        "lav-la-sagra-toledo:",
        "lav-zaragoza-huesca:",
        "barcelona-girona-portbou:",
        f"{BCN}:",
        f"{LAV_VALENCIA}:",
        f"{LAV_ALICANTE}:",
        f"{LAV_MURCIA}:",
        f"{MEDITERRANEO}:",
        f"{LAV_VALLADOLID}:",
        f"{LINK}:",
        "palencia-santander:",
        "zaragoza-castejon-logrono:",
        "castejon-pamplona:",
        "miranda-bilbao:",
        "sevilla-huelva:",
        "enlace-soto-de-cerrato:",
        "enlace-aljucen-la-garrovilla:",
        *extremadura_lines,
    )
    # los enlaces de Soto de Cerrato y de Aljucén a La Garrovilla, sin otro camino para sus trenes:
    # los otros dos lados de cada triángulo obligarían a invertir la marcha
    assert none["enlace-soto-de-cerrato:bif-soto-de-cerrato:bif-cerrato"] == 2
    assert none["enlace-aljucen-la-garrovilla:aljucen:garrovilla-las-vegas"] == 16
    assert {k: n for k, n in none.items() if not k.startswith(apart)} == {
        f"{LAV}:bif-malaga:majarabique": 89,
        f"{LAV}:majarabique:sevilla-santa-justa": 87,
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
        # de Chamartín a Pinar de las Rozas solo pasan los regionales de Madrid a Villalba y a
        # Ávila: la vuelta por la alta velocidad de Valladolid mide más del doble
        **{
            f"madrid-avila-valladolid:{a}:{b}": 12
            for a, b in [
                ("madrid-chamartin", "madrid-ramon-y-cajal"),
                ("madrid-ramon-y-cajal", "mirasierra-paco-de-lucia"),
                ("mirasierra-paco-de-lucia", "pitis"),
                ("pitis", "pinar-de-las-rozas"),
            ]
        },
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
    # salvo para los 2 Avant de Albacete a Toledo, que cambian de sentido en Madrid-Puerta de
    # Atocha: sus tramos no forman un camino seguido y su recorrido se queda en cada tramo
    assert all(s.without_alternative == 2 for s in trunk[2:10])
    # La línea de Valencia a Camp de Tarragona cierra un anillo con la de Madrid a Valencia y la de
    # Madrid a Barcelona, pero dar la vuelta entera no cuenta: de la bifurcación de Albacete a
    # València solo tienen otro camino los 4 AVE de Madrid a Castelló; los de Madrid a València,
    # no. Y a Madrid-Chamartín no llega ninguna otra línea cargada: sus dos tramos, sin otro camino.
    # Desde que está cargada la línea de Madrid a Valladolid lo tienen también los 7 trenes de
    # Valencia a Valladolid: su recorrido es más largo (576 km) y la vuelta por Camp de Tarragona
    # y Madrid ya no pasa del doble
    valencia = [s for s in exported.segments if s.segment_id.startswith(f"{LAV_VALENCIA}:")]
    # Y desde que está cargada la línea de València a Alicante por Xàtiva lo tienen todos los que
    # vienen de Madrid, por Albacete, Alicante y Xàtiva (273 km más): solo se quedan sin él los 10
    # de Requena-Utiel a València
    assert [(s.trains, s.without_alternative) for s in valencia[10:]] == [
        (42, 0),
        (42, 0),
        (52, 10),
        (52, 10),
    ]
    # los dos tramos de Madrid-Chamartín a Torrejón de Velasco dejaron de estar sin otro camino
    # al cargarse el túnel de Atocha a Chamartín: sus trenes lo tienen por él y la convencional
    assert {s: n for s, n in none.items() if s.startswith(f"{LAV_VALENCIA}:")} == {}
    assert [(s.trains, s.without_alternative) for s in valencia[:2]] == [(74, 0), (74, 0)]
    # y en la de Albacete a Alicante, los siete que van de Albacete a Alicante: 42 trenes hasta
    # la bifurcación de Murcia, 36 de allí a Monforte del Cid (los 6 de Madrid a Murcia que no
    # entran en Alicante ya han salido) y 56 de Monforte del Cid a Alicante, con los 20 Avant de
    # Alicante a Murcia. De la bifurcación a Albacete, 44, con otro camino salvo los 2 Avant de
    # Albacete a Toledo
    alicante = [s for s in exported.segments if s.segment_id.startswith(f"{LAV_ALICANTE}:")]
    assert [(s.trains, s.without_alternative) for s in alicante] == [
        (44, 2),
        (44, 2),
        (42, 0),
        (42, 0),
        (42, 0),
        (42, 0),
        (42, 0),
        (36, 0),
        (56, 20),
    ]
    # (desde la línea de València a Alicante por Xàtiva, los de Madrid a Alicante tienen la vuelta
    # por València y Xàtiva, 95 km más: solo se quedan sin otro camino los 20 de Alicante a Murcia)
    # a Murcia solo llega la alta velocidad de Monforte del Cid: ninguno de sus ocho tramos tiene
    # otro camino. Por el primero solo pasan los 6 trenes de Madrid que no entran en Alicante; en
    # la bifurcación Vinalopó se suman los 30 que vienen de Alicante por el enlace de Monforte
    # del Cid, y son 36 hasta Murcia
    murcia = [s for s in exported.segments if s.segment_id.startswith(f"{LAV_MURCIA}:")]
    # (los 6 del primero sí lo tienen desde la línea de València a Alicante: la vuelta por València)
    assert [(s.trains, s.without_alternative) for s in murcia] == [(6, 0)] + [(36, 36)] * 7
    assert murcia[0].by_operator == {"ouigo": 2, "renfe": 4}
    assert all(s.by_operator == {"ouigo": 6, "renfe": 30} for s in murcia[1:])
    # el enlace tampoco tiene otro camino: los otros dos lados de su triángulo obligarían a
    # invertir la marcha en la bifurcación de Murcia
    link = _of(exported.segments, f"{LINK}:monforte-del-cid-av:bif-vinalopo")
    assert (link.trains, link.without_alternative) == (30, 30)
    assert link.by_operator == {"ouigo": 4, "renfe": 26}
    # ni en Extremadura, adonde solo se llega por la convencional de Madrid: sus 34 trenes hasta
    # Illescas, 24 hasta Talavera de la Reina y 20 hasta Monfragüe no tienen otro camino. Tampoco
    # la entrada a Plasencia, el paso por Cáceres, la línea nueva de allí a Badajoz ni el ramal
    # de Mérida, que acaban en estaciones a las que no llega otra línea cargada
    extremadura = {s: n for s, n in none.items() if s.startswith(extremadura_lines)}
    assert len(extremadura) == 12 + 11 + 2 + 4
    assert {s: n for s, n in extremadura.items() if s.startswith(extremadura_lines[0])} == {
        f"{MADRID_PLASENCIA}:bif-planetario:leganes": 34,
        f"{MADRID_PLASENCIA}:leganes:fuenlabrada": 34,
        f"{MADRID_PLASENCIA}:fuenlabrada:humanes": 34,
        f"{MADRID_PLASENCIA}:humanes:illescas": 34,
        f"{MADRID_PLASENCIA}:illescas:torrijos": 24,
        f"{MADRID_PLASENCIA}:torrijos:montearagon": 24,
        f"{MADRID_PLASENCIA}:montearagon:talavera-de-la-reina": 24,
        f"{MADRID_PLASENCIA}:talavera-de-la-reina:oropesa-de-toledo": 20,
        f"{MADRID_PLASENCIA}:oropesa-de-toledo:navalmoral-de-la-mata": 20,
        f"{MADRID_PLASENCIA}:navalmoral-de-la-mata:casatejada": 20,
        f"{MADRID_PLASENCIA}:casatejada:monfrague": 20,
        # los 12 que entran en Plasencia: la vuelta por Cañaveral y la línea nueva mide mucho
        # más del doble que los 2,6 km de este tramo, que es todo su recorrido por esta línea
        # desde la bifurcación
        f"{MADRID_PLASENCIA}:bif-el-chaparral:bif-san-esteban": 12,
    }
    lav_badajoz = {s: n for s, n in extremadura.items() if s.startswith(extremadura_lines[1])}
    assert lav_badajoz.pop(f"{LAV_BADAJOZ}:plasencia:bif-san-esteban") == 14
    # la entrada a Cáceres: los 20 de la línea nueva y los 2 regionales que llegan por Cañaveral
    assert lav_badajoz.pop(f"{LAV_BADAJOZ}:bif-casa-de-la-torre:caceres") == 20 + 2
    # de Cáceres a Badajoz, nueve tramos: 8 trenes en el de la bifurcación Granja-Las Encinas a
    # Garrovilla-Las Vegas, por el que solo pasan los que van de Cáceres a Badajoz sin entrar en
    # Mérida (los 16 que entran salen por la bifurcación y vuelven por Garrovilla-Las Vegas), y
    # 24 en cada uno de los otros ocho
    assert lav_badajoz.pop(f"{LAV_BADAJOZ}:bif-granja-las-encinas:garrovilla-las-vegas") == 8
    assert len(lav_badajoz) == 8 and set(lav_badajoz.values()) == {24}
    assert f"{LAV_BADAJOZ}:caceres:bif-la-aldihuela" in lav_badajoz
    assert f"{LAV_BADAJOZ}:bif-san-nicolas:badajoz" in lav_badajoz
    assert {s: n for s, n in extremadura.items() if s.startswith(extremadura_lines[2])} == {
        f"{RAMAL_MERIDA}:bif-granja-las-encinas:aljucen": 16,
        f"{RAMAL_MERIDA}:aljucen:merida": 24,
    }
    # entre Monfragüe y Cáceres hay dos caminos, la línea nueva y el trazado antiguo, y cada uno
    # es el otro camino del otro mientras no pase del doble del recorrido del tren. En el tramo
    # largo de la línea nueva, de Arroyo de la Herrera a El Palmeral, lo tienen 10 de sus 20
    # trenes: los otros 10 lo tenían girando en una bifurcación, y con la regla de giro ya no
    new_line = _of(exported.segments, f"{LAV_BADAJOZ}:arroyo-de-la-herrera:bif-el-palmeral")
    assert (new_line.trains, new_line.without_alternative) == (20, 10)
    # en los tramos cortos junto a las bifurcaciones solo lo tienen los trenes cuyo recorrido
    # sigue más allá: 8 de los 20 de Monfragüe a El Chaparral (los de Madrid que no entran en
    # Plasencia), 2 de los 12 de San Esteban a Arroyo de la Herrera y 10 de los 20 de El Palmeral
    # a Casa de la Torre. De esos 10, 4 son los de Madrid que entran en Mérida: su recorrido es
    # seguido de Arroyo de la Herrera a Mérida (133,5 km) desde que no cuentan además en la curva
    # de Granja-Las Encinas a Garrovilla-Las Vegas
    in_part = {
        f"{MADRID_PLASENCIA}:monfrague:bif-el-chaparral": (20, 12),
        f"{LAV_BADAJOZ}:bif-san-esteban:arroyo-de-la-herrera": (12, 10),
        f"{LAV_BADAJOZ}:bif-el-palmeral:bif-casa-de-la-torre": (20, 10),
    }
    for segment_id, expected in in_part.items():
        some = _of(exported.segments, segment_id)
        assert (some.trains, some.without_alternative) == expected
    # y los 2 regionales del trazado antiguo, que por él solo recorren 39,6 km entre Cañaveral y
    # Casa de la Torre, no lo tienen: la vuelta por la línea nueva mide más del doble
    assert {s: n for s, n in extremadura.items() if s.startswith(extremadura_lines[3])} == {
        f"{MONFRAGUE_CACERES}:monfrague:mirabel": 2,
        f"{MONFRAGUE_CACERES}:mirabel:casas-de-millan": 2,
        f"{MONFRAGUE_CACERES}:casas-de-millan:canaveral": 2,
        f"{MONFRAGUE_CACERES}:canaveral:bif-casa-de-la-torre": 2,
    }
    # Los 34 de la salida de Madrid cuentan también en el primer tramo de la convencional de
    # Andalucía, de Madrid-Puerta de Atocha a la bifurcación Planetario, por dos reglas de
    # recorrido: 33 tienen Leganés como parada siguiente y el Regional 17703, que no para allí,
    # Fuenlabrada. Con los 41 que ya llevaba el tramo son 75. Esos 34 no tienen otro camino: la
    # vuelta por Córdoba para volver a la bifurcación Planetario no cuenta. Los otros 41, sí
    shared = _of(exported.segments, f"{CONV}:madrid-puerta-de-atocha:bif-planetario")
    assert (shared.trains, shared.without_alternative) == (41 + 34, 34)
    # De la alta velocidad de Barcelona solo quedan los tres tramos de Camp de Tarragona a
    # Barcelona-Sants, fuera del anillo, con sus 108 trenes
    # la de Madrid a Valladolid entera: 122 trenes hasta Segovia, 111 hasta la bifurcación Medina,
    # donde salen los de Galicia, y 81 hasta Valladolid. Desde que está la convencional por Ávila
    # casi todos tienen otro camino por ella; no lo tienen los 11 de Segovia-Guiomar ni los 8 de
    # Medina del Campo AV, para los que la vuelta mide más del doble. Con la regla de giro
    # tampoco los 22 de Galicia en los dos tramos de Segovia-Guiomar a la bifurcación Medina: de
    # la convencional por Ávila no se pasa a la línea de Zamora sin invertir la marcha
    valladolid = [s for s in exported.segments if s.segment_id.startswith(f"{LAV_VALLADOLID}:")]
    assert [(s.trains, s.without_alternative) for s in valladolid] == [
        (122, 19),
        (122, 19),
        (111, 30),
        (111, 30),
        (81, 0),
    ]
    # y la de Valladolid a León, que la continúa: 51 trenes hasta la bifurcación Venta de Baños,
    # donde salen los 18 de Burgos; 35 de la bifurcación Cerrato a Palencia, con los 2 que llegan
    # de Burgos, y 26 de Palencia a León
    leon = [s for s in exported.segments if s.segment_id.startswith(f"{LAV_LEON}:")]
    assert [(s.trains, s.without_alternative) for s in leon] == [
        (51, 51),
        (51, 51),
        (33, 33),
        (35, 35),
        (26, 26),
        (26, 26),
        (26, 26),
        (26, 26),
    ]
    assert all(set(s.by_operator) == {"renfe"} for s in leon)
    # tampoco en la alta velocidad de Barcelona, que solo comparte con las demás la cabecera de
    # Madrid; los tres de Camp de Tarragona a Barcelona-Sants, que solo tenía ella, tienen otro
    # desde que está la línea de Tarragona a Barcelona por la costa
    barcelona = [s for s in exported.segments if s.segment_id.startswith(f"{BCN}:")]
    assert len(barcelona) == 20
    assert {s: n for s, n in none.items() if s.startswith(f"{BCN}:")} == {}
    camp_sants = _of(exported.segments, f"{BCN}:camp-de-tarragona:l-arboc")
    assert (camp_sants.trains, camp_sants.without_alternative) == (108, 0)
    assert _of(exported.segments, f"{BCN}:madrid-puerta-de-atocha:bif-vallecas-av").trains == 74
    # los cinco que entran y salen de Zaragoza-Delicias y de Lleida-Pirineus tienen el baipás, y
    # solo llevan los trenes que paran en la estación o salen de la línea por ella. Con la regla
    # de giro, el baipás no vale para los trenes que acaban en la estación o salen de ella hacia
    # el otro lado: desde el baipás no se entra en ella sin invertir la marcha. Son 8 y 4 en la
    # entrada a Zaragoza-Delicias y 16 en la salida de Lleida-Pirineus
    stations = {
        f"{BCN}:bif-moncasi:zaragoza-delicias": 56,
        f"{BCN}:zaragoza-delicias:bif-huesca": 55,
        f"{BCN}:bif-huesca:bif-canal-imperial": 51,
        f"{BCN}:bif-les-torres-de-sanui:lleida-pirineus": 31,
        f"{BCN}:lleida-pirineus:bif-artesa-de-lleida": 47,
    }
    without_bypass = {
        f"{BCN}:bif-moncasi:zaragoza-delicias": 8,
        f"{BCN}:zaragoza-delicias:bif-huesca": 4,
        f"{BCN}:lleida-pirineus:bif-artesa-de-lleida": 16,
    }
    for s in barcelona:
        if s.segment_id in stations:
            assert (s.trains, s.without_alternative) == (
                stations[s.segment_id],
                without_bypass.get(s.segment_id, 0),
            )
    # los baipases llevan los que no paran: 22 el de Zaragoza y 42 el de Lleida. Con el baipás
    # cortado entrarían en la estación, 4,9 km y 6 minutos más en Zaragoza
    around_zaragoza = _of(exported.segments, "baipas-zaragoza:bif-moncasi:bif-canal-imperial")
    assert (around_zaragoza.trains, around_zaragoza.without_alternative) == (22, 0)
    assert around_zaragoza.by_operator == {"ouigo": 4, "renfe": 18}
    # el grupo más numeroso es el de Madrid a Barcelona; los demás, los que siguen por la línea
    # de Barcelona a Figueres, con un recorrido más largo
    direct, *beyond = around_zaragoza.groups
    assert direct.trains + sum(g.trains for g in beyond) == 22
    assert all(g.line_ids == [BCN, LAV_FIGUERES] for g in beyond)
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
    # para todos sus trenes. De Joaquín Sorolla a Castelló solo la tienen los 4 AVE de Madrid. Los
    # dos de La Feredat a Camp de Tarragona tienen otro desde que está la línea de Tarragona a
    # Barcelona por la costa: quedan quince
    coast_none = {s: n for s, n in none.items() if s.startswith(f"{MEDITERRANEO}:")}
    # Y desde la línea de València a Alicante por Xàtiva ya no queda ninguno sin otro camino para
    # todos: los 9 trenes de Barcelona y Figueres a Alicante, y en el primer tramo también los 2
    # de Barcelona hacia Albacete, tienen la vuelta por Madrid y la alta velocidad de Albacete
    assert coast_none == {}
    first_coast = _of(
        exported.segments, f"{MEDITERRANEO}:valencia-estacio-del-nord:valencia-joaquin-sorolla"
    )
    assert (first_coast.trains, first_coast.without_alternative) == (54, 43)
    assert f"{MEDITERRANEO}:cambiador-la-boella:camp-de-tarragona" not in coast_none
    boella = _of(exported.segments, f"{MEDITERRANEO}:cambiador-la-boella:camp-de-tarragona")
    assert (boella.trains, boella.without_alternative) == (19, 0)
    partly = _of(exported.segments, f"{MEDITERRANEO}:almassora:castello-de-la-plana")
    assert (partly.trains, partly.without_alternative) == (52, 39)
    # y la línea nueva: 43 trenes de València a Xàtiva, 27 hasta la bifurcación de La Encina, 17
    # en la variante de Caudete, 21 hasta Villena y 40 de Villena a Alicante. En ninguno se quedan
    # todos sin otro camino: lo tienen los que vienen de Barcelona
    xativa = [s for s in exported.segments if s.segment_id.startswith("valencia-xativa-alicante:")]
    assert [(s.trains, s.without_alternative) for s in xativa] == (
        [(43, 32)] * 11 + [(27, 16), (17, 8), (21, 12)] + [(40, 31)] * 6
    )
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
    # otro ancho. Los de recorrido corto (los Avant de Sevilla, Málaga y Granada), no. Y desde
    # la regla de giro, tampoco los que siguen de Córdoba a Sevilla: la vuelta por Granada llega
    # a la bifurcación de Málaga por la línea de Málaga, y para tomar la de Sevilla habría que
    # invertir la marcha en Córdoba
    first = _of(exported.segments, CORDOBA_BIF_MALAGA)
    assert (first.trains, first.without_alternative) == (146, 89)
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
    # el grupo más numeroso de Adamuz – Córdoba: los 37 trenes entre Madrid y Sevilla (eran 41,
    # con los 2 Alvia de Cádiz, que siguen ahora por la línea de Sevilla a Cádiz, y los 2
    # Intercity de Huelva que paran en Santa Justa, que siguen por la línea de Sevilla a Huelva)
    top = _of(exported.segments, ADAMUZ_CORDOBA).groups[0]
    assert (top.trains, top.from_node_id, top.to_node_id) == (37, MADRID, SEVILLA)
    assert top.alternative is not None
    assert (top.alternative.extra_km, top.alternative.extra_min) == (97.0, 106)
