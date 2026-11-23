"""La línea León – Oviedo – Gijón por la variante de Pajares: la línea 130 de Adif de León a la
bifurcación Pajares y de Pola de Lena a Gijón, y entre las dos, la variante (984 en las vías de
OSM). La vía antigua del puerto de Pajares no se carga: sus trenes dejan la línea y vuelven."""

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
    LEON_GIJON_SPEC,
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
from oniel.validate import expected_pk_km, loaded_line

LINE = "leon-oviedo-gijon"
LINE_130 = "osm-relation-18343947"
VARIANT = "osm-relation-5549743"
WIKIPEDIA = "wikipedia-variante-de-pajares"
MAP = "adif-declaracion-red-2026-mapas"
LEON, LENA, MIERES, OVIEDO, GIJON, AVILES = "15100", "15122", "15203", "15211", "15410", "16403"
#: Paradas de la vía antigua del puerto de Pajares, de La Robla a Campomanes.
PASS_STOPS = ["15106", "15108", "15109", "15112", "15113", "15116", "15118", "15120"]
ALL_SEGMENTS = [
    "leon:bif-pajares",
    "bif-pajares:la-robla-av",
    "la-robla-av:campomanes-av",
    "campomanes-av:pola-de-lena",
    "pola-de-lena:ujo",
    "ujo:mieres-puente",
    "mieres-puente:llamaquique",
    "llamaquique:oviedo",
    "oviedo:villabona-de-asturias",
    "villabona-de-asturias:calzada-de-asturias",
    "calzada-de-asturias:gijon-sanz-crespo",
]
VARIANT_SEGMENTS = ALL_SEGMENTS[1:4]


@pytest.fixture(scope="module")
def spec() -> NetworkSpec:
    return load_network_spec(LEON_GIJON_SPEC)


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


def test_the_geometry_is_the_old_line_with_the_variant_in_the_middle(line: BuiltNetwork) -> None:
    """Tres partes sin saltos: la línea 130 hasta la bifurcación Pajares, la variante hasta Pola
    de Lena y otra vez la 130 hasta Gijón."""
    coords = line.line.polyline.coords
    assert haversine_km(coords[0], (-5.5819405, 42.5951002)) < 0.1
    assert haversine_km(coords[-1], (-5.6762251, 43.5375667)) < 0.05
    assert [p.source_id for p in line.line.part_spans] == [LINE_130, VARIANT, LINE_130]
    assert not line.line.gaps_km and not line.line.joins_km
    # la variante empieza en el nodo de la bifurcación y mide lo que dice Wikipedia: 49,7 km
    variant = line.line.part_spans[1]
    assert variant.km_from == pytest.approx(line.node("bif-pajares").km)
    assert variant.km_to - variant.km_from == pytest.approx(49.7, abs=0.2)
    assert line.line.polyline.length_km == pytest.approx(132.6, abs=0.1)


def test_nodes_stations_and_junctions(line: BuiltNetwork) -> None:
    assert [n.spec.id for n in line.nodes] == [
        "leon",
        "bif-pajares",
        "la-robla-av",
        "campomanes-av",
        "pola-de-lena",
        "ujo",
        "mieres-puente",
        "llamaquique",
        "oviedo",
        "villabona-de-asturias",
        "calzada-de-asturias",
        "gijon-sanz-crespo",
    ]
    assert {n.spec.id: n.spec.adif_code for n in line.nodes if n.spec.kind == "estacion"} == {
        "leon": LEON,
        "pola-de-lena": LENA,
        "ujo": "15200",
        "mieres-puente": MIERES,
        "llamaquique": "15218",
        "oviedo": OVIEDO,
        "villabona-de-asturias": None,
        "calzada-de-asturias": "15401",
        "gijon-sanz-crespo": GIJON,
    }
    assert {n.spec.id: n.spec.kind for n in line.nodes if n.spec.kind != "estacion"} == {
        "bif-pajares": "bifurcacion",
        "la-robla-av": "paet",
        "campomanes-av": "paet",
    }
    assert {n.spec.id for n in line.nodes if n.spec.rank == "secundario"} == {
        "la-robla-av",
        "ujo",
        "llamaquique",
        "calzada-de-asturias",
    }
    # el puerto de Pajares y el ramal de Avilés quedan a trazos
    assert {c.id: c.node_id for c in line.spec.connections} == {
        "conv-rampa-de-pajares": "bif-pajares",
        "conv-villabona-san-juan-de-nieva": "villabona-de-asturias",
    }
    assert all(n.offset_m < 100 for n in line.nodes)


