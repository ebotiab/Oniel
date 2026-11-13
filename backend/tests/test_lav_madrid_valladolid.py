"""La línea de alta velocidad Madrid – Segovia – Valladolid (080 de Adif): la primera al norte de
Madrid, con la bifurcación de la que sale la línea de Galicia."""

from __future__ import annotations

from collections import Counter

import pytest
from conftest import DATA_DIR, LAV_VALLADOLID_SPEC, SOURCES

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

LINE = "lav-madrid-valladolid"
RELATION = "osm-relation-4777557"
MAP = "adif-declaracion-red-2026-mapas"
CHAMARTIN, SEGOVIA, VALLADOLID = "17000", "08004", "10600"
#: Paradas de la línea de alta velocidad de Olmedo a Galicia de las que una fuente da los
#: kilómetros de vía desde la bifurcación Medina.
GALICIA_LINE_KM = {
    "08240": 21.574,
    "30200": 98.579,
    "08247": 199.704,
    "08251": 248.729,
    "22100": 328.649,
}
#: Estaciones de la línea convencional de Madrid a Irún a un lado y a otro de Valladolid: un tren
#: que para en alguna no llega a Valladolid por la alta velocidad.
CONVENTIONAL = {"10500", "10504", "11000", "10605", "10200"}
ALL_SEGMENTS = [
    "madrid-chamartin:soto-del-real",
    "soto-del-real:segovia-guiomar",
    "segovia-guiomar:garcillan",
    "garcillan:bif-medina",
    "bif-medina:valladolid-campo-grande",
]


@pytest.fixture(scope="module")
def spec() -> NetworkSpec:
    return load_network_spec(LAV_VALLADOLID_SPEC)


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


def test_the_geometry_runs_from_chamartin_to_valladolid(line: BuiltNetwork) -> None:
    """El trazado va de los andenes de Madrid-Chamartín a la estación de Valladolid-Campo Grande,
    de una pieza, y no sigue hacia Burgos aunque la relación de OSM sí lo haga."""
    coords = line.line.polyline.coords
    assert haversine_km(coords[0], (-3.6822622, 40.4720571)) < 0.25
    assert haversine_km(coords[-1], (-4.7269507, 41.6421265)) < 0.05
    assert [p.source_id for p in line.line.part_spans] == [RELATION]
    assert not line.line.gaps_km
    # 178,6 km medidos frente a los 178,559 km que hay del origen del trazado al PK 179,309: si
    # el final fuera la parada de la relación, el camino pasaría de largo la estación y volvería
    # por la otra vía, 3,3 km de más
    assert line.line.polyline.length_km == pytest.approx(179.309 - 0.75, abs=0.05)
    assert max(c[1] for c in coords) < 41.65


def test_nodes_are_ready_for_the_lines_that_follow(line: BuiltNetwork) -> None:
    assert [n.spec.id for n in line.nodes] == [
        "madrid-chamartin",
        "soto-del-real",
        "segovia-guiomar",
        "garcillan",
        "bif-medina",
        "valladolid-campo-grande",
    ]
    assert {n.spec.id: n.spec.kind for n in line.nodes if n.spec.rank == "secundario"} == {
        "soto-del-real": "paet",
        "garcillan": "paet",
    }
    assert {n.spec.id: n.spec.adif_code for n in line.nodes if n.spec.kind == "estacion"} == {
        "madrid-chamartin": CHAMARTIN,
        "segovia-guiomar": SEGOVIA,
        "valladolid-campo-grande": VALLADOLID,
    }
    # la bifurcación de la que sale la línea de Galicia y la estación de Valladolid son nodos
    # principales: de ellos colgarán las líneas siguientes, que hoy salen a trazos
    assert line.node("bif-medina").spec.kind == "bifurcacion"
    assert line.node("bif-medina").spec.rank == "principal"
    assert {c.id: c.node_id for c in line.spec.connections} == {
        "lav-olmedo-zamora-galicia": "bif-medina",
        "lav-valladolid-palencia-leon": "valladolid-campo-grande",
        "conv-valladolid-medina-del-campo": "valladolid-campo-grande",
    }
    assert all(n.offset_m < 250 for n in line.nodes)


