"""La línea convencional Madrid – Ávila – Medina del Campo – Valladolid (el primer trecho de la 100
de Adif, Madrid – Hendaya): sale de Madrid-Chamartín, cruza la sierra por Villalba y El Escorial y
llega a Valladolid-Campo Grande por Ávila y Medina del Campo. El ramal de Príncipe Pío, por el que
llegan casi todos sus trenes, y las salidas a Segovia, Salamanca y Zamora quedan a trazos."""

from __future__ import annotations

from collections import Counter

import pytest
from conftest import (
    BURGOS_VITORIA_SPEC,
    DATA_DIR,
    LAV_VALLADOLID_SPEC,
    MADRID_AVILA_VALLADOLID_SPEC,
    SOURCES,
)

from oniel.geo import haversine_km
from oniel.gtfs.reader import GtfsFeed, GtfsTrip
from oniel.gtfs.trips import calls_for_trip, calls_on_line, route_for_trip, select_trips_for_spec
from oniel.network.build import BuiltNetwork, build_network
from oniel.network.spec import NetworkSpec, load_network_spec, load_sources
from oniel.sim.passes import LineSegment, SegmentPass, resolve_passes
from oniel.validate import loaded_line

LINE = "madrid-avila-valladolid"
MAP = "adif-declaracion-red-2026-mapas"
CHAMARTIN, PRINCIPE_PIO, ATOCHA = "17000", "10000", "18000"
VILLALBA, AVILA, MEDINA, VALLADOLID = "10200", "10400", "10500", "10600"
SEGOVIA, SALAMANCA, PENARANDA, EL_CARPIO = "12100", "30100", "34010", "32002"
NODES = [
    "madrid-chamartin",
    "madrid-ramon-y-cajal",
    "mirasierra-paco-de-lucia",
    "pitis",
    "pinar-de-las-rozas",
    "las-matas",
    "torrelodones",
    "galapagar-la-navata",
    "villalba-de-guadarrama",
    "san-yago",
    "las-zorreras-navalquejigo",
    "el-escorial",
    "zarzalejo",
    "robledo-de-chavela",
    "santa-maria-de-la-alameda-peguerinos",
    "el-pimpollar",
    "las-navas-del-marques",
    "navalperal",
    "herradon-la-canada",
    "guimorcondo",
    "avila",
    "arevalo",
    "medina-del-campo",
    "pozaldez",
    "matapozuelos",
    "valdestillas",
    "viana",
    "valladolid-campo-grande",
]
ALL_SEGMENTS = [f"{a}:{b}" for a, b in zip(NODES, NODES[1:], strict=False)]


def _from(a: str, b: str) -> list[str]:
    return ALL_SEGMENTS[NODES.index(a) : NODES.index(b)]


@pytest.fixture(scope="module")
def spec() -> NetworkSpec:
    return load_network_spec(MADRID_AVILA_VALLADOLID_SPEC)


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


def test_the_geometry_joins_two_relations_of_line_100(line: BuiltNetwork) -> None:
    """De Chamartín a Pinar de las Rozas, la relación del trecho de Pitis; desde allí, la de
    Madrid – Valladolid – Burgos, que llega a Madrid por Príncipe Pío y de la que no se usa ese
    ramal. Empalman en un nodo que comparten: 250,2 km."""
    coords = line.line.polyline.coords
    assert haversine_km(coords[0], (-3.6815079, 40.4740481)) < 0.05
    assert haversine_km(coords[-1], (-4.7268608, 41.6418742)) < 0.05
    assert [p.source_id for p in line.line.part_spans] == [
        "osm-relation-18369027",
        "osm-relation-13489217",
    ]
    assert not line.line.gaps_km
    assert line.line.polyline.length_km == pytest.approx(250.2, abs=0.1)
    assert all(n.offset_m < 250 for n in line.nodes)
    assert all(n.offset_m < 35 for n in line.nodes[1:])


