"""La convencional Alcázar de San Juan – Albacete – La Encina, el trecho central de la línea 300
de Adif (Madrid – Valencia), de vía doble."""

from __future__ import annotations

from collections import Counter

import pytest
from conftest import ALBACETE_SPEC, CONV_SPEC, DATA_DIR, MZCR_SPEC, SOURCES

from oniel.domain.station_closures import STATION_CLOSURES
from oniel.geo import haversine_km
from oniel.gtfs.reader import GtfsFeed
from oniel.gtfs.trips import calls_for_trip, select_trips_for_spec
from oniel.network.build import BuiltNetwork, build_network
from oniel.network.spec import NetworkSpec, load_network_spec, load_sources
from oniel.sim.passes import LineNode, LineSegment, resolve_passes

LINE = "alcazar-albacete"
RELATION = "osm-relation-18368327"
MAP = "adif-declaracion-red-2026-mapas"
#: Las estaciones intermedias, a las que solo se llega por esta línea.
INTERMEDIATE = ["60402", "60406", "60500", "60503", "60505", "60507"]


@pytest.fixture(scope="module")
def albacete_spec() -> NetworkSpec:
    return load_network_spec(ALBACETE_SPEC)


@pytest.fixture(scope="module")
def conv_spec() -> NetworkSpec:
    return load_network_spec(CONV_SPEC)


@pytest.fixture(scope="module")
def albacete(albacete_spec: NetworkSpec) -> BuiltNetwork:
    return build_network(albacete_spec, DATA_DIR)


def test_el_trazado_llega_desde_alcazar_hasta_la_bifurcacion(
    albacete: BuiltNetwork, conv_spec: NetworkSpec
) -> None:
    """El trazado sale de la estación de Alcázar de San Juan, donde acaba el trecho de la línea 300
    que usa la convencional, y llega por Albacete hasta la bifurcación de La Encina."""
    alcazar = next(n for n in conv_spec.nodes if n.id == "alcazar-de-san-juan").position
    assert alcazar.lon is not None and alcazar.lat is not None
    coords = albacete.line.polyline.coords
    assert haversine_km(coords[0], (alcazar.lon, alcazar.lat)) < 0.1
    assert haversine_km(coords[-1], (-0.9264679, 38.7591849)) < 0.01
    assert [p.source_id for p in albacete.line.part_spans] == [RELATION, RELATION]
    assert albacete.node("albacete-los-llanos").km == pytest.approx(130.76, abs=0.01)
    assert albacete.length_km == pytest.approx(231.48, abs=0.01)
    assert not albacete.line.gaps_km


def test_alcazar_is_the_station_of_the_main_line(
    albacete: BuiltNetwork, conv_spec: NetworkSpec
) -> None:
    assert [n.spec.id for n in albacete.nodes] == [
        "alcazar-de-san-juan",
        "campo-de-criptana",
        "socuellamos",
        "villarrobledo",
        "minaya",
        "la-roda-de-albacete",
        "la-gineta",
        "albacete-los-llanos",
        "bif-chinchilla",
        "almansa",
        "la-encina",
        "bif-la-encina",
    ]
    assert {n.spec.id for n in albacete.nodes if n.spec.shared} == {
        "alcazar-de-san-juan",
        "bif-la-encina",
    }
    theirs = next(n for n in conv_spec.nodes if n.id == "alcazar-de-san-juan")
    ours = albacete.node("alcazar-de-san-juan").spec
    assert not theirs.shared and ours.position == theirs.position
    assert ours.adif_code == theirs.adif_code == "60400"
    assert ours.reference_pk_km == theirs.reference_pk_km == 148.1
    assert all(n.offset_m < 100 for n in albacete.nodes)
    # con la línea cargada, de Alcázar ya no sale una conexión a trazos hacia Levante...
    assert all(c.node_id != "alcazar-de-san-juan" for c in conv_spec.connections)
    (conn,) = albacete.spec.connections
    assert (conn.node_id, conn.to_node_id, conn.status) == (
        "bif-chinchilla",
        "murcia-del-carmen",
        "no_cargada",
    )
    xativa = load_network_spec(DATA_DIR / "curated" / "valencia-xativa-alicante.json")
    assert not {"conv-la-encina-albacete", "conv-caudete-la-encina"} & {
        c.id for c in xativa.connections
    }
    junction = next(n for n in xativa.nodes if n.id == "bif-la-encina")
    assert not junction.shared and junction.position == albacete.node(junction.id).spec.position


