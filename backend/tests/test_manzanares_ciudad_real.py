"""Tercera línea: la convencional Manzanares – Ciudad Real (línea 522 de Adif), de vía única."""

from __future__ import annotations

import pytest
from conftest import CONV_SPEC, DATA_DIR, MZCR_SPEC, SOURCES

from oniel.geo import haversine_km
from oniel.gtfs.reader import GtfsFeed
from oniel.gtfs.trips import calls_for_trip, route_for_trip, select_trips_for_spec
from oniel.network.build import BuiltNetwork, build_network
from oniel.network.spec import NetworkSpec, load_network_spec, load_sources
from oniel.sim.passes import LineNode, LineSegment, resolve_passes

RELATION = "osm-relation-6759901"


@pytest.fixture(scope="module")
def mzcr_spec() -> NetworkSpec:
    return load_network_spec(MZCR_SPEC)


@pytest.fixture(scope="module")
def conv_spec() -> NetworkSpec:
    return load_network_spec(CONV_SPEC)


@pytest.fixture(scope="module")
def mzcr(mzcr_spec: NetworkSpec) -> BuiltNetwork:
    return build_network(mzcr_spec, DATA_DIR)


def test_the_geometry_runs_from_manzanares_station_to_ciudad_real_station(
    mzcr: BuiltNetwork, spec: NetworkSpec, conv_spec: NetworkSpec
) -> None:
    """El trazado empieza junto a la estación de Manzanares de la convencional y termina junto a
    la de Ciudad Real de la alta velocidad, y mide lo que dicen las fuentes (64,5 km)."""
    manzanares = next(n for n in conv_spec.nodes if n.id == "manzanares").position
    ciudad_real = next(n for n in spec.nodes if n.id == "ciudad-real").position
    assert manzanares.lon is not None and manzanares.lat is not None
    assert ciudad_real.lon is not None and ciudad_real.lat is not None
    coords = mzcr.line.polyline.coords
    assert haversine_km(coords[0], (manzanares.lon, manzanares.lat)) < 0.1
    assert haversine_km(coords[-1], (ciudad_real.lon, ciudad_real.lat)) < 0.1
    assert mzcr.line.polyline.length_km == pytest.approx(64.5, abs=0.2)
    assert not mzcr.line.gaps_km and not mzcr.line.joins_km
    assert [p.source_id for p in mzcr.line.part_spans] == [RELATION]
    # pasa por Daimiel, al noroeste, y baja a Almagro: no es la línea recta de 47 km
    assert max(lat for _, lat in coords) > 39.06 and min(lat for _, lat in coords) < 38.90


def test_its_ends_are_the_stations_it_shares_with_the_other_two_lines(
    mzcr: BuiltNetwork, spec: NetworkSpec, conv_spec: NetworkSpec
) -> None:
    assert [n.spec.id for n in mzcr.nodes] == ["manzanares", "daimiel", "almagro", "ciudad-real"]
    assert {n.spec.id for n in mzcr.nodes if n.spec.shared} == {"manzanares", "ciudad-real"}
    # los nodos compartidos los definen las otras líneas, con las mismas coordenadas
    owners = {"manzanares": conv_spec, "ciudad-real": spec}
    for node_id, owner in owners.items():
        theirs = next(n for n in owner.nodes if n.id == node_id)
        ours = mzcr.node(node_id).spec
        assert not theirs.shared and ours.position == theirs.position
        assert ours.adif_code == theirs.adif_code
    assert all(n.offset_m < 100 for n in mzcr.nodes)


@pytest.mark.parametrize(
    ("node_id", "reference_pk"),
    [("manzanares", 197.319), ("daimiel", 218.799), ("almagro", 240.112), ("ciudad-real", 261.783)],
)
def test_nodes_sit_on_adif_kilometre_points_counted_from_madrid(
    mzcr: BuiltNetwork, node_id: str, reference_pk: float
) -> None:
    """Los PK de la línea 522 continúan los de Madrid: el origen, Manzanares, es el 197,319."""
    assert mzcr.spec.line.pk_origin_km == 197.319
    node = mzcr.node(node_id)
    assert node.spec.reference_pk_km == reference_pk
    assert node.km + mzcr.spec.line.pk_origin_km == pytest.approx(reference_pk, abs=0.1)


