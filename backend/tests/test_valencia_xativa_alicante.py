"""La línea convencional València – Xàtiva – Alicante: la 300 de Adif de València a La Encina, la
variante de Caudete (332) y la 330 de La Encina a Alicante. Une València-Estació del Nord, que
define la línea de Castelló, con Alicante-Terminal, que define la alta velocidad de Albacete. La
línea de Almansa y Albacete sale a trazos de la bifurcación de La Encina y de Caudete."""

from __future__ import annotations

from collections import Counter

import pytest
from conftest import (
    DATA_DIR,
    LAV_ALICANTE_SPEC,
    MEDITERRANEO_SPEC,
    SOURCES,
    VALENCIA_ALICANTE_SPEC,
)

from oniel.geo import haversine_km
from oniel.gtfs.reader import GtfsFeed, GtfsTrip
from oniel.gtfs.trips import calls_for_trip, calls_on_line, route_for_trip, select_trips_for_spec
from oniel.network.build import BuiltNetwork, build_network
from oniel.network.spec import NetworkSpec, load_network_spec, load_sources
from oniel.sim.passes import LineSegment, SegmentPass, resolve_passes
from oniel.validate import loaded_line

LINE = "valencia-xativa-alicante"
RELATION = "osm-relation-16947106"
WIKIPEDIA = "wikipedia-linea-330-la-encina-alicante"
MAP = "adif-declaracion-red-2026-mapas"
VALENCIA, XATIVA, CAUDETE, VILLENA, ALICANTE = "65000", "64100", "60901", "60902", "60911"
ALMANSA, LA_ENCINA, ALBACETE, ALCOI, MURCIA, CASTELLO = (
    "60800",
    "60900",
    "60600",
    "69011",
    "61200",
    "65300",
)
NODES = [
    "valencia-estacio-del-nord",
    "alfafar-benetusser",
    "massanassa",
    "catarroja",
    "silla",
    "benifaio",
    "algemesi",
    "alzira",
    "carcaixent",
    "la-pobla-llarga",
    "l-enova-manuel",
    "xativa",
    "bif-la-encina",
    "caudete",
    "villena",
    "sax",
    "elda-petrer",
    "novelda-aspe",
    "sant-vicent-centre",
    "universidad-de-alicante",
    "alicante-terminal",
]
ALL_SEGMENTS = [f"{a}:{b}" for a, b in zip(NODES, NODES[1:], strict=False)]
TO_XATIVA = ALL_SEGMENTS[:11]
TO_BIF = ALL_SEGMENTS[:12]
FROM_CAUDETE = ALL_SEGMENTS[13:]
FROM_VILLENA = ALL_SEGMENTS[14:]


@pytest.fixture(scope="module")
def spec() -> NetworkSpec:
    return load_network_spec(VALENCIA_ALICANTE_SPEC)


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


def test_the_geometry_is_one_piece_from_valencia_to_alicante(line: BuiltNetwork) -> None:
    """Un solo trozo de la relación del servicio regional de València a Alacant, sin saltos:
    183,1 km. Empieza en el vértice de las vías más cercano a la Estació del Nord, a 220 m del
    nodo de la estación, que no se mueve."""
    coords = line.line.polyline.coords
    assert haversine_km(coords[0], (-0.3771908, 39.4669126)) < 0.25
    assert haversine_km(coords[-1], (-0.4955241, 38.3447127)) < 0.15
    assert [p.source_id for p in line.line.part_spans] == [RELATION]
    assert not line.line.gaps_km and not line.line.joins_km
    assert line.line.polyline.length_km == pytest.approx(183.1, abs=0.1)


def test_nodes_stations_junction_and_dashed_lines(line: BuiltNetwork) -> None:
    assert [n.spec.id for n in line.nodes] == NODES
    assert line.node("bif-la-encina").spec.kind == "bifurcacion"
    assert all(n.spec.kind == "estacion" for n in line.nodes if n.spec.id != "bif-la-encina")
    assert {n.spec.id for n in line.nodes if n.spec.rank != "secundario"} == {
        "valencia-estacio-del-nord",
        "xativa",
        "bif-la-encina",
        "caudete",
        "villena",
        "elda-petrer",
        "alicante-terminal",
    }
    assert line.node("xativa").spec.adif_code == XATIVA
    assert line.node("xativa").km == pytest.approx(55.9, abs=0.1)
    assert {c.id: c.node_id for c in line.spec.connections} == {
        "conv-xativa-alcoi": "xativa",
        "conv-la-encina-albacete": "bif-la-encina",
        "conv-caudete-la-encina": "caudete",
        "conv-alicante-murcia": "alicante-terminal",
    }
    for c in line.spec.connections:
        node = line.node(c.node_id).spec.position
        assert c.sketch[0] == (node.lon, node.lat) and c.status == "no_cargada"
    assert all(n.offset_m < 50 for n in line.nodes[1:-1])


