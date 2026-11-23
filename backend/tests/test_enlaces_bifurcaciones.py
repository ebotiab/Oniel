"""Los tres enlaces cargados el 23 de noviembre de 2026 (#260): el de Soto de Cerrato, entre la
línea de alta velocidad de Burgos y la de León; el de Aljucén a La Garrovilla, por el que se va
de Mérida a Badajoz, y el túnel de Atocha a Chamartín por Recoletos.

Los tres eran conexiones a trazos. Son enlaces (``link_of``), como el de Monforte del Cid: cada
uno cuelga de una línea y elige sus trenes con su propio filtro."""

from __future__ import annotations

from collections import Counter
from pathlib import Path

import pytest
from conftest import (
    CONV_SPEC,
    DATA_DIR,
    FEED,
    LAV_BADAJOZ_SPEC,
    LAV_BURGOS_SPEC,
    LAV_LEON_SPEC,
    LINK_ALJUCEN_SPEC,
    LINK_CERRATO_SPEC,
    LINK_MADRID_SPEC,
    MADRID_AVILA_VALLADOLID_SPEC,
    MADRID_PLASENCIA_SPEC,
    RAMAL_MERIDA_SPEC,
    SOURCES,
    SPECS,
)

from oniel.gtfs.reader import GtfsFeed
from oniel.gtfs.trips import select_trips_for_spec
from oniel.network.build import BuiltNetwork, build_network
from oniel.network.spec import NetworkSpec, load_network_spec, load_sources
from oniel.validate import validate_all

CERRATO = "enlace-soto-de-cerrato"
ALJUCEN = "enlace-aljucen-la-garrovilla"
MADRID = "enlace-atocha-chamartin"
LINKS: dict[str, Path] = {
    CERRATO: LINK_CERRATO_SPEC,
    ALJUCEN: LINK_ALJUCEN_SPEC,
    MADRID: LINK_MADRID_SPEC,
}
PALENCIA, BURGOS = "14100", "11014"
MERIDA = "37500"
TOWARDS_BADAJOZ = {"37611", "37603", "37608", "37604", "37606"}
ATOCHA, RECOLETOS, NUEVOS_MINISTERIOS, CHAMARTIN = "18000", "18001", "18002", "17000"
PRINCIPE_PIO = "10000"


@pytest.fixture(scope="module")
def specs() -> dict[str, NetworkSpec]:
    return {line: load_network_spec(path) for line, path in LINKS.items()}


@pytest.fixture(scope="module")
def nets(specs: dict[str, NetworkSpec]) -> dict[str, BuiltNetwork]:
    return {line: build_network(spec, DATA_DIR) for line, spec in specs.items()}


def _node_ids(path: Path) -> set[str]:
    return {n.id for n in load_network_spec(path).nodes}


def test_each_link_hangs_from_one_line_and_ends_on_another(
    specs: dict[str, NetworkSpec],
) -> None:
    """Cada enlace va de un nodo de la línea de la que cuelga a un nodo de otra línea cargada."""
    expected = {
        CERRATO: (LAV_BURGOS_SPEC, "bif-soto-de-cerrato", LAV_LEON_SPEC, "bif-cerrato"),
        ALJUCEN: (LAV_BADAJOZ_SPEC, "garrovilla-las-vegas", RAMAL_MERIDA_SPEC, "aljucen"),
        MADRID: (
            CONV_SPEC,
            "madrid-puerta-de-atocha",
            MADRID_AVILA_VALLADOLID_SPEC,
            "madrid-chamartin",
        ),
    }
    for line, (parent, join, other, far) in expected.items():
        spec = specs[line]
        assert spec.line.link_of == load_network_spec(parent).line.id
        assert spec.line.bypass_of is None
        ends = {spec.nodes[0].id, spec.nodes[-1].id}
        assert ends == {join, far}
        assert join in _node_ids(parent) and far not in _node_ids(parent)
        assert far in _node_ids(other)
        assert all(n.shared for n in spec.nodes if n.id in ends)
        # ya no va a trazos en ninguna de las dos líneas que une
        for neighbour in (parent, other):
            names = [c.name.lower() for c in load_network_spec(neighbour).connections]
            assert not any("garrovilla" in n or "cerrato" in n or "túneles" in n for n in names)


