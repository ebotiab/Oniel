"""La línea convencional Burgos – Miranda de Ebro – Vitoria (un trecho de la 100 de Adif, Madrid –
Hendaya): sale de Burgos-Rosa Manzano, donde acaba la alta velocidad de Venta de Baños, y llega a
Vitoria por Miranda de Ebro. Las ramas de Bilbao, de Logroño y de Altsasu quedan a trazos."""

from __future__ import annotations

from collections import Counter

import pytest
from conftest import (
    BURGOS_VITORIA_SPEC,
    DATA_DIR,
    LAV_BURGOS_SPEC,
    LAV_LEON_SPEC,
    LAV_VALLADOLID_SPEC,
    SOURCES,
)

from oniel.geo import haversine_km
from oniel.gtfs.reader import GtfsFeed, GtfsTrip
from oniel.gtfs.trips import calls_for_trip, calls_on_line, route_for_trip, select_trips_for_spec
from oniel.network.build import BuiltNetwork, build_network
from oniel.network.spec import NetworkSpec, load_network_spec, load_sources
from oniel.sim.passes import LineSegment, SegmentPass, resolve_passes
from oniel.validate import loaded_line

LINE = "burgos-miranda-vitoria"
RELATION = "osm-relation-18347132"
WIKIPEDIA = "wikipedia-linea-100"
MAP = "adif-declaracion-red-2026-mapas"
BURGOS, BRIVIESCA, MIRANDA, VITORIA = "11014", "11109", "11200", "11208"
NODES = [
    "burgos-rosa-manzano",
    "briviesca",
    "pancorbo",
    "miranda-de-ebro",
    "manzanos",
    "la-puebla-de-arganzon",
    "nanclares-langraiz",
    "vitoria-gasteiz",
]
ALL_SEGMENTS = [f"{a}:{b}" for a, b in zip(NODES, NODES[1:], strict=False)]


@pytest.fixture(scope="module")
def spec() -> NetworkSpec:
    return load_network_spec(BURGOS_VITORIA_SPEC)


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


def test_the_geometry_follows_line_100_from_burgos_to_vitoria(line: BuiltNetwork) -> None:
    """Un solo trozo de la relación de la línea Madrid – Hendaya, de la estación de Burgos a la de
    Vitoria, sin saltos: 117,3 km."""
    coords = line.line.polyline.coords
    assert haversine_km(coords[0], (-3.6663219, 42.3711651)) < 0.05
    assert haversine_km(coords[-1], (-2.672697, 42.841303)) < 0.05
    assert [p.source_id for p in line.line.part_spans] == [RELATION]
    assert not line.line.gaps_km and not line.line.joins_km
    assert line.line.polyline.length_km == pytest.approx(117.3, abs=0.1)


def test_nodes_stations_and_dashed_branches(line: BuiltNetwork) -> None:
    assert [n.spec.id for n in line.nodes] == NODES
    assert all(n.spec.kind == "estacion" for n in line.nodes)
    assert {n.spec.id for n in line.nodes if n.spec.rank == "secundario"} == {
        "briviesca",
        "pancorbo",
        "manzanos",
        "la-puebla-de-arganzon",
        "nanclares-langraiz",
    }
    assert line.node("miranda-de-ebro").spec.adif_code == MIRANDA
    assert line.node("vitoria-gasteiz").spec.adif_code == VITORIA
    assert {c.id: c.node_id for c in line.spec.connections} == {
        "conv-miranda-logrono": "miranda-de-ebro",
        "conv-vitoria-altsasu": "vitoria-gasteiz",
    }
    for c in line.spec.connections:
        node = line.node(c.node_id).spec.position
        assert c.sketch[0] == (node.lon, node.lat) and c.status == "no_cargada"
    assert all(n.offset_m < 50 for n in line.nodes)