def test_nodes_stations_and_dashed_branches(line: BuiltNetwork) -> None:
    assert [n.spec.id for n in line.nodes] == NODES
    assert all(n.spec.kind == "estacion" for n in line.nodes)
    principal = {n.spec.id for n in line.nodes if n.spec.rank == "principal"}
    assert principal == {
        "madrid-chamartin",
        "pinar-de-las-rozas",
        "villalba-de-guadarrama",
        "el-escorial",
        "avila",
        "arevalo",
        "medina-del-campo",
        "valladolid-campo-grande",
    }
    assert line.node("avila").spec.adif_code == AVILA
    assert line.node("medina-del-campo").spec.adif_code == MEDINA
    assert {c.id: c.node_id for c in line.spec.connections} == {
        "conv-villalba-segovia": "villalba-de-guadarrama",
        "conv-avila-salamanca": "avila",
        "conv-medina-salamanca": "medina-del-campo",
        "conv-valladolid-venta-de-banos": "valladolid-campo-grande",
    }
    for c in line.spec.connections:
        node = line.node(c.node_id).spec.position
        assert c.sketch[0] == (node.lon, node.lat) and c.status == "no_cargada"


def test_chamartin_and_valladolid_are_the_high_speed_nodes(line: BuiltNetwork) -> None:
    """Las dos cabeceras las define la alta velocidad por Segovia, que ya no sale a trazos de
    Valladolid hacia Medina del Campo: esta línea las incorpora sin moverlas."""
    shared = {n.spec.id for n in line.nodes if n.spec.shared}
    assert shared == {"madrid-chamartin", "valladolid-campo-grande"}
    lav = load_network_spec(LAV_VALLADOLID_SPEC)
    for node_id in shared:
        theirs = next(n for n in lav.nodes if n.id == node_id)
        assert line.node(node_id).spec.position == theirs.position
    assert all("medina" not in c.id for c in lav.connections)


def test_kilometre_points_restart_where_the_principe_pio_branch_joins(
    line: BuiltNetwork,
) -> None:
    """Los puntos kilométricos del esquema de la línea cuentan desde Chamartín, pero entre Pitis y
    Pinar de las Rozas el trazado mide 0,75 km más que ellos: la cuenta se retoma en Pinar, donde
    se une el ramal de Príncipe Pío. Desde allí cada estación queda a menos de 0,9 km del suyo."""
    assert [(r.node, r.pk_km) for r in line.spec.line.pk_restarts] == [("pinar-de-las-rozas", 20.4)]
    assert line.node("avila").spec.reference_pk_km == 120.6
    assert line.node("medina-del-campo").spec.reference_pk_km == 206.3
    pinar = line.node("pinar-de-las-rozas").km
    for node in line.nodes[1:-1]:
        ref = node.spec.reference_pk_km
        if ref is None:
            continue
        if node.km <= pinar:
            assert node.km == pytest.approx(ref, abs=0.75), node.spec.id
        else:
            assert 20.4 + node.km - pinar == pytest.approx(ref, abs=0.9), node.spec.id


def test_double_track_electrified_and_speeds_from_the_tracks(line: BuiltNetwork) -> None:
    assert [s.id.removeprefix(f"{LINE}:") for s in line.segments] == ALL_SEGMENTS
    assert all(s.tracks == 2 for s in line.segments)
    assert line.spec.line.gauge_mm == 1668 and line.spec.line.electrification == "3 kV CC"
    speeds = [s.max_speed_kmh or 0 for s in line.segments]
    assert all(speeds) and max(speeds) == 160
    # la sierra, entre El Escorial y Ávila, es lo más lento
    assert max(speeds[NODES.index("santa-maria-de-la-alameda-peguerinos") : 18]) <= 105


def test_signalling_as_the_map_draws_it(line: BuiltNetwork) -> None:
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
    stations = sources["osm-instalaciones-madrid-avila-valladolid"]
    assert stations.file and (DATA_DIR / stations.file).exists()
    assert spec.line.verification_source_id == "wikipedia-linea-100-esquema"
    assert "wikipedia-linea-100" in sources
    for section in spec.attribute_sections:
        assert section.source_id in sources
    assert {o.id for o in spec.operators if o.role == "operador"} == {"renfe"}
    assert all(o.source_id in sources for o in spec.operators)
    assert spec.line.zone == "castilla-y-leon"


