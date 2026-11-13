"""La línea de alta velocidad de la bifurcación de Albacete a Alicante (042 de Adif): el ramal
que sale de la de Madrid a Valencia y une Albacete con Madrid por un segundo camino."""

from __future__ import annotations

from collections import Counter

import pytest
from conftest import ALBACETE_SPEC, DATA_DIR, LAV_ALICANTE_SPEC, LAV_VALENCIA_SPEC, SOURCES

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

LINE = "lav-albacete-alicante"
TRUNK = "lav-madrid-valencia"
RELATION = "osm-relation-11146315"
MAP = "adif-declaracion-red-2026-mapas"
#: Estaciones de alta velocidad a las que no llega ningún tren convencional.
ONLY_HIGH_SPEED = {"03309", "03410", "03208"}
#: Paradas de la línea de alta velocidad de Monforte del Cid a Murcia, que no está cargada.
MURCIA_LINE = ["03410", "03412", "62002", "62001", "61200"]
#: Estaciones intermedias de la línea convencional de Alcázar de San Juan a Albacete y de la de
#: La Encina a Alicante: un tren que para en alguna no va por la alta velocidad.
CONVENTIONAL = {"60402", "60406", "60500", "60503", "60505", "60507", "60800", "60902", "60905"}


@pytest.fixture(scope="module")
def spec() -> NetworkSpec:
    return load_network_spec(LAV_ALICANTE_SPEC)


@pytest.fixture(scope="module")
def line(spec: NetworkSpec) -> BuiltNetwork:
    return build_network(spec, DATA_DIR)


@pytest.fixture(scope="module")
def trunk() -> BuiltNetwork:
    return build_network(load_network_spec(LAV_VALENCIA_SPEC), DATA_DIR)


@pytest.fixture(scope="module")
def lines(line: BuiltNetwork, trunk: BuiltNetwork) -> list[LoadedLine]:
    return [loaded_line(line), loaded_line(trunk)]


def _stops(trip: GtfsTrip) -> list[str]:
    return [st.stop_id for st in trip.stop_times]


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


def test_the_geometry_runs_from_the_junction_to_alicante(
    line: BuiltNetwork, trunk: BuiltNetwork
) -> None:
    """El trazado empieza donde las vías se separan de la línea de Valencia y termina junto a la
    estación de Alicante-Terminal, de una pieza."""
    coords = line.line.polyline.coords
    junction = trunk.node("bif-albacete")
    # la relación de la línea 042 arranca 208 m más allá del punto que el tronco da a la bifurcación
    assert haversine_km(coords[0], (junction.lon, junction.lat)) < 0.3
    assert haversine_km(coords[-1], (-0.4955241, 38.3447127)) < 0.2
    assert [p.source_id for p in line.line.part_spans] == [RELATION]
    assert not line.line.gaps_km
    # 237,7 km medidos frente a los 237,8 km entre los PK de la bifurcación y de Alicante
    assert line.line.polyline.length_km == pytest.approx(485.925 - 248.1, abs=0.3)


def test_it_shares_the_junction_and_albacete_station(line: BuiltNetwork) -> None:
    assert [n.spec.id for n in line.nodes] == [
        "bif-albacete",
        "pozorrubielos",
        "albacete-los-llanos",
        "chinchilla-av",
        "bonete-av",
        "las-chozas",
        "villena-av",
        "bif-murcia",
        "monforte-del-cid-av",
        "alicante-terminal",
    ]
    assert {n.spec.id for n in line.nodes if n.spec.shared} == {
        "bif-albacete",
        "albacete-los-llanos",
    }
    # tres estaciones, dos bifurcaciones, cuatro PAET y un puesto de banalización; los PAET y el
    # puesto son nodos secundarios
    assert [n.spec.id for n in line.nodes if n.spec.kind == "estacion"] == [
        "albacete-los-llanos",
        "villena-av",
        "alicante-terminal",
    ]
    assert {n.spec.id: n.spec.kind for n in line.nodes if n.spec.rank == "secundario"} == {
        "pozorrubielos": "paet",
        "chinchilla-av": "paet",
        "bonete-av": "paet",
        "las-chozas": "pb",
        "monforte-del-cid-av": "paet",
    }
    # Albacete-Los Llanos la define la línea convencional, con las mismas coordenadas y código
    conventional = load_network_spec(ALBACETE_SPEC)
    theirs = next(n for n in conventional.nodes if n.id == "albacete-los-llanos")
    ours = line.node("albacete-los-llanos").spec
    assert not theirs.shared and ours.position == theirs.position
    assert ours.adif_code == theirs.adif_code == "60600"
    # con la línea cargada ya no sale a trazos ni de Albacete ni de la bifurcación
    assert [c.id for c in conventional.connections] == ["conv-albacete-levante"]
    trunk_spec = load_network_spec(LAV_VALENCIA_SPEC)
    assert all(c.node_id != "bif-albacete" for c in trunk_spec.connections)
    # lo que queda a trazos: la línea de Murcia y la convencional de La Encina a Alicante. El
    # enlace de alta velocidad hacia Valencia por Xàtiva figura en la fuente como futuro: no
    # es un nodo ni una conexión
    assert {c.id: c.node_id for c in line.spec.connections} == {
        "lav-monforte-murcia": "bif-murcia",
        "conv-alicante-la-encina": "alicante-terminal",
    }
    assert "encina" not in " ".join(n.spec.id for n in line.nodes)


