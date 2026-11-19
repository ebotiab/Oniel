"""La línea convencional Palencia – Santander (la 160 de Adif): sale de Palencia, donde la deja la
alta velocidad de León, sube por Aguilar de Campoo y Reinosa, cruza la cordillera Cantábrica y
baja por Torrelavega hasta Santander. Vía única de ancho ibérico, electrificada, en toda su
longitud."""

from __future__ import annotations

from collections import Counter

import pytest
from conftest import (
    DATA_DIR,
    LAV_LEON_SPEC,
    LAV_VALLADOLID_SPEC,
    PALENCIA_SANTANDER_SPEC,
    SOURCES,
)

from oniel.geo import haversine_km
from oniel.gtfs.reader import GtfsFeed, GtfsTrip
from oniel.gtfs.trips import calls_for_trip, calls_on_line, route_for_trip, select_trips_for_spec
from oniel.network.build import BuiltNetwork, build_network
from oniel.network.spec import NetworkSpec, load_annotations, load_network_spec, load_sources
from oniel.sim.passes import LineSegment, SegmentPass, resolve_passes
from oniel.validate import loaded_line

LINE = "palencia-santander"
MAP = "adif-declaracion-red-2026-mapas"
PALENCIA, AGUILAR, MATAPORQUERA, REINOSA = "14100", "14114", "14200", "14202"
TORRELAVEGA, SANTANDER = "14213", "14223"
VALLADOLID, VENTA_DE_BANOS, CHAMARTIN, ALICANTE = "10600", "11000", "17000", "60911"
NODES = [
    "palencia",
    "monzon-de-campos",
    "el-carrion",
    "amusco",
    "pina",
    "fromista",
    "osorno",
    "espinosa-de-villagonzalo",
    "herrera-de-pisuerga",
    "alar-del-rey",
    "mave",
    "aguilar-de-campoo",
    "quintanilla-de-las-torres",
    "mataporquera",
    "reinosa",
    "barcena",
    "los-corrales-de-buelna",
    "torrelavega",
    "renedo",
    "maliano",
    "valdecilla",
    "santander",
]
ALL_SEGMENTS = [f"{a}:{b}" for a, b in zip(NODES, NODES[1:], strict=False)]


@pytest.fixture(scope="module")
def spec() -> NetworkSpec:
    return load_network_spec(PALENCIA_SANTANDER_SPEC)


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


def test_the_geometry_is_one_relation_from_palencia_to_santander(line: BuiltNetwork) -> None:
    """La relación de servicio de la línea 160 es de una pieza: 217,0 km, lo mismo que da
    Wikipedia. Acaba a la entrada de la estación de Santander, unos 400 m antes de los andenes."""
    coords = line.line.polyline.coords
    assert haversine_km(coords[0], (-4.5336556, 42.0158571)) < 0.05
    assert haversine_km(coords[-1], (-3.8164434, 43.4578983)) < 0.05
    assert [p.source_id for p in line.line.part_spans] == ["osm-relation-4220975"]
    assert not line.line.gaps_km
    assert line.line.polyline.length_km == pytest.approx(217.0, abs=0.1)
    assert all(n.offset_m < 25 for n in line.nodes[:-1])
    assert line.node("santander").offset_m < 400


def test_nodes_and_main_stations(line: BuiltNetwork) -> None:
    assert [n.spec.id for n in line.nodes] == NODES
    assert all(n.spec.kind == "estacion" for n in line.nodes)
    principal = {n.spec.id for n in line.nodes if n.spec.rank == "principal"}
    assert principal == {"palencia", "aguilar-de-campoo", "reinosa", "torrelavega", "santander"}
    assert line.node("reinosa").spec.adif_code == REINOSA
    assert line.node("santander").spec.adif_code == SANTANDER
    assert line.spec.connections == []


def test_palencia_is_the_high_speed_node(line: BuiltNetwork) -> None:
    """Palencia la define la alta velocidad de Valladolid a León: esta línea la incorpora sin
    moverla, y aquella ya no sale a trazos hacia Santander."""
    assert {n.spec.id for n in line.nodes if n.spec.shared} == {"palencia"}
    leon = load_network_spec(LAV_LEON_SPEC)
    theirs = next(n for n in leon.nodes if n.id == "palencia")
    assert line.node("palencia").spec.position == theirs.position
    assert all("santander" not in c.id for c in leon.connections)


def test_kilometre_points_count_from_madrid(line: BuiltNetwork) -> None:
    """Los puntos kilométricos de la línea siguen la numeración desde Madrid: Palencia es el
    297,3, y las cuatro estaciones que los traen quedan a menos de 0,25 km del suyo."""
    assert line.spec.line.pk_origin_km == 297.3
    with_pk = [n for n in line.nodes if n.spec.reference_pk_km is not None]
    assert [n.spec.id for n in with_pk] == [
        "aguilar-de-campoo",
        "reinosa",
        "torrelavega",
        "santander",
    ]
    for node in with_pk:
        assert 297.3 + node.km == pytest.approx(node.spec.reference_pk_km, abs=0.25), node.spec.id


