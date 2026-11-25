"""Las dos líneas que completan Galicia: la de alta velocidad Ourense – Santiago de Compostela y
la de A Coruña – Santiago – Vigo (el Eje Atlántico), que se juntan en Santiago."""

from __future__ import annotations

from collections import Counter

import pytest
from conftest import (
    DATA_DIR,
    EJE_ATLANTICO_SPEC,
    LAV_OURENSE_SPEC,
    LAV_SANTIAGO_SPEC,
    SOURCES,
)

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
from oniel.sim.passes import LineSegment, resolve_passes
from oniel.validate import loaded_line

SANTIAGO_LINE = "lav-ourense-santiago"
EJE_LINE = "eje-atlantico"
HIGH_SPEED = "osm-relation-4777980"
CONVENTIONAL = "osm-relation-11109438"
EJE_RELATION = "osm-relation-1941090"
MAP = "adif-declaracion-red-2026-mapas"
OURENSE, SANTIAGO, CORUNA = "22100", "31400", "31412"
VILAGARCIA, PONTEVEDRA, URZAIZ, GUIXAR = "23008", "23004", "08223", "22308"
PADRON, PONTECESURES, CATOIRA = "23011", "23010", "23009"
CHAMARTIN = "17000"
#: Estaciones de la línea antigua de Ourense a Santiago, por O Carballiño y Lalín.
OLD_LINE = ["31303", "31304", "31306", "31308"]
#: Paradas repetidas del horario: la misma estación con otro código, un minuto después y sin
#: subida ni bajada de viajeros, en algunos trenes.
DUPLICATES = {"99117": "ourense", "99159": "santiago", "99143": "a-coruna", "99161": "pontevedra"}
SANTIAGO_SEGMENTS = [
    "ourense:bif-coto-da-torre",
    "bif-coto-da-torre:bif-a-grandeira",
    "bif-a-grandeira:santiago",
]
EJE_NODES = [
    "a-coruna",
    "uxes",
    "cerceda-meirama",
    "ordes",
    "santiago",
    "bif-rio-sar",
    "osebe",
    "bif-angueira",
    "padron-barbanza",
    "vilagarcia-de-arousa",
    "portela",
    "pontevedra-universidade",
    "pontevedra",
    "arcade",
    "redondela-av",
    "vigo-urzaiz",
]
EJE_SEGMENTS = [f"{a}:{b}" for a, b in zip(EJE_NODES, EJE_NODES[1:], strict=False)]


@pytest.fixture(scope="module")
def santiago_spec() -> NetworkSpec:
    return load_network_spec(LAV_SANTIAGO_SPEC)


@pytest.fixture(scope="module")
def eje_spec() -> NetworkSpec:
    return load_network_spec(EJE_ATLANTICO_SPEC)


@pytest.fixture(scope="module")
def santiago_line(santiago_spec: NetworkSpec) -> BuiltNetwork:
    return build_network(santiago_spec, DATA_DIR)


@pytest.fixture(scope="module")
def eje(eje_spec: NetworkSpec) -> BuiltNetwork:
    return build_network(eje_spec, DATA_DIR)


def _stops(trip: GtfsTrip) -> list[str]:
    return [st.stop_id for st in trip.stop_times]


def _pairs(trip: GtfsTrip) -> set[tuple[str, str]]:
    stops = _stops(trip)
    return set(zip(stops, stops[1:], strict=False)) | set(zip(stops[1:], stops, strict=False))


def _segments(trip: GtfsTrip, feed: GtfsFeed, net: BuiltNetwork) -> list[str]:
    """Los tramos de la línea por los que cuenta el viaje, en el orden de la línea."""
    own = loaded_line(net)
    route = route_for_trip(net.spec, trip)
    calls = calls_on_line(
        calls_for_trip(trip, feed, net.spec, nodes=own.nodes, others=[], route=route), route
    )
    assert all(c.node_id or c.exit_node_ids for c in calls), trip.train_number
    segments = [LineSegment(s.id, s.km_from, s.km_to) for s in net.segments]
    passes, resolution = resolve_passes(calls, own.nodes, segments)
    assert resolution == "completa", trip.train_number
    order = [s.id.split(":", 1)[1] for s in net.segments]
    return sorted({p.segment_id.split(":", 1)[1] for p in passes}, key=order.index)


