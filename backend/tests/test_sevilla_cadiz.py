"""La línea convencional Sevilla – Cádiz (el último trecho de la 400 de Adif, Alcázar de San Juan –
Cádiz): sale de Sevilla-Santa Justa, donde acaba la alta velocidad de Madrid, y llega a Cádiz por
Utrera y Jerez de la Frontera. La línea de Marchena y Málaga sale a trazos de la bifurcación
Utrera."""

from __future__ import annotations

from collections import Counter

import pytest
from conftest import DATA_DIR, SEVILLA_CADIZ_SPEC, SOURCES, SPEC

from oniel.geo import haversine_km
from oniel.gtfs.reader import GtfsFeed, GtfsTrip
from oniel.gtfs.trips import calls_for_trip, calls_on_line, route_for_trip, select_trips_for_spec
from oniel.network.build import BuiltNetwork, build_network
from oniel.network.spec import NetworkSpec, load_network_spec, load_sources
from oniel.sim.passes import LineSegment, SegmentPass, resolve_passes
from oniel.validate import loaded_line

LINE = "sevilla-cadiz"
RELATION = "osm-relation-11351144"
WIKIPEDIA = "wikipedia-linea-400-sevilla-cadiz"
MAP = "adif-declaracion-red-2026-mapas"
MADRID, CORDOBA, SEVILLA, JEREZ, CADIZ = "60000", "50500", "51003", "51300", "51405"
LORA, OSUNA, JAEN = "50600", "01007", "03100"
NODES = [
    "sevilla-santa-justa",
    "san-bernardo",
    "virgen-del-rocio",
    "bellavista",
    "dos-hermanas",
    "bif-utrera",
    "utrera",
    "las-cabezas-de-san-juan",
    "lebrija",
    "aeropuerto-de-jerez",
    "jerez-de-la-frontera",
    "el-puerto-de-santa-maria",
    "puerto-real",
    "san-fernando-bahia-sur",
    "estadio",
    "segunda-aguada",
    "cadiz",
]
ALL_SEGMENTS = [f"{a}:{b}" for a, b in zip(NODES, NODES[1:], strict=False)]
TO_BIF_UTRERA = ALL_SEGMENTS[:5]


@pytest.fixture(scope="module")
def spec() -> NetworkSpec:
    return load_network_spec(SEVILLA_CADIZ_SPEC)


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


def test_the_geometry_follows_line_400_from_seville_to_cadiz(line: BuiltNetwork) -> None:
    """Un solo trozo de la relación de la línea 400, del punto de parada de la vía 9 de Santa
    Justa, a 30 m del nodo de la estación, a la de Cádiz, sin saltos: 152,5 km."""
    coords = line.line.polyline.coords
    assert haversine_km(coords[0], (-5.974927, 37.392496)) < 0.05
    assert haversine_km(coords[-1], (-6.2868833, 36.5279393)) < 0.05
    assert [p.source_id for p in line.line.part_spans] == [RELATION]
    assert not line.line.gaps_km and not line.line.joins_km
    assert line.line.polyline.length_km == pytest.approx(152.5, abs=0.1)


def test_nodes_stations_junction_and_dashed_branch(line: BuiltNetwork) -> None:
    assert [n.spec.id for n in line.nodes] == NODES
    assert line.node("bif-utrera").spec.kind == "bifurcacion"
    assert all(n.spec.kind == "estacion" for n in line.nodes if n.spec.id != "bif-utrera")
    assert {n.spec.id for n in line.nodes if n.spec.rank == "secundario"} == {
        "san-bernardo",
        "virgen-del-rocio",
        "bellavista",
        "las-cabezas-de-san-juan",
        "aeropuerto-de-jerez",
        "puerto-real",
        "estadio",
        "segunda-aguada",
    }
    assert line.node("jerez-de-la-frontera").spec.adif_code == JEREZ
    assert line.node("cadiz").spec.adif_code == CADIZ
    assert {c.id: c.node_id for c in line.spec.connections} == {
        "conv-bif-utrera-marchena": "bif-utrera"
    }
    for c in line.spec.connections:
        node = line.node(c.node_id).spec.position
        assert c.sketch[0] == (node.lon, node.lat) and c.status == "no_cargada"
    assert all(n.offset_m < 50 for n in line.nodes)


