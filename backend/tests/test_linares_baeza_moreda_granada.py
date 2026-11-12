"""Cuarta línea: la convencional Linares-Baeza – Moreda – Granada (líneas 410 y 416 de Adif)."""

from __future__ import annotations

import json
from collections import Counter

import pytest
from conftest import CONV_SPEC, DATA_DIR, LBMG_SPEC, SOURCES

from oniel.geo import haversine_km
from oniel.gtfs.reader import GtfsFeed
from oniel.gtfs.trips import calls_for_trip, route_for_trip, select_trips_for_spec
from oniel.network.build import BuiltNetwork, build_network
from oniel.network.spec import NetworkSpec, load_network_spec, load_sources
from oniel.sim.passes import LineNode, LineSegment, resolve_passes
from oniel.validate import expected_pk_km

LINE = "linares-baeza-moreda-granada"
SERVICE_RELATION = "osm-relation-6641023"
LINE_416 = "osm-relation-11350675"
NODES = [
    "linares-baeza",
    "jodar-ubeda",
    "cabra-del-santo-cristo",
    "moreda",
    "bif-almeria",
    "iznalloz",
    "granada",
]
NORTH = [f"{LINE}:{a}:{b}" for a, b in zip(NODES[:3], NODES[1:4], strict=True)]
TRIANGLE = f"{LINE}:moreda:bif-almeria"
SOUTH = [f"{LINE}:bif-almeria:iznalloz", f"{LINE}:iznalloz:granada"]


@pytest.fixture(scope="module")
def lbmg_spec() -> NetworkSpec:
    return load_network_spec(LBMG_SPEC)


@pytest.fixture(scope="module")
def lbmg(lbmg_spec: NetworkSpec) -> BuiltNetwork:
    return build_network(lbmg_spec, DATA_DIR)


def test_the_geometry_runs_from_linares_baeza_to_granada_without_a_gap(
    lbmg: BuiltNetwork,
) -> None:
    """Dos partes de dos relaciones de OSM que comparten el nodo en el que se empalman, 293 m al
    sur de la estación de Moreda: el trazado no tiene huecos ni saltos."""
    conv = load_network_spec(CONV_SPEC)
    linares = next(n for n in conv.nodes if n.id == "linares-baeza").position
    granada = lbmg.node("granada")
    assert linares.lon is not None and linares.lat is not None
    coords = lbmg.line.polyline.coords
    assert haversine_km(coords[0], (linares.lon, linares.lat)) < 0.05
    assert haversine_km(coords[-1], (granada.lon, granada.lat)) < 0.1
    # 117,5 km de la línea 410 y 56,1 km de la 416; por los PK de Adif serían 174,2 km
    assert lbmg.line.polyline.length_km == pytest.approx(173.7, abs=0.2)
    assert not lbmg.line.gaps_km and not lbmg.line.joins_km
    assert [p.source_id for p in lbmg.line.part_spans] == [SERVICE_RELATION, LINE_416]
    assert lbmg.line.part_spans[0].km_to == pytest.approx(117.5, abs=0.1)
    # baja de Linares-Baeza (38,07° N) a Moreda y gira al oeste hasta Granada (3,61° O)
    assert coords[0][1] > 38.06 and min(lon for lon, _ in coords) < -3.6


def test_linares_baeza_is_the_node_of_the_conventional_line(lbmg: BuiltNetwork) -> None:
    assert [n.spec.id for n in lbmg.nodes] == NODES
    assert {n.spec.id for n in lbmg.nodes if n.spec.shared} == {"linares-baeza"}
    conv = load_network_spec(CONV_SPEC)
    theirs = next(n for n in conv.nodes if n.id == "linares-baeza")
    ours = lbmg.node("linares-baeza").spec
    assert not theirs.shared and ours.position == theirs.position
    assert ours.adif_code == theirs.adif_code == "50300"
    assert all(n.offset_m < 50 for n in lbmg.nodes)
    # la bifurcación no es una estación y queda como nodo secundario
    bif = lbmg.node("bif-almeria").spec
    assert (bif.kind, bif.rank, bif.adif_code) == ("bifurcacion", "secundario", None)


@pytest.mark.parametrize(
    ("node_id", "reference_pk"),
    [
        ("linares-baeza", 8.634),
        ("jodar-ubeda", 47.247),
        ("cabra-del-santo-cristo", 94.377),
        ("moreda", 126.124),
        ("bif-almeria", 1.1),
        ("iznalloz", 23.977),
        ("granada", 56.746),
    ],
)
def test_kilometre_points_follow_line_410_to_moreda_and_restart_there_for_line_416(
    lbmg: BuiltNetwork, node_id: str, reference_pk: float
) -> None:
    """Hasta Moreda valen los PK de la línea 410, que se cuentan desde Linares-San José
    (Linares-Baeza es el 8,634); la 416 empieza en cero en Moreda."""
    line = lbmg.spec.line
    assert line.pk_origin_km == 8.634
    assert [(r.node, r.pk_km) for r in line.pk_restarts] == [("moreda", 0.0)]
    node = lbmg.node(node_id)
    assert node.spec.reference_pk_km == reference_pk
    assert expected_pk_km(lbmg, node.km) == pytest.approx(reference_pk, abs=0.4)


