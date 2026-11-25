"""La línea convencional Miranda de Ebro – Orduña – Bilbao, el último trecho de la línea 700 de
Adif: sale de Miranda, donde la cruza la línea de Burgos a Vitoria, y llega a Bilbao-Abando por
Orduña y el valle del Nervión. Vía única hasta Orduña y doble de ahí a Bilbao, de ancho ibérico y
electrificada."""

from __future__ import annotations

from collections import Counter

import pytest
from conftest import (
    BURGOS_VITORIA_SPEC,
    DATA_DIR,
    LAV_BURGOS_SPEC,
    LAV_LEON_SPEC,
    LAV_VALLADOLID_SPEC,
    MIRANDA_BILBAO_SPEC,
    SOURCES,
    ZARAGOZA_LOGRONO_SPEC,
)

from oniel.geo import haversine_km
from oniel.gtfs.reader import GtfsFeed, GtfsTrip
from oniel.gtfs.trips import calls_for_trip, calls_on_line, route_for_trip, select_trips_for_spec
from oniel.network.build import BuiltNetwork, build_network
from oniel.network.spec import NetworkSpec, load_annotations, load_network_spec, load_sources
from oniel.sim.passes import LineSegment, SegmentPass, resolve_passes
from oniel.validate import loaded_line

LINE = "miranda-bilbao"
MAP = "adif-declaracion-red-2026-mapas"
MIRANDA, LLODIO, BILBAO = "11200", "13106", "13200"
BURGOS, VALLADOLID, CHAMARTIN, LOGRONO, BARCELONA = "11014", "10600", "17000", "81100", "71801"
NODES = ["miranda-de-ebro", "orduna", "llodio", "bilbao-abando"]
ALL_SEGMENTS = [f"{a}:{b}" for a, b in zip(NODES, NODES[1:], strict=False)]
#: Las paradas de la línea en la otra punta del puente: las que salen por Miranda de Ebro.
VIA_MIRANDA = (LINE, "miranda-de-ebro")


@pytest.fixture(scope="module")
def spec() -> NetworkSpec:
    return load_network_spec(MIRANDA_BILBAO_SPEC)


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


def test_the_geometry_is_one_piece_of_the_line_700_relation(line: BuiltNetwork) -> None:
    """La pieza de la relación de la línea 700 que va de Miranda de Ebro a Bilbao es de una
    pieza: 104,0 km, de la estación de Miranda a los andenes de Abando."""
    coords = line.line.polyline.coords
    assert haversine_km(coords[0], (-2.9410258, 42.6905962)) < 0.05
    assert haversine_km(coords[-1], (-2.927682, 43.26056)) < 0.05
    assert [p.source_id for p in line.line.part_spans] == ["osm-relation-9277501"]
    assert not line.line.gaps_km
    assert line.line.polyline.length_km == pytest.approx(104.0, abs=0.1)
    assert all(n.offset_m < 25 for n in line.nodes)


def test_nodes_and_main_stations(line: BuiltNetwork) -> None:
    """Las estaciones en las que paran los trenes cargados y Orduña, donde empieza la vía doble."""
    assert [n.spec.id for n in line.nodes] == NODES
    assert all(n.spec.kind == "estacion" for n in line.nodes)
    secondary = {n.spec.id for n in line.nodes if n.spec.rank == "secundario"}
    assert secondary == {"orduna"}
    assert line.node("llodio").spec.adif_code == LLODIO
    assert line.node("bilbao-abando").spec.adif_code == BILBAO
    assert line.spec.connections == []


def test_miranda_is_the_node_of_the_burgos_line(line: BuiltNetwork) -> None:
    """Miranda de Ebro la define la línea de Burgos a Vitoria: esta la incorpora sin moverla, y
    aquella ya no sale a trazos hacia Bilbao, solo hacia Logroño."""
    assert {n.spec.id for n in line.nodes if n.spec.shared} == {"miranda-de-ebro"}
    burgos = load_network_spec(BURGOS_VITORIA_SPEC)
    theirs = next(n for n in burgos.nodes if n.id == "miranda-de-ebro")
    assert line.node("miranda-de-ebro").spec.position == theirs.position
    assert [c.id for c in burgos.connections if c.node_id == "miranda-de-ebro"] == [
        "conv-miranda-logrono"
    ]


def test_kilometre_points_count_from_castejon(line: BuiltNetwork) -> None:
    """Los puntos kilométricos siguen la numeración de Castejón a Bilbao: Miranda de Ebro es el
    145,2, y Orduña y Llodio quedan a menos de 0,1 km del suyo."""
    assert line.spec.line.pk_origin_km == 145.2
    with_pk = [n for n in line.nodes if n.spec.reference_pk_km is not None]
    assert [n.spec.id for n in with_pk] == ["orduna", "llodio"]
    for node in with_pk:
        assert 145.2 + node.km == pytest.approx(node.spec.reference_pk_km, abs=0.1), node.spec.id


def test_single_track_to_orduna_and_double_to_bilbao(line: BuiltNetwork) -> None:
    assert [s.id.removeprefix(f"{LINE}:") for s in line.segments] == ALL_SEGMENTS
    assert [s.tracks for s in line.segments] == [1, 2, 2]
    assert line.spec.line.gauge_mm == 1668 and line.spec.line.electrification == "3 kV CC"
    speeds = [s.max_speed_kmh or 0 for s in line.segments]
    assert all(speeds) and max(speeds) == 140


