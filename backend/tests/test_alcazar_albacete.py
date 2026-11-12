"""Quinta línea: la convencional Alcázar de San Juan – Albacete, el trecho central de la línea 300
de Adif (Madrid – Valencia), de vía doble."""

from __future__ import annotations

from collections import Counter

import pytest
from conftest import ALBACETE_SPEC, CONV_SPEC, DATA_DIR, MZCR_SPEC, SOURCES

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


def test_the_geometry_runs_from_alcazar_station_to_albacete_station(
    albacete: BuiltNetwork, conv_spec: NetworkSpec
) -> None:
    """El trazado sale de la estación de Alcázar de San Juan, donde acaba el trecho de la línea 300
    que usa la convencional, y termina junto a la estación de Albacete-Los Llanos."""
    alcazar = next(n for n in conv_spec.nodes if n.id == "alcazar-de-san-juan").position
    assert alcazar.lon is not None and alcazar.lat is not None
    coords = albacete.line.polyline.coords
    assert haversine_km(coords[0], (alcazar.lon, alcazar.lat)) < 0.1
    assert haversine_km(coords[-1], (-1.84845, 38.999384)) < 0.1
    assert [p.source_id for p in albacete.line.part_spans] == [RELATION]
    # 130,8 km medidos frente a los 130,6 km que separan los PK de las dos estaciones
    assert albacete.line.polyline.length_km == pytest.approx(130.6, abs=0.3)
    assert not albacete.line.gaps_km
    # va hacia el este y algo al sur: 125 km en línea recta
    assert haversine_km(coords[0], coords[-1]) == pytest.approx(125, abs=2)


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
    ]
    assert {n.spec.id for n in albacete.nodes if n.spec.shared} == {"alcazar-de-san-juan"}
    theirs = next(n for n in conv_spec.nodes if n.id == "alcazar-de-san-juan")
    ours = albacete.node("alcazar-de-san-juan").spec
    assert not theirs.shared and ours.position == theirs.position
    assert ours.adif_code == theirs.adif_code == "60400"
    assert ours.reference_pk_km == theirs.reference_pk_km == 148.1
    assert all(n.offset_m < 100 for n in albacete.nodes)
    # con la línea cargada, de Alcázar ya no sale una conexión a trazos hacia Levante...
    assert all(c.node_id != "alcazar-de-san-juan" for c in conv_spec.connections)
    # ...y de Albacete salen dos: la línea convencional hacia La Encina y la alta velocidad
    assert {c.id: c.node_id for c in albacete.spec.connections} == {
        "conv-albacete-levante": "albacete-los-llanos",
        "lav-albacete-madrid-levante": "albacete-los-llanos",
    }


def test_adif_kilometre_points_continue_those_of_madrid_alcazar(albacete: BuiltNetwork) -> None:
    """Los PK siguen contando desde Madrid: Alcázar es el 148,1 y Albacete, el 278,7. El medido
    queda a menos de 300 m del de Adif en todas las estaciones."""
    origin = albacete.spec.line.pk_origin_km
    assert origin == 148.1
    for node in albacete.nodes:
        assert node.spec.reference_pk_km is not None
        assert node.km + origin == pytest.approx(node.spec.reference_pk_km, abs=0.35)
    assert albacete.node("albacete-los-llanos").spec.reference_pk_km == 278.7


def test_the_whole_line_is_double_track(albacete: BuiltNetwork) -> None:
    assert len(albacete.segments) == 7
    assert all(s.tracks == 2 for s in albacete.segments)
    assert all(s.id.startswith(f"{LINE}:") for s in albacete.segments)
    assert max(s.max_speed_kmh or 0 for s in albacete.segments) == 200
    # los tramos van de estación a estación: el trazado sobra unos metros en cada extremo
    assert sum(s.length_km for s in albacete.segments) == pytest.approx(
        albacete.line.polyline.length_km, abs=0.1
    )