def test_it_starts_at_the_burgos_station_of_the_high_speed_line(line: BuiltNetwork) -> None:
    """Burgos-Rosa Manzano la define la alta velocidad de Venta de Baños, que ya no sale a trazos
    hacia Miranda: esta línea la incorpora sin moverla."""
    assert {n.spec.id for n in line.nodes if n.spec.shared} == {"burgos-rosa-manzano"}
    burgos = load_network_spec(LAV_BURGOS_SPEC)
    theirs = next(n for n in burgos.nodes if n.id == "burgos-rosa-manzano")
    assert line.node("burgos-rosa-manzano").spec.position == theirs.position
    assert all("miranda" not in c.id for c in burgos.connections)


def test_kilometre_points_follow_line_100_after_the_burgos_bypass(line: BuiltNetwork) -> None:
    """Los puntos kilométricos de Adif cuentan desde Madrid por el trazado anterior a la variante
    de Burgos: el origen de la línea es el 374,9 y Burgos no guarda el suyo. Cada estación queda a
    menos de 150 m."""
    origin = line.spec.line.pk_origin_km
    assert origin == 374.9
    assert line.node("burgos-rosa-manzano").spec.reference_pk_km is None
    assert line.node("miranda-de-ebro").spec.reference_pk_km == 458.913
    assert line.node("vitoria-gasteiz").spec.reference_pk_km == 492.292
    for node in line.nodes[1:]:
        assert node.spec.reference_pk_km is not None
        assert node.km + origin == pytest.approx(node.spec.reference_pk_km, abs=0.15)


def test_double_track_and_speeds_from_the_tracks(line: BuiltNetwork) -> None:
    assert [s.id.removeprefix(f"{LINE}:") for s in line.segments] == ALL_SEGMENTS
    assert all(s.tracks == 2 for s in line.segments)
    assert line.spec.line.gauge_mm == 1668 and line.spec.line.electrification == "3 kV CC"
    # las vías de OSM traen la velocidad en todos los tramos; la más baja, el paso de Pancorbo y
    # la llegada a Miranda
    assert [s.max_speed_kmh for s in line.segments] == [200, 160, 110, 110, 110, 150, 150]


def test_signalling_as_the_map_draws_it(line: BuiltNetwork) -> None:
    for segment in line.segments:
        assert segment.attributes["proteccion_tren"].value == "asfa"
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
    stations = sources["osm-instalaciones-burgos-vitoria"]
    assert stations.file and (DATA_DIR / stations.file).exists()
    assert spec.line.verification_source_id == WIKIPEDIA and WIKIPEDIA in sources
    for section in spec.attribute_sections:
        assert section.source_id in sources
    assert {o.id for o in spec.operators if o.role == "operador"} == {"renfe"}
    assert all(o.source_id in sources for o in spec.operators)
    assert spec.line.zone == "cantabrico"


def test_the_filter_takes_every_train_that_runs_on_the_line(
    feed: GtfsFeed, ouigo_feed: GtfsFeed, spec: NetworkSpec
) -> None:
    """Entran los viajes que paran en dos estaciones de la línea: 182 de Renfe y ninguno de
    Ouigo. Los que solo paran en una no recorren ningún tramo."""
    assert spec.corridor_filter.min_node_stops == 2
    trips = select_trips_for_spec(feed, spec)
    assert len(trips) == 182
    assert Counter(t.product for t in trips) == {
        "Intercity": 54,
        "Regional Exprés": 45,
        "Alvia": 38,
        "Media Distancia": 33,
        "Regional": 12,
    }
    codes = {n.adif_code for n in spec.nodes}
    selected = {t.trip_id for t in trips}
    for trip in feed.trips.values():
        stops = _stops(trip)
        # ningún tren pasa de un lado a otro de la línea sin parar en ella
        if trip.trip_id not in selected:
            assert len(codes & set(stops)) <= 1, trip.train_number
    assert select_trips_for_spec(ouigo_feed, spec) == []


