"""Vitoria–Irún: continuidad, procedencia y reparto por los dos accesos de Altsasu."""

from __future__ import annotations

from collections import Counter

import pytest
from conftest import BURGOS_VITORIA_SPEC, DATA_DIR, SOURCES, VITORIA_IRUN_SPEC

from oniel.gtfs.reader import GtfsFeed, read_feed
from oniel.gtfs.trips import calls_for_trip, calls_on_line, route_for_trip, select_trips_for_spec
from oniel.network.build import BuiltNetwork, build_network
from oniel.network.spec import NetworkSpec, load_feeds, load_network_spec, load_sources
from oniel.sim.passes import LineSegment, resolve_passes
from oniel.validate import loaded_line


@pytest.fixture(scope="module")
def spec() -> NetworkSpec:
    return load_network_spec(VITORIA_IRUN_SPEC)


@pytest.fixture(scope="module")
def line(spec: NetworkSpec) -> BuiltNetwork:
    return build_network(spec, DATA_DIR)


def test_trazado_continuo_sin_regreso_a_burgos(line: BuiltNetwork) -> None:
    """La otra vía de Vitoria produciría un rodeo de 233 km antes de volver a la estación."""
    assert line.line.polyline.length_km == pytest.approx(145.35, abs=0.03)
    assert line.length_km == pytest.approx(145.345, abs=0.01)
    assert line.nodes[0].km < 0.01
    assert not line.line.gaps_km and not line.line.joins_km
    assert max(n.offset_m for n in line.nodes) < 25
    assert len(line.nodes) == 21 and len(line.segments) == 20
    assert line.node("san-sebastian-donostia").km == pytest.approx(128.48, abs=0.02)
    assert line.node("bif-altsasu").km < line.node("altsasu").km


def test_vitoria_conserva_la_identidad_y_sustituye_el_trazo(spec: NetworkSpec) -> None:
    previous = load_network_spec(BURGOS_VITORIA_SPEC)
    theirs = next(n for n in previous.nodes if n.id == "vitoria-gasteiz")
    ours = next(n for n in spec.nodes if n.id == theirs.id)
    assert ours.shared and ours.position == theirs.position
    assert {n.id for n in spec.nodes if n.shared} == {theirs.id}
    assert "conv-vitoria-altsasu" not in {c.id for c in previous.connections}
    assert all(
        previous.stop_mappings[code].via[-1].line == spec.line.id
        for code in ("11300", "11511", "11600")
    )


def test_nombres_ferroviarios_y_puntos_kilometricos_sin_inventar(line: BuiltNetwork) -> None:
    assert line.node("san-sebastian-donostia").spec.name == "San Sebastián-Donostia"
    assert line.node("irun").spec.name == "Irun"
    assert line.node("agurain-salvatierra-de-alava").spec.name == "Agurain-Salvatierra de Álava"
    assert line.spec.line.reference_length_km is None and line.spec.line.opened_on is None
    for n in line.nodes:
        if n.spec.reference_pk_km is not None:
            assert abs(n.km + line.spec.line.pk_origin_km - n.spec.reference_pk_km) < 0.4
    # El esquema histórico difiere desde Beasain: no se reemplazan sus PK por kilómetros medidos.
    assert line.node("beasain").spec.reference_pk_km is None
    assert line.node("irun").spec.reference_pk_km is None


def test_atributos_con_fuente_y_sin_anticipar_la_alta_velocidad(line: BuiltNetwork) -> None:
    sources = {s.id: s for s in load_sources(SOURCES)}
    assert line.spec.line.max_speed_kmh == max(s.max_speed_kmh or 0 for s in line.segments) == 160
    assert line.spec.line.gauge_mm == 1668
    assert line.spec.line.electrification == "3 kV CC"
    for s in line.segments:
        assert s.tracks == 2
        assert s.attributes["proteccion_tren"].value == "asfa"
        assert s.attributes["bloqueo"].value == "bab"
        assert s.attributes["mando"].value == "ctc"
        assert s.attributes["electrification"].value == "3 kV CC"
        for a in s.attributes.values():
            assert a.source_id in sources and a.checked_on
    for sid in (
        "osm-vitoria-irun-2026",
        "osm-instalaciones-vitoria-irun",
        "osm-nudo-altsasu",
        "osm-astigarraga-2026",
        "wikipedia-vitoria-irun-2026",
    ):
        source = sources[sid]
        assert source.file and (DATA_DIR / source.file).is_file()
        assert source.publisher and source.url and source.license and source.coverage