def test_adif_kilometre_points_continue_those_of_the_trunk(line: BuiltNetwork) -> None:
    """Los PK siguen contando desde Madrid-Chamartín: la bifurcación es el 248,1 y Alicante, el
    485,925. El medido queda a menos de 200 m del de la fuente en todos los nodos."""
    origin = line.spec.line.pk_origin_km
    assert origin == 248.1
    assert {n.spec.id: n.spec.reference_pk_km for n in line.nodes} == {
        "bif-albacete": 248.1,
        "pozorrubielos": 262.4,
        "albacete-los-llanos": 321.086,
        "chinchilla-av": 337.27,
        "bonete-av": 373.545,
        "las-chozas": 407.648,
        "villena-av": 435.526,
        "bif-murcia": 461.356,
        "monforte-del-cid-av": 464.649,
        "alicante-terminal": 485.925,
    }
    for node in line.nodes:
        assert node.spec.reference_pk_km is not None
        assert node.km + origin == pytest.approx(node.spec.reference_pk_km, abs=0.2)
    # las estaciones quedan junto al trazado; la de Albacete, a 157 m, porque sus coordenadas son
    # las de la línea convencional, que entra en la estación por otras vías
    assert all(n.offset_m < 250 for n in line.nodes)


def test_the_whole_line_is_double_track_at_high_speed(line: BuiltNetwork) -> None:
    assert len(line.segments) == 9
    assert all(s.tracks == 2 for s in line.segments)
    # 300 km/h en casi toda la línea; 240 a la salida de Albacete y 290 de la bifurcación de
    # Murcia a Alicante, como en el cuadro de velocidades de la fuente de verificación
    assert [s.max_speed_kmh for s in line.segments] == [300, 300, 240, 300, 300, 300, 300, 290, 290]
    assert all(s.max_speed_kmh is not None for s in line.segments)
    assert sum(s.length_km for s in line.segments) == pytest.approx(
        line.line.polyline.length_km, abs=0.1
    )


def test_signalling_as_the_map_draws_it(line: BuiltNetwork) -> None:
    """Mapa 4 de la Declaración sobre la Red: BCA en toda la línea; ERTMS de nivel 1 al norte de
    Albacete y de nivel 2 al sur de La Encina. Entre las dos el mapa no dibuja ningún símbolo; el
    nodo cargado junto a La Encina es el puesto de banalización de Las Chozas."""
    read = {
        s.id.removeprefix(f"{LINE}:"): s.attributes["proteccion_tren"].value for s in line.segments
    }
    assert read == {
        "bif-albacete:pozorrubielos": "ertms_n1_asfa",
        "pozorrubielos:albacete-los-llanos": "ertms_n1_asfa",
        "albacete-los-llanos:chinchilla-av": "sin_dato_publicado",
        "chinchilla-av:bonete-av": "sin_dato_publicado",
        "bonete-av:las-chozas": "sin_dato_publicado",
        "las-chozas:villena-av": "ertms_n2_asfa",
        "villena-av:bif-murcia": "ertms_n2_asfa",
        "bif-murcia:monforte-del-cid-av": "ertms_n2_asfa",
        "monforte-del-cid-av:alicante-terminal": "ertms_n2_asfa",
    }
    for segment in line.segments:
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
    assert str(spec.line.verification_source_id) in sources
    for section in spec.attribute_sections:
        assert section.source_id in sources
    operators = {o.id: o for o in spec.operators if o.role == "operador"}
    assert set(operators) == {"renfe", "ouigo", "iryo"}
    assert operators["iryo"].timetable == "no_publicado"
    assert "Albacete a Alicante" in str(sources["iryo-web"].coverage)
    assert all(o.source_id in sources for o in spec.operators)


def test_the_filter_takes_high_speed_trains_and_leaves_the_conventional_ones(
    feed: GtfsFeed, spec: NetworkSpec
) -> None:
    """Entran 307 viajes: AVE, AVLO, Alvia y Avant. Ninguno para en una estación intermedia de
    las líneas convencionales, y ningún tren con parada en Villena AV o en Elche AV queda fuera."""
    trips = select_trips_for_spec(feed, spec)
    assert len(trips) == 307
    assert Counter(t.product for t in trips) == {"AVE": 173, "AVANT": 96, "ALVIA": 24, "AVLO": 14}
    selected = {t.trip_id for t in trips}
    for trip in trips:
        assert not {s.stop_id for s in trip.stop_times} & CONVENTIONAL, trip.train_number
    for trip in feed.trips.values():
        stops = {s.stop_id for s in trip.stop_times}
        if stops & {"03309", "03410"}:
            assert trip.trip_id in selected, trip.train_number
    # los trenes convencionales que paran en Albacete y en Alicante siguen fuera
    both = [
        t
        for t in feed.trips.values()
        if {"60600", "60911"} <= {s.stop_id for s in t.stop_times} and t.trip_id not in selected
    ]
    assert both and all({s.stop_id for s in t.stop_times} & CONVENTIONAL for t in both)
    assert set(spec.corridor_filter.any_of_stop_ids) == ONLY_HIGH_SPEED