def test_each_train_counts_on_the_segments_it_runs(feed: GtfsFeed, line: BuiltNetwork) -> None:
    """Los Alvia de Madrid a Irún recorren la línea entera; los de Logroño y Bilbao la dejan en
    Miranda de Ebro, y los regionales de Miranda a Altsasu no pasan de Miranda hacia Burgos."""
    trips = select_trips_for_spec(feed, line.spec)
    irun = [t for t in trips if {BURGOS, "11600"} <= set(_stops(t))]
    logrono = [t for t in trips if {BURGOS, "81100"} <= set(_stops(t))]
    bilbao = [t for t in trips if {BURGOS, "13200"} <= set(_stops(t))]
    altsasu = [t for t in trips if BURGOS not in _stops(t) and "11300" in _stops(t)]
    assert irun and logrono and bilbao and altsasu
    for trip in irun[:10]:
        assert _short(_passes(trip, feed, line)) == ALL_SEGMENTS
    for trip in logrono + bilbao:
        assert _short(_passes(trip, feed, line)) == ALL_SEGMENTS[:3]
    for trip in altsasu:
        assert _short(_passes(trip, feed, line)) == ALL_SEGMENTS[3:]


def test_stops_on_each_side_leave_by_the_right_node(spec: NetworkSpec) -> None:
    sm = spec.stop_mappings
    for node in NODES:
        code = next(n.adif_code for n in spec.nodes if n.id == node)
        assert code and sm[code].node == node
    for stop_id in ("13106", "13200", "81002", "81100"):
        assert sm[stop_id].exits == ["miranda-de-ebro"]
    for stop_id in ("11300", "11511", "11600", "80100", "04040", "71801"):
        assert sm[stop_id].exits == ["vitoria-gasteiz"] and not sm[stop_id].via
    # hacia Valladolid y Madrid, por la alta velocidad de Burgos y la línea de León
    assert [(v.line, v.node) for v in sm["17000"].via] == [
        ("lav-venta-de-banos-burgos", "burgos-rosa-manzano"),
        ("lav-valladolid-leon", "bif-venta-de-banos"),
        ("lav-madrid-valladolid", "valladolid-campo-grande"),
    ]
    # Palencia y León llegan por el ramal de Soto de Cerrato, que no está cargado; la línea
    # convencional de Venta de Baños a Burgos tampoco
    for stop_id in ("14100", "15100", "11000", "10000"):
        assert sm[stop_id].exits == ["burgos-rosa-manzano"] and not sm[stop_id].via
    # y al revés: Miranda y Vitoria, desde las líneas de Burgos, León y Madrid
    expected = {
        LAV_BURGOS_SPEC: [(LINE, "burgos-rosa-manzano")],
        LAV_LEON_SPEC: [
            ("lav-venta-de-banos-burgos", "bif-venta-de-banos"),
            (LINE, "burgos-rosa-manzano"),
        ],
        LAV_VALLADOLID_SPEC: [
            ("lav-valladolid-leon", "valladolid-campo-grande"),
            ("lav-venta-de-banos-burgos", "bif-venta-de-banos"),
            (LINE, "burgos-rosa-manzano"),
        ],
    }
    for path, via in expected.items():
        other = load_network_spec(path).stop_mappings
        for stop_id in (MIRANDA, VITORIA):
            assert [(v.line, v.node) for v in other[stop_id].via] == via, (path.name, stop_id)


def test_briviesca_only_sees_the_conventional_trains(feed: GtfsFeed, spec: NetworkSpec) -> None:
    """En Briviesca solo paran trenes que llegan a Burgos por la línea convencional; la alta
    velocidad de Burgos los deja fuera por eso mismo."""
    trips = [t for t in select_trips_for_spec(feed, spec) if BRIVIESCA in _stops(t)]
    assert trips
    assert {t.product for t in trips} <= {"Media Distancia", "Regional Exprés", "Regional"}