def test_it_starts_at_the_station_the_high_speed_line_ends_at(line: BuiltNetwork) -> None:
    """León lo define la línea de Valladolid, que va antes en la importación: esta lo incorpora
    sin moverlo, y aquella ya no sale a trazos hacia Asturias."""
    assert {n.spec.id for n in line.nodes if n.spec.shared} == {"leon"}
    south = load_network_spec(LAV_LEON_SPEC)
    theirs = next(n for n in south.nodes if n.id == "leon")
    ours = line.node("leon").spec
    assert not theirs.shared and ours.position == theirs.position
    assert ours.adif_code == theirs.adif_code == LEON
    assert all("asturias" not in c.id for c in south.connections)
    # hacia el sur, las paradas llevan el camino por las líneas ya cargadas
    spec = line.spec
    for stop_id in ("14100", "10600"):
        assert spec.stop_mappings[stop_id].exits == ["leon"]
        assert [(v.line, v.node) for v in spec.stop_mappings[stop_id].via] == [
            ("lav-valladolid-leon", "leon")
        ]
    assert [(v.line, v.node) for v in spec.stop_mappings["17000"].via] == [
        ("lav-valladolid-leon", "leon"),
        ("lav-madrid-valladolid", "valladolid-campo-grande"),
    ]
    assert [(v.line, v.node) for v in spec.stop_mappings["60911"].via] == [
        ("lav-valladolid-leon", "leon"),
        ("lav-madrid-valladolid", "valladolid-campo-grande"),
        ("lav-madrid-valencia", "madrid-chamartin"),
        ("lav-albacete-alicante", "bif-albacete"),
    ]
    # y al revés: las estaciones de Asturias, desde las líneas por las que llegan sus trenes
    for stop_id in (LENA, MIERES, OVIEDO, GIJON):
        assert [(v.line, v.node) for v in south.stop_mappings[stop_id].via] == [(LINE, "leon")]
        for path in (LAV_VALLADOLID_SPEC, LAV_VALENCIA_SPEC, LAV_ALICANTE_SPEC, LAV_MURCIA_SPEC):
            via = load_network_spec(path).stop_mappings[stop_id].via
            assert [(v.line, v.node) for v in via][-2:] == [
                ("lav-valladolid-leon", "valladolid-campo-grande"),
                (LINE, "leon"),
            ]
    # Avilés no es un nodo de esta línea: sigue como salida sin camino
    assert south.stop_mappings[AVILES].exits == ["leon"] and not south.stop_mappings[AVILES].via


def test_kilometre_points_restart_at_the_variant_and_at_pola_de_lena(line: BuiltNetwork) -> None:
    """La variante cuenta desde su inicio, 0,4 km después de la bifurcación; desde Pola de Lena
    vale la numeración de la línea 130, que cuenta desde León por el puerto y por trazados
    antiguos: el trazado actual se queda hasta 1,4 km por detrás."""
    assert line.spec.line.pk_origin_km == 0.0
    assert [(r.node, r.pk_km) for r in line.spec.line.pk_restarts] == [
        ("bif-pajares", -0.4),
        ("pola-de-lena", 108.119),
    ]
    assert {n.spec.id: n.spec.reference_pk_km for n in line.nodes if n.spec.reference_pk_km} == {
        "la-robla-av": 2.849,
        "campomanes-av": 43.388,
        "ujo": 115.189,
        "mieres-puente": 120.275,
        "llamaquique": 138.172,
        "oviedo": 139.138,
        "villabona-de-asturias": 151.917,
        "calzada-de-asturias": 168.759,
        "gijon-sanz-crespo": 170.773,
    }
    for node_id in ("la-robla-av", "campomanes-av"):
        node = line.node(node_id)
        assert expected_pk_km(line, node.km) == pytest.approx(node.spec.reference_pk_km, abs=0.05)
    for node in line.nodes[5:]:
        delta = expected_pk_km(line, node.km) - (node.spec.reference_pk_km or 0.0)
        assert -1.45 < delta < -0.4, node.spec.id