def test_trains_without_a_stop_enter_through_the_rules(feed: GtfsFeed, spec: NetworkSpec) -> None:
    rules = {r.id: r.consecutive_stop_ids for r in spec.route_overrides}
    assert rules == {
        "albacete-elche-sin-alicante": ["60600", "03410"],
        "madrid-albacete-sin-cuenca": ["17000", "60600"],
        "madrid-alicante-sin-parada": ["17000", "60911"],
        "madrid-elche-sin-parada": ["17000", "03410"],
    }
    matched = Counter(
        route.override.id
        for trip in select_trips_for_spec(feed, spec)
        if (route := route_for_trip(spec, trip)) is not None
    )
    assert matched == {
        "madrid-albacete-sin-cuenca": 31,
        "madrid-alicante-sin-parada": 27,
        "madrid-elche-sin-parada": 20,
    }
    # Madrid-Chamartín y Cuenca son salidas por la bifurcación de Albacete, y a las dos se llega
    # por la línea de Valencia, que empieza en Chamartín
    for stop_id in ("17000", "03208"):
        mapping = spec.stop_mappings[stop_id]
        assert mapping.exits == ["bif-albacete"] and mapping.track_km is None
        assert [(leg.line, leg.node) for leg in mapping.via] == [(TRUNK, "bif-albacete")]


def test_trains_to_murcia_leave_by_one_of_two_junctions(
    feed: GtfsFeed,
    ouigo_feed: GtfsFeed,
    line: BuiltNetwork,
    lines: list[LoadedLine],
) -> None:
    """Hacia Elche, Orihuela y Murcia se sale por dos sitios: los trenes que vienen de Alicante,
    por el enlace de Monforte del Cid; los que no entran en Alicante, por la bifurcación de
    Murcia, 3,3 km antes."""
    spec = line.spec
    for stop_id in MURCIA_LINE:
        assert spec.stop_mappings[stop_id].exits == ["monforte-del-cid-av"]
    for rule in spec.route_overrides:
        if rule.id in ("albacete-elche-sin-alicante", "madrid-elche-sin-parada"):
            assert {s: m.exits for s, m in rule.stop_mappings.items()} == dict.fromkeys(
                MURCIA_LINE, ["bif-murcia"]
            )
        else:
            assert not rule.stop_mappings
    trips = select_trips_for_spec(feed, spec)
    # los Avant de Alicante a Murcia solo recorren el último tramo
    avant = [t for t in trips if t.product == "AVANT" and "61200" in _stops(t)]
    assert len(avant) == 72
    for trip in avant[:5]:
        assert _short(_passes(trip, feed, line, lines)) == ["monforte-del-cid-av:alicante-terminal"]
    # los de Madrid a Murcia sin parada hasta Elche dejan la línea en la bifurcación de Murcia
    direct = [
        t for t in trips if ("17000", "03410") in _pairs(t) or ("03410", "17000") in _pairs(t)
    ]
    assert len(direct) == 20
    for trip in direct[:5]:
        short = _short(_passes(trip, feed, line, lines))
        assert len(short) == 7
        assert {short[0], short[-1]} == {"bif-albacete:pozorrubielos", "villena-av:bif-murcia"}
    # los que entran en Alicante y siguen a Murcia la recorren entera; el trecho de Monforte del
    # Cid a Alicante lo hacen dos veces, y se cuenta un paso por tramo
    through = [t for t in trips if {"60600", "60911", "61200"} <= set(_stops(t))]
    assert len(through) == 19
    for trip in through[:5]:
        assert len(_short(_passes(trip, feed, line, lines))) == 9
    # los dos de Ouigo que van de Albacete a Elche sin entrar en Alicante, por su regla
    ouigo = select_trips_for_spec(ouigo_feed, spec)
    assert len(ouigo) == 10
    skipping = [t for t in ouigo if "03410" in _stops(t) and "60911" not in _stops(t)]
    assert len(skipping) == 2
    for trip in skipping:
        route = route_for_trip(spec, trip)
        assert route is not None and route.override.id == "albacete-elche-sin-alicante"
        assert _short(_passes(trip, ouigo_feed, line, lines))[-1] == "villena-av:bif-murcia"


def _pairs(trip: GtfsTrip) -> set[tuple[str, str]]:
    stops = _stops(trip)
    return set(zip(stops, stops[1:], strict=False))


def test_the_trunk_reaches_the_branch_stations_through_the_junction() -> None:
    trunk_spec = load_network_spec(LAV_VALENCIA_SPEC)
    for stop_id in ("60600", "03309", "60911"):
        mapping = trunk_spec.stop_mappings[stop_id]
        assert mapping.exits == ["bif-albacete"]
        assert [(leg.line, leg.node) for leg in mapping.via] == [(LINE, "bif-albacete")]