# --- Ourense – Santiago de Compostela ---------------------------------------------------------


def test_ourense_santiago_is_traced_from_the_two_relations_already_stored(
    santiago_line: BuiltNetwork,
) -> None:
    """El primer kilómetro, por la vía de la línea convencional; el resto, por la relación de la
    alta velocidad, que acaba 160 m antes del nodo de la estación de Santiago."""
    line = santiago_line.line
    coords = line.polyline.coords
    assert haversine_km(coords[0], (-7.872551, 42.350692)) < 0.1
    assert haversine_km(coords[-1], (-8.5451964, 42.8704417)) < 0.2
    assert [p.source_id for p in line.part_spans] == [CONVENTIONAL, HIGH_SPEED]
    assert line.part_spans[0].km_to == pytest.approx(1.0, abs=0.05)
    assert not line.gaps_km
    assert line.joins_km == [] or max(line.joins_km) < 0.001
    # 87,8 km medidos frente a los 88,280 de la tabla de puntos kilométricos
    assert line.polyline.length_km == pytest.approx(88.28, abs=0.5)
    assert santiago_line.spec.line.reference_length_km == 88.28


def test_ourense_santiago_nodes_and_kilometre_points(santiago_line: BuiltNetwork) -> None:
    assert [n.spec.id for n in santiago_line.nodes] == [
        "ourense",
        "bif-coto-da-torre",
        "bif-a-grandeira",
        "santiago",
    ]
    assert {n.spec.id: n.spec.reference_pk_km for n in santiago_line.nodes} == {
        "ourense": 0.0,
        "bif-coto-da-torre": 1.041,
        "bif-a-grandeira": 85.041,
        "santiago": 88.28,
    }
    for node in santiago_line.nodes:
        assert node.spec.reference_pk_km is not None
        assert node.km == pytest.approx(node.spec.reference_pk_km, abs=0.5)
    assert all(n.offset_m < 200 for n in santiago_line.nodes)
    assert {n.spec.id for n in santiago_line.nodes if n.spec.rank == "secundario"} == {
        "bif-coto-da-torre",
        "bif-a-grandeira",
    }
    # lo que sale de la línea y no está cargado: la línea antigua de Lalín y el enlace de Conxo
    assert {c.id: c.node_id for c in santiago_line.spec.connections} == {
        "conv-ourense-santiago": "bif-a-grandeira",
        "enlace-conxo": "bif-a-grandeira",
    }


def test_ourense_is_the_node_of_the_line_from_olmedo(santiago_line: BuiltNetwork) -> None:
    """Ourense lo define la línea de Olmedo: esta lo incorpora sin moverlo, y la conexión a trazos
    hacia Santiago desaparece de allí."""
    assert {n.spec.id for n in santiago_line.nodes if n.spec.shared} == {"ourense"}
    olmedo = load_network_spec(LAV_OURENSE_SPEC)
    theirs = build_network(olmedo, DATA_DIR).node("ourense")
    ours = santiago_line.node("ourense")
    assert not theirs.spec.shared
    # las mismas coordenadas; cada trazado acaba en su vía de la estación, a 30 m una de otra
    assert ours.spec.position == theirs.spec.position
    assert haversine_km((ours.lon, ours.lat), (theirs.lon, theirs.lat)) < 0.05
    assert ours.km == 0.0
    assert all(c.id != "lav-ourense-santiago" for c in olmedo.connections)
    # Madrid y las estaciones de la línea de Olmedo siguen por ella desde Ourense
    mappings = santiago_line.spec.stop_mappings
    assert [(v.line, v.node) for v in mappings["30200"].via] == [("lav-olmedo-ourense", "ourense")]
    assert [(v.line, v.node) for v in mappings[CHAMARTIN].via] == [
        ("lav-olmedo-ourense", "ourense"),
        ("lav-madrid-valladolid", "bif-medina"),
    ]