def test_double_track_and_speeds(line: BuiltNetwork) -> None:
    assert [s.id.removeprefix(f"{LINE}:") for s in line.segments] == ALL_SEGMENTS
    assert {s.tracks for s in line.segments} == {2}
    assert not [s for s in line.spec.attribute_sections if s.attribute == "tracks"]
    # el primer tramo lleva la velocidad declarada: el desvío de la bifurcación trae 250 km/h
    assert [s.max_speed_kmh for s in line.segments] == [
        160,
        160,
        200,
        160,
        130,
        130,
        130,
        70,
        140,
        140,
        100,
    ]
    declared = [s for s in line.spec.attribute_sections if s.attribute == "max_speed_kmh"]
    assert [(s.from_node, s.to_node, s.value) for s in declared] == [("leon", "bif-pajares", 160)]
    assert sum(s.length_km for s in line.segments) == pytest.approx(
        line.line.polyline.length_km, abs=0.1
    )


def test_gauge_and_electrification_change_on_the_variant(line: BuiltNetwork) -> None:
    """La línea es de ancho ibérico a 3 kV. En la variante hay tercer carril de la bifurcación a
    Campomanes AV, y 25 kV de la bifurcación a Pola de Lena, como dibuja el mapa 4."""
    assert line.spec.line.gauge_mm == 1668 and line.spec.line.electrification == "3 kV CC"
    by_id = {s.id.removeprefix(f"{LINE}:"): s for s in line.segments}
    gauge = {k: s.attributes["gauge"].value for k, s in by_id.items() if "gauge" in s.attributes}
    assert gauge == dict.fromkeys(VARIANT_SEGMENTS[:2], "mixto")
    power = {
        k: s.attributes["electrification"].value
        for k, s in by_id.items()
        if "electrification" in s.attributes
    }
    assert power == dict.fromkeys(VARIANT_SEGMENTS, "25kv_ca")
    for key in VARIANT_SEGMENTS[:2]:
        assert by_id[key].attributes["gauge"].source_id == MAP


def test_signalling_as_the_map_draws_it(line: BuiltNetwork) -> None:
    """Mapa 4: BAB con CTC en toda la línea; ASFA en los dos trechos de la línea 130 y el símbolo
    de «ERTMS N2» con el de ASFA a lo largo de la variante."""
    for segment in line.segments:
        key = segment.id.removeprefix(f"{LINE}:")
        expected = "ertms_n2_asfa" if key in VARIANT_SEGMENTS else "asfa"
        assert segment.attributes["proteccion_tren"].value == expected, key
        assert segment.attributes["bloqueo"].value == "bab"
        assert segment.attributes["mando"].value == "ctc"
        for attribute in ("proteccion_tren", "bloqueo", "mando"):
            assert segment.attributes[attribute].source_id == MAP


