"""La línea convencional Tarragona – Vilanova i la Geltrú – Barcelona: sale de la bifurcación La
Feredat, en la línea de València, por el enlace de Vila-seca (632 de Adif), sigue por la 210 hasta
Sant Vicenç de Calders y por la 200, por la costa, hasta Barcelona-Sants. Las líneas de Reus, de
Salou-Port Aventura, de Valls y de Vilafranca del Penedès salen a trazos."""

from __future__ import annotations

from collections import Counter

import pytest
from conftest import BCN_SPEC, DATA_DIR, MEDITERRANEO_SPEC, SOURCES, TARRAGONA_BARCELONA_SPEC

from oniel.geo import haversine_km
from oniel.gtfs.reader import GtfsFeed, GtfsTrip
from oniel.gtfs.trips import calls_for_trip, calls_on_line, route_for_trip, select_trips_for_spec
from oniel.network.build import BuiltNetwork, build_network
from oniel.network.spec import NetworkSpec, load_network_spec, load_sources
from oniel.sim.passes import LineSegment, SegmentPass, resolve_passes
from oniel.validate import loaded_line

LINE = "tarragona-barcelona"
RELATION = "osm-relation-5913127"
WIKIPEDIA = "wikipedia-lineas-210-y-200"
MAP = "adif-declaracion-red-2026-mapas"
MEDITERRANEO = "valencia-castello-tarragona"
FEREDAT, VILA_SECA_BIF, SANT_VICENC, SANTS = (
    "bif-la-feredat",
    "bif-vila-seca",
    "sant-vicenc-de-calders",
    "barcelona-sants",
)
TARRAGONA, SANTS_STOP, CASTELLO, CAMBRILS = "71500", "71801", "65300", "65422"
REUS, RODA_DE_MAR, SALOU, LLEIDA, PICAMOIXONS = "71400", "72101", "65411", "78400", "73100"
NODES = [
    FEREDAT,
    VILA_SECA_BIF,
    "vila-seca",
    "tarragona",
    "altafulla-tamarit",
    "torredembarra",
    SANT_VICENC,
    "vilanova-i-la-geltru",
    SANTS,
]
ALL_SEGMENTS = [f"{a}:{b}" for a, b in zip(NODES, NODES[1:], strict=False)]


@pytest.fixture(scope="module")
def spec() -> NetworkSpec:
    return load_network_spec(TARRAGONA_BARCELONA_SPEC)


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


def test_the_geometry_follows_the_r16_from_la_feredat_to_sants(line: BuiltNetwork) -> None:
    """Un solo trozo de la relación del servicio R16, que recorre las vías de las líneas 632, 210
    y 200 sin huecos, de la bifurcación La Feredat a Barcelona-Sants: 95,6 km."""
    coords = line.line.polyline.coords
    assert haversine_km(coords[0], (1.1267256, 41.121723)) < 0.05
    assert haversine_km(coords[-1], (2.1400042, 41.3790068)) < 0.06
    assert [p.source_id for p in line.line.part_spans] == [RELATION]
    assert not line.line.gaps_km and not line.line.joins_km
    assert line.line.polyline.length_km == pytest.approx(95.6, abs=0.1)


def test_nodes_stations_junctions_and_dashed_lines(line: BuiltNetwork) -> None:
    assert [n.spec.id for n in line.nodes] == NODES
    assert {n.spec.id for n in line.nodes if n.spec.kind == "bifurcacion"} == {
        FEREDAT,
        VILA_SECA_BIF,
    }
    assert {n.spec.id for n in line.nodes if n.spec.rank == "secundario"} == {
        FEREDAT,
        VILA_SECA_BIF,
        "vila-seca",
        "altafulla-tamarit",
        "torredembarra",
    }
    assert line.node("tarragona").spec.adif_code == TARRAGONA
    assert {c.id: c.node_id for c in line.spec.connections} == {
        "reus-caspe-zaragoza": VILA_SECA_BIF,
        "tarragona-salou": "tarragona",
        "sant-vicenc-valls": SANT_VICENC,
        "sant-vicenc-vilafranca": SANT_VICENC,
    }
    for c in line.spec.connections:
        node = line.node(c.node_id).spec.position
        assert c.sketch[0] == (node.lon, node.lat) and c.status == "no_cargada"
    assert all(n.offset_m < 60 for n in line.nodes)


