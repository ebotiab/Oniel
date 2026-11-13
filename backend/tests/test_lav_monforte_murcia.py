"""La línea de alta velocidad de Monforte del Cid a Murcia (046 de Adif): sale de la de Albacete
a Alicante en la bifurcación de Murcia y llega a Murcia del Carmen por Elche y Orihuela."""

from __future__ import annotations

from collections import Counter

import pytest
from conftest import DATA_DIR, LAV_ALICANTE_SPEC, LAV_MURCIA_SPEC, LAV_VALENCIA_SPEC, SOURCES, SPEC

from oniel.geo import haversine_km
from oniel.gtfs.reader import GtfsFeed, GtfsTrip
from oniel.gtfs.trips import (
    LoadedLine,
    calls_for_trip,
    calls_on_line,
    route_for_trip,
    select_trips_for_spec,
)
from oniel.network.build import BuiltNetwork, build_network
from oniel.network.spec import NetworkSpec, load_network_spec, load_sources
from oniel.sim.passes import LineSegment, SegmentPass, resolve_passes
from oniel.validate import loaded_line

LINE = "lav-monforte-murcia"
BRANCH = "lav-albacete-alicante"
TRUNK = "lav-madrid-valencia"
RELATION = "osm-relation-18342974"
WIKIPEDIA = "wikipedia-lav-madrid-levante"
MAP = "adif-declaracion-red-2026-mapas"
#: Estaciones a las que solo se llega por esta línea.
ONLY_THIS_LINE = {"03410", "03412"}
#: Estaciones de la línea convencional de Alicante a Murcia y de las que salen de Murcia: un tren
#: que para en alguna no va por la alta velocidad.
CONVENTIONAL = {"62003", "62100", "62101", "62102", "62103", "61303", "61015", "06002"}


@pytest.fixture(scope="module")
def spec() -> NetworkSpec:
    return load_network_spec(LAV_MURCIA_SPEC)


@pytest.fixture(scope="module")
def line(spec: NetworkSpec) -> BuiltNetwork:
    return build_network(spec, DATA_DIR)


@pytest.fixture(scope="module")
def branch() -> BuiltNetwork:
    return build_network(load_network_spec(LAV_ALICANTE_SPEC), DATA_DIR)


@pytest.fixture(scope="module")
def lines(line: BuiltNetwork, branch: BuiltNetwork) -> list[LoadedLine]:
    others = [build_network(load_network_spec(p), DATA_DIR) for p in (LAV_VALENCIA_SPEC, SPEC)]
    return [loaded_line(net) for net in (line, branch, *others)]


def _stops(trip: GtfsTrip) -> list[str]:
    return [st.stop_id for st in trip.stop_times]


def _pairs(trip: GtfsTrip) -> set[tuple[str, str]]:
    stops = _stops(trip)
    return set(zip(stops, stops[1:], strict=False))


def _passes(
    trip: GtfsTrip, feed: GtfsFeed, net: BuiltNetwork, lines: list[LoadedLine]
) -> list[SegmentPass]:
    own = loaded_line(net)
    others = [other for other in lines if other.line_id != own.line_id]
    route = route_for_trip(net.spec, trip)
    calls = calls_on_line(
        calls_for_trip(trip, feed, net.spec, nodes=own.nodes, others=others, route=route), route
    )
    assert all(c.node_id or c.exit_node_ids for c in calls), trip.train_number
    segments = [LineSegment(s.id, s.km_from, s.km_to) for s in net.segments]
    passes, resolution = resolve_passes(calls, own.nodes, segments)
    assert resolution == "completa", trip.train_number
    return passes


def _short(passes: list[SegmentPass]) -> list[str]:
    return [p.segment_id.split(":", 1)[1] for p in passes]


def test_the_geometry_runs_from_the_junction_to_murcia(
    line: BuiltNetwork, branch: BuiltNetwork
) -> None:
    """El trazado empieza en el punto que la línea de Alicante da a la bifurcación de Murcia y
    termina en la estación de Murcia del Carmen, de una pieza."""
    coords = line.line.polyline.coords
    junction = branch.node("bif-murcia")
    assert haversine_km(coords[0], (junction.lon, junction.lat)) < 0.001
    assert haversine_km(coords[-1], (-1.131508, 37.9748243)) < 0.1
    assert [p.source_id for p in line.line.part_spans] == [RELATION]
    assert not line.line.gaps_km
    # 67,8 km medidos frente a los 68,4 km entre los PK de la bifurcación y de Murcia
    assert line.line.polyline.length_km == pytest.approx(67.75, abs=0.05)
    assert line.spec.line.reference_length_km == pytest.approx(529.798 - 461.356)