def test_it_joins_two_loaded_lines_and_replaces_their_dashed_links(line: BuiltNetwork) -> None:
    """Los dos extremos son nodos que ya definen otras líneas: se incorporan sin moverlos, y de
    aquellas se retiran las conexiones a trazos que esta línea sustituye. Las paradas de esta
    línea llevan allí `via`."""
    assert {n.spec.id for n in line.nodes if n.spec.shared} == {
        "valencia-estacio-del-nord",
        "alicante-terminal",
    }
    coast = load_network_spec(MEDITERRANEO_SPEC)
    lav = load_network_spec(LAV_ALICANTE_SPEC)
    for other, node_id in ((coast, "valencia-estacio-del-nord"), (lav, "alicante-terminal")):
        theirs = next(n for n in other.nodes if n.id == node_id)
        assert line.node(node_id).spec.position == theirs.position
    assert all(c.id != "valencia-nord-sur" for c in coast.connections)
    assert all(c.id != "conv-alicante-la-encina" for c in lav.connections)
    for stop_id in (XATIVA, VILLENA, "60905", ALICANTE):
        assert [(v.line, v.node) for v in coast.stop_mappings[stop_id].via] == [
            (LINE, "valencia-estacio-del-nord")
        ]


def test_kilometre_points_count_from_caudete_on_line_330(line: BuiltNetwork) -> None:
    """De València a La Encina los puntos kilométricos decrecen y no se guardan. Desde Caudete
    (PK 383,1 de la línea 330) cada estación queda a menos de 400 m del suyo."""
    assert [(r.node, r.pk_km) for r in line.spec.line.pk_restarts] == [("caudete", 383.1)]
    caudete = line.node("caudete").km
    with_pk = [n for n in line.nodes if n.spec.reference_pk_km is not None]
    assert [n.spec.id for n in with_pk] == NODES[14:]
    for node in with_pk:
        assert node.km - caudete + 383.1 == pytest.approx(node.spec.reference_pk_km, abs=0.4)


def test_double_track_to_xativa_and_single_from_there(line: BuiltNetwork) -> None:
    assert [s.id.removeprefix(f"{LINE}:") for s in line.segments] == ALL_SEGMENTS
    assert [s.tracks for s in line.segments] == [2] * 11 + [1] * 9
    assert line.spec.line.tracks == 1
    assert line.spec.line.gauge_mm == 1668 and line.spec.line.electrification == "3 kV CC"
    # ningún tramo cambia de ancho ni de tensión: el ancho estándar es el de las vías en obras
    assert not [
        s for s in line.spec.attribute_sections if s.attribute in ("gauge", "electrification")
    ]
    assert all(s.max_speed_kmh for s in line.segments)
    assert max(s.max_speed_kmh or 0 for s in line.segments) == 200


def test_signalling_as_the_map_draws_it(line: BuiltNetwork) -> None:
    for i, segment in enumerate(line.segments):
        assert segment.attributes["proteccion_tren"].value == "asfa"
        assert segment.attributes["bloqueo"].value == ("bab" if i < 11 else "bau")
        assert segment.attributes["mando"].value == "ctc"
        for key in ("proteccion_tren", "bloqueo", "mando"):
            assert segment.attributes[key].source_id == MAP


def test_sources_and_operators_are_registered(spec: NetworkSpec) -> None:
    sources = {s.id: s for s in load_sources(SOURCES)}
    for part in spec.line.geometry_source.parts:
        source = sources[part.source_id]
        assert source.license == "ODbL 1.0"
        assert source.file == part.file and (DATA_DIR / part.file).exists()
    for source_id in ("osm-relation-16801769", "osm-relation-18343079"):
        other = sources[source_id]
        assert other.file and (DATA_DIR / other.file).exists()
    assert spec.line.verification_source_id == WIKIPEDIA and WIKIPEDIA in sources
    for section in spec.attribute_sections:
        assert section.source_id in sources
    assert {o.id for o in spec.operators if o.role == "operador"} == {"renfe"}
    assert all(o.source_id in sources for o in spec.operators)
    assert spec.line.zone == "levante"