def test_signalling_changes_at_villarrobledo_and_la_roda(albacete: BuiltNetwork) -> None:
    """Mapa 4 de la Declaración sobre la Red: «BAB» hasta Villarrobledo, «BAD» hasta La Roda y
    «BAB ctc» hasta Albacete. Donde el rótulo no lleva «ctc», el mando queda sin dato publicado."""
    by_segment = {s.id.removeprefix(f"{LINE}:"): s.attributes for s in albacete.segments}
    read = {
        k: (a["proteccion_tren"].value, a["bloqueo"].value, a["mando"].value)
        for k, a in by_segment.items()
    }
    assert read == {
        "alcazar-de-san-juan:campo-de-criptana": ("asfa", "bab", "sin_dato_publicado"),
        "campo-de-criptana:socuellamos": ("asfa", "bab", "sin_dato_publicado"),
        "socuellamos:villarrobledo": ("asfa", "bab", "sin_dato_publicado"),
        "villarrobledo:minaya": ("asfa", "bad", "sin_dato_publicado"),
        "minaya:la-roda-de-albacete": ("asfa", "bad", "sin_dato_publicado"),
        "la-roda-de-albacete:la-gineta": ("asfa", "bab", "ctc"),
        "la-gineta:albacete-los-llanos": ("asfa", "bab", "ctc"),
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
    """Entran 149 viajes: Media Distancia, Regional Exprés y el Alvia de Barcelona a Córdoba.
    Todos recorren la línea entera. Quedan fuera los trenes que solo la tocan en Albacete: los de
    alta velocidad, que llegan por Cuenca, y los de Albacete a Valencia, Murcia y Cartagena."""
    nodes = {n.spec.id: LineNode(n.spec.id, n.km, n.lon, n.lat) for n in albacete.nodes}
    segments = [LineSegment(s.id, s.km_from, s.km_to) for s in albacete.segments]
    trips = select_trips_for_spec(feed, albacete_spec)
    assert len(trips) == 149
    assert Counter(t.product for t in trips) == {"MD": 112, "REG.EXP.": 29, "ALVIA": 8}
    by_segment = dict.fromkeys((s.id for s in albacete.segments), 0)
    kinds: Counter[str] = Counter()
    for trip in trips:
        calls = calls_for_trip(trip, feed, albacete_spec)
        assert all(c.node_id or c.exit_node_ids for c in calls), trip.train_number
        passes, resolution = resolve_passes(calls, nodes, segments)
        assert resolution == "completa"
        for p in passes:
            by_segment[p.segment_id] += 1
            kinds[p.kind] += 1
    assert set(by_segment.values()) == {149}
    # no todos paran en todas las estaciones: Minaya y La Gineta tienen pocos trenes
    assert kinds == {"publicado": 537, "estimado": 506}
    # ningún tren de alta velocidad: en Albacete paran, pero no en las estaciones intermedias
    selected = {t.trip_id for t in trips}
    through_albacete = {
        t.trip_id for t in feed.trips.values() if "60600" in {s.stop_id for s in t.stop_times}
    }
    assert len(through_albacete - selected) > 200
    for trip_id in through_albacete - selected:
        stops = {s.stop_id for s in feed.trips[trip_id].stop_times}
        assert not stops & set(INTERMEDIATE)


def test_the_other_lines_reach_albacete_through_alcazar(conv_spec: NetworkSpec) -> None:
    """Las estaciones de la línea son, para la convencional, salidas por Alcázar hacia ella; para
    la de Manzanares a Ciudad Real, por Manzanares, la convencional y, desde Alcázar, esta."""
    mzcr_spec = load_network_spec(MZCR_SPEC)
    for stop_id in [*INTERMEDIATE, "60600"]:
        mapping = conv_spec.stop_mappings[stop_id]
        assert mapping.exits == ["alcazar-de-san-juan"]
        assert [(leg.line, leg.node) for leg in mapping.via] == [(LINE, "alcazar-de-san-juan")]
        far = mzcr_spec.stop_mappings[stop_id]
        assert far.exits == ["manzanares"]
        assert [(leg.line, leg.node) for leg in far.via] == [
            ("convencional-madrid-alcazar-cordoba", "manzanares"),
            (LINE, "alcazar-de-san-juan"),
        ]