def test_it_shares_the_junction_with_the_alicante_line(
    line: BuiltNetwork, branch: BuiltNetwork
) -> None:
    assert [n.spec.id for n in line.nodes] == [
        "bif-murcia",
        "bif-vinalopo",
        "elche-av",
        "san-isidro-albatera-catral-av",
        "callosa-de-segura-cox",
        "orihuela-miguel-hernandez",
        "beniel",
        "bif-el-regueron",
        "murcia-del-carmen",
    ]
    assert {n.spec.id for n in line.nodes if n.spec.shared} == {"bif-murcia"}
    assert not branch.node("bif-murcia").spec.shared
    # cinco estaciones, tres bifurcaciones y un PAET; el PAET y la bifurcación de El Reguerón
    # son nodos secundarios
    assert [n.spec.id for n in line.nodes if n.spec.kind == "estacion"] == [
        "elche-av",
        "callosa-de-segura-cox",
        "orihuela-miguel-hernandez",
        "beniel",
        "murcia-del-carmen",
    ]
    assert {n.spec.id: n.spec.kind for n in line.nodes if n.spec.rank == "secundario"} == {
        "san-isidro-albatera-catral-av": "paet",
        "bif-el-regueron": "bifurcacion",
    }
    # con la línea cargada, de la bifurcación de Murcia ya no sale nada a trazos; de Monforte del
    # Cid sale el enlace por el que llegan los trenes de Alicante, que se une en Vinalopó
    assert all(c.node_id != "bif-murcia" for c in branch.spec.connections)
    link = next(c for c in branch.spec.connections if c.id == "enlace-monforte-vinalopo")
    vinalopo = line.node("bif-vinalopo")
    assert haversine_km(link.sketch[-1], (vinalopo.lon, vinalopo.lat)) < 0.05
    # lo que sigue desde Murcia queda a trazos: Cartagena, Lorca y Águilas, y Albacete por Cieza
    assert {c.id: c.node_id for c in line.spec.connections} == {
        "conv-murcia-cartagena": "bif-el-regueron",
        "conv-murcia-lorca-aguilas": "murcia-del-carmen",
        "conv-murcia-albacete-por-cieza": "murcia-del-carmen",
    }


def test_adif_kilometre_points_continue_those_of_the_alicante_line(line: BuiltNetwork) -> None:
    """Los PK siguen contando desde Madrid-Chamartín: la bifurcación es el 461,356 y Murcia, el
    529,798. Cuatro nodos cuadran a menos de 100 m; la bifurcación Vinalopó, Elche AV y Murcia se
    apartan hasta 1 km, dentro de la tolerancia."""
    origin = line.spec.line.pk_origin_km
    assert origin == 461.356
    assert {n.spec.id: n.spec.reference_pk_km for n in line.nodes} == {
        "bif-murcia": 461.356,
        "bif-vinalopo": 464.922,
        "elche-av": 482.21,
        "san-isidro-albatera-catral-av": 493.568,
        "callosa-de-segura-cox": 498.232,
        "orihuela-miguel-hernandez": 507.582,
        "beniel": 513.352,
        # el PK que la fuente da a El Reguerón cae 5,7 km antes del punto en que las vías se
        # juntan con las de Cartagena: el nodo no lo lleva
        "bif-el-regueron": None,
        "murcia-del-carmen": 529.798,
    }
    delta = {
        n.spec.id: round(n.km + origin - n.spec.reference_pk_km, 1)
        for n in line.nodes
        if n.spec.reference_pk_km is not None
    }
    assert delta == {
        "bif-murcia": 0.0,
        "bif-vinalopo": -1.0,
        "elche-av": 0.4,
        "san-isidro-albatera-catral-av": 0.0,
        "callosa-de-segura-cox": 0.1,
        "orihuela-miguel-hernandez": 0.0,
        "beniel": -0.0,
        "murcia-del-carmen": -0.7,
    }
    assert all(abs(d) <= line.spec.line.pk_tolerance_km for d in delta.values())
    # las estaciones se sitúan con su punto de parada en OSM, sobre el trazado
    assert all(n.offset_m < 20 for n in line.nodes)