def test_it_joins_two_loaded_lines_and_replaces_the_dashed_link(line: BuiltNetwork) -> None:
    """La bifurcación La Feredat la define la línea de València y Barcelona-Sants, la alta
    velocidad de Madrid: esta línea las incorpora sin moverlas. La de València ya no sale a
    trazos hacia la costa, y sus paradas de esta línea siguen por ella."""
    assert {n.spec.id for n in line.nodes if n.spec.shared} == {FEREDAT, SANTS}
    for path, node_id in ((MEDITERRANEO_SPEC, FEREDAT), (BCN_SPEC, SANTS)):
        other = load_network_spec(path)
        theirs = next(n for n in other.nodes if n.id == node_id)
        assert line.node(node_id).spec.position == theirs.position
    coast = load_network_spec(MEDITERRANEO_SPEC)
    assert all(c.id != "convencional-tarragona-costa" for c in coast.connections)
    for stop_id in ("71401", TARRAGONA, "71502", "71503", "71600", "71700"):
        assert coast.stop_mappings[stop_id].exits == [FEREDAT]
        assert [(v.line, v.node) for v in coast.stop_mappings[stop_id].via] == [(LINE, FEREDAT)]
    # Barcelona-Sants sigue siendo, para la mayoría, la alta velocidad por Camp de Tarragona
    assert coast.stop_mappings[SANTS_STOP].exits == ["camp-de-tarragona"]


def test_kilometre_points_of_lines_210_and_200(line: BuiltNetwork) -> None:
    """La 210 numera desde Zaragoza-Miraflores hasta Tarragona y vuelve a empezar allí, en el
    trecho que fue de la línea de València; la 200 numera desde Madrid. Cada nodo queda a menos de
    0,5 km de su punto kilométrico."""
    assert line.spec.line.pk_origin_km == 0
    assert [(r.node, r.pk_km) for r in line.spec.line.pk_restarts] == [
        ("vila-seca", 94.3),
        ("tarragona", 0.0),
        (SANT_VICENC, 618.144),
    ]
    restarts = [(line.node(r.node).km, r.pk_km) for r in line.spec.line.pk_restarts]
    checked = 0
    for node in line.nodes:
        pk = node.spec.reference_pk_km
        if pk is None:
            continue
        at, origin = max((r for r in restarts if r[0] < node.km), key=lambda r: r[0])
        assert node.km - at + origin == pytest.approx(pk, abs=0.5), node.spec.id
        checked += 1
    assert checked == 5


def test_tracks_speeds_and_signalling(line: BuiltNetwork) -> None:
    assert [s.id.removeprefix(f"{LINE}:") for s in line.segments] == ALL_SEGMENTS
    # el enlace de La Feredat es de vía única; el resto, de vía doble
    assert [s.tracks for s in line.segments] == [1] + [2] * 7
    assert line.spec.line.gauge_mm == 1668 and line.spec.line.electrification == "3 kV CC"
    assert [s.max_speed_kmh for s in line.segments] == [50, 125, 135, 160, 160, 140, 160, 160]
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
    stations = sources["osm-instalaciones-tarragona-barcelona"]
    assert stations.file and (DATA_DIR / stations.file).exists()
    assert spec.line.verification_source_id == WIKIPEDIA and WIKIPEDIA in sources
    for section in spec.attribute_sections:
        assert section.source_id in sources
    assert {o.id for o in spec.operators if o.role == "operador"} == {"renfe"}
    assert all(o.source_id in sources for o in spec.operators)
    assert spec.line.zone == "cataluna"