def test_salidas_sin_cargar_en_los_dos_accesos_de_altsasu(spec: NetworkSpec) -> None:
    pamplona = load_network_spec(DATA_DIR / "curated/castejon-pamplona.json")
    north = next(c for c in pamplona.connections if c.id == "conv-pamplona-altsasu")
    assert north.to_node_id == "altsasu"
    south = next(c for c in spec.connections if c.id == "conv-bif-altsasu-pamplona")
    assert south.node_id == "bif-altsasu" and south.to_node_id == "pamplona"
    assert all(c.status == "no_cargada" for c in [north, *spec.connections])
    assert spec.stop_mappings["80100"].exits == ["bif-altsasu"]
    assert spec.route_overrides[0].stop_mappings["80100"].exits == ["altsasu"]


def test_horarios_sin_cercanias_ni_operadores_ajenos(
    spec: NetworkSpec, feed: GtfsFeed, ouigo_feed: GtfsFeed
) -> None:
    trips = select_trips_for_spec(feed, spec)
    assert len(trips) == 145
    assert Counter(t.product for t in trips) == {
        "Intercity": 42,
        "Regional Exprés": 36,
        "Alvia": 33,
        "Media Distancia": 22,
        "Regional": 12,
    }
    assert len({t.trip_id for t in trips}) == len(trips)
    assert {o.id for o in spec.operators if o.role == "operador"} == {"renfe"}
    assert select_trips_for_spec(ouigo_feed, spec) == []
    for declared in load_feeds(SOURCES):
        if declared.operator_id in {"iryo", "sncf"}:
            other = read_feed(
                DATA_DIR / declared.file,
                stop_id_prefix=declared.stop_id_prefix,
                stop_id_aliases=declared.stop_id_aliases,
                train_number_field=declared.train_number_field,
            )
            assert select_trips_for_spec(other, spec) == []


def test_cada_familia_recorre_solo_sus_tramos(line: BuiltNetwork, feed: GtfsFeed) -> None:
    own = loaded_line(line)
    segments = [LineSegment(s.id, s.km_from, s.km_to) for s in line.segments]
    families: Counter[str] = Counter()
    for trip in select_trips_for_spec(feed, line.spec):
        route = route_for_trip(line.spec, trip)
        calls = calls_on_line(
            calls_for_trip(trip, feed, line.spec, nodes=own.nodes, others=[], route=route), route
        )
        passes, resolution = resolve_passes(calls, own.nodes, segments)
        assert resolution == "completa", trip.train_number
        assert all(p.kind != "indeterminado" for p in passes)
        ids = {p.segment_id for p in passes}
        assert len(ids) == len(passes), trip.train_number
        stops = {s.stop_id for s in trip.stop_times}
        if {"11208", "80100"} <= stops and "11300" not in stops:
            assert ids == {s.id for s in line.segments[:4]}, trip.train_number
            families["vitoria-pamplona"] += 1
        if {"11300", "80100", "11511"} <= stops:
            assert ids == {s.id for s in line.segments[5:17]}, trip.train_number
            families["barcelona-san-sebastian"] += 1
        if {"17000", "11600"} <= stops:
            assert ids == {s.id for s in line.segments}, trip.train_number
            families["madrid-irun"] += 1
    assert all(
        families[f] > 0 for f in ("vitoria-pamplona", "barcelona-san-sebastian", "madrid-irun")
    )