def test_it_starts_at_santa_justa_and_replaces_the_dashed_link(line: BuiltNetwork) -> None:
    """Sevilla-Santa Justa la define la alta velocidad de Madrid, que ya no sale a trazos hacia
    Cádiz: esta línea la incorpora sin moverla, y las paradas de Cádiz siguen por ella."""
    assert {n.spec.id for n in line.nodes if n.spec.shared} == {"sevilla-santa-justa"}
    lav = load_network_spec(SPEC)
    theirs = next(n for n in lav.nodes if n.id == "sevilla-santa-justa")
    assert line.node("sevilla-santa-justa").spec.position == theirs.position
    assert all(c.id != "sevilla-cadiz" for c in lav.connections)
    for stop_id in (JEREZ, "51400", "51406", CADIZ):
        assert [(v.line, v.node) for v in lav.stop_mappings[stop_id].via] == [
            (LINE, "sevilla-santa-justa")
        ]


def test_kilometre_points_restart_after_the_lebrija_bypass(line: BuiltNetwork) -> None:
    """La numeración de Sevilla a Cádiz vuelve a empezar en Santa Justa, con un origen de 0,3.
    Desde el aeropuerto de Jerez es la del trazado anterior a la variante de Lebrija, unos 5,3 km
    más largo: la cuenta se retoma allí con su punto kilométrico, 99,7. Cada nodo queda a menos de
    400 m del suyo."""
    assert line.spec.line.pk_origin_km == 0.3
    assert [(r.node, r.pk_km) for r in line.spec.line.pk_restarts] == [
        ("aeropuerto-de-jerez", 99.7)
    ]
    assert line.node("sevilla-santa-justa").spec.reference_pk_km is None
    assert line.node("aeropuerto-de-jerez").spec.reference_pk_km is None
    airport = line.node("aeropuerto-de-jerez").km
    for node in line.nodes:
        pk = node.spec.reference_pk_km
        if pk is None:
            continue
        km = node.km + 0.3 if node.km < airport else node.km - airport + 99.7
        assert km == pytest.approx(pk, abs=0.4), node.spec.id


def test_double_track_and_speeds(line: BuiltNetwork) -> None:
    assert [s.id.removeprefix(f"{LINE}:") for s in line.segments] == ALL_SEGMENTS
    assert all(s.tracks == 2 for s in line.segments)
    assert line.spec.line.gauge_mm == 1668 and line.spec.line.electrification == "3 kV CC"
    # 160 hasta la bifurcación Utrera y 140 hasta Utrera, del mapa 3 de la Declaración sobre la
    # Red; desde Utrera, las de las vías de OSM
    assert [s.max_speed_kmh for s in line.segments] == [160] * 5 + [140] + [200] * 8 + [100, 200]
    for segment in line.segments[:6]:
        assert segment.attributes["max_speed_kmh"].source_id == MAP


def test_signalling_as_the_map_draws_it(line: BuiltNetwork) -> None:
    for segment in line.segments:
        assert segment.attributes["proteccion_tren"].value == "ertms_n1_asfa"
        assert segment.attributes["bloqueo"].value == "bab"
        assert segment.attributes["mando"].value == "ctc"
        for key in ("proteccion_tren", "bloqueo", "mando"):
            assert segment.attributes[key].source_id == MAP


def test_sources_and_operators_are_registered(spec: NetworkSpec) -> None:
    sources = {s.id: s for s in load_sources(SOURCES)}
    for part in spec.line.geometry_source.parts:
        source = sources[part.source_id]
        assert source.license == "ODbL 1.0"
        assert source.file == part.file and (DATA_DIR / part.file).exists()
    stations = sources["osm-instalaciones-sevilla-cadiz"]
    assert stations.file and (DATA_DIR / stations.file).exists()
    assert spec.line.verification_source_id == WIKIPEDIA and WIKIPEDIA in sources
    for section in spec.attribute_sections:
        assert section.source_id in sources
    assert {o.id for o in spec.operators if o.role == "operador"} == {"renfe"}
    assert all(o.source_id in sources for o in spec.operators)
    assert spec.line.zone == "andalucia"