def test_ourense_santiago_tracks_voltage_and_speed(santiago_line: BuiltNetwork) -> None:
    """Vía única y 3 kV en el kilómetro de la salida de Ourense, por la línea convencional; vía
    doble a 25 kV y ancho ibérico en el resto."""
    segments = santiago_line.segments
    assert [s.id.removeprefix(f"{SANTIAGO_LINE}:") for s in segments] == SANTIAGO_SEGMENTS
    assert [s.tracks for s in segments] == [1, 2, 2]
    assert segments[0].attributes["electrification"].value == "3 kV CC"
    assert all("electrification" not in s.attributes for s in segments[1:])
    assert santiago_line.spec.line.gauge_mm == 1668
    assert santiago_line.spec.line.electrification == "25 kV 50 Hz"
    assert [s.max_speed_kmh for s in segments] == [110, 300, 80]
    assert all(s.typical_speed_kmh for s in segments)
    assert [round(s.length_km, 1) for s in segments] == [1.1, 83.8, 2.9]


def test_ourense_santiago_signalling_as_the_map_draws_it(santiago_line: BuiltNetwork) -> None:
    for segment in santiago_line.segments:
        assert segment.attributes["proteccion_tren"].value == "ertms_n1_asfa"
        assert segment.attributes["bloqueo"].value == "bca"
        assert segment.attributes["mando"].value == "sin_dato_publicado"
        for key in ("proteccion_tren", "bloqueo", "mando"):
            assert segment.attributes[key].source_id == MAP


def test_ourense_santiago_takes_the_trains_of_the_new_line(
    feed: GtfsFeed, ouigo_feed: GtfsFeed, santiago_spec: NetworkSpec
) -> None:
    """Entran los que paran en Ourense y en Santiago sin parar en la línea antigua, y los de
    Madrid a Vigo que no paran en Santiago, por una regla de recorrido."""
    spec = santiago_spec
    assert spec.corridor_filter.required_stop_ids == [OURENSE, SANTIAGO]
    assert spec.corridor_filter.exclude_stop_ids == OLD_LINE
    trips = select_trips_for_spec(feed, spec)
    assert len(trips) == 288
    assert Counter(t.product for t in trips) == {
        "Avant": 138,
        "AVE": 92,
        "AVLO": 46,
        "Alvia": 6,
        "Media Distancia": 6,
    }
    selected = {t.trip_id for t in trips}
    # los regionales de la línea antigua quedan fuera, aunque paren en Ourense y en Santiago
    old = [t for t in feed.trips.values() if set(OLD_LINE) & set(_stops(t))]
    assert old and not {t.trip_id for t in old} & selected
    assert any({OURENSE, SANTIAGO} <= set(_stops(t)) for t in old)
    # todo tren que lleva seguidas Ourense y Santiago, o Ourense y Vilagarcía, está dentro
    for trip in feed.trips.values():
        if {(OURENSE, SANTIAGO), (OURENSE, VILAGARCIA)} & _pairs(trip):
            assert trip.trip_id in selected, trip.train_number
    assert select_trips_for_spec(ouigo_feed, spec) == []


