"""La línea convencional Sevilla – Huelva: de Sevilla-Santa Justa a la bifurcación Los Naranjos por
la línea de Córdoba (la 400 de Adif) y desde allí por la 440, de vía única, hasta Huelva."""

from __future__ import annotations

from collections import Counter

import pytest
from conftest import DATA_DIR, SEVILLA_HUELVA_SPEC, SOURCES, SPEC

from oniel.geo import haversine_km
from oniel.gtfs.reader import GtfsFeed, GtfsTrip
from oniel.gtfs.trips import calls_for_trip, calls_on_line, route_for_trip, select_trips_for_spec
from oniel.network.build import BuiltNetwork, build_network
from oniel.network.spec import NetworkSpec, load_network_spec, load_sources
from oniel.sim.passes import LineSegment, SegmentPass, resolve_passes
from oniel.validate import loaded_line

LINE = "sevilla-huelva"
MAP = "adif-declaracion-red-2026-mapas"
SANTA_JUSTA, LA_PALMA, HUELVA, BENACAZON = "51003", "43011", "43019", "43005"
MADRID, CORDOBA, LORA, LOS_ROSALES, GIBRALEON = "60000", "50500", "50600", "50700", "42020"
NODES = [
    "sevilla-santa-justa",
    "bif-los-naranjos",
    "bif-cartuja",
    "benacazon",
    "carrion-de-los-cespedes",
    "escacena",
    "la-palma-del-condado",
    "villarrasa",
    "niebla-puerta-del-buey",
    "san-juan-del-puerto",
    "huelva-mercancias",
    "huelva",
]
ALL_SEGMENTS = [f"{a}:{b}" for a, b in zip(NODES, NODES[1:], strict=False)]


@pytest.fixture(scope="module")
def spec() -> NetworkSpec:
    return load_network_spec(SEVILLA_HUELVA_SPEC)


@pytest.fixture(scope="module")
def line(spec: NetworkSpec) -> BuiltNetwork:
    return build_network(spec, DATA_DIR)


def _stops(trip: GtfsTrip) -> list[str]:
    return [st.stop_id for st in trip.stop_times]


def _passes(trip: GtfsTrip, feed: GtfsFeed, net: BuiltNetwork) -> list[SegmentPass]:
    own = loaded_line(net)
    route = route_for_trip(net.spec, trip)
    calls = calls_on_line(
        calls_for_trip(trip, feed, net.spec, nodes=own.nodes, others=[], route=route), route
    )
    assert all(c.node_id or c.exit_node_ids for c in calls), trip.train_number
    segments = [LineSegment(s.id, s.km_from, s.km_to) for s in net.segments]
    passes, resolution = resolve_passes(calls, own.nodes, segments)
    assert resolution == "completa", trip.train_number
    return passes


def _short(passes: list[SegmentPass]) -> list[str]:
    return sorted(
        (p.segment_id.split(":", 1)[1] for p in passes), key=lambda s: ALL_SEGMENTS.index(s)
    )


def test_the_geometry_is_one_relation_from_santa_justa_to_huelva(line: BuiltNetwork) -> None:
    """La relación de servicio de la línea 72 de Media Distancia es de una pieza: sale del punto
    de parada de la vía 9 de Santa Justa, sigue la línea 400 hasta la bifurcación Los Naranjos y
    la 440 hasta Huelva. Mide 117,0 km."""
    coords = line.line.polyline.coords
    assert haversine_km(coords[0], (-5.975224, 37.3923692)) < 0.05
    assert haversine_km(coords[-1], (-6.9449039, 37.2524874)) < 0.05
    assert [p.source_id for p in line.line.part_spans] == ["osm-relation-2424191"]
    assert not line.line.gaps_km
    assert line.line.polyline.length_km == pytest.approx(117.0, abs=0.1)
    assert all(n.offset_m < 70 for n in line.nodes)
    assert line.node("bif-los-naranjos").km == pytest.approx(6.37, abs=0.05)


def test_nodes_and_main_stations(line: BuiltNetwork) -> None:
    assert [n.spec.id for n in line.nodes] == NODES
    junctions = {n.spec.id for n in line.nodes if n.spec.kind == "bifurcacion"}
    assert junctions == {"bif-los-naranjos", "bif-cartuja", "huelva-mercancias"}
    principal = {n.spec.id for n in line.nodes if n.spec.rank == "principal"}
    assert principal == {"sevilla-santa-justa", "bif-los-naranjos", "la-palma-del-condado", "huelva"}
    assert line.node("huelva").spec.adif_code == HUELVA
    assert line.node("la-palma-del-condado").spec.adif_code == LA_PALMA
    assert {c.id: c.node_id for c in line.spec.connections} == {
        "conv-los-naranjos-cordoba": "bif-los-naranjos",
        "conv-huelva-zafra": "huelva-mercancias",
    }


