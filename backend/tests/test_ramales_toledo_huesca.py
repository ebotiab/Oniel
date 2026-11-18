"""Los dos ramales cortos de alta velocidad: La Sagra – Toledo, que sale de la línea Madrid –
Sevilla, y Zaragoza – Huesca, que sale de la de Barcelona junto a Zaragoza-Miraflores. Los dos
estaban a trazos en esas líneas."""

from __future__ import annotations

from collections import Counter

import pytest
from conftest import BCN_SPEC, DATA_DIR, HUESCA_SPEC, SOURCES, SPEC, TOLEDO_SPEC

from oniel.geo import haversine_km
from oniel.gtfs.reader import GtfsFeed, GtfsTrip
from oniel.gtfs.trips import calls_for_trip, calls_on_line, route_for_trip, select_trips_for_spec
from oniel.network.build import BuiltNetwork, build_network
from oniel.network.spec import NetworkSpec, load_network_spec, load_sources
from oniel.sim.passes import LineSegment, SegmentPass, resolve_passes
from oniel.validate import loaded_line

MAP = "adif-declaracion-red-2026-mapas"
ATOCHA, TOLEDO, CUENCA = "60000", "92102", "03208"
DELICIAS, TARDIENTA, HUESCA = "04040", "78200", "74200"


@pytest.fixture(scope="module")
def toledo() -> BuiltNetwork:
    return build_network(load_network_spec(TOLEDO_SPEC), DATA_DIR)


@pytest.fixture(scope="module")
def huesca() -> BuiltNetwork:
    return build_network(load_network_spec(HUESCA_SPEC), DATA_DIR)


def _stops(trip: GtfsTrip) -> list[str]:
    return [st.stop_id for st in trip.stop_times]


def _passes(trip: GtfsTrip, feed: GtfsFeed, net: BuiltNetwork) -> list[str]:
    own = loaded_line(net)
    route = route_for_trip(net.spec, trip)
    calls = calls_on_line(
        calls_for_trip(trip, feed, net.spec, nodes=own.nodes, others=[], route=route), route
    )
    segments = [LineSegment(s.id, s.km_from, s.km_to) for s in net.segments]
    passes: list[SegmentPass]
    passes, resolution = resolve_passes(calls, own.nodes, segments)
    assert resolution == "completa", trip.train_number
    return sorted(p.segment_id.split(":", 1)[1] for p in passes)


# La Sagra – Toledo


def test_toledo_geometry_is_the_020_relation(toledo: BuiltNetwork) -> None:
    """Un solo trozo de la relación 15616205, del desvío de La Sagra a la topera de una vía de
    andén de Toledo: 22,2 km, 1,4 más que el PK de la estación (véase docs/datos.md)."""
    coords = toledo.line.polyline.coords
    assert haversine_km(coords[0], (-3.8360015, 39.9907849)) < 0.01
    assert haversine_km(coords[-1], (-4.0104056, 39.862563)) < 0.01
    assert [p.source_id for p in toledo.line.part_spans] == ["osm-relation-15616205"]
    assert not toledo.line.gaps_km and not toledo.line.joins_km
    assert toledo.line.polyline.length_km == pytest.approx(22.2, abs=0.1)
    assert [n.spec.id for n in toledo.nodes] == ["bif-la-sagra", "toledo"]
    assert all(n.offset_m < 50 for n in toledo.nodes)


def test_toledo_hangs_from_the_la_sagra_junction_without_moving_it(toledo: BuiltNetwork) -> None:
    sevilla = load_network_spec(SPEC)
    bif = next(n for n in sevilla.nodes if n.id == "bif-la-sagra")
    assert bif.position.km == 52.7
    assert toledo.node("bif-la-sagra").spec.shared
    assert all(c.id != "lav-la-sagra-toledo" for c in sevilla.connections)
    assert not toledo.spec.connections


def test_toledo_attributes(toledo: BuiltNetwork) -> None:
    (segment,) = toledo.segments
    assert segment.tracks == 2 and segment.max_speed_kmh == 220
    assert toledo.spec.line.gauge_mm == 1435
    assert segment.attributes["proteccion_tren"].value == "lzb_asfa"
    assert segment.attributes["bloqueo"].value == "bca"
    assert segment.attributes["mando"].value == "sin_dato_publicado"
    assert all(segment.attributes[k].source_id == MAP for k in ("proteccion_tren", "bloqueo"))
    assert toledo.spec.line.zone == "madrid-castilla-la-mancha"


def test_toledo_trains_are_the_avant_and_they_also_run_on_the_sevilla_line(
    feed: GtfsFeed, ouigo_feed: GtfsFeed, toledo: BuiltNetwork
) -> None:
    """132 Avant en el horario de pruebas: los de Madrid a Toledo y los que siguen a Cuenca y
    Albacete. Antes no pasaban el filtro de la línea Madrid – Sevilla, porque no paran en Córdoba;
    ahora entran en ella por una regla de recorrido y cuentan de Madrid a La Sagra."""
    trips = select_trips_for_spec(feed, toledo.spec)
    assert len(trips) == 132
    assert Counter(t.product for t in trips) == {"AVANT": 132}
    assert select_trips_for_spec(ouigo_feed, toledo.spec) == []
    sevilla = build_network(load_network_spec(SPEC), DATA_DIR)
    on_sevilla = {t.trip_id for t in select_trips_for_spec(feed, sevilla.spec)}
    assert {t.trip_id for t in trips} <= on_sevilla
    for trip in trips:
        assert _passes(trip, feed, toledo) == ["bif-la-sagra:toledo"]
        passes = _passes(trip, feed, sevilla)
        assert passes == [
            "bif-los-gavilanes:bif-torrejon-de-velasco",
            "bif-torrejon-de-velasco:bif-yeles",
            "bif-yeles:bif-la-sagra",
            "madrid-puerta-de-atocha:bif-los-gavilanes",
        ], trip.train_number
    assert any(CUENCA in _stops(t) for t in trips)