def test_adif_kilometre_points_continue_those_of_madrid_alcazar(albacete: BuiltNetwork) -> None:
    """Los PK siguen contando desde Madrid: Alcázar es el 148,1 y Albacete, el 278,7. El medido
    queda a menos de 300 m del de Adif en todas las estaciones."""
    origin = albacete.spec.line.pk_origin_km
    assert origin == 148.1
    for node in albacete.nodes:
        if node.spec.id in {"bif-chinchilla", "bif-la-encina"}:
            assert node.spec.reference_pk_km is None
            continue
        assert node.spec.reference_pk_km is not None
        assert node.km + origin == pytest.approx(node.spec.reference_pk_km, abs=0.35)
    assert albacete.node("albacete-los-llanos").spec.reference_pk_km == 278.7


def test_the_whole_line_is_double_track(albacete: BuiltNetwork) -> None:
    assert len(albacete.segments) == 11
    assert all(s.tracks == 2 for s in albacete.segments)
    assert all(s.id.startswith(f"{LINE}:") for s in albacete.segments)
    assert max(s.max_speed_kmh or 0 for s in albacete.segments) == 200
    # los tramos van de estación a estación: el trazado sobra unos metros en cada extremo
    assert sum(s.length_km for s in albacete.segments) == pytest.approx(
        albacete.line.polyline.length_km, abs=0.1
    )


def test_signalling_changes_at_villarrobledo_and_la_roda(albacete: BuiltNetwork) -> None:
    """Mapa 4 de la Declaración sobre la Red: «BAB» hasta Villarrobledo, «BAD» hasta La Roda y
    «BAB ctc» hasta Albacete. Donde el rótulo no lleva «ctc», el mando es «sin control centralizado»."""
    by_segment = {s.id.removeprefix(f"{LINE}:"): s.attributes for s in albacete.segments}
    read = {
        k: (a["proteccion_tren"].value, a["bloqueo"].value, a["mando"].value)
        for k, a in by_segment.items()
    }
    assert read == {
        "alcazar-de-san-juan:campo-de-criptana": ("asfa", "bab", "sin_ctc"),
        "campo-de-criptana:socuellamos": ("asfa", "bab", "sin_ctc"),
        "socuellamos:villarrobledo": ("asfa", "bab", "sin_ctc"),
        "villarrobledo:minaya": ("asfa", "bad", "sin_ctc"),
        "minaya:la-roda-de-albacete": ("asfa", "bad", "sin_ctc"),
        "la-roda-de-albacete:la-gineta": ("asfa", "bab", "ctc"),
        "la-gineta:albacete-los-llanos": ("asfa", "bab", "ctc"),
        **{s.id.removeprefix(f"{LINE}:"): ("asfa", "bab", "ctc") for s in albacete.segments[7:]},
    }
    for attributes in by_segment.values():
        for key in ("proteccion_tren", "bloqueo", "mando"):
            assert attributes[key].source_id == MAP


def test_sources_of_the_line_are_registered(albacete_spec: NetworkSpec) -> None:
    sources = {s.id: s for s in load_sources(SOURCES)}
    geometry = sources[albacete_spec.line.geometry_source.source_id]
    assert geometry.id == RELATION and geometry.license == "ODbL 1.0"
    assert geometry.file is not None and (DATA_DIR / geometry.file).exists()
    assert "Albacete" in str(geometry.coverage)
    verification = sources[str(albacete_spec.line.verification_source_id)]
    assert verification.id == "wikipedia-linea-300-alcazar-albacete"
    assert "278,7" in str(verification.coverage)
    for section in albacete_spec.attribute_sections:
        assert section.source_id in sources


