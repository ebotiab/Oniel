"""La línea de alta velocidad Barcelona – Girona – Figueres: la continuación de la de Madrid a
Barcelona (050 de Adif) hasta el límite con la sección internacional de Figueres a Perpiñán."""

from __future__ import annotations

from collections import Counter

import pytest
from conftest import BCN_SPEC, DATA_DIR, LAV_FIGUERES_SPEC, MEDITERRANEO_SPEC, SOURCES

from oniel.geo import haversine_km
from oniel.gtfs.reader import GtfsFeed, GtfsTrip
from oniel.gtfs.trips import (
    calls_for_trip,
    calls_on_line,
    route_for_trip,
    select_trips_for_spec,
)
from oniel.network.build import BuiltNetwork, build_network
from oniel.network.spec import NetworkSpec, load_network_spec, load_sources
from oniel.sim.passes import LineSegment, SegmentPass, resolve_passes
from oniel.validate import loaded_line

LINE = "lav-barcelona-figueres"
RELATION = "osm-relation-11082425"
WIKIPEDIA = "wikipedia-lav-madrid-barcelona"
MAP = "adif-declaracion-red-2026-mapas"
SANTS, GIRONA, FIGUERES, PERPIGNAN = "71801", "79300", "04307", "87374"
LIMIT = "limite-seccion-internacional"
ALL_SEGMENTS = [
    "barcelona-sants:bif-mollet",
    "bif-mollet:riells",
    "riells:vilobi-d-onyar",
    "vilobi-d-onyar:bif-girona-mercaderies",
    "bif-girona-mercaderies:girona",
    "girona:figueres-vilafant",
    f"figueres-vilafant:{LIMIT}",
]


@pytest.fixture(scope="module")
def spec() -> NetworkSpec:
    return load_network_spec(LAV_FIGUERES_SPEC)


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


def test_the_geometry_runs_from_sants_to_the_owner_change(line: BuiltNetwork) -> None:
    """Un solo trozo de la relación de Madrid a la frontera: de Barcelona-Sants al punto en que
    la vía pasa de Adif a la sociedad de la sección internacional, sin saltos."""
    coords = line.line.polyline.coords
    assert haversine_km(coords[0], (2.1400042, 41.3790068)) < 0.05
    assert coords[-1] == (2.9293482, 42.2963818)
    assert [p.source_id for p in line.line.part_spans] == [RELATION]
    assert not line.line.gaps_km and not line.line.joins_km
    # 132,6 km medidos frente a los 131,7 que hay entre los PK 621,0 y 752,7
    assert line.line.polyline.length_km == pytest.approx(132.6, abs=0.1)
    assert line.spec.line.reference_length_km == 131.7


def test_nodes_stations_junctions_and_passing_loops(line: BuiltNetwork) -> None:
    assert {n.spec.id: n.spec.kind for n in line.nodes} == {
        "barcelona-sants": "estacion",
        "bif-mollet": "bifurcacion",
        "riells": "paet",
        "vilobi-d-onyar": "paet",
        "bif-girona-mercaderies": "bifurcacion",
        "girona": "estacion",
        "figueres-vilafant": "estacion",
        LIMIT: "referencia",
    }
    assert [n.spec.id for n in line.nodes] == [
        "barcelona-sants",
        *(s.split(":")[1] for s in ALL_SEGMENTS),
    ]
    assert {n.spec.id for n in line.nodes if n.spec.rank == "secundario"} == {
        "bif-mollet",
        "riells",
        "vilobi-d-onyar",
        "bif-girona-mercaderies",
    }
    assert line.node("girona").spec.adif_code == GIRONA
    assert line.node("figueres-vilafant").spec.adif_code == FIGUERES
    assert all(n.offset_m < 50 for n in line.nodes)
    assert {c.id: c.node_id for c in line.spec.connections} == {
        "seccion-internacional-figueres-perpinan": LIMIT,
    }


def test_it_starts_at_the_station_the_madrid_line_defines(line: BuiltNetwork) -> None:
    """Barcelona-Sants la define la línea de Madrid, que va antes en la importación: esta la
    incorpora sin moverla, y aquella ya no sale a trazos hacia la frontera."""
    assert {n.spec.id for n in line.nodes if n.spec.shared} == {"barcelona-sants"}
    madrid = load_network_spec(BCN_SPEC)
    theirs = next(n for n in madrid.nodes if n.id == "barcelona-sants")
    assert not theirs.shared and line.node("barcelona-sants").spec.position == theirs.position
    assert all("frontera" not in c.id for c in madrid.connections)