def test_lengths_tracks_and_speeds(nets: dict[str, BuiltNetwork]) -> None:
    """El de Soto de Cerrato mide 5,2 km (4,4 km de sus vías y 0,8 km de la línea de León hasta
    la bifurcación Cerrato); el de Aljucén, 7,1 km, y el túnel, 7,7 km en tres tramos."""
    cerrato, aljucen, madrid = nets[CERRATO], nets[ALJUCEN], nets[MADRID]
    assert cerrato.line.polyline.length_km == pytest.approx(5.17, abs=0.02)
    assert [(p.source_id, round(p.km_to, 1)) for p in cerrato.line.part_spans] == [
        ("osm-ramal-soto-de-cerrato", 4.4),
        ("osm-relation-5546933", 5.2),
    ]
    assert cerrato.line.joins_km == []
    (segment,) = cerrato.segments
    assert (segment.tracks, segment.max_speed_kmh, segment.typical_speed_kmh) == (1, 160, 160)

    assert aljucen.line.polyline.length_km == pytest.approx(7.10, abs=0.02)
    (segment,) = aljucen.segments
    assert segment.id == f"{ALJUCEN}:aljucen:garrovilla-las-vegas"
    assert (segment.tracks, segment.max_speed_kmh) == (1, 120)

    assert madrid.line.polyline.length_km == pytest.approx(7.67, abs=0.02)
    assert [n.spec.id for n in madrid.nodes] == [
        "madrid-puerta-de-atocha",
        "madrid-recoletos",
        "madrid-nuevos-ministerios",
        "madrid-chamartin",
    ]
    assert [round(s.length_km, 1) for s in madrid.segments] == [1.8, 2.7, 3.1]
    assert {(s.tracks, s.max_speed_kmh) for s in madrid.segments} == {(2, 60)}
    assert all(n.offset_m < 300 for net in nets.values() for n in net.nodes)


def test_sources_and_signalling(specs: dict[str, NetworkSpec]) -> None:
    """Todo lo que declaran sale de una fuente registrada, y los tres llevan la señalización que
    dibuja el mapa 4 de la Declaración sobre la Red."""
    sources = {s.id: s for s in load_sources(SOURCES)}
    signalling = {
        CERRATO: {
            "proteccion_tren": "ertms_n2_asfa",
            "bloqueo": "bca",
            "mando": "sin_dato_publicado",
        },
        ALJUCEN: {"proteccion_tren": "asfa", "bloqueo": "bau", "mando": "ctc"},
        MADRID: {"proteccion_tren": "asfa", "bloqueo": "bab", "mando": "ctc"},
    }
    for line, spec in specs.items():
        used = {p.source_id for p in spec.line.geometry_source.parts}
        used |= {t.source_id for t in spec.attribute_sections}
        assert used <= set(sources), line
        values = {t.attribute: t.value for t in spec.attribute_sections}
        assert {k: values[k] for k in signalling[line]} == signalling[line]
    assert sources["osm-relation-18369025"].file == (
        "raw/osm/relation_18369025_linea_900_tunel_recoletos_2026-11-23.json"
    )
    assert (DATA_DIR / str(sources["osm-relation-18369025"].file)).exists()


def test_cerrato_carries_the_trains_between_palencia_and_burgos(
    feed: GtfsFeed, specs: dict[str, NetworkSpec]
) -> None:
    """Sus trenes paran en Palencia y en Burgos-Rosa Manzano, seguidas: los Alvia de Barcelona a
    Galicia. Los regionales que llevan las dos paradas van por la línea convencional, paran en
    Venta de Baños y quedan fuera."""
    trips = select_trips_for_spec(feed, specs[CERRATO])
    assert Counter(t.product for t in trips) == {"ALVIA": 6}
    for trip in trips:
        stops = [st.stop_id for st in trip.stop_times]
        assert abs(stops.index(PALENCIA) - stops.index(BURGOS)) == 1


def test_aljucen_carries_the_trains_between_merida_and_badajoz(
    feed: GtfsFeed, specs: dict[str, NetworkSpec]
) -> None:
    """Sus trenes paran en Mérida y, justo antes o justo después, en una estación del lado de
    Badajoz. Todos están también en la línea de Aljucén a Mérida."""
    trips = select_trips_for_spec(feed, specs[ALJUCEN])
    assert Counter(t.product for t in trips) == {
        "MD": 55,
        "ALVIA": 37,
        "REG.EXP.": 22,
        "REGIONAL": 14,
    }
    for trip in trips:
        stops = [st.stop_id for st in trip.stop_times]
        at = stops.index(MERIDA)
        assert TOWARDS_BADAJOZ & set(stops[max(at - 1, 0) : at + 2])
    on_merida = {
        t.trip_id for t in select_trips_for_spec(feed, load_network_spec(RAMAL_MERIDA_SPEC))
    }
    assert {t.trip_id for t in trips} <= on_merida


