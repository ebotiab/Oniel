"""Cuarta línea: el ramal convencional Espelúy – Jaén (línea 402 de Adif), de vía única."""

from __future__ import annotations

import datetime as dt

import pytest
from conftest import CONV_SPEC, DATA_DIR, JAEN_SPEC, SOURCES

from oniel.geo import haversine_km
from oniel.gtfs.reader import GtfsFeed
from oniel.gtfs.trips import calls_for_trip, select_trips_for_spec
from oniel.network.build import BuiltNetwork, build_network
from oniel.network.spec import NetworkSpec, load_annotations, load_network_spec, load_sources
from oniel.sim.passes import LineNode, LineSegment, resolve_passes

LINE_400 = "osm-relation-11351144"
RELATION = "osm-relation-11351146"
ANNOTATIONS = DATA_DIR / "curated" / "anotaciones.json"


@pytest.fixture(scope="module")
def jaen_spec() -> NetworkSpec:
    return load_network_spec(JAEN_SPEC)


@pytest.fixture(scope="module")
def conv_spec() -> NetworkSpec:
    return load_network_spec(CONV_SPEC)


@pytest.fixture(scope="module")
def jaen(jaen_spec: NetworkSpec) -> BuiltNetwork:
    return build_network(jaen_spec, DATA_DIR)


def test_the_geometry_runs_from_espeluy_station_to_jaen_station(
    jaen: BuiltNetwork, conv_spec: NetworkSpec
) -> None:
    """El trazado sale de la estación de Espelúy por la línea 400, toma el ramal en la aguja del
    km 340,1 y termina junto a la estación de Jaén."""
    espeluy = next(n for n in conv_spec.nodes if n.id == "espeluy").position
    assert espeluy.lon is not None and espeluy.lat is not None
    coords = jaen.line.polyline.coords
    assert haversine_km(coords[0], (espeluy.lon, espeluy.lat)) < 0.1
    assert haversine_km(coords[-1], (-3.790798, 37.779827)) < 0.1
    # 0,9 km por la línea 400 y los 32,3 km de la relación de la línea 402: Wikipedia da 32,8 km
    # para la línea, contados desde la aguja
    assert [p.source_id for p in jaen.line.part_spans] == [LINE_400, RELATION]
    first, second = jaen.line.part_spans
    assert first.km_to == pytest.approx(0.94, abs=0.05)
    assert second.km_to - second.km_from == pytest.approx(32.8, abs=0.7)
    assert jaen.line.polyline.length_km == pytest.approx(33.2, abs=0.1)
    assert not jaen.line.gaps_km
    # baja hacia el sur: Jaén queda 25 km por debajo de Espelúy
    assert coords[0][1] - coords[-1][1] == pytest.approx(0.23, abs=0.01)


def test_espeluy_is_the_station_of_the_main_line(
    jaen: BuiltNetwork, conv_spec: NetworkSpec
) -> None:
    assert [n.spec.id for n in jaen.nodes] == ["espeluy", "mengibar-artichuela", "jaen"]
    assert {n.spec.id for n in jaen.nodes if n.spec.shared} == {"espeluy"}
    theirs = next(n for n in conv_spec.nodes if n.id == "espeluy")
    ours = jaen.node("espeluy").spec
    assert not theirs.shared and ours.position == theirs.position
    assert ours.adif_code == theirs.adif_code == "50400"
    assert all(n.offset_m < 100 for n in jaen.nodes)
    # con la línea cargada, de Espelúy ya no sale una conexión a trazos
    assert all(c.node_id != "espeluy" for c in conv_spec.connections)
    assert jaen.spec.connections == []