def test_the_whole_line_is_single_track(mzcr: BuiltNetwork) -> None:
    assert [s.id.split(":", 1)[1] for s in mzcr.segments] == [
        "manzanares:daimiel",
        "daimiel:almagro",
        "almagro:ciudad-real",
    ]
    assert all(s.tracks == 1 for s in mzcr.segments)
    assert all(s.source_id == RELATION and s.max_speed_kmh == 140 for s in mzcr.segments)
    assert sum(s.length_km for s in mzcr.segments) == pytest.approx(mzcr.line.polyline.length_km)


def test_sources_of_the_line_are_registered(mzcr_spec: NetworkSpec) -> None:
    sources = {s.id: s for s in load_sources(SOURCES)}
    geometry = sources[mzcr_spec.line.geometry_source.source_id]
    assert geometry.license == "ODbL 1.0" and geometry.retrieved_on == "2026-11-10"
    assert geometry.file is not None and (DATA_DIR / geometry.file).exists()
    assert geometry.file == mzcr_spec.line.geometry_source.parts[0].file
    assert mzcr_spec.line.verification_source_id == "wikipedia-linea-522"
    for source_id in ("wikipedia-linea-522", "fcmaf-linea-522"):
        assert sources[source_id].retrieved_on == "2026-11-10"
        assert "522" in f"{sources[source_id].name} {sources[source_id].coverage}"


def test_the_filter_selects_the_regional_trains_that_stop_on_the_line(
    feed: GtfsFeed, mzcr_spec: NetworkSpec, mzcr: BuiltNetwork
) -> None:
    """Entran por el filtro los 130 MD y Regional Exprés que paran en las cuatro estaciones; todos
    tienen paso publicado en los tres tramos."""
    nodes = {n.spec.id: LineNode(n.spec.id, n.km, n.lon, n.lat) for n in mzcr.nodes}
    segments = [LineSegment(s.id, s.km_from, s.km_to) for s in mzcr.segments]
    regional = [
        t for t in select_trips_for_spec(feed, mzcr_spec) if route_for_trip(mzcr_spec, t) is None
    ]
    assert len(regional) == 130
    assert {t.product for t in regional} == {"MD", "REG.EXP."}
    for trip in regional:
        calls = calls_for_trip(trip, feed, mzcr_spec)
        assert all(c.node_id or c.exit_node_ids for c in calls), trip.train_number
        passes, resolution = resolve_passes(calls, nodes, segments)
        assert resolution == "completa"
        assert [p.kind for p in passes] == ["publicado"] * 3, trip.train_number


def test_regional_trains_appear_here_and_on_the_conventional_line_up_to_manzanares(
    feed: GtfsFeed, spec: NetworkSpec, conv_spec: NetworkSpec, mzcr_spec: NetworkSpec
) -> None:
    """Un MD Alcázar de San Juan – Ciudad Real está en esta línea y en la convencional solo hasta
    Manzanares; no entra en la alta velocidad aunque pare en Ciudad Real."""
    regional = {
        t.trip_id
        for t in select_trips_for_spec(feed, mzcr_spec)
        if route_for_trip(mzcr_spec, t) is None
    }
    assert regional <= {t.trip_id for t in select_trips_for_spec(feed, conv_spec)}
    assert not regional & {t.trip_id for t in select_trips_for_spec(feed, spec)}
    conv = build_network(conv_spec, DATA_DIR)
    nodes = {n.spec.id: LineNode(n.spec.id, n.km, n.lon, n.lat) for n in conv.nodes}
    segments = [LineSegment(s.id, s.km_from, s.km_to) for s in conv.segments]
    south_of_manzanares = {
        s.id for s in conv.segments if s.km_from >= conv.node("manzanares").km - 0.05
    }
    for trip_id in regional:
        passes, _ = resolve_passes(
            calls_for_trip(feed.trips[trip_id], feed, conv_spec), nodes, segments
        )
        assert passes and not {p.segment_id for p in passes} & south_of_manzanares