def test_the_filter_takes_every_train_that_runs_on_the_line(
    feed: GtfsFeed, ouigo_feed: GtfsFeed, spec: NetworkSpec
) -> None:
    """Entran los viajes que paran en dos estaciones de la línea: 202 de Renfe y ninguno de
    Ouigo. Los que solo paran en Sevilla-Santa Justa no recorren ningún tramo."""
    assert spec.corridor_filter.min_node_stops == 2
    trips = select_trips_for_spec(feed, spec)
    assert len(trips) == 202
    assert Counter(t.product for t in trips) == {"MD": 177, "ALVIA": 25}
    codes = {n.adif_code for n in spec.nodes}
    selected = {t.trip_id for t in trips}
    for trip in feed.trips.values():
        if trip.trip_id not in selected:
            assert len(codes & set(_stops(trip))) <= 1, trip.train_number
    assert select_trips_for_spec(ouigo_feed, spec) == []


def test_each_train_counts_on_the_segments_it_runs(feed: GtfsFeed, line: BuiltNetwork) -> None:
    """Los Alvia de Madrid y los Media Distancia de Córdoba y Jaén recorren la línea entera; los
    de Málaga y Osuna la dejan en la bifurcación Utrera."""
    trips = select_trips_for_spec(feed, line.spec)
    madrid = [t for t in trips if MADRID in _stops(t)]
    cordoba = [t for t in trips if LORA in _stops(t)]
    malaga = [t for t in trips if OSUNA in _stops(t)]
    assert len(madrid) == 25 and cordoba and malaga
    for trip in madrid + cordoba:
        assert _short(_passes(trip, feed, line)) == ALL_SEGMENTS, trip.train_number
    for trip in malaga:
        assert _short(_passes(trip, feed, line)) == TO_BIF_UTRERA, trip.train_number


def test_stops_on_each_side_leave_by_the_right_node(spec: NetworkSpec) -> None:
    sm = spec.stop_mappings
    for node in NODES:
        code = next(n.adif_code for n in spec.nodes if n.id == node)
        if code:
            assert sm[code].node == node
    # Madrid, por la alta velocidad
    for stop_id in (MADRID, "37200", "37300"):
        assert [(v.line, v.node) for v in sm[stop_id].via] == [
            ("lav-madrid-sevilla", "sevilla-santa-justa")
        ]
    # Córdoba y Jaén, por la línea convencional de Córdoba a Sevilla, que no está cargada
    for stop_id in (CORDOBA, LORA, JAEN):
        assert sm[stop_id].exits == ["sevilla-santa-justa"] and not sm[stop_id].via
    for stop_id in ("01003", OSUNA, "54413"):
        assert sm[stop_id].exits == ["bif-utrera"] and not sm[stop_id].via
    # los Alvia que paran en Córdoba llegan a Santa Justa por la alta velocidad
    (rule,) = spec.route_overrides
    assert rule.consecutive_stop_ids == [JEREZ, SEVILLA, CORDOBA]
    assert [(v.line, v.node) for v in rule.stop_mappings[CORDOBA].via] == [
        ("lav-madrid-sevilla", "sevilla-santa-justa")
    ]


def test_the_high_speed_line_now_takes_its_direct_trains(feed: GtfsFeed) -> None:
    """Los trenes de Madrid a Sevilla y a Cádiz que no paran en Córdoba no pasaban el filtro de la
    alta velocidad: entran por dos reglas de recorrido nuevas. Son 23 viajes en el fichero de las
    pruebas: 10 AVE sin paradas entre Madrid y Sevilla y 13 Alvia de Madrid a Cádiz."""
    lav = load_network_spec(SPEC)
    rules = {r.id: r for r in lav.route_overrides}
    assert rules["madrid-sevilla-sin-paradas"].consecutive_stop_ids == [MADRID, SEVILLA]
    assert rules["madrid-jerez-sin-paradas"].consecutive_stop_ids == [MADRID, JEREZ]
    trips = select_trips_for_spec(feed, lav)
    direct = [
        t
        for t in trips
        if MADRID in _stops(t) and CORDOBA not in _stops(t) and {SEVILLA, JEREZ} & set(_stops(t))
    ]
    assert Counter(t.product for t in direct) == {"AVE": 10, "ALVIA": 13}