def test_sources_and_operators_are_registered(spec: NetworkSpec) -> None:
    sources = {s.id: s for s in load_sources(SOURCES)}
    for part in spec.line.geometry_source.parts:
        source = sources[part.source_id]
        assert source.license == "ODbL 1.0" and source.retrieved_on == "2026-11-15"
        assert source.file == part.file and (DATA_DIR / part.file).exists()
    stations = sources["osm-instalaciones-leon-gijon"]
    assert stations.file and (DATA_DIR / stations.file).exists()
    assert spec.line.verification_source_id == WIKIPEDIA
    assert {WIKIPEDIA, "wikipedia-linea-130"} <= set(sources)
    for section in spec.attribute_sections:
        assert section.source_id in sources
    operators = {o.id: o for o in spec.operators if o.role == "operador"}
    assert set(operators) == {"renfe"}
    assert all(o.source_id in sources for o in spec.operators)
    assert spec.line.zone == "cantabrico"
    assert (DATA_DIR / "raw" / "interrupciones" / "consultas_2026-11-15_leon_gijon.json").exists()


def test_the_filter_takes_every_train_with_two_stops_on_the_line(
    feed: GtfsFeed, ouigo_feed: GtfsFeed, spec: NetworkSpec, line: BuiltNetwork
) -> None:
    """Entran 141 viajes de Renfe y ninguno de Ouigo. Quedan fuera los de vía estrecha, que de
    esta línea solo tocan Oviedo."""
    assert spec.corridor_filter.min_node_stops == 2
    assert not spec.corridor_filter.exclude_stop_ids and not spec.route_overrides
    trips = select_trips_for_spec(feed, spec)
    assert len(trips) == 141
    assert Counter(t.product for t in trips) == {
        "Alvia": 50,
        "AVE": 39,
        "Regional": 25,
        "AVLO": 16,
        "Media Distancia": 11,
    }
    selected = {t.trip_id for t in trips}
    stations = {n.spec.adif_code for n in line.nodes if n.spec.adif_code}
    left_out = [t for t in feed.trips.values() if OVIEDO in _stops(t) and t.trip_id not in selected]
    assert len(left_out) == 14
    for trip in left_out:
        assert trip.product == "Regional" and set(_stops(trip)) & stations == {OVIEDO}
    assert select_trips_for_spec(ouigo_feed, spec) == []


def test_regional_trains_leave_the_line_to_climb_the_pass(
    feed: GtfsFeed, spec: NetworkSpec, line: BuiltNetwork
) -> None:
    """Los regionales van por la vía antigua del puerto: dejan la línea en la bifurcación Pajares
    y vuelven en Pola de Lena, así que no cuentan en los tres tramos de la variante."""
    for stop_id in PASS_STOPS:
        mapping = spec.stop_mappings[stop_id]
        assert mapping.exits == ["bif-pajares", "pola-de-lena"] and mapping.aside
    trips = select_trips_for_spec(feed, spec)
    regional = [t for t in trips if t.product == "Regional"]
    assert len(regional) == 25
    for trip in regional:
        assert set(PASS_STOPS) <= set(_stops(trip))
        assert _short(_passes(trip, feed, line)) == ALL_SEGMENTS[:1] + ALL_SEGMENTS[4:]
    for trip in trips:
        if trip.product != "Regional":
            assert not set(PASS_STOPS) & set(_stops(trip))


def test_each_train_counts_on_the_segments_it_runs(feed: GtfsFeed, line: BuiltNetwork) -> None:
    """Los de Gijón recorren la línea entera; los de Avilés la dejan en Villabona de Asturias."""
    trips = select_trips_for_spec(feed, line.spec)
    assert line.spec.stop_mappings[AVILES].exits == ["villabona-de-asturias"]
    per_segment: Counter[str] = Counter()
    for trip in trips:
        passes = _short(_passes(trip, feed, line))
        per_segment.update(passes)
        if AVILES in _stops(trip):
            assert passes == ALL_SEGMENTS[:9]
        elif trip.product != "Regional":
            assert passes == ALL_SEGMENTS
    assert sum(1 for t in trips if AVILES in _stops(t)) == 20
    assert [per_segment[s] for s in ALL_SEGMENTS] == [
        141,
        116,
        116,
        116,
        141,
        141,
        141,
        141,
        141,
        121,
        121,
    ]