def test_trains_that_skip_santiago_leave_at_a_grandeira(
    feed: GtfsFeed, santiago_line: BuiltNetwork, eje: BuiltNetwork
) -> None:
    """Diez viajes van de Ourense a Vilagarcía sin parar en Santiago: toman el enlace de Conxo,
    que no está cargado. No cuentan en la llegada a Santiago ni en su salida hacia Vigo."""
    for net in (santiago_line, eje):
        rules = {r.id: r.consecutive_stop_ids for r in net.spec.route_overrides}
        assert rules == {"ourense-vilagarcia-sin-santiago": [OURENSE, VILAGARCIA]}
    trips = select_trips_for_spec(feed, santiago_line.spec)
    skipping = [t for t in trips if (OURENSE, VILAGARCIA) in _pairs(t)]
    assert len(skipping) == 10
    assert all(route_for_trip(santiago_line.spec, t) is not None for t in skipping)
    assert all(route_for_trip(eje.spec, t) is not None for t in skipping)
    for trip in skipping:
        assert _segments(trip, feed, santiago_line) == SANTIAGO_SEGMENTS[:2]
        # en la otra línea entran por la bifurcación Río Sar y llegan a Vigo-Urzáiz
        assert _segments(trip, feed, eje) == EJE_SEGMENTS[5:]
    rule = santiago_line.spec.route_overrides[0]
    for stop_id in (VILAGARCIA, PONTEVEDRA, URZAIZ):
        mapping = rule.stop_mappings[stop_id]
        assert mapping.exits == ["bif-a-grandeira"]
        assert [(v.line, v.node) for v in mapping.via] == [(EJE_LINE, "bif-rio-sar")]
    theirs = eje.spec.route_overrides[0].stop_mappings[OURENSE]
    assert theirs.exits == ["bif-rio-sar"]
    assert [(v.line, v.node) for v in theirs.via] == [(SANTIAGO_LINE, "bif-a-grandeira")]
    # los demás recorren la línea entera
    counts = Counter(s for t in trips for s in _segments(t, feed, santiago_line))
    assert [counts[s] for s in SANTIAGO_SEGMENTS] == [288, 288, 278]


# --- A Coruña – Santiago – Vigo ---------------------------------------------------------------


def test_the_eje_is_traced_from_one_relation_in_one_piece(eje: BuiltNetwork) -> None:
    line = eje.line
    coords = line.polyline.coords
    assert haversine_km(coords[0], (-8.4099507, 43.3525198)) < 0.1
    assert haversine_km(coords[-1], (-8.7118996, 42.2349637)) < 0.01
    assert [p.source_id for p in line.part_spans] == [EJE_RELATION]
    assert not line.gaps_km
    # 155,2 km medidos frente a los 155,6 que da Wikipedia de A Coruña a Vigo
    assert line.polyline.length_km == pytest.approx(155.6, abs=0.5)


def test_eje_nodes_stations_and_what_hangs_from_them(eje: BuiltNetwork) -> None:
    assert [n.spec.id for n in eje.nodes] == EJE_NODES
    assert {n.spec.id for n in eje.nodes if n.spec.rank == "principal"} == {
        "a-coruna",
        "santiago",
        "vilagarcia-de-arousa",
        "pontevedra",
        "vigo-urzaiz",
    }
    assert {n.spec.id for n in eje.nodes if n.spec.kind == "bifurcacion"} == {
        "bif-rio-sar",
        "bif-angueira",
    }
    assert {n.spec.adif_code for n in eje.nodes if n.spec.kind == "estacion"} == {
        CORUNA,
        "31411",
        "31416",
        "31415",
        SANTIAGO,
        "23013",
        "23021",
        VILAGARCIA,
        "23005",
        "23018",
        PONTEVEDRA,
        "23002",
        "08224",
        URZAIZ,
    }
    # el apeadero de Portela queda a 250 m del trazado en OSM; los demás nodos, a menos de 100
    assert {n.spec.id for n in eje.nodes if n.offset_m >= 100} == {"portela"}
    # ninguna fuente da los puntos kilométricos de la línea
    assert all(n.spec.reference_pk_km is None for n in eje.nodes)
    assert {c.id: c.node_id for c in eje.spec.connections} == {
        "conv-a-coruna-betanzos": "a-coruna",
        "conv-padron-catoira": "bif-angueira",
        "conv-arcade-vigo-guixar": "arcade",
    }


