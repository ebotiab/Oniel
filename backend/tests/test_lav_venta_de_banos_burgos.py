"""La línea de alta velocidad Venta de Baños – Burgos (080 de Adif): sale de la de León en la
bifurcación Venta de Baños y acaba en Burgos-Rosa Manzano, donde los trenes del País Vasco pasan a
la línea convencional."""

from __future__ import annotations

from collections import Counter

import pytest
from conftest import (
    DATA_DIR,
    LAV_ALICANTE_SPEC,
    LAV_BURGOS_SPEC,
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

LINE = "lav-venta-de-banos-burgos"
RELATION = "osm-relation-4777557"
WIKIPEDIA = "wikipedia-lav-venta-de-banos-burgos-vitoria"
MAP = "adif-declaracion-red-2026-mapas"
VALLADOLID, PALENCIA, LEON, BURGOS, MIRANDA = "10600", "14100", "15100", "11014", "11200"
#: Paradas que delatan a un tren que va por la línea convencional (Venta de Baños, Villaquirán,
#: Briviesca) o que viene de Zaragoza por ella (los Intercity de Zaragoza a Valladolid).
EXCLUDED = {"04040", "11000", "11009", "11109"}
ALL_SEGMENTS = [
    "bif-venta-de-banos:bif-soto-de-cerrato",
    "bif-soto-de-cerrato:rio-arlanzon",
    "rio-arlanzon:estepar",
    "estepar:burgos-rosa-manzano",
]


@pytest.fixture(scope="module")
def spec() -> NetworkSpec:
    return load_network_spec(LAV_BURGOS_SPEC)


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


def test_the_geometry_follows_the_relation_to_burgos(line: BuiltNetwork) -> None:
    """Un solo trozo de la relación de Madrid a Burgos, de la bifurcación Venta de Baños al
    desvío que hay al norte de la estación de Burgos, sin saltos."""
    coords = line.line.polyline.coords
    assert haversine_km(coords[0], (-4.4877585, 41.9242256)) < 0.01
    assert haversine_km(coords[-1], (-3.6609406, 42.3723919)) < 0.01
    assert [p.source_id for p in line.line.part_spans] == [RELATION]
    assert not line.line.gaps_km and not line.line.joins_km
    # 86,3 km hasta la estación frente a los 86,463 de la fuente; el trazado sigue 0,46 km más,
    # hasta el desvío de la salida norte
    assert line.node("burgos-rosa-manzano").km == pytest.approx(86.463, abs=0.25)
    assert line.line.polyline.length_km - line.node("burgos-rosa-manzano").km == pytest.approx(
        0.46, abs=0.05
    )
    assert line.spec.line.reference_length_km == 86.463


def test_nodes_station_junctions_and_passing_loops(line: BuiltNetwork) -> None:
    assert [n.spec.id for n in line.nodes] == [
        "bif-venta-de-banos",
        "bif-soto-de-cerrato",
        "rio-arlanzon",
        "estepar",
        "burgos-rosa-manzano",
    ]
    assert {n.spec.id: n.spec.kind for n in line.nodes} == {
        "bif-venta-de-banos": "bifurcacion",
        "bif-soto-de-cerrato": "bifurcacion",
        "rio-arlanzon": "paet",
        "estepar": "paet",
        "burgos-rosa-manzano": "estacion",
    }
    assert line.node("burgos-rosa-manzano").spec.adif_code == BURGOS
    assert {n.spec.id for n in line.nodes if n.spec.rank == "secundario"} == {
        "bif-soto-de-cerrato",
        "rio-arlanzon",
        "estepar",
    }
    assert {c.id: c.node_id for c in line.spec.connections} == {
        "ramal-soto-de-cerrato-cerrato": "bif-soto-de-cerrato",
        "conv-burgos-miranda-vitoria": "burgos-rosa-manzano",
    }
    assert all(n.offset_m < 50 for n in line.nodes)


def test_it_starts_at_the_junction_the_leon_line_defines(line: BuiltNetwork) -> None:
    """La bifurcación Venta de Baños la define la línea de León, que va antes en la importación:
    esta la incorpora sin moverla, y la de León ya no sale a trazos hacia Burgos. El ramal de
    Soto de Cerrato acaba en la bifurcación Cerrato de aquella."""
    assert {n.spec.id for n in line.nodes if n.spec.shared} == {"bif-venta-de-banos"}
    leon = load_network_spec(LAV_LEON_SPEC)
    theirs = next(n for n in leon.nodes if n.id == "bif-venta-de-banos")
    ours = line.node("bif-venta-de-banos").spec
    assert not theirs.shared and ours.position == theirs.position
    assert all("burgos" not in c.id for c in leon.connections)
    cerrato = next(n for n in leon.nodes if n.id == "bif-cerrato").position
    ramal = next(c for c in line.spec.connections if c.id == "ramal-soto-de-cerrato-cerrato")
    assert ramal.sketch[-1] == (cerrato.lon, cerrato.lat)


def test_kilometre_points_continue_those_of_line_080(line: BuiltNetwork) -> None:
    """La numeración sigue la de la línea 080 desde Madrid: la bifurcación Venta de Baños es el
    PK 217,578 y Burgos-Rosa Manzano, el 304,041. Cada nodo queda a menos de 200 m."""
    origin = line.spec.line.pk_origin_km
    assert origin == 217.578
    assert {n.spec.id: n.spec.reference_pk_km for n in line.nodes} == {
        "bif-venta-de-banos": 217.578,
        "bif-soto-de-cerrato": 222.674,
        "rio-arlanzon": 257.565,
        "estepar": 282.378,
        "burgos-rosa-manzano": 304.041,
    }
    for node in line.nodes:
        assert node.spec.reference_pk_km is not None
        assert node.km + origin == pytest.approx(node.spec.reference_pk_km, abs=0.2)


def test_single_track_from_soto_de_cerrato_to_burgos(line: BuiltNetwork) -> None:
    """Vía doble solo en los primeros kilómetros: la tabla de la fuente la da hasta la
    bifurcación La Vega, 0,3 km después de Soto de Cerrato."""
    assert [s.id.removeprefix(f"{LINE}:") for s in line.segments] == ALL_SEGMENTS
    assert [s.tracks for s in line.segments] == [2, 1, 1, 1]
    assert line.spec.line.tracks == 1
    single = sum(s.length_km for s in line.segments if s.tracks == 1)
    assert single == pytest.approx(81.3, abs=0.5)
    (section,) = [a for a in line.spec.attribute_sections if a.attribute == "tracks"]
    assert section.value == 2 and section.source_id == WIKIPEDIA
    # las vías de OSM traen la velocidad en todos los tramos: 300 km/h, y 210 al llegar a Burgos
    assert [s.max_speed_kmh for s in line.segments] == [300, 300, 300, 300]
    assert [s.typical_speed_kmh for s in line.segments] == [300, 300, 300, 210]


def test_signalling_as_the_map_draws_it(line: BuiltNetwork) -> None:
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
    for name in (
        "estacion_burgos_rosa_manzano_2026-11-15.json",
        "ramal_soto_de_cerrato_2026-11-15.json",
    ):
        assert (DATA_DIR / "raw" / "osm" / name).exists()
    assert (
        sources["osm-ramal-soto-de-cerrato"].file == "raw/osm/ramal_soto_de_cerrato_2026-11-15.json"
    )
    assert spec.line.verification_source_id == WIKIPEDIA and WIKIPEDIA in sources
    for section in spec.attribute_sections:
        assert section.source_id in sources
    # solo Renfe: Ouigo no llega a Burgos
    operators = {o.id for o in spec.operators if o.role == "operador"}
    assert operators == {"renfe"}
    assert all(o.source_id in sources for o in spec.operators)
    assert spec.line.zone == "castilla-y-leon"
    assert spec.line.opened_on == "2022-07-22"


def test_the_filter_takes_the_high_speed_trains_to_burgos(
    feed: GtfsFeed, ouigo_feed: GtfsFeed, spec: NetworkSpec
) -> None:
    """Entran 130 viajes de Renfe y ninguno de Ouigo: los que paran en Burgos y en Valladolid o
    Palencia, salvo los que delatan la línea convencional."""
    f = spec.corridor_filter
    assert f.required_stop_ids == [BURGOS]
    assert set(f.any_of_stop_ids) == {VALLADOLID, PALENCIA}
    assert set(f.exclude_stop_ids) == EXCLUDED
    trips = select_trips_for_spec(feed, spec)
    assert len(trips) == 130
    assert Counter(t.product for t in trips) == {"Intercity": 48, "ALVIA": 38, "AVE": 25, "MD": 19}
    selected = {t.trip_id for t in trips}
    # todo tren que va de Valladolid o de Palencia a Burgos sin paradas está dentro, salvo los
    # que van por la convencional: los de Zaragoza a Valladolid y los de Madrid-Príncipe Pío a
    # Irún, que siguen a Briviesca
    direct = [
        t for t in feed.trips.values() if _pairs(t) & {(VALLADOLID, BURGOS), (PALENCIA, BURGOS)}
    ]
    for trip in direct:
        if not EXCLUDED & set(_stops(trip)):
            assert trip.trip_id in selected, trip.train_number
    left_out = [t for t in direct if t.trip_id not in selected]
    assert left_out and all(EXCLUDED & set(_stops(t)) for t in left_out)
    # de los que paran en alguna de esas, solo entran, por una regla, los Alvia de Barcelona, que
    # paran en Zaragoza y llegan de Palencia
    by_rule = [t for t in trips if EXCLUDED & set(_stops(t))]
    assert by_rule and all(
        set(_stops(t)) & EXCLUDED == {"04040"} and (PALENCIA, BURGOS) in _pairs(t) for t in by_rule
    )
    assert select_trips_for_spec(ouigo_feed, spec) == []


def test_the_rule_for_the_trains_from_palencia(feed: GtfsFeed, spec: NetworkSpec) -> None:
    """Los Alvia de León y Galicia a Barcelona y al País Vasco: entran por el ramal y se cuentan
    de Palencia a Miranda de Ebro. Son los mismos seis que la línea de León hace llegar desde
    Burgos por la bifurcación Cerrato."""
    (rule,) = spec.route_overrides
    assert rule.consecutive_stop_ids == [PALENCIA, BURGOS, MIRANDA]
    assert (rule.from_stop_id, rule.to_stop_id) == (PALENCIA, MIRANDA)
    ours = {
        t.trip_id for t in select_trips_for_spec(feed, spec) if route_for_trip(spec, t) is not None
    }
    leon = load_network_spec(LAV_LEON_SPEC)
    theirs = {
        t.trip_id
        for t in select_trips_for_spec(feed, leon)
        if (route := route_for_trip(leon, t)) and route.override.id == "burgos-palencia-leon"
    }
    assert ours == theirs and len(ours) == 6


def test_each_train_counts_on_the_segments_it_runs(feed: GtfsFeed, line: BuiltNetwork) -> None:
    """Los de Madrid y Valladolid recorren la línea entera; los que vienen de Palencia entran en
    la bifurcación Soto de Cerrato y no pasan por el primer tramo."""
    trips = select_trips_for_spec(feed, line.spec)
    from_valladolid = [t for t in trips if (VALLADOLID, BURGOS) in _pairs(t)]
    from_palencia = [t for t in trips if (PALENCIA, BURGOS) in _pairs(t)]
    assert len(from_valladolid) + len(from_palencia) == len(trips)
    for trip in from_valladolid[:12]:
        assert _short(_passes(trip, feed, line)) == ALL_SEGMENTS
    assert from_palencia
    for trip in from_palencia:
        assert _short(_passes(trip, feed, line)) == ALL_SEGMENTS[1:]


def test_stops_on_each_side_leave_by_the_right_node(spec: NetworkSpec) -> None:
    sm = spec.stop_mappings
    assert sm[BURGOS].node == "burgos-rosa-manzano"
    for stop_id in (MIRANDA, "11208", "11511", "11600", "13200", "81100"):
        assert sm[stop_id].exits == ["burgos-rosa-manzano"] and not sm[stop_id].via
    # hacia Valladolid y Madrid, por la bifurcación Venta de Baños y la línea de León
    assert [(v.line, v.node) for v in sm[VALLADOLID].via] == [
        ("lav-valladolid-leon", "bif-venta-de-banos")
    ]
    assert [(v.line, v.node) for v in sm["17000"].via] == [
        ("lav-valladolid-leon", "bif-venta-de-banos"),
        ("lav-madrid-valladolid", "valladolid-campo-grande"),
    ]
    # hacia Palencia y León, por el ramal, que entra en la línea de León por la bifurcación
    # Cerrato; las de Galicia, sin camino cargado
    for stop_id in (PALENCIA, LEON):
        assert sm[stop_id].exits == ["bif-soto-de-cerrato"]
        assert [(v.line, v.node) for v in sm[stop_id].via] == [
            ("lav-valladolid-leon", "bif-cerrato")
        ]
    for stop_id in ("20200", "22100", "31400", "08223"):
        assert sm[stop_id].exits == ["bif-soto-de-cerrato"] and not sm[stop_id].via
    # y al revés: Burgos, desde la línea de Madrid y desde las de Levante
    madrid = load_network_spec(LAV_VALLADOLID_SPEC)
    assert [(v.line, v.node) for v in madrid.stop_mappings[BURGOS].via] == [
        ("lav-valladolid-leon", "valladolid-campo-grande"),
        (LINE, "bif-venta-de-banos"),
    ]
    for path in (LAV_VALENCIA_SPEC, LAV_ALICANTE_SPEC, LAV_MURCIA_SPEC):
        via = load_network_spec(path).stop_mappings[BURGOS].via
        assert [(v.line, v.node) for v in via][-3:] == [
            ("lav-madrid-valladolid", "madrid-chamartin"),
            ("lav-valladolid-leon", "valladolid-campo-grande"),
            (LINE, "bif-venta-de-banos"),
        ]
