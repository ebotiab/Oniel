"""La línea convencional Barcelona – Girona – Portbou (la 270 de Adif, precedida por el túnel de
Aragó desde Barcelona-Sants): sale de Sants, como la alta velocidad de Figueres, y llega a la
frontera por Granollers, Maçanet-Massanes, Girona y Figueres. Comparte con la alta velocidad las
estaciones de Barcelona-Sants y de Girona; la línea del Maresme y la continuación a Cerbère salen
a trazos."""

from __future__ import annotations

from collections import Counter

import pytest
from conftest import BARCELONA_PORTBOU_SPEC, DATA_DIR, LAV_FIGUERES_SPEC, SOURCES

from oniel.geo import haversine_km
from oniel.gtfs.reader import GtfsFeed, GtfsTrip
from oniel.gtfs.trips import calls_for_trip, calls_on_line, route_for_trip, select_trips_for_spec
from oniel.network.build import BuiltNetwork, build_network
from oniel.network.spec import NetworkSpec, load_network_spec, load_sources
from oniel.sim.passes import LineSegment, SegmentPass, resolve_passes
from oniel.validate import loaded_line

LINE = "barcelona-girona-portbou"
RELATION = "osm-relation-11087891"
R11 = "osm-relation-6021916"
WIKIPEDIA = "wikipedia-linea-270-barcelona-portbou"
MAP = "adif-declaracion-red-2026-mapas"
SANTS, PASSEIG_DE_GRACIA, CLOT, GIRONA = "71801", "71802", "79009", "79300"
GRANOLLERS, FLACA, FIGUERES, PORTBOU, CERBERE = "79100", "79303", "79309", "79315", "79316"
FIGUERES_VILAFANT = "04307"
NODES = [
    "barcelona-sants",
    "barcelona-passeig-de-gracia",
    "barcelona-el-clot",
    "barcelona-sant-andreu",
    "granollers-centre",
    "sant-celoni",
    "gualba",
    "riells-i-viabrea-breda",
    "hostalric",
    "macanet-massanes",
    "sils",
    "caldes-de-malavella",
    "riudellots",
    "fornells-de-la-selva",
    "girona",
    "celra",
    "bordils-juia",
    "flaca",
    "sant-jordi-desvalls",
    "camallera",
    "sant-miquel-de-fluvia",
    "vilamalla",
    "figueres",
    "vilajuiga",
    "llanca",
    "colera",
    "portbou",
]
ALL_SEGMENTS = [f"{a}:{b}" for a, b in zip(NODES, NODES[1:], strict=False)]
GIRONA_INDEX = NODES.index("girona")
FIGUERES_INDEX = NODES.index("figueres")


@pytest.fixture(scope="module")
def spec() -> NetworkSpec:
    return load_network_spec(BARCELONA_PORTBOU_SPEC)


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


def test_the_geometry_joins_the_r11_route_and_line_270(line: BuiltNetwork) -> None:
    """Dos trozos empalmados en el primer nodo de la relación de la línea 270, en la bifurcación
    Aragó: de Sants hasta ella, por el recorrido del R11, y de ella a Portbou, por la línea 270.
    168,3 km sin saltos. Arranca en el vértice de la relación del R11 más cercano a Sants, en sus
    vías 13 y 14, a 60 m del nodo de la estación."""
    coords = line.line.polyline.coords
    assert haversine_km(coords[0], (2.1400042, 41.3790068)) < 0.07
    assert haversine_km(coords[-1], (3.158012, 42.424798)) < 0.05
    assert [p.source_id for p in line.line.part_spans] == [R11, RELATION]
    assert not line.line.gaps_km
    assert line.line.polyline.length_km == pytest.approx(168.3, abs=0.1)