def test_single_track_from_orihuela_and_mixed_gauge_into_murcia(line: BuiltNetwork) -> None:
    assert len(line.segments) == 8
    assert [s.tracks for s in line.segments] == [2, 2, 2, 2, 2, 1, 1, 1]
    single = [s for s in line.segments if s.tracks == 1]
    assert single[0].from_node.spec.id == "orihuela-miguel-hernandez"
    assert all(s.attributes["tracks"].source_id == WIKIPEDIA for s in single)
    assert sum(s.length_km for s in single) == pytest.approx(21.5, abs=0.05)
    # el ancho mixto, solo de El Reguerón a Murcia, donde la vía es la de los trenes de Cartagena
    mixed = {
        s.id.removeprefix(f"{LINE}:"): s.attributes["gauge"]
        for s in line.segments
        if "gauge" in s.attributes
    }
    assert list(mixed) == ["bif-el-regueron:murcia-del-carmen"]
    (gauge,) = mixed.values()
    assert (gauge.value, gauge.source_id) == ("mixto", RELATION)
    # 200 km/h según las vías de OSM; 165 en el arranque y 160 en la entrada a Murcia
    assert [s.max_speed_kmh for s in line.segments] == [165, 200, 200, 200, 200, 200, 200, 160]
    assert sum(s.length_km for s in line.segments) == pytest.approx(
        line.line.polyline.length_km, abs=0.1
    )


def test_signalling_as_the_map_draws_it(line: BuiltNetwork) -> None:
    """Mapa 4 de la Declaración sobre la Red: BCA y ERTMS de nivel 2 en toda la línea."""
    for segment in line.segments:
        assert segment.attributes["proteccion_tren"].value == "ertms_n2_asfa"
        assert segment.attributes["bloqueo"].value == "bca"
        assert segment.attributes["mando"].value == "sin_dato_publicado"
        for key in ("proteccion_tren", "bloqueo", "mando"):
            assert segment.attributes[key].source_id == MAP


def test_sources_and_operators_are_registered(spec: NetworkSpec) -> None:
    sources = {s.id: s for s in load_sources(SOURCES)}
    geometry = sources[spec.line.geometry_source.source_id]
    assert geometry.id == RELATION and geometry.license == "ODbL 1.0"
    assert geometry.retrieved_on == "2026-11-13"
    assert geometry.file is not None and (DATA_DIR / geometry.file).exists()
    for extra in ("estaciones_lav_monforte_murcia", "vias_enlace_monforte_vinalopo"):
        assert (DATA_DIR / f"raw/osm/{extra}_2026-11-13.json").exists()
        assert extra in str(geometry.notes)
    assert spec.line.verification_source_id == WIKIPEDIA
    assert "Murcia del Carmen (529,798)" in str(sources[WIKIPEDIA].coverage)
    for section in spec.attribute_sections:
        assert section.source_id in sources
    # Renfe y Ouigo, con sus horarios; Iryo no llega a Murcia y no se declara
    operators = {o.id: o for o in spec.operators if o.role == "operador"}
    assert set(operators) == {"renfe", "ouigo"}
    assert all(o.timetable != "no_publicado" for o in operators.values())
    assert "Murcia" in str(sources["iryo-web"].notes)
    assert all(o.source_id in sources for o in spec.operators)


def test_the_filter_takes_high_speed_trains_and_leaves_the_conventional_ones(
    feed: GtfsFeed, spec: NetworkSpec
) -> None:
    """Entran 111 viajes: Avant de Alicante a Murcia, AVE y AVLO de Madrid. Los Media Distancia,
    Intercity y Proximidad que paran en Orihuela y en Murcia del Carmen van por las líneas
    convencionales y quedan fuera."""
    trips = select_trips_for_spec(feed, spec)
    assert len(trips) == 111
    assert Counter(t.product for t in trips) == {"AVANT": 72, "AVE": 32, "AVLO": 7}
    selected = {t.trip_id for t in trips}
    for trip in trips:
        assert not set(_stops(trip)) & CONVENTIONAL, trip.train_number
        assert set(_stops(trip)) & ONLY_THIS_LINE, trip.train_number
    outside = [t for t in feed.trips.values() if "61200" in _stops(t) and t.trip_id not in selected]
    assert outside and all(not set(_stops(t)) & ONLY_THIS_LINE for t in outside)
    assert {t.product for t in outside} >= {"MD", "Intercity"}
    assert set(spec.corridor_filter.any_of_stop_ids) == ONLY_THIS_LINE