def test_single_track_electrified_and_speeds_from_the_tracks(line: BuiltNetwork) -> None:
    assert [s.id.removeprefix(f"{LINE}:") for s in line.segments] == ALL_SEGMENTS
    assert all(s.tracks == 1 for s in line.segments)
    assert line.spec.line.gauge_mm == 1668 and line.spec.line.electrification == "3 kV CC"
    speeds = [s.max_speed_kmh or 0 for s in line.segments]
    assert all(speeds) and max(speeds) == 155
    # la montaña, de Reinosa a Bárcena, es lo más lento
    assert speeds[ALL_SEGMENTS.index("reinosa:barcena")] == 110


def test_signalling_as_the_map_draws_it(line: BuiltNetwork) -> None:
    for segment in line.segments:
        assert segment.attributes["proteccion_tren"].value == "asfa"
        assert segment.attributes["bloqueo"].value == "bau"
        assert segment.attributes["mando"].value == "ctc"
        for key in ("proteccion_tren", "bloqueo", "mando"):
            assert segment.attributes[key].source_id == MAP


def test_sources_and_operators_are_registered(spec: NetworkSpec) -> None:
    sources = {s.id: s for s in load_sources(SOURCES)}
    for part in spec.line.geometry_source.parts:
        source = sources[part.source_id]
        assert source.license == "ODbL 1.0"
        assert source.file == part.file and (DATA_DIR / part.file).exists()
    stations = sources["osm-instalaciones-palencia-santander"]
    assert stations.file and (DATA_DIR / stations.file).exists()
    assert (DATA_DIR / "raw" / "osm" / "via_entrada_santander_2026-11-19.json").exists()
    assert spec.line.verification_source_id == "wikipedia-linea-palencia-santander"
    for section in spec.attribute_sections:
        assert section.source_id in sources
    assert {o.id for o in spec.operators if o.role == "operador"} == {"renfe"}
    assert all(o.source_id in sources for o in spec.operators)
    assert spec.line.zone == "cantabrico"


def test_the_filter_takes_the_trains_to_santander(
    feed: GtfsFeed, ouigo_feed: GtfsFeed, spec: NetworkSpec
) -> None:
    """Entran los viajes que paran en dos nodos de la línea y en una de sus estaciones propias:
    65 de Renfe y ninguno de Ouigo. Los trenes de vía estrecha que paran en Santander o en
    Mataporquera, y los de León y Burgos que paran en Palencia, quedan fuera."""
    trips = select_trips_for_spec(feed, spec)
    assert len(trips) == 65
    assert Counter(t.product for t in trips) == {
        "ALVIA": 28,
        "REG.EXP.": 20,
        "Intercity": 9,
        "MD": 8,
    }
    assert all(SANTANDER in _stops(t) for t in trips)
    assert select_trips_for_spec(ouigo_feed, spec) == []


def test_each_train_counts_from_palencia(feed: GtfsFeed, line: BuiltNetwork) -> None:
    """Todos recorren la línea entera: los Alvia de Madrid y de Alicante y los regionales de
    Valladolid, que llegan a Palencia por la línea convencional, por Venta de Baños."""
    trips = select_trips_for_spec(feed, line.spec)
    alvia = [t for t in trips if CHAMARTIN in _stops(t)]
    regional = [t for t in trips if VENTA_DE_BANOS in _stops(t)]
    alicante = [t for t in trips if ALICANTE in _stops(t)]
    assert alvia and regional and alicante
    for trip in trips:
        assert _short(_passes(trip, feed, line)) == ALL_SEGMENTS


def test_stops_beyond_palencia_go_through_the_high_speed_line(spec: NetworkSpec) -> None:
    """Valladolid y lo que hay más allá se alcanzan por la alta velocidad de León; Venta de Baños y
    las estaciones de la línea convencional de Valladolid, que no está cargada, salen sin más por
    Palencia."""
    sm = spec.stop_mappings
    assert [(v.line, v.node) for v in sm[VALLADOLID].via] == [("lav-valladolid-leon", "palencia")]
    assert [(v.line, v.node) for v in sm[CHAMARTIN].via] == [
        ("lav-valladolid-leon", "palencia"),
        ("lav-madrid-valladolid", "valladolid-campo-grande"),
    ]
    assert [(v.line, v.node) for v in sm[ALICANTE].via][0] == ("lav-valladolid-leon", "palencia")
    assert sm[VENTA_DE_BANOS].exits == ["palencia"] and not sm[VENTA_DE_BANOS].via


def test_the_madrid_line_reaches_santander_through_palencia() -> None:
    other = load_network_spec(LAV_VALLADOLID_SPEC).stop_mappings
    for stop_id in (AGUILAR, REINOSA, TORRELAVEGA, SANTANDER):
        assert [(v.line, v.node) for v in other[stop_id].via] == [
            ("lav-valladolid-leon", "valladolid-campo-grande"),
            (LINE, "palencia"),
        ]


def test_the_high_speed_works_to_aguilar_are_a_project() -> None:
    annotations = load_annotations(DATA_DIR / "curated" / "anotaciones.json")
    project = next(a for a in annotations if a.id == "proyecto-lav-palencia-aguilar")
    assert project.kind == "proyecto" and project.status == "en_obras"
    assert project.geometry is not None
    sources = {s.id for s in load_sources(SOURCES)}
    assert set(project.source_ids) <= sources
    assert [m.date for m in project.milestones][-1] == "2026-05-06"