def test_adif_kilometre_points_are_750_m_ahead_of_the_trace(line: BuiltNetwork) -> None:
    """Los PK de la fuente quedan todos 0,75 km por delante del kilómetro medido desde los andenes
    de Chamartín, con menos de 50 m de diferencia entre sí: la línea lleva ese origen."""
    origin = line.spec.line.pk_origin_km
    assert origin == 0.75
    assert {n.spec.id: n.spec.reference_pk_km for n in line.nodes if n.spec.reference_pk_km} == {
        "soto-del-real": 35.464,
        "segovia-guiomar": 68.476,
        "garcillan": 86.48,
        "bif-medina": 133.884,
        "valladolid-campo-grande": 179.309,
    }
    for node in line.nodes:
        if node.spec.reference_pk_km is not None:
            assert node.km + origin == pytest.approx(node.spec.reference_pk_km, abs=0.05)
    # Madrid-Chamartín es el kilómetro 0 del trazado y no guarda PK de esta línea
    assert line.node("madrid-chamartin").km == 0.0
    assert line.node("madrid-chamartin").spec.reference_pk_km is None


def test_the_whole_line_is_double_track_at_high_speed(line: BuiltNetwork) -> None:
    assert [s.id.removeprefix(f"{LINE}:") for s in line.segments] == ALL_SEGMENTS
    assert all(s.tracks == 2 for s in line.segments)
    # 300 km/h en los cinco tramos: las vías de OSM traen la velocidad y ninguno queda sin ella
    assert [s.max_speed_kmh for s in line.segments] == [300] * 5
    assert sum(s.length_km for s in line.segments) == pytest.approx(
        line.line.polyline.length_km, abs=0.1
    )


def test_signalling_as_the_map_draws_it(line: BuiltNetwork) -> None:
    """Mapa 4 de la Declaración sobre la Red: BCA y el símbolo de «ERTMS N1 y 2» con el de
    «ASFA - AV» en toda la línea; del mando no dice nada."""
    for segment in line.segments:
        assert segment.attributes["proteccion_tren"].value == "ertms_n1_n2_asfa"
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
    assert spec.line.verification_source_id == "wikipedia-lav-madrid-valladolid"
    assert "wikipedia-lav-madrid-valladolid" in sources
    for section in spec.attribute_sections:
        assert section.source_id in sources
    # Renfe y Ouigo, con horarios cargados. Iryo no figura: su página de destinos no nombra
    # ninguna estación de esta línea
    operators = {o.id: o for o in spec.operators if o.role == "operador"}
    assert set(operators) == {"renfe", "ouigo"}
    assert all(o.timetable == "cargado" for o in operators.values())
    assert "Valladolid" not in str(sources["iryo-web"].coverage)
    assert all(o.source_id in sources for o in spec.operators)
    assert spec.line.zone == "castilla-y-leon"


def test_the_filter_takes_the_trains_of_the_line_and_leaves_the_conventional_ones(
    feed: GtfsFeed, ouigo_feed: GtfsFeed, spec: NetworkSpec
) -> None:
    """Entran 761 viajes de Renfe y 8 de Ouigo. Valladolid-Campo Grande no sirve de filtro: en
    ella paran también los trenes de la línea convencional."""
    assert spec.corridor_filter.any_of_stop_ids == [SEGOVIA]
    trips = select_trips_for_spec(feed, spec)
    assert len(trips) == 761
    assert Counter(t.product for t in trips) == {
        "AVANT": 232,
        "AVE": 220,
        "ALVIA": 168,
        "Intercity": 75,
        "AVLO": 66,
    }
    selected = {t.trip_id for t in trips}
    for trip in feed.trips.values():
        if SEGOVIA in _stops(trip):
            assert trip.trip_id in selected, trip.train_number
    for trip in trips:
        assert not set(_stops(trip)) & CONVENTIONAL, trip.train_number
    # quedan fuera los trenes que paran en Valladolid sin venir de Madrid por esta línea: los de
    # Medina del Campo, Viana, Venta de Baños, Palencia o Burgos. Ninguno para en Chamartín
    left_out = [
        t for t in feed.trips.values() if VALLADOLID in _stops(t) and t.trip_id not in selected
    ]
    assert len(left_out) == 451
    assert all(CHAMARTIN not in _stops(t) for t in left_out)
    assert {t.product for t in left_out} == {
        "MD",
        "PROXIMDAD",
        "REG.EXP.",
        "REGIONAL",
        "Intercity",
    }
    assert len(select_trips_for_spec(ouigo_feed, spec)) == 8