def test_trains_join_at_one_of_two_junctions(
    feed: GtfsFeed, ouigo_feed: GtfsFeed, line: BuiltNetwork, lines: list[LoadedLine]
) -> None:
    """Los trenes de Madrid que no entran en Alicante recorren la línea desde su origen, la
    bifurcación de Murcia; los que salen de Alicante se unen en la bifurcación Vinalopó y no
    pasan por el primer tramo."""
    spec = line.spec
    first = "bif-murcia:bif-vinalopo"
    trips = select_trips_for_spec(feed, spec)
    # los Avant de Alicante a Murcia: los 7 tramos desde Vinalopó
    avant = [t for t in trips if t.product == "AVANT"]
    assert len(avant) == 72
    for trip in avant[:6]:
        short = _short(_passes(trip, feed, line, lines))
        assert len(short) == 7 and first not in short
    # los que vienen de Madrid parando en Alicante, igual: entre Villena y Alicante no tocan
    # esta línea, aunque las dos paradas sean salidas suyas
    through = [t for t in trips if {"60911", "03309"} <= set(_stops(t))]
    assert len(through) == 19
    for trip in through[:6]:
        assert route_for_trip(spec, trip) is None
        short = _short(_passes(trip, feed, line, lines))
        assert len(short) == 7 and first not in short
    # los de Madrid-Chamartín sin parada hasta Elche AV, por su regla: los 8 tramos
    direct = [
        t for t in trips if ("17000", "03410") in _pairs(t) or ("03410", "17000") in _pairs(t)
    ]
    assert len(direct) == 20
    for trip in direct[:6]:
        route = route_for_trip(spec, trip)
        assert route is not None and route.override.id == "madrid-elche-sin-parada"
        passes = _passes(trip, feed, line, lines)
        assert len(passes) == 8 and first in _short(passes)
        assert all(p.kind != "indeterminado" for p in passes)
    assert len(avant) + len(through) + len(direct) == len(trips)
    # en esa regla, a Madrid-Chamartín se llega por la línea de Alicante y la de Valencia, de la
    # que es cabecera
    rules = {r.id: r for r in spec.route_overrides}
    assert list(rules) == [
        "albacete-elche-sin-alicante",
        "madrid-elche-sin-parada",
        "madrid-murcia-sin-parada",
    ]
    chamartin = rules["madrid-elche-sin-parada"].stop_mappings["17000"]
    assert chamartin.exits == ["bif-murcia"] and chamartin.track_km is None
    assert [(leg.line, leg.node) for leg in chamartin.via] == [
        (BRANCH, "bif-murcia"),
        (TRUNK, "bif-albacete"),
    ]
    # los dos de Ouigo que van de Albacete a Elche AV sin entrar en Alicante, por la suya
    ouigo = select_trips_for_spec(ouigo_feed, spec)
    assert len(ouigo) == 7
    skipping = [t for t in ouigo if "60911" not in _stops(t)]
    assert len(skipping) == 2
    for trip in skipping:
        route = route_for_trip(spec, trip)
        assert route is not None and route.override.id == "albacete-elche-sin-alicante"
        assert first in _short(_passes(trip, ouigo_feed, line, lines))
    for trip in ouigo:
        if trip not in skipping:
            assert first not in _short(_passes(trip, ouigo_feed, line, lines))


def test_stops_between_stations_are_published(
    feed: GtfsFeed, line: BuiltNetwork, lines: list[LoadedLine]
) -> None:
    """Entre Callosa de Segura-Cox, Orihuela y Beniel no hay ningún nodo intermedio: el Avant que
    para en las tres tiene paso publicado en esos dos tramos, y estimado en los demás."""
    stopping = next(
        t
        for t in select_trips_for_spec(feed, line.spec)
        if {"03412", "62002", "62001"} <= set(_stops(t))
    )
    kinds = {p.segment_id.split(":", 1)[1]: p.kind for p in _passes(stopping, feed, line, lines)}
    assert kinds["callosa-de-segura-cox:orihuela-miguel-hernandez"] == "publicado"
    assert kinds["orihuela-miguel-hernandez:beniel"] == "publicado"
    assert Counter(kinds.values()) == {"estimado": 5, "publicado": 2}


def test_the_neighbouring_lines_reach_murcia_through_this_one() -> None:
    """En la línea de Alicante y en la de Valencia, las paradas de esta línea son salidas con
    `via` hacia ella; ya no hacen falta kilómetros de vía declarados hasta Elche AV."""
    branch = load_network_spec(LAV_ALICANTE_SPEC)
    for stop_id in ("03410", "03412", "62002", "62001", "61200"):
        mapping = branch.stop_mappings[stop_id]
        assert [(leg.line, leg.node) for leg in mapping.via] == [(LINE, "bif-vinalopo")]
    trunk = load_network_spec(LAV_VALENCIA_SPEC)
    for stop_id in ("03410", "62002", "61200"):
        mapping = trunk.stop_mappings[stop_id]
        assert mapping.exits == ["bif-albacete"] and mapping.track_km is None
        assert [(leg.line, leg.node) for leg in mapping.via] == [
            (BRANCH, "bif-albacete"),
            (LINE, "bif-murcia"),
        ]
    # el AVE de Madrid-Puerta de Atocha a Murcia sin paradas tiene su regla en las tres líneas
    for spec in (trunk, branch, load_network_spec(LAV_MURCIA_SPEC)):
        rule = next(r for r in spec.route_overrides if r.id == "madrid-murcia-sin-parada")
        assert rule.consecutive_stop_ids == ["60000", "61200"]
    assert trunk.line.id == TRUNK