def test_the_filter_selects_the_trains_that_run_along_the_line(
    feed: GtfsFeed, albacete_spec: NetworkSpec, albacete: BuiltNetwork
) -> None:
    """Los trenes de Hellín dejan la línea en Chinchilla y los de Villena en La Encina."""
    nodes = {n.spec.id: LineNode(n.spec.id, n.km, n.lon, n.lat) for n in albacete.nodes}
    segments = [LineSegment(s.id, s.km_from, s.km_to) for s in albacete.segments]
    trips = select_trips_for_spec(feed, albacete_spec)
    assert len(trips) == 180
    assert Counter(t.product for t in trips) == {
        "Intercity": 10,
        "Regional": 18,
        "Media Distancia": 115,
        "Regional Exprés": 29,
        "Alvia": 8,
    }
    by_segment = dict.fromkeys((s.id for s in albacete.segments), 0)
    kinds: Counter[str] = Counter()
    for trip in trips:
        calls = calls_for_trip(trip, feed, albacete_spec)
        assert all(c.node_id or c.exit_node_ids for c in calls), trip.train_number
        passes, resolution = resolve_passes(calls, nodes, segments)
        assert resolution == "completa"
        stops = {s.stop_id for s in trip.stop_times}
        if "61005" in stops:
            assert [p.segment_id for p in passes] == [f"{LINE}:albacete-los-llanos:bif-chinchilla"]
        if {"60800", "60902"} <= stops:
            assert f"{LINE}:almansa:la-encina" in {p.segment_id for p in passes}
            assert f"{LINE}:la-encina:bif-la-encina" not in {p.segment_id for p in passes}
        for p in passes:
            if p.segment_id in STATION_CLOSURES and p.kind == "estimado":
                assert p.enter_s is None and p.exit_s is None
            by_segment[p.segment_id] += 1
            kinds[p.kind] += 1
    assert list(by_segment.values()) == [142] * 7 + [145, 135, 135, 57]
    # no todos paran en todas las estaciones: Minaya y La Gineta tienen pocos trenes
    assert kinds == {"publicado": 555, "estimado": 911}
    # ningún tren de alta velocidad: en Albacete paran, pero no en las estaciones intermedias
    selected = {t.trip_id for t in trips}
    through_albacete = {
        t.trip_id for t in feed.trips.values() if "60600" in {s.stop_id for s in t.stop_times}
    }
    assert len(through_albacete - selected) == 188
    for trip_id in through_albacete - selected:
        stops = {s.stop_id for s in feed.trips[trip_id].stop_times}
        assert not stops & set(INTERMEDIATE)


def test_the_other_lines_reach_albacete_through_alcazar(conv_spec: NetworkSpec) -> None:
    """Las estaciones de la línea son, para la convencional, salidas por Alcázar hacia ella; para
    la de Manzanares a Ciudad Real, por Manzanares, la convencional y, desde Alcázar, esta."""
    mzcr_spec = load_network_spec(MZCR_SPEC)
    for stop_id in [*INTERMEDIATE, "60600", "60800", "60900"]:
        mapping = conv_spec.stop_mappings[stop_id]
        assert mapping.exits == ["alcazar-de-san-juan"]
        assert [(leg.line, leg.node) for leg in mapping.via] == [(LINE, "alcazar-de-san-juan")]
        far = mzcr_spec.stop_mappings[stop_id]
        assert far.exits == ["manzanares"]
        assert [(leg.line, leg.node) for leg in far.via] == [
            ("convencional-madrid-alcazar-cordoba", "manzanares"),
            (LINE, "alcazar-de-san-juan"),
        ]