def test_the_filter_leaves_out_the_high_speed_trains(
    feed: GtfsFeed, ouigo_feed: GtfsFeed, spec: NetworkSpec
) -> None:
    """Entran los viajes que paran en dos nodos de la línea y en una de sus estaciones propias:
    502 de Renfe y ninguno de Ouigo. Los de alta velocidad, que paran en Chamartín y Valladolid,
    quedan fuera."""
    trips = select_trips_for_spec(feed, spec)
    assert len(trips) == 502
    assert Counter(t.product for t in trips) == {
        "Media Distancia": 160,
        "Proximidad": 150,
        "Regional": 131,
        "Regional Exprés": 55,
        "Intercity": 6,
    }
    assert not any("08004" in _stops(t) for t in trips)
    assert select_trips_for_spec(ouigo_feed, spec) == []


def test_each_train_counts_on_the_segments_it_runs(feed: GtfsFeed, line: BuiltNetwork) -> None:
    """Los de Príncipe Pío entran en Pinar de las Rozas; los de Segovia dejan la línea en
    Villalba; los de Salamanca por Medina solo recorren de Medina a Valladolid."""
    trips = select_trips_for_spec(feed, line.spec)
    pp_valladolid = [t for t in trips if _stops(t)[0] == PRINCIPE_PIO and VALLADOLID in _stops(t)]
    segovia = [t for t in trips if SEGOVIA in _stops(t) and CHAMARTIN in _stops(t)]
    sal_medina = [t for t in trips if EL_CARPIO in _stops(t) and VALLADOLID in _stops(t)]
    assert pp_valladolid and segovia and sal_medina
    for trip in pp_valladolid[:10]:
        assert _short(_passes(trip, feed, line)) == ALL_SEGMENTS[4:]
    for trip in segovia[:10]:
        assert _short(_passes(trip, feed, line)) == _from(
            "madrid-chamartin", "villalba-de-guadarrama"
        )
    for trip in sal_medina:
        assert _short(_passes(trip, feed, line)) == ALL_SEGMENTS[NODES.index("medina-del-campo") :]


def test_trains_that_reach_chamartin_through_principe_pio(
    feed: GtfsFeed, line: BuiltNetwork
) -> None:
    """Algunos regionales de Ávila siguen de Príncipe Pío a Atocha y Chamartín por el túnel de
    Cercanías: una regla los deja en Pinar de las Rozas, y no cuentan entre Chamartín y Pinar."""
    trips = [
        t
        for t in select_trips_for_spec(feed, line.spec)
        if PRINCIPE_PIO in _stops(t) and ATOCHA in _stops(t) and AVILA in _stops(t)
    ]
    assert len(trips) == 12
    for trip in trips:
        assert route_for_trip(line.spec, trip) is not None
        assert _short(_passes(trip, feed, line)) == _from("pinar-de-las-rozas", "avila")


def test_salamanca_leaves_by_avila_or_by_medina(spec: NetworkSpec) -> None:
    """Salamanca sale por Ávila, como la mayoría de sus trenes; los que llegan por Medina del Campo
    la cambian con una regla."""
    sm = spec.stop_mappings
    assert sm[SALAMANCA].exits == ["avila"] and sm[PENARANDA].exits == ["avila"]
    assert sm[EL_CARPIO].exits == ["medina-del-campo"]
    rules = {r.id: r for r in spec.route_overrides}
    for prev in (SALAMANCA, EL_CARPIO, "32001"):
        rule = rules[f"salamanca-por-medina-{prev}"]
        assert rule.consecutive_stop_ids == [prev, MEDINA]
        assert rule.stop_mappings[SALAMANCA].exits == ["medina-del-campo"]
    # Zamora es nodo de la alta velocidad, pero estos trenes llegan por la convencional
    assert sm["30200"].exits == ["medina-del-campo"] and not sm["30200"].via


def test_the_burgos_line_now_reaches_these_stations_through_valladolid() -> None:
    other = load_network_spec(BURGOS_VITORIA_SPEC).stop_mappings
    for stop_id in (VILLALBA, AVILA, MEDINA):
        assert [(v.line, v.node) for v in other[stop_id].via][-1] == (
            LINE,
            "valladolid-campo-grande",
        )
    assert not other[PRINCIPE_PIO].via