def test_madrid_carries_the_trains_that_stop_at_atocha_and_chamartin(
    feed: GtfsFeed, specs: dict[str, NetworkSpec]
) -> None:
    """Sus trenes paran en Atocha Cercanías y en Chamartín sin otra parada entre las dos que
    Recoletos y Nuevos Ministerios. Ninguno es de alta velocidad."""
    trips = select_trips_for_spec(feed, specs[MADRID])
    assert Counter(t.product for t in trips) == {
        "REGIONAL": 141,
        "MD": 122,
        "ALVIA": 55,
        "REG.EXP.": 8,
    }
    for trip in trips:
        stops = [st.stop_id for st in trip.stop_times]
        low, high = sorted((stops.index(ATOCHA), stops.index(CHAMARTIN)))
        assert set(stops[low + 1 : high]) <= {RECOLETOS, NUEVOS_MINISTERIOS}
    # los que llegan a Atocha desde Príncipe Pío se cuentan solo desde allí
    (rule,) = specs[MADRID].route_overrides
    assert rule.consecutive_stop_ids == [PRINCIPE_PIO, ATOCHA]
    assert rule.from_stop_id == PRINCIPE_PIO


@pytest.mark.parametrize(
    ("line", "trips", "passes", "rules"),
    [
        (CERRATO, 6, {"estimado": 6}, {}),
        (ALJUCEN, 128, {"estimado": 128}, {}),
        (MADRID, 326, {"estimado": 555, "publicado": 423}, {"principe-pio-atocha": 12}),
    ],
)
def test_validate_finds_no_problems(
    line: str, trips: int, passes: dict[str, int], rules: dict[str, int]
) -> None:
    """`validate` resuelve todos sus viajes, y los `via` de sus paradas se sostienen."""
    report = validate_all(LINKS[line], FEED, DATA_DIR, SPECS)
    assert report["problems"] == []
    assert report["gtfs"]["trips"] == trips
    assert report["gtfs"]["passes"] == passes
    assert report["gtfs"]["resolution"] == {"completa": trips}
    assert report["gtfs"]["route_overrides"] == rules


def test_the_neighbours_measure_through_the_links() -> None:
    """Los `via` de las líneas vecinas que saltaban de un nodo a otro en línea recta empiezan
    ahora por el enlace."""

    def first_leg(path: Path, stop_id: str) -> tuple[str, str]:
        via = load_network_spec(path).stop_mappings[stop_id].via
        return via[0].line, via[0].node

    assert first_leg(LAV_BURGOS_SPEC, PALENCIA) == (CERRATO, "bif-soto-de-cerrato")
    rules = load_network_spec(LAV_LEON_SPEC).route_overrides
    rule = next(r for r in rules if r.id == "burgos-palencia-leon")
    assert [(v.line, v.node) for v in rule.stop_mappings[BURGOS].via] == [
        (CERRATO, "bif-cerrato"),
        ("lav-venta-de-banos-burgos", "bif-soto-de-cerrato"),
    ]
    for stop_id in sorted(TOWARDS_BADAJOZ):
        assert first_leg(RAMAL_MERIDA_SPEC, stop_id) == (ALJUCEN, "aljucen")
    assert first_leg(CONV_SPEC, CHAMARTIN) == (MADRID, "madrid-puerta-de-atocha")
    for stop_id in (ATOCHA, RECOLETOS, NUEVOS_MINISTERIOS):
        assert first_leg(MADRID_AVILA_VALLADOLID_SPEC, stop_id) == (MADRID, "madrid-chamartin")
    via = load_network_spec(MADRID_PLASENCIA_SPEC).stop_mappings[CHAMARTIN].via
    assert [(v.line, v.node) for v in via] == [
        ("convencional-madrid-alcazar-cordoba", "bif-planetario"),
        (MADRID, "madrid-puerta-de-atocha"),
    ]