def test_santa_justa_is_the_high_speed_node() -> None:
    """Santa Justa la define la alta velocidad de Madrid: esta línea la incorpora sin moverla. La
    alta velocidad ya no sale a trazos hacia Huelva desde Santa Justa; desde el cambiador de
    Majarabique sale el enlace, que no está cargado, hasta la bifurcación Los Naranjos."""
    lav = load_network_spec(SPEC)
    ours = load_network_spec(SEVILLA_HUELVA_SPEC)
    assert {n.id for n in ours.nodes if n.shared} == {"sevilla-santa-justa"}
    theirs = next(n for n in lav.nodes if n.id == "sevilla-santa-justa")
    mine = next(n for n in ours.nodes if n.id == "sevilla-santa-justa")
    assert mine.position == theirs.position
    assert [(c.id, c.node_id) for c in lav.connections] == [
        ("majarabique-los-naranjos", "majarabique")
    ]


def test_kilometre_points_start_after_the_junction(line: BuiltNetwork) -> None:
    """Los puntos kilométricos de la línea 440 empiezan en la bifurcación Los Naranjos, pero todas
    las estaciones quedan 2,2 km más lejos de ella por el trazado que lo que dice su punto: la
    cuenta se retoma en la bifurcación con -2,2. Desde Benacazón quedan a menos de 0,25 km; la
    bifurcación de Cartuja, a 1 km."""
    assert [(r.node, r.pk_km) for r in line.spec.line.pk_restarts] == [("bif-los-naranjos", -2.2)]
    origin = line.node("bif-los-naranjos").km
    with_pk = [n for n in line.nodes if n.spec.reference_pk_km is not None]
    assert [n.spec.id for n in with_pk] == NODES[2:]
    for node in with_pk[1:]:
        assert node.km - origin - 2.2 == pytest.approx(node.spec.reference_pk_km, abs=0.25)
    cartuja = line.node("bif-cartuja")
    assert cartuja.km - origin - 2.2 == pytest.approx(3.3, abs=1.0)


def test_double_track_to_cartuja_and_speeds_from_the_map(line: BuiltNetwork) -> None:
    assert [s.id.removeprefix(f"{LINE}:") for s in line.segments] == ALL_SEGMENTS
    assert [s.tracks for s in line.segments] == [2, 2] + [1] * 9
    assert line.spec.line.gauge_mm == 1668 and line.spec.line.electrification == "3 kV CC"
    assert [s.max_speed_kmh for s in line.segments] == [155] + [140] * 9 + [90]


def test_signalling_as_the_map_draws_it(line: BuiltNetwork) -> None:
    """Bloqueo automático de vía doble hasta la bifurcación de Cartuja; de vía única hasta
    Aznalcázar, que no es un nodo y se lleva a Benacazón; de liberación automática hasta
    Huelva-Mercancías, y otra vez de vía única hasta Huelva."""
    blocks = [s.attributes["bloqueo"].value for s in line.segments]
    assert blocks == ["bab", "bab", "bau"] + ["blau"] * 7 + ["bau"]
    for segment in line.segments:
        assert segment.attributes["proteccion_tren"].value == "asfa"
        assert segment.attributes["mando"].value == "ctc"
        for key in ("proteccion_tren", "bloqueo", "mando", "max_speed_kmh"):
            assert segment.attributes[key].source_id == MAP


def test_sources_and_operators_are_registered(spec: NetworkSpec) -> None:
    sources = {s.id: s for s in load_sources(SOURCES)}
    for part in spec.line.geometry_source.parts:
        source = sources[part.source_id]
        assert source.license == "ODbL 1.0"
        assert source.file == part.file and (DATA_DIR / part.file).exists()
    for source_id in ("osm-instalaciones-sevilla-huelva", "osm-relation-11375073"):
        assert sources[source_id].file and (DATA_DIR / sources[source_id].file).exists()
    assert spec.line.verification_source_id == "wikipedia-linea-sevilla-huelva"
    for section in spec.attribute_sections:
        assert section.source_id in sources
    assert {o.id for o in spec.operators if o.role == "operador"} == {"renfe"}
    assert all(o.source_id in sources for o in spec.operators)
    assert spec.line.zone == "andalucia"