def test_the_filter_takes_every_train_that_runs_on_the_line(
    feed: GtfsFeed, ouigo_feed: GtfsFeed, spec: NetworkSpec
) -> None:
    """Entran los viajes que paran en dos estaciones de la línea y los regionales que van de
    Almansa a Villena sin parar en Caudete: 556 de Renfe y ninguno de Ouigo."""
    assert spec.corridor_filter.min_node_stops == 2
    assert spec.corridor_filter.consecutive_stop_ids == [[ALMANSA, VILLENA]]
    trips = select_trips_for_spec(feed, spec)
    assert len(trips) == 556
    assert Counter(t.product for t in trips) == {
        "REGIONAL": 314,
        "MD": 167,
        "REG.EXP.": 34,
        "EUROMED": 19,
        "Intercity": 14,
        "ALVIA": 8,
    }
    codes = {n.adif_code for n in spec.nodes if n.adif_code}
    selected = {t.trip_id for t in trips}
    for trip in feed.trips.values():
        if trip.trip_id not in selected:
            assert len(codes & set(_stops(trip))) <= 1, trip.train_number
    assert select_trips_for_spec(ouigo_feed, spec) == []


def test_each_train_counts_on_the_segments_it_runs(feed: GtfsFeed, line: BuiltNetwork) -> None:
    """Cinco recorridos: la línea entera (138 viajes, con los 19 Euromed, que no paran entre
    València y Alicante), de València a Xàtiva (los 119 de Alcoi), de València a la bifurcación de
    La Encina (57, los de Albacete), de Caudete a Alicante (78, los de Albacete y Ciudad Real) y
    de Villena a Alicante (164)."""
    trips = select_trips_for_spec(feed, line.spec)
    runs = Counter(tuple(_short(_passes(t, feed, line))) for t in trips)
    assert runs == {
        tuple(ALL_SEGMENTS): 138,
        tuple(TO_XATIVA): 119,
        tuple(TO_BIF): 57,
        tuple(FROM_CAUDETE): 78,
        tuple(FROM_VILLENA): 164,
    }
    euromed = [t for t in trips if t.product == "EUROMED"]
    assert all(VALENCIA in _stops(t) and ALICANTE in _stops(t) for t in euromed)
    for trip in trips:
        stops, run = _stops(trip), _short(_passes(trip, feed, line))
        if ALCOI in stops:
            assert run == TO_XATIVA, trip.train_number
        if ALMANSA in stops:
            # los de Albacete: por la bifurcación si vienen de València, por Caudete si van a
            # Alicante; ninguno recorre la variante de Caudete
            assert run in (TO_BIF, FROM_CAUDETE), trip.train_number
            assert "bif-la-encina:caudete" not in run


def test_stops_on_each_side_leave_by_the_right_node(spec: NetworkSpec) -> None:
    sm = spec.stop_mappings
    for node in spec.nodes:
        if node.adif_code:
            assert sm[node.adif_code].node == node.id
    # la costa hacia Castelló y Barcelona, por la línea de València a Camp de Tarragona
    assert [(v.line, v.node) for v in sm[CASTELLO].via] == [
        ("valencia-castello-tarragona", "valencia-estacio-del-nord")
    ]
    assert [v.line for v in sm["71801"].via] == [
        "valencia-castello-tarragona",
        "lav-madrid-barcelona",
    ]
    # la línea de Alcoi sale de Xàtiva; la convencional de Murcia, de Alicante
    assert sm[ALCOI].exits == ["xativa"] and not sm[ALCOI].via
    assert sm[MURCIA].exits == ["alicante-terminal"] and not sm[MURCIA].via
    # La Encina, Almansa y Albacete quedan a un lado, con dos salidas: la bifurcación para los
    # trenes de València y Caudete para los de Alicante
    for stop_id in (LA_ENCINA, ALMANSA, ALBACETE, "37200"):
        assert sm[stop_id].exits == ["bif-la-encina", "caudete"] and sm[stop_id].aside
        assert not sm[stop_id].via
    assert spec.route_overrides == []