def test_nodes_stations_and_dashed_lines(line: BuiltNetwork) -> None:
    assert [n.spec.id for n in line.nodes] == NODES
    assert all(n.spec.kind == "estacion" for n in line.nodes)
    assert {n.spec.id for n in line.nodes if n.spec.rank != "secundario"} == {
        "barcelona-sants",
        "barcelona-passeig-de-gracia",
        "barcelona-el-clot",
        "granollers-centre",
        "sant-celoni",
        "macanet-massanes",
        "girona",
        "flaca",
        "figueres",
        "llanca",
        "portbou",
    }
    assert line.node("figueres").spec.adif_code == FIGUERES
    assert line.node("portbou").spec.adif_code == PORTBOU
    assert {c.id: c.node_id for c in line.spec.connections} == {
        "conv-macanet-maresme": "macanet-massanes",
        "conv-portbou-cerbere": "portbou",
    }
    for c in line.spec.connections:
        node = line.node(c.node_id).spec.position
        assert c.sketch[0] == (node.lon, node.lat) and c.status == "no_cargada"
    assert all(n.offset_m < 70 for n in line.nodes)


def test_it_shares_sants_and_girona_with_the_high_speed_line(line: BuiltNetwork) -> None:
    """Barcelona-Sants y Girona las define la alta velocidad, que va antes en la importación: esta
    línea las incorpora sin moverlas, y aquella ya no sale a trazos desde Girona. Figueres no es
    Figueres-Vilafant: son dos estaciones y dos nodos."""
    assert {n.spec.id for n in line.nodes if n.spec.shared} == {"barcelona-sants", "girona"}
    lav = load_network_spec(LAV_FIGUERES_SPEC)
    for node_id in ("barcelona-sants", "girona"):
        theirs = next(n for n in lav.nodes if n.id == node_id)
        assert line.node(node_id).spec.position == theirs.position
    assert all(not c.id.startswith("conv-girona") for c in lav.connections)
    assert FIGUERES_VILAFANT not in {n.spec.adif_code for n in line.nodes}


def test_kilometre_points_are_those_of_line_270_from_el_clot(line: BuiltNetwork) -> None:
    """Sants y Passeig de Gràcia están antes de la bifurcación Aragó, donde empieza la línea 270:
    no tienen PK. La cuenta se retoma en El Clot con el suyo, 110,068, y cada nodo queda a menos
    de 100 m de su PK."""
    assert [(r.node, r.pk_km) for r in line.spec.line.pk_restarts] == [
        ("barcelona-el-clot", 110.068)
    ]
    for node_id in ("barcelona-sants", "barcelona-passeig-de-gracia", "barcelona-el-clot"):
        assert line.node(node_id).spec.reference_pk_km is None
    clot = line.node("barcelona-el-clot").km
    for node in line.nodes:
        pk = node.spec.reference_pk_km
        if pk is not None:
            assert node.km - clot + 110.068 == pytest.approx(pk, abs=0.1), node.spec.id


def test_double_track_gauge_and_signalling(line: BuiltNetwork) -> None:
    assert [s.id.removeprefix(f"{LINE}:") for s in line.segments] == ALL_SEGMENTS
    assert all(s.tracks == 2 for s in line.segments)
    assert line.spec.line.gauge_mm == 1668 and line.spec.line.electrification == "3 kV CC"
    vilamalla = NODES.index("vilamalla")
    mixed = {s.id.removeprefix(f"{LINE}:") for s in line.segments if "gauge" in s.attributes}
    assert mixed == set(ALL_SEGMENTS[GIRONA_INDEX:vilamalla])
    for i, segment in enumerate(line.segments):
        assert segment.attributes["proteccion_tren"].value == "asfa"
        bad = i >= vilamalla
        assert segment.attributes["bloqueo"].value == ("bad" if bad else "bab")
        assert segment.attributes["mando"].value == ("sin_ctc" if bad else "ctc")
        for key in ("proteccion_tren", "bloqueo", "mando"):
            assert segment.attributes[key].source_id == MAP
    assert all(s.max_speed_kmh for s in line.segments)