def test_the_filter_and_the_rules_take_the_trains(
    feed: GtfsFeed, ouigo_feed: GtfsFeed, spec: NetworkSpec
) -> None:
    """Entran 212 viajes de Renfe y ninguno de Ouigo. 28 paran en dos estaciones de la línea: los
    regionales de Sevilla a Huelva y los Alvia e Intercity de Madrid. Los demás entran por las
    reglas de recorrido: los regionales que van de Santa Justa a Lora del Río, a Los Rosales o a
    Zafra, y los de Huelva a Gibraleón."""
    trips = select_trips_for_spec(feed, spec)
    assert len(trips) == 212
    assert Counter(t.product for t in trips) == {
        "MD": 172,
        "REG.EXP.": 24,
        "ALVIA": 12,
        "Intercity": 4,
    }
    rules = Counter(r.override.id for t in trips if (r := route_for_trip(spec, t)))
    assert rules == {
        "regionales-por-lora-del-rio": 113,
        "regionales-por-los-rosales": 41,
        "regionales-de-zafra-por-los-rosales": 17,
        "regionales-de-zafra-y-jabugo": 13,
    }
    assert select_trips_for_spec(ouigo_feed, spec) == []


def test_each_family_counts_where_it_runs(feed: GtfsFeed, line: BuiltNetwork) -> None:
    """Los regionales de Sevilla a Huelva y los Intercity que paran en Santa Justa recorren la
    línea entera. Los Alvia que no paran en Sevilla entran por la bifurcación Los Naranjos. Los
    regionales de Córdoba, Jaén y Extremadura solo pasan de Santa Justa a la bifurcación, y los
    de Zafra y Jabugo, de Huelva-Mercancías a Huelva."""
    trips = select_trips_for_spec(feed, line.spec)
    seen: Counter[str] = Counter()
    for trip in trips:
        stops = _stops(trip)
        passes = _short(_passes(trip, feed, line))
        if BENACAZON in stops or (SANTA_JUSTA in stops and LA_PALMA in stops):
            assert passes == ALL_SEGMENTS, trip.train_number
            seen["entera"] += 1
        elif LA_PALMA in stops:
            assert MADRID in stops and SANTA_JUSTA not in stops
            assert passes == ALL_SEGMENTS[1:], trip.train_number
            seen["por Los Naranjos"] += 1
        elif GIBRALEON in stops:
            assert passes == ["huelva-mercancias:huelva"], trip.train_number
            seen["Zafra y Jabugo"] += 1
        else:
            assert SANTA_JUSTA in stops and LA_PALMA not in stops
            assert passes == ["sevilla-santa-justa:bif-los-naranjos"], trip.train_number
            seen["hacia Córdoba"] += 1
    assert seen == {"entera": 16, "por Los Naranjos": 12, "Zafra y Jabugo": 13, "hacia Córdoba": 171}


def test_madrid_trains_reach_the_line_through_majarabique(spec: NetworkSpec) -> None:
    """Córdoba y Madrid salen por la bifurcación Los Naranjos con `via` por la alta velocidad
    desde Majarabique; en la alta velocidad, La Palma del Condado y Huelva llevan el `via`
    recíproco."""
    sm = spec.stop_mappings
    for stop_id in (CORDOBA, MADRID):
        assert sm[stop_id].exits == ["bif-los-naranjos"]
        assert [(v.line, v.node) for v in sm[stop_id].via] == [
            ("lav-madrid-sevilla", "majarabique")
        ]
    other = load_network_spec(SPEC).stop_mappings
    for stop_id in (LA_PALMA, HUELVA):
        assert other[stop_id].exits == ["majarabique", "sevilla-santa-justa"]
        assert [(v.line, v.node) for v in other[stop_id].via] == [(LINE, "bif-los-naranjos")]


def test_rules_only_map_their_own_exit(spec: NetworkSpec) -> None:
    rules = {r.id: r for r in spec.route_overrides}
    for rule_id, stop_id in [
        ("regionales-por-lora-del-rio", LORA),
        ("regionales-por-los-rosales", LOS_ROSALES),
    ]:
        rule = rules[rule_id]
        assert (rule.from_stop_id, rule.to_stop_id) == (SANTA_JUSTA, stop_id)
        assert rule.stop_mappings[stop_id].exits == ["bif-los-naranjos"]
    zafra = rules["regionales-de-zafra-y-jabugo"]
    assert (zafra.from_stop_id, zafra.to_stop_id) == (HUELVA, GIBRALEON)
    assert zafra.stop_mappings[GIBRALEON].exits == ["huelva-mercancias"]