def test_kilometre_points_continue_those_of_the_madrid_line(line: BuiltNetwork) -> None:
    """La numeración sigue la de la línea 050 desde Madrid: Barcelona-Sants es el PK 621,0.
    Hasta Girona cada nodo queda a menos de 0,5 km de su PK; Figueres-Vilafant y el límite, a
    1,1 km y a 0,9 km, porque de Girona a Figueres el trazado mide 0,6 km más que los PK."""
    origin = line.spec.line.pk_origin_km
    assert origin == 621.0
    assert {n.spec.id: n.spec.reference_pk_km for n in line.nodes} == {
        "barcelona-sants": 621.0,
        "bif-mollet": 640.5,
        "riells": 678.1,
        "vilobi-d-onyar": 703.5,
        "bif-girona-mercaderies": 710.7,
        "girona": 714.7,
        "figueres-vilafant": 748.865,
        LIMIT: 752.7,
    }
    deltas = {n.spec.id: n.km + origin - (n.spec.reference_pk_km or 0) for n in line.nodes}
    assert all(0 <= d < 0.5 for k, d in deltas.items() if k not in ("figueres-vilafant", LIMIT))
    assert deltas["figueres-vilafant"] == pytest.approx(1.06, abs=0.05)
    assert deltas[LIMIT] == pytest.approx(0.92, abs=0.05)


def test_double_track_and_the_speeds_of_the_osm_ways(line: BuiltNetwork) -> None:
    assert [s.id.removeprefix(f"{LINE}:") for s in line.segments] == ALL_SEGMENTS
    assert all(s.tracks == 2 for s in line.segments)
    assert all(
        s.attributes["tracks"].source_id == "adif-declaracion-red-2026-mapas" for s in line.segments
    )
    # ningún tramo se queda sin velocidad: la más baja, en la entrada a Girona
    assert [s.max_speed_kmh for s in line.segments] == [220, 255, 245, 245, 125, 290, 290]
    assert line.spec.line.max_speed_kmh == 290


def test_signalling_as_the_map_draws_it(line: BuiltNetwork) -> None:
    for segment in line.segments:
        assert segment.attributes["proteccion_tren"].value == "ertms_n1_asfa"
        assert segment.attributes["bloqueo"].value == "bca"
        assert segment.attributes["mando"].value == "sin_dato_publicado"
        for key in ("proteccion_tren", "bloqueo", "mando"):
            assert segment.attributes[key].source_id == MAP


def test_sources_and_operators_are_registered(spec: NetworkSpec) -> None:
    sources = {s.id: s for s in load_sources(SOURCES)}
    (part,) = spec.line.geometry_source.parts
    assert part.source_id == RELATION and sources[RELATION].license == "ODbL 1.0"
    assert sources[RELATION].file == part.file and (DATA_DIR / part.file).exists()
    nodes = sources["osm-instalaciones-lav-barcelona-figueres"]
    assert nodes.file == "raw/osm/adif_facility_nodes_lav_barcelona_figueres_2026-11-18.json"
    assert (DATA_DIR / nodes.file).exists()
    assert spec.line.verification_source_id == WIKIPEDIA and WIKIPEDIA in sources
    for section in spec.attribute_sections:
        assert section.source_id in sources
    # solo Renfe: Ouigo e Iryo acaban en Barcelona, y por eso es una línea aparte de la de
    # Madrid. Los TGV de SNCF la recorren, pero sus horarios no están cargados: no se declara
    # como operador, y la fuente y la descripción lo dicen
    assert {o.id for o in spec.operators if o.role == "operador"} == {"renfe"}
    assert all(o.source_id in sources for o in spec.operators)
    madrid = load_network_spec(BCN_SPEC)
    assert {o.id for o in madrid.operators if o.role == "operador"} == {"renfe", "ouigo", "iryo"}
    sncf = sources["sncf-horarios-abiertos"]
    assert sncf.file is not None and (DATA_DIR / sncf.file).exists()
    assert "SNCF" in (spec.line.description or "")
    assert spec.line.zone == "cataluna"
    assert spec.line.opened_on == "2013-01-09"
    assert spec.line.bypass_of is None and spec.line.link_of is None