# Zaragoza – Huesca


def test_huesca_geometry_is_the_070_relation(huesca: BuiltNetwork) -> None:
    """Un solo trozo de la relación 9277290, del desvío junto a la bifurcación Huesca a la topera
    de Huesca: 79,3 km, lo que suman los tres tramos que da Wikipedia."""
    coords = huesca.line.polyline.coords
    assert haversine_km(coords[0], (-0.8679365, 41.6327802)) < 0.01
    assert haversine_km(coords[-1], (-0.4097232, 42.1330289)) < 0.01
    assert [p.source_id for p in huesca.line.part_spans] == ["osm-relation-9277290"]
    assert not huesca.line.gaps_km and not huesca.line.joins_km
    assert huesca.line.polyline.length_km == pytest.approx(79.3, abs=0.1)
    assert [n.spec.id for n in huesca.nodes] == ["bif-huesca", "tardienta", "huesca"]
    assert all(n.offset_m < 50 for n in huesca.nodes)
    assert all(n.spec.reference_pk_km is None for n in huesca.nodes)


def test_huesca_hangs_from_the_barcelona_line_without_moving_the_junction(
    huesca: BuiltNetwork,
) -> None:
    barcelona = load_network_spec(BCN_SPEC)
    bif = next(n for n in barcelona.nodes if n.id == "bif-huesca")
    assert huesca.node("bif-huesca").spec.position == bif.position
    assert huesca.node("bif-huesca").spec.shared
    assert all(c.id != "zaragoza-huesca" for c in barcelona.connections)
    for stop_id in (TARDIENTA, HUESCA):
        via = barcelona.stop_mappings[stop_id].via
        assert [(v.line, v.node) for v in via] == [("lav-zaragoza-huesca", "bif-huesca")]
    assert {c.id: c.node_id for c in huesca.spec.connections} == {
        "tardienta-lleida": "tardienta",
        "huesca-canfranc": "huesca",
    }


def test_single_track_and_mixed_gauge_from_tardienta(huesca: BuiltNetwork) -> None:
    """Vía única en toda la línea; de ancho estándar hasta Tardienta y de tres carriles de allí a
    Huesca, compartida con los regionales de Canfranc."""
    first, second = huesca.segments
    assert first.tracks == 1 and second.tracks == 1
    assert "gauge" not in first.attributes
    assert second.attributes["gauge"].value == "mixto"
    assert [first.max_speed_kmh, second.max_speed_kmh] == [200, 160]
    for segment in huesca.segments:
        assert segment.attributes["proteccion_tren"].value == "asfa"
        assert segment.attributes["bloqueo"].value == "blau"
        assert segment.attributes["mando"].value == "ctc"
    assert huesca.spec.line.zone == "aragon-navarra-rioja"


def test_huesca_takes_the_ave_and_leaves_the_regional_trains_out(
    feed: GtfsFeed, ouigo_feed: GtfsFeed, huesca: BuiltNetwork
) -> None:
    """11 AVE en el horario de pruebas, de Madrid y de Zaragoza. Los regionales que paran en
    Tardienta o en Huesca van de Zaragoza a Tardienta por la línea convencional y paran en
    alguna estación de ella: quedan fuera."""
    trips = select_trips_for_spec(feed, huesca.spec)
    assert len(trips) == 11
    assert Counter(t.product for t in trips) == {"AVE": 11}
    assert select_trips_for_spec(ouigo_feed, huesca.spec) == []
    selected = {t.trip_id for t in trips}
    for trip in feed.trips.values():
        stops = set(_stops(trip))
        if trip.trip_id not in selected and stops & {TARDIENTA, HUESCA}:
            assert trip.product not in {"AVE", "AVLO", "ALVIA"}, trip.train_number
    for trip in trips:
        calls = _stops(trip)
        assert DELICIAS in calls
        expected = ["bif-huesca:tardienta", "tardienta:huesca"]
        if HUESCA not in calls:
            expected = expected[:1]
        assert _passes(trip, feed, huesca) == expected, trip.train_number


def test_sources_are_registered() -> None:
    sources = {s.id: s for s in load_sources(SOURCES)}
    for path in (TOLEDO_SPEC, HUESCA_SPEC):
        spec: NetworkSpec = load_network_spec(path)
        for part in spec.line.geometry_source.parts:
            source = sources[part.source_id]
            assert source.license == "ODbL 1.0"
            assert source.file == part.file and (DATA_DIR / part.file).exists()
        assert spec.line.verification_source_id in sources
        for section in spec.attribute_sections:
            assert section.source_id in sources
        assert {o.id for o in spec.operators if o.role == "operador"} == {"renfe"}
    stations = sources["osm-instalaciones-toledo-huesca"]
    assert stations.file and (DATA_DIR / stations.file).exists()