def test_signalling_as_the_map_draws_it(line: BuiltNetwork) -> None:
    """El mapa 4 dibuja bloqueo automático de vía única hasta Orduña y de vía doble de ahí a
    Bilbao, los dos con control de tráfico centralizado, y ASFA."""
    blocks = [s.attributes["bloqueo"].value for s in line.segments]
    assert blocks == ["bau", "bab", "bab"]
    for segment in line.segments:
        assert segment.attributes["proteccion_tren"].value == "asfa"
        assert segment.attributes["mando"].value == "ctc"
        for key in ("proteccion_tren", "bloqueo", "mando"):
            assert segment.attributes[key].source_id == MAP


def test_sources_and_operators_are_registered(spec: NetworkSpec) -> None:
    sources = {s.id: s for s in load_sources(SOURCES)}
    for part in spec.line.geometry_source.parts:
        source = sources[part.source_id]
        assert source.license == "ODbL 1.0"
        assert source.file == part.file and (DATA_DIR / part.file).exists()
    stations = sources["osm-instalaciones-miranda-bilbao"]
    assert stations.file and (DATA_DIR / stations.file).exists()
    assert spec.line.verification_source_id == "wikipedia-linea-casetas-bilbao"
    for section in spec.attribute_sections:
        assert section.source_id in sources
    assert {o.id for o in spec.operators if o.role == "operador"} == {"renfe"}
    assert all(o.source_id in sources for o in spec.operators)
    assert spec.line.zone == "cantabrico"


def test_the_filter_takes_the_trains_to_bilbao(
    feed: GtfsFeed, ouigo_feed: GtfsFeed, spec: NetworkSpec
) -> None:
    """Entran los viajes que paran en dos estaciones de la línea: 28 de Renfe, todos con parada
    en Miranda de Ebro y en Bilbao, y ninguno de Ouigo."""
    trips = select_trips_for_spec(feed, spec)
    assert len(trips) == 28
    assert Counter(t.product for t in trips) == {"Alvia": 24, "Intercity": 4}
    assert all(MIRANDA in _stops(t) and BILBAO in _stops(t) for t in trips)
    assert select_trips_for_spec(ouigo_feed, spec) == []


def test_each_train_runs_the_whole_line(feed: GtfsFeed, line: BuiltNetwork) -> None:
    """Todos la recorren entera: los de Madrid, que llegan a Miranda por Burgos, y los de
    Barcelona, que llegan por Logroño."""
    trips = select_trips_for_spec(feed, line.spec)
    assert any(CHAMARTIN in _stops(t) for t in trips)
    assert any(BARCELONA in _stops(t) for t in trips)
    for trip in trips:
        assert _short(_passes(trip, feed, line)) == ALL_SEGMENTS


def test_stops_beyond_miranda(spec: NetworkSpec) -> None:
    """Burgos, Valladolid y Madrid se alcanzan por la línea de Burgos a Vitoria y la alta
    velocidad; Logroño y lo que sigue hacia Barcelona salen sin más por Miranda de Ebro, porque el
    trecho de Miranda a Logroño no está cargado."""
    sm = spec.stop_mappings
    assert [(v.line, v.node) for v in sm[BURGOS].via] == [
        ("burgos-miranda-vitoria", "miranda-de-ebro")
    ]
    assert [(v.line, v.node) for v in sm[CHAMARTIN].via] == [
        ("burgos-miranda-vitoria", "miranda-de-ebro"),
        ("lav-venta-de-banos-burgos", "burgos-rosa-manzano"),
        ("lav-valladolid-leon", "bif-venta-de-banos"),
        ("lav-madrid-valladolid", "valladolid-campo-grande"),
    ]
    for stop_id in (LOGRONO, BARCELONA):
        assert sm[stop_id].exits == ["miranda-de-ebro"] and not sm[stop_id].via


def test_the_neighbouring_lines_reach_bilbao_through_miranda() -> None:
    """En las líneas por las que llegan los trenes de Madrid, Llodio y Bilbao llevan al final del
    camino esta línea, desde Miranda de Ebro. En la del Ebro siguen saliendo por Logroño, sin
    camino cargado hasta Miranda."""
    for path in (BURGOS_VITORIA_SPEC, LAV_BURGOS_SPEC, LAV_LEON_SPEC, LAV_VALLADOLID_SPEC):
        other = load_network_spec(path).stop_mappings
        for stop_id in (LLODIO, BILBAO):
            via = [(v.line, v.node) for v in other[stop_id].via]
            assert via[-1] == VIA_MIRANDA, (path.name, stop_id)
    ebro = load_network_spec(ZARAGOZA_LOGRONO_SPEC).stop_mappings
    assert ebro[BILBAO].exits == ["logrono"] and not ebro[BILBAO].via


def test_the_basque_high_speed_sketch_ends_at_the_bilbao_station(line: BuiltNetwork) -> None:
    """El esbozo de la «Y» vasca acaba en el mismo punto que el nodo de Bilbao-Abando."""
    annotations = load_annotations(DATA_DIR / "curated" / "anotaciones.json")
    project = next(a for a in annotations if a.id == "proyecto-y-vasca")
    assert project.kind == "proyecto" and project.status == "en_obras"
    assert project.geometry is not None
    bilbao = line.node("bilbao-abando").spec.position
    assert bilbao is not None
    ends = [tuple(p) for branch in project.geometry["coordinates"] for p in branch]
    assert (bilbao.lon, bilbao.lat) in ends