def test_the_filter_takes_the_trains_that_stop_at_figueres_vilafant(
    feed: GtfsFeed, ouigo_feed: GtfsFeed, spec: NetworkSpec
) -> None:
    """Entran los viajes que paran en Figueres-Vilafant, a la que solo llega esta línea. Los
    regionales de la línea convencional paran en Girona y en Sants, pero no en ella."""
    f = spec.corridor_filter
    assert f.any_of_stop_ids == [FIGUERES] and f.min_node_stops == 1
    assert not f.required_stop_ids and not f.exclude_stop_ids
    trips = select_trips_for_spec(feed, spec)
    assert len(trips) == 208
    assert Counter(t.product for t in trips) == {
        "Avant": 104,
        "AVE internacional": 54,
        "AVE": 41,
        "Euromed": 9,
    }
    selected = {t.trip_id for t in trips}
    at_girona = [t for t in feed.trips.values() if GIRONA in _stops(t)]
    left_out = [t for t in at_girona if t.trip_id not in selected]
    # los que se quedan fuera son todos regionales, que paran en Barcelona-Passeig de Gràcia o
    # en alguna estación de la línea convencional
    assert left_out and not {t.product for t in left_out} & {
        "AVE",
        "AVE internacional",
        "Avant",
        "Euromed",
    }
    assert all(FIGUERES not in _stops(t) for t in left_out)
    assert not spec.route_overrides
    assert select_trips_for_spec(ouigo_feed, spec) == []


def test_each_train_counts_on_the_segments_it_runs(feed: GtfsFeed, line: BuiltNetwork) -> None:
    """Todos salen de Barcelona-Sants o llegan a ella y recorren la línea hasta
    Figueres-Vilafant: 154 acaban allí y los 54 internacionales siguen por el último tramo. El
    lector une los trozos en que el horario parte esos trenes en Figueres-Vilafant."""
    trips = select_trips_for_spec(feed, line.spec)
    seen: Counter[int] = Counter()
    for trip in trips:
        stops = _stops(trip)
        assert SANTS in stops and GIRONA in stops, trip.train_number
        to_france = any(s.startswith("87") for s in stops)
        expected = ALL_SEGMENTS if to_france else ALL_SEGMENTS[:6]
        assert _short(_passes(trip, feed, line)) == expected, trip.train_number
        seen[len(expected)] += 1
    assert seen == {6: 154, 7: 54}


def test_stops_on_each_side_leave_by_the_right_node(spec: NetworkSpec) -> None:
    sm = spec.stop_mappings
    assert sm[SANTS].node == "barcelona-sants"
    assert sm[GIRONA].node == "girona" and sm[FIGUERES].node == "figueres-vilafant"
    # hacia Francia, por el límite con la sección internacional, sin camino cargado
    for stop_id in (PERPIGNAN, "87088", "87173", "87302", "87814", "87912", "87089"):
        assert sm[stop_id].exits == [LIMIT] and not sm[stop_id].via
    # hacia Madrid, por Barcelona-Sants y la línea de Madrid
    for stop_id in ("60000", "04007", "70600", "04040", "78400", "04104"):
        assert sm[stop_id].exits == ["barcelona-sants"]
        assert [(v.line, v.node) for v in sm[stop_id].via] == [
            ("lav-madrid-barcelona", "barcelona-sants")
        ]
    # hacia Castelló y València, además por la línea de la costa desde Camp de Tarragona
    for stop_id in ("65300", "65000"):
        assert [(v.line, v.node) for v in sm[stop_id].via] == [
            ("lav-madrid-barcelona", "barcelona-sants"),
            ("valencia-castello-tarragona", "camp-de-tarragona"),
        ]
    # y al revés: Girona y Figueres-Vilafant, desde la línea de Madrid y desde la de la costa
    madrid = load_network_spec(BCN_SPEC)
    coast = load_network_spec(MEDITERRANEO_SPEC)
    for stop_id in (GIRONA, FIGUERES):
        assert [(v.line, v.node) for v in madrid.stop_mappings[stop_id].via] == [
            (LINE, "barcelona-sants")
        ]
        assert [(v.line, v.node) for v in coast.stop_mappings[stop_id].via] == [
            ("lav-madrid-barcelona", "camp-de-tarragona"),
            (LINE, "barcelona-sants"),
        ]
    assert madrid.stop_mappings[PERPIGNAN].exits == ["barcelona-sants"]
    assert not madrid.stop_mappings[PERPIGNAN].via
