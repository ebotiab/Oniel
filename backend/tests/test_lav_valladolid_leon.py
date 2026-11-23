"""La línea de alta velocidad Valladolid – Palencia – León (080 y 084 de Adif): la continuación
hacia el norte de la de Madrid a Valladolid, con la bifurcación de la que sale la de Burgos."""

from __future__ import annotations

from collections import Counter

import pytest
from conftest import (
    DATA_DIR,
    LAV_ALICANTE_SPEC,
    LAV_LEON_SPEC,
    LAV_MURCIA_SPEC,
    LAV_VALENCIA_SPEC,
    LAV_VALLADOLID_SPEC,
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
from oniel.sim.passes import LineSegment, SegmentPass, resolve_passes
from oniel.validate import loaded_line

LINE = "lav-valladolid-leon"
RELATIONS = ["osm-relation-4777557", "osm-relation-5546933"]
WIKIPEDIA = "wikipedia-lav-valladolid-leon"
MAP = "adif-declaracion-red-2026-mapas"
CHAMARTIN, VALLADOLID, PALENCIA, LEON, BURGOS = "17000", "10600", "14100", "15100", "11014"
#: Estaciones de las líneas convencionales que van al lado de la alta velocidad entre Valladolid,
#: Palencia y León: un tren que para en alguna no va por esta línea.
CONVENTIONAL = {
    "10610",
    "10602",
    "10603",
    "10604",
    "10605",
    "11000",
    "15001",
    "15003",
    "15004",
    "15006",
    "15007",
    "15008",
    "15009",
    "15012",
    "15014",
    "15015",
}
ALL_SEGMENTS = [
    "valladolid-campo-grande:bif-las-pajareras",
    "bif-las-pajareras:bif-venta-de-banos",
    "bif-venta-de-banos:bif-cerrato",
    "bif-cerrato:palencia",
    "palencia:bif-las-barreras",
    "bif-las-barreras:bif-las-arenas",
    "bif-las-arenas:bif-vilecha",
    "bif-vilecha:leon",
]


@pytest.fixture(scope="module")
def spec() -> NetworkSpec:
    return load_network_spec(LAV_LEON_SPEC)


@pytest.fixture(scope="module")
def line(spec: NetworkSpec) -> BuiltNetwork:
    return build_network(spec, DATA_DIR)


def _stops(trip: GtfsTrip) -> list[str]:
    return [st.stop_id for st in trip.stop_times]


def _pairs(trip: GtfsTrip) -> set[tuple[str, str]]:
    stops = _stops(trip)
    return set(zip(stops, stops[1:], strict=False)) | set(zip(stops[1:], stops, strict=False))


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


def test_the_geometry_joins_two_relations_at_the_junction(line: BuiltNetwork) -> None:
    """El trazado sale de Valladolid-Campo Grande por la relación de la línea de Madrid a Burgos
    y, en la bifurcación Venta de Baños, sigue por la de Venta de Baños a León, sin saltos."""
    coords = line.line.polyline.coords
    assert haversine_km(coords[0], (-4.7269507, 41.6421265)) < 0.05
    assert haversine_km(coords[-1], (-5.5819405, 42.5951002)) < 0.1
    assert [p.source_id for p in line.line.part_spans] == RELATIONS
    assert not line.line.gaps_km and not line.line.joins_km
    # el cambio de relación es el nodo de la bifurcación
    assert line.line.part_spans[0].km_to == pytest.approx(line.node("bif-venta-de-banos").km)
    # 166,0 km medidos frente a los 166,141 de la fuente
    assert line.line.polyline.length_km == pytest.approx(166.141, abs=0.2)
    assert line.spec.line.reference_length_km == 166.141


def test_nodes_stations_and_junctions(line: BuiltNetwork) -> None:
    assert [n.spec.id for n in line.nodes] == [
        "valladolid-campo-grande",
        "bif-las-pajareras",
        "bif-venta-de-banos",
        "bif-cerrato",
        "palencia",
        "bif-las-barreras",
        "bif-las-arenas",
        "bif-vilecha",
        "leon",
    ]
    assert {n.spec.id: n.spec.adif_code for n in line.nodes if n.spec.kind == "estacion"} == {
        "valladolid-campo-grande": VALLADOLID,
        "palencia": PALENCIA,
        "leon": LEON,
    }
    # los puntos en los que cambia el número de vías son nodos secundarios; la bifurcación de la
    # que sale la línea de Burgos, principal
    assert {n.spec.id for n in line.nodes if n.spec.rank == "secundario"} == {
        "bif-las-pajareras",
        "bif-cerrato",
        "bif-las-barreras",
        "bif-las-arenas",
        "bif-vilecha",
    }
    assert line.node("bif-venta-de-banos").spec.kind == "bifurcacion"
    assert line.node("bif-venta-de-banos").spec.rank == "principal"
    # las líneas de Burgos y de Santander ya están cargadas: dejan de salir a trazos
    assert {c.id: c.node_id for c in line.spec.connections} == {
        "conv-leon-galicia": "leon",
    }
    assert all(n.offset_m < 100 for n in line.nodes)


def test_it_starts_at_the_station_the_line_from_madrid_ends_at(line: BuiltNetwork) -> None:
    """Valladolid-Campo Grande la define la línea de Madrid, que va antes en la importación: esta
    la incorpora sin moverla, y la de Madrid ya no sale a trazos hacia Palencia y León."""
    assert {n.spec.id for n in line.nodes if n.spec.shared} == {"valladolid-campo-grande"}
    madrid = load_network_spec(LAV_VALLADOLID_SPEC)
    theirs = next(n for n in madrid.nodes if n.id == "valladolid-campo-grande")
    ours = line.node("valladolid-campo-grande").spec
    assert not theirs.shared and ours.position == theirs.position
    assert ours.adif_code == theirs.adif_code == VALLADOLID
    assert all("palencia" not in c.id for c in madrid.connections)
    # hacia el sur, las paradas de la línea de Madrid y las de Levante llevan el camino
    spec = line.spec
    for stop_id in (CHAMARTIN, "08004"):
        mapping = spec.stop_mappings[stop_id]
        assert mapping.exits == ["valladolid-campo-grande"]
        assert [(v.line, v.node) for v in mapping.via] == [
            ("lav-madrid-valladolid", "valladolid-campo-grande")
        ]
    assert [(v.line, v.node) for v in spec.stop_mappings["60911"].via] == [
        ("lav-madrid-valladolid", "valladolid-campo-grande"),
        ("lav-madrid-valencia", "madrid-chamartin"),
        ("lav-albacete-alicante", "bif-albacete"),
    ]
    # y al revés: Palencia y León, desde la línea de Madrid y desde las de Levante
    for stop_id in (PALENCIA, LEON):
        assert [(v.line, v.node) for v in madrid.stop_mappings[stop_id].via] == [
            (LINE, "valladolid-campo-grande")
        ]
        for path in (LAV_VALENCIA_SPEC, LAV_ALICANTE_SPEC, LAV_MURCIA_SPEC):
            via = load_network_spec(path).stop_mappings[stop_id].via
            assert [(v.line, v.node) for v in via][-2:] == [
                ("lav-madrid-valladolid", "madrid-chamartin"),
                (LINE, "valladolid-campo-grande"),
            ]


def test_kilometre_points_continue_those_of_the_line_from_madrid(line: BuiltNetwork) -> None:
    """La numeración sigue la de la línea de Madrid: Valladolid es el PK 179,309 y León, el
    345,450. Cada nodo queda a menos de 200 m del kilómetro medido en el trazado."""
    origin = line.spec.line.pk_origin_km
    assert origin == 179.309
    assert {n.spec.id: n.spec.reference_pk_km for n in line.nodes if n.spec.reference_pk_km} == {
        "bif-las-pajareras": 187.36,
        "bif-venta-de-banos": 217.578,
        "bif-cerrato": 223.53,
        "palencia": 230.627,
        "bif-las-barreras": 259.999,
        "bif-las-arenas": 297.591,
        "bif-vilecha": 338.245,
        "leon": 345.45,
    }
    for node in line.nodes:
        if node.spec.reference_pk_km is not None:
            assert node.km + origin == pytest.approx(node.spec.reference_pk_km, abs=0.2)
    assert line.node("valladolid-campo-grande").km == 0.0


def test_single_and_double_track_alternate(line: BuiltNetwork) -> None:
    """Tres trechos de vía única (a la salida de Valladolid, de Cerrato a Las Barreras y de Las
    Arenas a Vilecha) y tres de vía doble, como dice la tabla de puntos kilométricos."""
    assert [s.id.removeprefix(f"{LINE}:") for s in line.segments] == ALL_SEGMENTS
    assert [s.tracks for s in line.segments] == [1, 2, 2, 1, 1, 2, 1, 2]
    single = sum(s.length_km for s in line.segments if s.tracks == 1)
    # 8,051 + 36,469 + 40,654 km de vía única en la fuente
    assert single == pytest.approx(85.174, abs=0.5)
    for section in line.spec.attribute_sections:
        if section.attribute == "tracks":
            assert section.value == 1 and section.source_id == WIKIPEDIA
    # las vías de OSM traen la velocidad en todos los tramos: ninguno queda sin ella
    assert [s.max_speed_kmh for s in line.segments] == [200, 300, 190, 150, 300, 300, 300, 300]
    assert sum(s.length_km for s in line.segments) == pytest.approx(
        line.line.polyline.length_km, abs=0.1
    )


def test_signalling_as_the_map_draws_it(line: BuiltNetwork) -> None:
    """Mapa 4 de la Declaración sobre la Red: BCA y el símbolo de «ERTMS N2» con el de
    «ASFA - AV» en toda la línea; del mando no dice nada."""
    for segment in line.segments:
        assert segment.attributes["proteccion_tren"].value == "ertms_n2_asfa"
        assert segment.attributes["bloqueo"].value == "bca"
        assert segment.attributes["mando"].value == "sin_dato_publicado"
        for key in ("proteccion_tren", "bloqueo", "mando"):
            assert segment.attributes[key].source_id == MAP


def test_sources_and_operators_are_registered(spec: NetworkSpec) -> None:
    sources = {s.id: s for s in load_sources(SOURCES)}
    for part in spec.line.geometry_source.parts:
        source = sources[part.source_id]
        assert source.license == "ODbL 1.0"
        assert source.file == part.file and (DATA_DIR / part.file).exists()
    assert [p.source_id for p in spec.line.geometry_source.parts] == RELATIONS
    assert sources["osm-relation-5546933"].retrieved_on == "2026-11-14"
    assert (DATA_DIR / "raw" / "osm" / "estaciones_palencia_leon_2026-11-14.json").exists()
    assert spec.line.verification_source_id == WIKIPEDIA and WIKIPEDIA in sources
    for section in spec.attribute_sections:
        assert section.source_id in sources
    # solo Renfe: los trenes de Ouigo acaban en Valladolid
    operators = {o.id: o for o in spec.operators if o.role == "operador"}
    assert set(operators) == {"renfe"}
    assert all(o.source_id in sources for o in spec.operators)
    assert spec.line.zone == "castilla-y-leon"


def test_the_filter_takes_the_high_speed_trains_and_leaves_the_conventional_ones(
    feed: GtfsFeed, ouigo_feed: GtfsFeed, spec: NetworkSpec
) -> None:
    """Entran 387 viajes de Renfe y ninguno de Ouigo. Las tres estaciones son también de las
    líneas convencionales: el filtro deja fuera a los trenes que paran en alguna estación
    intermedia de esas líneas."""
    assert set(spec.corridor_filter.exclude_stop_ids) == CONVENTIONAL | {"04040"}
    assert spec.corridor_filter.min_node_stops == 2
    assert spec.corridor_filter.consecutive_stop_ids == [[VALLADOLID, BURGOS]]
    trips = select_trips_for_spec(feed, spec)
    assert len(trips) == 387
    assert Counter(t.product for t in trips) == {
        "Alvia": 116,
        "AVE": 114,
        "Intercity": 75,
        "Media Distancia": 66,
        "AVLO": 16,
    }
    selected = {t.trip_id for t in trips}
    for trip in trips:
        assert not set(_stops(trip)) & CONVENTIONAL, trip.train_number
    # todo viaje que va sin paradas entre dos de las tres estaciones está dentro: entre ellas,
    # sin paradas, solo se va por la alta velocidad
    direct = {(VALLADOLID, PALENCIA), (PALENCIA, LEON), (VALLADOLID, LEON), (CHAMARTIN, LEON)}
    for trip in feed.trips.values():
        if _pairs(trip) & direct:
            assert trip.trip_id in selected, trip.train_number
    # quedan fuera los que paran en dos de las tres estaciones y, entre ellas, en alguna de la
    # línea convencional
    nodes = {VALLADOLID, PALENCIA, LEON}
    left_out = [
        t
        for t in feed.trips.values()
        if len(nodes & set(_stops(t))) >= 2 and t.trip_id not in selected
    ]
    assert left_out and all(set(_stops(t)) & CONVENTIONAL for t in left_out)
    assert {t.product for t in left_out} == {
        "Media Distancia",
        "Proximidad",
        "Regional Exprés",
        "Regional",
    }
    # de Valladolid a Burgos sin paradas quedan fuera los que paran en Zaragoza: los Intercity
    # de Zaragoza a Valladolid y Salamanca, que van por la línea convencional
    burgos = [t for t in feed.trips.values() if (VALLADOLID, BURGOS) in _pairs(t)]
    out = [t for t in burgos if t.trip_id not in selected]
    assert out and all("04040" in _stops(t) and t.product == "Intercity" for t in out)
    assert select_trips_for_spec(ouigo_feed, spec) == []


def test_rules_for_the_trains_from_burgos_and_the_non_stop_ones(
    feed: GtfsFeed, spec: NetworkSpec
) -> None:
    rules = {r.id: r.consecutive_stop_ids for r in spec.route_overrides}
    assert rules == {
        "burgos-palencia-leon": [BURGOS, PALENCIA, LEON],
        "madrid-leon-sin-parada": [CHAMARTIN, LEON],
    }
    matched = Counter(
        route.override.id
        for trip in select_trips_for_spec(feed, spec)
        if (route := route_for_trip(spec, trip)) is not None
    )
    assert matched == {"burgos-palencia-leon": 6, "madrid-leon-sin-parada": 4}
    # los mismos cuatro viajes entran sin parar en la línea de Madrid, por su regla
    madrid = load_network_spec(LAV_VALLADOLID_SPEC)
    theirs = {
        t.trip_id
        for t in select_trips_for_spec(feed, madrid)
        if (route := route_for_trip(madrid, t)) and route.override.id == "madrid-leon-sin-parada"
    }
    ours = {
        t.trip_id
        for t in select_trips_for_spec(feed, spec)
        if (route := route_for_trip(spec, t)) and route.override.id == "madrid-leon-sin-parada"
    }
    assert ours == theirs and len(ours) == 4


def test_each_train_counts_on_the_segments_it_runs(feed: GtfsFeed, line: BuiltNetwork) -> None:
    """Los de Burgos dejan la línea en la bifurcación Venta de Baños; los de Santander, en
    Palencia; los que llegan de Burgos a Palencia entran junto a la bifurcación Cerrato."""
    trips = select_trips_for_spec(feed, line.spec)

    def having(pair: tuple[str, str]) -> list[GtfsTrip]:
        return [t for t in trips if pair in _pairs(t)]

    for trip in having((VALLADOLID, BURGOS))[:8]:
        assert _short(_passes(trip, feed, line)) == ALL_SEGMENTS[:2]
    for trip in having((PALENCIA, "14114"))[:4] + having((PALENCIA, "14202"))[:4]:
        assert _short(_passes(trip, feed, line)) == ALL_SEGMENTS[:4]
    for trip in having((CHAMARTIN, LEON)) + having((VALLADOLID, LEON))[:4]:
        assert _short(_passes(trip, feed, line)) == ALL_SEGMENTS
    from_burgos = having((BURGOS, PALENCIA))
    assert len(from_burgos) == 6
    for trip in from_burgos:
        assert _short(_passes(trip, feed, line)) == ALL_SEGMENTS[3:]


def test_stops_beyond_the_line_leave_by_the_right_node(spec: NetworkSpec) -> None:
    for stop_id in (BURGOS, "11200", "11208", "11600", "13200", "81100"):
        assert spec.stop_mappings[stop_id].exits == ["bif-venta-de-banos"]
    for stop_id in ("14114", "14202", "14213", "14223"):
        assert spec.stop_mappings[stop_id].exits == ["palencia"]
        # la línea de Santander ya está cargada: siguen por ella desde Palencia
        assert [(v.line, v.node) for v in spec.stop_mappings[stop_id].via] == [
            ("palencia-santander", "palencia")
        ]
    for stop_id in ("15122", "15211", "15410", "20100", "20200", "22100", "31400"):
        assert spec.stop_mappings[stop_id].exits == ["leon"]
    # Burgos es ya una estación cargada: los de Madrid llegan a ella por la bifurcación Venta de
    # Baños y los que vienen de Palencia, por el ramal que se une a la línea de Burgos en Soto de
    # Cerrato
    assert [(v.line, v.node) for v in spec.stop_mappings[BURGOS].via] == [
        ("lav-venta-de-banos-burgos", "bif-venta-de-banos")
    ]
    rule = next(r for r in spec.route_overrides if r.id == "burgos-palencia-leon")
    assert rule.from_stop_id == BURGOS
    assert rule.stop_mappings[BURGOS].exits == ["bif-cerrato"]
    assert [(v.line, v.node) for v in rule.stop_mappings[BURGOS].via] == [
        ("enlace-soto-de-cerrato", "bif-cerrato"),
        ("lav-venta-de-banos-burgos", "bif-soto-de-cerrato"),
    ]