def test_a_restart_has_to_name_a_node_of_the_line() -> None:
    raw = json.loads(LBMG_SPEC.read_text(encoding="utf-8"))
    raw["line"]["pk_restarts"] = [{"node": "guadix", "pk_km": 0.0}]
    with pytest.raises(ValueError, match="pk_restarts apunta a un nodo desconocido guadix"):
        NetworkSpec.model_validate(raw)


def test_the_whole_line_is_single_track_and_has_no_overhead_wire(lbmg: BuiltNetwork) -> None:
    assert [s.id for s in lbmg.segments] == [*NORTH, TRIANGLE, *SOUTH]
    assert all(s.tracks == 1 and s.max_speed_kmh == 140 for s in lbmg.segments)
    assert [s.source_id for s in lbmg.segments] == [SERVICE_RELATION] * 3 + [LINE_416] * 3
    assert lbmg.spec.line.electrification == "Sin electrificar"
    # el primer nodo se proyecta a 5 m del principio del trazado
    total = sum(s.length_km for s in lbmg.segments)
    assert total == pytest.approx(lbmg.line.polyline.length_km, abs=0.02)


def test_sources_of_the_line_are_registered(lbmg_spec: NetworkSpec) -> None:
    sources = {s.id: s for s in load_sources(SOURCES)}
    for part in lbmg_spec.line.geometry_source.parts:
        geometry = sources[part.source_id]
        assert geometry.license == "ODbL 1.0" and geometry.retrieved_on == "2026-11-12"
        assert geometry.file == part.file and (DATA_DIR / part.file).exists()
    assert lbmg_spec.line.verification_source_id == "wikipedia-lineas-410-416"
    wikipedia = sources["wikipedia-lineas-410-416"]
    assert wikipedia.license == "CC BY-SA 4.0" and wikipedia.retrieved_on == "2026-11-12"
    coverage = wikipedia.coverage or ""
    assert "410" in coverage and "416" in coverage
    # el número de vías, de Wikipedia; la señalización, del mapa 4 de la Declaración sobre la Red
    sections = {t.attribute: t for t in lbmg_spec.attribute_sections}
    assert (sections["tracks"].value, sections["tracks"].source_id) == (1, wikipedia.id)
    signalling = {a: (t.value, t.source_id) for a, t in sections.items() if a != "tracks"}
    declaration = "adif-declaracion-red-2026-mapas"
    assert signalling == {
        "proteccion_tren": ("asfa", declaration),
        "bloqueo": ("bau", declaration),
        "mando": ("ctc", declaration),
    }
    assert all((t.from_node, t.to_node) == ("linares-baeza", "granada") for t in sections.values())


def test_no_train_runs_the_whole_line(
    feed: GtfsFeed, lbmg_spec: NetworkSpec, lbmg: BuiltNetwork
) -> None:
    """Los trenes de Granada a Almería dejan la línea en la bifurcación, sin entrar en Moreda; los
    de Linares-Baeza a Almería paran en Moreda y siguen hacia Guadix. Por el kilómetro que queda
    entre la estación y la bifurcación no pasa ningún tren de los horarios."""
    nodes = {n.spec.id: LineNode(n.spec.id, n.km, n.lon, n.lat) for n in lbmg.nodes}
    segments = [LineSegment(s.id, s.km_from, s.km_to) for s in lbmg.segments]
    trips = select_trips_for_spec(feed, lbmg_spec)
    assert Counter(t.product for t in trips) == {"MD": 26, "ALVIA": 12}
    by_route: Counter[tuple[str, ...]] = Counter()
    kinds: Counter[str] = Counter()
    for trip in trips:
        route = route_for_trip(lbmg_spec, trip)
        calls = calls_for_trip(trip, feed, lbmg_spec, route=route)
        assert all(c.node_id or c.exit_node_ids for c in calls), trip.train_number
        passes, resolution = resolve_passes(calls, nodes, segments)
        assert resolution == "completa"
        crossed = tuple(p.segment_id for p in passes)
        assert crossed in (tuple(NORTH), tuple(SOUTH)), trip.train_number
        # solo los que paran en Moreda encajan con la regla de recorrido
        assert (route is not None) == (crossed == tuple(NORTH))
        by_route[crossed] += 1
        kinds.update(p.kind for p in passes)
    assert by_route == {tuple(NORTH): 4, tuple(SOUTH): 34}
    # publicados: los tres tramos de los 4 trenes de Linares-Baeza y los de los 3 Media Distancia
    # que paran en Iznalloz, entre Iznalloz y Granada
    assert kinds == {"publicado": 4 * 3 + 6, "estimado": 62}


def test_trains_to_almeria_that_stop_at_moreda_leave_through_the_station(
    feed: GtfsFeed, lbmg_spec: NetworkSpec
) -> None:
    by_moreda = [t for t in select_trips_for_spec(feed, lbmg_spec) if route_for_trip(lbmg_spec, t)]
    assert len(by_moreda) == 4 and {t.product for t in by_moreda} == {"MD"}
    for trip in by_moreda:
        route = route_for_trip(lbmg_spec, trip)
        calls = {c.stop_id: c for c in calls_for_trip(trip, feed, lbmg_spec, route=route)}
        assert calls["56100"].node_id == "moreda"
        assert calls["56200"].exit_node_ids == calls["56312"].exit_node_ids == ("moreda",)
    # sin la regla, Guadix es una salida por la bifurcación, como para los trenes de Granada
    general = lbmg_spec.stop_mappings["56200"]
    assert general.exits == ["bif-almeria"]