def test_sources_and_operators_are_registered(spec: NetworkSpec) -> None:
    sources = {s.id: s for s in load_sources(SOURCES)}
    for part in spec.line.geometry_source.parts:
        source = sources[part.source_id]
        assert source.license == "ODbL 1.0"
        assert source.file == part.file and (DATA_DIR / part.file).exists()
    stations = sources["osm-instalaciones-barcelona-portbou"]
    assert stations.file and (DATA_DIR / stations.file).exists()
    assert spec.line.verification_source_id == WIKIPEDIA and WIKIPEDIA in sources
    for section in spec.attribute_sections:
        assert section.source_id in sources
    assert {o.id for o in spec.operators if o.role == "operador"} == {"renfe"}
    assert all(o.source_id in sources for o in spec.operators)
    assert spec.line.zone == "cataluna"


def test_the_filter_takes_the_regional_trains_only(
    feed: GtfsFeed, ouigo_feed: GtfsFeed, spec: NetworkSpec
) -> None:
    """Entran los regionales que paran en dos estaciones de la línea y en alguna que solo tiene
    ella: 117 viajes de Renfe en el fichero de las pruebas. Quedan fuera la alta velocidad, que
    para en Sants y Girona; los regionales del sur, que paran en Sants y Passeig de Gràcia; y los
    de Cerbère a Portbou, que solo paran en una."""
    trips = select_trips_for_spec(feed, spec)
    assert len(trips) == 117
    assert Counter(t.product for t in trips) == {"Media Distancia": 78, "Regional": 39}
    assert all(FIGUERES_VILAFANT not in _stops(t) for t in trips)
    selected = {t.trip_id for t in trips}
    for trip in feed.trips.values():
        stops = _stops(trip)
        if FIGUERES_VILAFANT in stops or (PASSEIG_DE_GRACIA in stops and CLOT not in stops):
            assert trip.trip_id not in selected, trip.train_number
        if stops[:1] == [CERBERE] and stops[1:] == [PORTBOU]:
            assert trip.trip_id not in selected
    assert select_trips_for_spec(ouigo_feed, spec) == []


def test_each_train_counts_on_the_segments_it_runs(feed: GtfsFeed, line: BuiltNetwork) -> None:
    """Los de Barcelona a Portbou recorren la línea entera, paren o no en Granollers; los de
    Barcelona a Figueres acaban en Figueres, y los que salen de Girona o de Flaçà, allí."""
    trips = select_trips_for_spec(feed, line.spec)
    portbou = [t for t in trips if {SANTS, PORTBOU} <= set(_stops(t))]
    figueres = [t for t in trips if SANTS in _stops(t) and _stops(t)[-1] == FIGUERES]
    girona = [t for t in trips if _stops(t)[0] == GIRONA]
    flaca = [t for t in trips if _stops(t)[0] == FLACA]
    assert portbou and figueres and girona and flaca
    assert any(GRANOLLERS not in _stops(t) for t in portbou)
    for trip in portbou:
        assert _short(_passes(trip, feed, line)) == ALL_SEGMENTS, trip.train_number
    for trip in figueres:
        assert _short(_passes(trip, feed, line)) == ALL_SEGMENTS[:FIGUERES_INDEX]
    for trip in girona:
        assert _short(_passes(trip, feed, line)) == ALL_SEGMENTS[:GIRONA_INDEX]
    for trip in flaca:
        assert _short(_passes(trip, feed, line)) == ALL_SEGMENTS[: NODES.index("flaca")]


def test_stops_map_to_their_nodes_and_cerbere_leaves_by_portbou(spec: NetworkSpec) -> None:
    sm = spec.stop_mappings
    for node in spec.nodes:
        assert node.adif_code and sm[node.adif_code].node == node.id
    assert sm[CERBERE].exits == ["portbou"] and not sm[CERBERE].via