def test_the_whole_line_is_single_track(jaen: BuiltNetwork) -> None:
    assert [s.id for s in jaen.segments] == [
        "espeluy-jaen:espeluy:mengibar-artichuela",
        "espeluy-jaen:mengibar-artichuela:jaen",
    ]
    assert all(s.tracks == 1 and s.max_speed_kmh == 160 for s in jaen.segments)
    assert sum(s.length_km for s in jaen.segments) == pytest.approx(jaen.line.polyline.length_km)
    # de Mengíbar-Artichuela a Jaén, 28,0 km medidos frente a 28,8 km entre sus PK (148,0 y 119,2)
    assert jaen.segments[1].length_km == pytest.approx(28.8, abs=0.9)


def test_sources_of_the_line_are_registered(jaen_spec: NetworkSpec) -> None:
    sources = {s.id: s for s in load_sources(SOURCES)}
    geometry = sources[jaen_spec.line.geometry_source.source_id]
    assert geometry.license == "ODbL 1.0" and geometry.retrieved_on == "2026-11-12"
    assert geometry.file is not None and (DATA_DIR / geometry.file).exists()
    assert geometry.file == jaen_spec.line.geometry_source.parts[1].file
    assert jaen_spec.line.verification_source_id == "wikipedia-linea-402"
    assert "402" in str(sources["wikipedia-linea-402"].coverage)
    for section in jaen_spec.attribute_sections:
        assert section.source_id in sources


def test_the_filter_selects_the_trains_of_jaen_and_mengibar(
    feed: GtfsFeed, jaen_spec: NetworkSpec, jaen: BuiltNetwork
) -> None:
    """Entran los 221 Media Distancia que paran en Jaén o en Mengíbar-Artichuela. Todos recorren
    el primer tramo; los 20 que van de Linares-Baeza a Mengíbar-Artichuela no llegan a Jaén."""
    nodes = {n.spec.id: LineNode(n.spec.id, n.km, n.lon, n.lat) for n in jaen.nodes}
    segments = [LineSegment(s.id, s.km_from, s.km_to) for s in jaen.segments]
    trips = select_trips_for_spec(feed, jaen_spec)
    assert len(trips) == 221
    assert {t.product for t in trips} == {"MD"}
    first, second = (s.id for s in jaen.segments)
    by_segment = {first: 0, second: 0}
    published = 0
    for trip in trips:
        calls = calls_for_trip(trip, feed, jaen_spec)
        assert all(c.node_id or c.exit_node_ids for c in calls), trip.train_number
        passes, resolution = resolve_passes(calls, nodes, segments)
        assert resolution == "completa"
        for p in passes:
            by_segment[p.segment_id] += 1
            published += p.kind == "publicado"
    assert by_segment == {first: 221, second: 201}
    # solo los trenes que paran en Mengíbar-Artichuela y en Jaén tienen horas publicadas
    assert published == 20


def test_the_main_line_reaches_jaen_through_espeluy(conv_spec: NetworkSpec) -> None:
    for stop_id in ("03001", "03100"):
        mapping = conv_spec.stop_mappings[stop_id]
        assert mapping.exits == ["espeluy"]
        assert [(leg.line, leg.node) for leg in mapping.via] == [("espeluy-jaen", "espeluy")]
    rules = {r.id: r for r in conv_spec.route_overrides}
    assert rules["cordoba-jaen-sin-paradas"].consecutive_stop_ids == ["50500", "03100"]
    assert rules["linares-baeza-mengibar"].consecutive_stop_ids == ["50300", "03001"]


def test_the_line_has_no_passenger_trains_while_the_main_line_works_last() -> None:
    """Desde el 6 de septiembre de 2026 los trenes de Jaén hacen su recorrido por carretera."""
    cut = next(
        a for a in load_annotations(ANNOTATIONS) if a.id == "espeluy-jaen-sin-trenes-2026-09-06"
    )
    assert (cut.kind, cut.status, cut.line_id) == ("interrupcion", "vigente", "espeluy-jaen")
    assert (cut.from_node, cut.to_node) == ("espeluy", "jaen")
    assert cut.source_ids[0] == "renfe-nota-md-jaen-madrid-2026-09"
    assert cut.active_on(dt.date(2026, 11, 10)) and not cut.active_on(dt.date(2026, 9, 5))