def test_santiago_is_the_same_node_in_both_lines(
    santiago_line: BuiltNetwork, eje: BuiltNetwork
) -> None:
    theirs = santiago_line.node("santiago")
    ours = eje.node("santiago")
    assert not theirs.spec.shared and ours.spec.shared
    assert {n.spec.id for n in eje.nodes if n.spec.shared} == {"santiago"}
    # las mismas coordenadas; el trazado de la línea de Ourense acaba 160 m antes de la estación
    assert ours.spec.position == theirs.spec.position
    assert haversine_km((ours.lon, ours.lat), (theirs.lon, theirs.lat)) < 0.2
    assert ours.km == pytest.approx(61.4, abs=0.1)
    # cada línea nombra a la otra en las paradas que quedan del otro lado de Santiago
    for stop_id in (CORUNA, VILAGARCIA, PONTEVEDRA, URZAIZ):
        mapping = santiago_line.spec.stop_mappings[stop_id]
        assert mapping.exits == ["santiago"]
        assert [(v.line, v.node) for v in mapping.via] == [(EJE_LINE, "santiago")]
    ourense = eje.spec.stop_mappings[OURENSE]
    assert ourense.exits == ["santiago"]
    assert [(v.line, v.node) for v in ourense.via] == [(SANTIAGO_LINE, "santiago")]
    assert [(v.line, v.node) for v in eje.spec.stop_mappings[CHAMARTIN].via] == [
        (SANTIAGO_LINE, "santiago"),
        ("lav-olmedo-ourense", "ourense"),
        ("lav-madrid-valladolid", "bif-medina"),
    ]


def test_eje_is_double_track_with_speed_on_every_segment(eje: BuiltNetwork) -> None:
    assert [s.id.removeprefix(f"{EJE_LINE}:") for s in eje.segments] == EJE_SEGMENTS
    assert all(s.tracks == 2 for s in eje.segments)
    assert all(s.max_speed_kmh and s.typical_speed_kmh for s in eje.segments)
    assert max(s.max_speed_kmh or 0 for s in eje.segments) == 200
    assert eje.spec.line.gauge_mm == 1668
    for segment in eje.segments:
        assert segment.attributes["proteccion_tren"].value == "ertms_n1_asfa"
        assert segment.attributes["bloqueo"].value == "bab"
        assert segment.attributes["mando"].value == "ctc"
        for key in ("proteccion_tren", "bloqueo", "mando"):
            assert segment.attributes[key].source_id == MAP


def test_the_eje_takes_every_train_that_stops_twice_on_it(
    feed: GtfsFeed, ouigo_feed: GtfsFeed, eje_spec: NetworkSpec
) -> None:
    assert eje_spec.corridor_filter.min_node_stops == 2
    trips = select_trips_for_spec(feed, eje_spec)
    assert len(trips) == 432
    assert Counter(t.product for t in trips) == {
        "Avant": 133,
        "AVE": 92,
        "Media Distancia": 89,
        "Regional": 66,
        "AVLO": 46,
        "Alvia": 6,
    }
    selected = {t.trip_id for t in trips}
    # quedan fuera los que de la línea solo tocan una estación: los de Ferrol, Lugo y Monforte
    # en A Coruña y los de Ourense que acaban en Santiago
    stations = {s for s, m in eje_spec.stop_mappings.items() if m.node}
    assert not stations & set(DUPLICATES)
    for trip in feed.trips.values():
        assert (len(stations & set(_stops(trip))) >= 2) == (trip.trip_id in selected)
    assert select_trips_for_spec(ouigo_feed, eje_spec) == []