def test_trains_without_a_stop_in_segovia_enter_through_the_rules(
    feed: GtfsFeed, spec: NetworkSpec
) -> None:
    rules = {r.id: r.consecutive_stop_ids for r in spec.route_overrides}
    assert rules == {
        "madrid-valladolid-sin-parada": [CHAMARTIN, VALLADOLID],
        "madrid-leon-sin-parada": [CHAMARTIN, "15100"],
        "madrid-medina-sin-parada": [CHAMARTIN, "08240"],
        "madrid-zamora-sin-parada": [CHAMARTIN, "30200"],
        "madrid-ourense-sin-parada": [CHAMARTIN, "22100"],
    }
    matched = Counter(
        route.override.id
        for trip in select_trips_for_spec(feed, spec)
        if (route := route_for_trip(spec, trip)) is not None
    )
    assert matched == {
        "madrid-valladolid-sin-parada": 188,
        "madrid-zamora-sin-parada": 115,
        "madrid-medina-sin-parada": 14,
        "madrid-ourense-sin-parada": 6,
        "madrid-leon-sin-parada": 4,
    }
    # ningún tren sale de Chamartín hacia el norte sin que alguna regla o el filtro lo recoja:
    # la parada siguiente a Chamartín de todos los que entran es una de estas
    after = {b for t in select_trips_for_spec(feed, spec) for a, b in _pairs(t) if a == CHAMARTIN}
    north = {SEGOVIA, VALLADOLID, "15100", "08240", "30200", "22100"}
    assert north <= after


def test_each_train_counts_on_the_segments_it_runs(
    feed: GtfsFeed, ouigo_feed: GtfsFeed, line: BuiltNetwork
) -> None:
    """Los trenes de Galicia y de Salamanca dejan la línea en la bifurcación Medina; los demás la
    recorren hasta Valladolid, paren o no en ella."""
    trips = select_trips_for_spec(feed, line.spec)

    def having(pair: tuple[str, str]) -> list[GtfsTrip]:
        return [t for t in trips if pair in _pairs(t)]

    for trip in having((CHAMARTIN, "30200"))[:5] + having((CHAMARTIN, "22100"))[:3]:
        assert _short(_passes(trip, feed, line)) == ALL_SEGMENTS[:4]
    for trip in having((SEGOVIA, "08240"))[:5]:
        short = _short(_passes(trip, feed, line))
        assert short[-2:] == ALL_SEGMENTS[2:4] and ALL_SEGMENTS[4] not in short
    for trip in having((CHAMARTIN, VALLADOLID))[:5] + having((CHAMARTIN, "15100")):
        assert _short(_passes(trip, feed, line)) == ALL_SEGMENTS
    for trip in select_trips_for_spec(ouigo_feed, line.spec):
        assert _short(_passes(trip, ouigo_feed, line)) == ALL_SEGMENTS


def test_stops_beyond_the_line_leave_by_the_right_node(spec: NetworkSpec) -> None:
    """Las paradas de la línea de Galicia son salidas por la bifurcación Medina, con los kilómetros
    de vía que da la fuente; las del norte, por Valladolid."""
    for stop_id, km in GALICIA_LINE_KM.items():
        mapping = spec.stop_mappings[stop_id]
        assert mapping.exits == ["bif-medina"] and mapping.track_km == km
    for stop_id in ("30100", "31400", "31412", "08223"):
        assert spec.stop_mappings[stop_id].exits == ["bif-medina"]
    for stop_id in ("14100", "15100", "11014", "15410", "14223", "11600", "13200"):
        assert spec.stop_mappings[stop_id].exits == ["valladolid-campo-grande"]
    assert spec.stop_mappings[CHAMARTIN].node == "madrid-chamartin"