def test_the_filter_takes_the_regional_trains_and_leaves_the_euromed_out(
    feed: GtfsFeed, ouigo_feed: GtfsFeed, spec: NetworkSpec
) -> None:
    """Entran los viajes que paran en dos estaciones de la línea: 91 de Renfe en el fichero de las
    pruebas, regionales e Intercity. Los Euromed y los de alta velocidad solo paran en
    Barcelona-Sants y van por Camp de Tarragona; las lanzaderas de Tarragona a Salou-Port Aventura
    solo paran en Tarragona."""
    assert spec.corridor_filter.min_node_stops == 2
    trips = select_trips_for_spec(feed, spec)
    assert len(trips) == 91
    assert Counter(t.product for t in trips) == {"REG.EXP.": 84, "Intercity": 6, "REGIONAL": 1}
    codes = {n.adif_code for n in spec.nodes}
    selected = {t.trip_id for t in trips}
    for trip in feed.trips.values():
        if trip.trip_id not in selected:
            assert len(codes & set(_stops(trip))) <= 1, trip.train_number
    assert not any(t.product == "EUROMED" for t in trips)
    assert select_trips_for_spec(ouigo_feed, spec) == []


def test_each_family_enters_the_line_where_it_should(feed: GtfsFeed, line: BuiltNetwork) -> None:
    """Los de València y Tortosa entran por La Feredat; los de Reus, Móra la Nova, Caspe y
    Zaragoza, y los de Lleida por La Plana-Picamoixons, por la bifurcación Vila-seca; los de
    Salou-Port Aventura, en Tarragona, y los de Lleida por Valls, en Sant Vicenç de Calders."""
    trips = [t for t in select_trips_for_spec(feed, line.spec) if SANTS_STOP in _stops(t)]
    first: Counter[str] = Counter()
    for trip in trips:
        stops = _stops(trip)
        passes = _short(_passes(trip, feed, line))
        if CAMBRILS in stops or CASTELLO in stops:
            start = FEREDAT
        elif REUS in stops:
            start = VILA_SECA_BIF
        elif SALOU in stops:
            start = "tarragona"
        else:
            assert RODA_DE_MAR in stops, trip.train_number
            start = SANT_VICENC
        expected = ALL_SEGMENTS[NODES.index(start) :]
        assert passes == expected, trip.train_number
        first[start] += 1
    assert first == {FEREDAT: 28, VILA_SECA_BIF: 47, "tarragona": 6, SANT_VICENC: 8}
    # los dos que van de Tarragona a Lleida por Reus solo recorren el trecho de Vila-seca
    others = [t for t in select_trips_for_spec(feed, line.spec) if SANTS_STOP not in _stops(t)]
    assert len(others) == 2
    for trip in others:
        assert _short(_passes(trip, feed, line)) == ALL_SEGMENTS[1:3], trip.train_number


def test_lleida_stops_leave_by_reus_or_by_valls(spec: NetworkSpec) -> None:
    """Las paradas de la línea de Lleida salen, en general, por la bifurcación Vila-seca, hacia
    Reus; una regla de recorrido saca por Sant Vicenç de Calders a los trenes que pasan por Roda de
    Mar, camino de Valls."""
    sm = spec.stop_mappings
    for stop_id in (REUS, PICAMOIXONS, LLEIDA, "04040"):
        assert sm[stop_id].exits == [VILA_SECA_BIF] and not sm[stop_id].via
    for stop_id in (RODA_DE_MAR, "76004"):
        assert sm[stop_id].exits == [SANT_VICENC]
    assert sm[SALOU].exits == ["tarragona"]
    assert sm["79400"].exits == [SANTS] and sm["71802"].exits == [SANTS]
    # Passeig de Gràcia es un nodo de la línea de Portbou: se llega a ella desde Sants
    assert [(v.line, v.node) for v in sm["71802"].via] == [("barcelona-girona-portbou", SANTS)]
    (rule,) = spec.route_overrides
    assert rule.consecutive_stop_ids == [RODA_DE_MAR, "71600"]
    assert rule.stop_mappings[LLEIDA].exits == [SANT_VICENC]
    assert rule.stop_mappings[PICAMOIXONS].exits == [SANT_VICENC]