def test_duplicate_stops_are_exits_next_to_their_station(
    feed: GtfsFeed, santiago_spec: NetworkSpec, eje_spec: NetworkSpec
) -> None:
    """El horario repite algunas estaciones con otro código («Santiago-Turístico»), un minuto
    después y sin viajeros. No son un nodo, o el tren saldría dos veces en la ficha de la
    estación: son salidas por su estación, a 0,1 km, para que el paso no quede indeterminado."""
    for spec, stop_ids in (
        (santiago_spec, ("99117", "99159")),
        (eje_spec, ("99159", "99143", "99161")),
    ):
        for stop_id in stop_ids:
            mapping = spec.stop_mappings[stop_id]
            assert mapping.node is None and mapping.exits == [DUPLICATES[stop_id]]
            assert mapping.track_km == 0.1 and not mapping.via
    for stop_id in DUPLICATES:
        for call in (
            st for t in feed.trips.values() for st in t.stop_times if st.stop_id == stop_id
        ):
            assert call.pickup_type == 1 and call.drop_off_type == 1


def test_old_tracks_are_stops_to_one_side(feed: GtfsFeed, eje: BuiltNetwork) -> None:
    """Padrón, Pontecesures y Catoira están en la vía antigua, entre la bifurcación Angueira y
    Vilagarcía: sus trenes no cuentan en el trazado nuevo. Los de Vigo-Guixar dejan la línea en
    Arcade."""
    for stop_id in (PADRON, PONTECESURES, CATOIRA):
        mapping = eje.spec.stop_mappings[stop_id]
        assert mapping.exits == ["bif-angueira", "vilagarcia-de-arousa"] and mapping.aside
    for stop_id in (GUIXAR, "22300", "23000", "23001"):
        mapping = eje.spec.stop_mappings[stop_id]
        assert mapping.exits == ["arcade"] and not mapping.via
    trips = select_trips_for_spec(feed, eje.spec)
    new_track = set(EJE_SEGMENTS[7:9])
    after_arcade = set(EJE_SEGMENTS[13:])
    by_old_track = [t for t in trips if {PADRON, PONTECESURES, CATOIRA} & set(_stops(t))]
    to_guixar = [t for t in trips if GUIXAR in _stops(t)]
    assert len(by_old_track) == 66 and len(to_guixar) == 49
    for trip in by_old_track:
        assert not new_track & set(_segments(trip, feed, eje))
    for trip in to_guixar:
        assert not after_arcade & set(_segments(trip, feed, eje))
    counts = Counter(s for t in trips for s in _segments(t, feed, eje))
    assert [counts[s] for s in EJE_SEGMENTS] == [339] * 4 + [196, 206, 206, 140, 140] + [
        195
    ] * 4 + [146, 146]


def test_sources_and_operators_are_registered(
    santiago_spec: NetworkSpec, eje_spec: NetworkSpec
) -> None:
    sources = {s.id: s for s in load_sources(SOURCES)}
    geometry = sources[EJE_RELATION]
    assert geometry.license == "ODbL 1.0" and geometry.retrieved_on == "2026-11-18"
    assert geometry.file is not None and (DATA_DIR / geometry.file).exists()
    assert santiago_spec.line.verification_source_id == "wikipedia-lav-ourense-santiago"
    assert eje_spec.line.verification_source_id == "wikipedia-eje-atlantico"
    for spec in (santiago_spec, eje_spec):
        assert spec.line.geometry_source.source_id in sources
        assert spec.line.verification_source_id in sources
        for section in spec.attribute_sections:
            assert section.source_id in sources
        # solo Renfe: ni el fichero de Ouigo ni la página de destinos de Iryo nombran Galicia
        operators = {o.id: o for o in spec.operators if o.role == "operador"}
        assert set(operators) == {"renfe"}
        assert operators["renfe"].timetable == "cargado"
        assert all(o.source_id in sources for o in spec.operators)
        assert spec.line.zone == "galicia"
    assert "Santiago" not in str(sources["iryo-web"].coverage)
    for name in (
        "osm/instalaciones_galicia_2026-11-18.json",
        "osm/vias_santiago_sur_2026-11-18.json",
        "osm/vias_padron_vigo_2026-11-18.json",
        "interrupciones/consultas_2026-11-18_galicia.json",
    ):
        assert (DATA_DIR / "raw" / name).exists()
