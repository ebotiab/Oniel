"""La línea de alta velocidad Olmedo – Zamora – Ourense: el camino de Madrid a Galicia, que sale
de la línea de Valladolid en la bifurcación Medina."""

from __future__ import annotations

from collections import Counter

import pytest
from conftest import (
    DATA_DIR,
    LAV_ALICANTE_SPEC,
    LAV_OURENSE_SPEC,
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

LINE = "lav-olmedo-ourense"
HIGH_SPEED = "osm-relation-4777980"
CONVENTIONAL = "osm-relation-11109438"
WIKIPEDIA = "wikipedia-lav-olmedo-zamora-galicia"
MAP = "adif-declaracion-red-2026-mapas"
CHAMARTIN, SEGOVIA = "17000", "08004"
MEDINA, ZAMORA, SANABRIA, GUDINA, OURENSE = "08240", "30200", "08247", "08251", "22100"
SALAMANCA = "30100"
ALL_SEGMENTS = [
    "bif-medina:medina-del-campo-av",
    "medina-del-campo-av:toro-av",
    "toro-av:coreses",
    "coreses:zamora",
    "zamora:bif-los-conforcos",
    "bif-los-conforcos:tabara",
    "tabara:sanabria-av",
    "sanabria-av:pedralba",
    "pedralba:vilavella",
    "vilavella:a-gudina-porta-de-galicia",
    "a-gudina-porta-de-galicia:meaman",
    "meaman:taboadela",
    "taboadela:ourense",
]
SINGLE_TRACK = {
    "medina-del-campo-av:toro-av",
    "toro-av:coreses",
    "zamora:bif-los-conforcos",
    "pedralba:vilavella",
    "taboadela:ourense",
}


@pytest.fixture(scope="module")
def spec() -> NetworkSpec:
    return load_network_spec(LAV_OURENSE_SPEC)


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


def test_the_geometry_joins_two_relations_without_gaps(line: BuiltNetwork) -> None:
    """La relación de la alta velocidad no trae la salida de Zamora ni la llegada a Ourense, que
    van por vías de la línea convencional: esos dos trechos salen de la relación de esa línea, y
    los cuatro empalmes son nodos de OSM que están en las dos."""
    coords = line.line.polyline.coords
    assert haversine_km(coords[0], (-4.6802476, 41.2731733)) < 0.01
    assert haversine_km(coords[-1], (-7.872551, 42.350692)) < 0.1
    assert [p.source_id for p in line.line.part_spans] == [
        HIGH_SPEED,
        CONVENTIONAL,
        HIGH_SPEED,
        CONVENTIONAL,
    ]
    assert not line.line.gaps_km
    assert line.line.joins_km == [] or max(line.line.joins_km) < 0.001
    borrowed = [p.km_to - p.km_from for p in line.line.part_spans if p.source_id == CONVENTIONAL]
    assert borrowed == [pytest.approx(2.4, abs=0.1), pytest.approx(14.7, abs=0.1)]
    # 328,3 km medidos frente a los 328,649 que hay del PK 133,884 al 462,533
    assert line.line.polyline.length_km == pytest.approx(462.533 - 133.884, abs=0.5)
    # no sigue hacia Santiago, aunque la relación sí
    assert max(c[1] for c in coords) < 42.36


def test_nodes_stations_and_what_hangs_from_them(line: BuiltNetwork) -> None:
    assert [n.spec.id for n in line.nodes] == [
        "bif-medina",
        "medina-del-campo-av",
        "toro-av",
        "coreses",
        "zamora",
        "bif-los-conforcos",
        "tabara",
        "sanabria-av",
        "pedralba",
        "vilavella",
        "a-gudina-porta-de-galicia",
        "meaman",
        "taboadela",
        "ourense",
    ]
    assert {n.spec.id: n.spec.adif_code for n in line.nodes if n.spec.kind == "estacion"} == {
        "medina-del-campo-av": MEDINA,
        "zamora": ZAMORA,
        "sanabria-av": SANABRIA,
        "a-gudina-porta-de-galicia": GUDINA,
        "ourense": OURENSE,
    }
    assert {n.spec.id: n.spec.kind for n in line.nodes if n.spec.rank == "secundario"} == {
        "toro-av": "paet",
        "coreses": "pb",
        "bif-los-conforcos": "bifurcacion",
        "tabara": "paet",
        "pedralba": "bifurcacion",
        "vilavella": "pb",
        "meaman": "paet",
    }
    assert all(n.offset_m < 250 for n in line.nodes)
    # lo que sale de la línea y no está cargado: el enlace de Salamanca, las líneas convencionales
    # de Zamora y las dos convencionales que siguen desde Ourense; la de Santiago ya está cargada
    assert {c.id: c.node_id for c in line.spec.connections} == {
        "enlace-medina-salamanca": "medina-del-campo-av",
        "conv-zamora-medina-del-campo": "zamora",
        "conv-zamora-ourense": "zamora",
        "conv-ourense-vigo": "ourense",
        "conv-ourense-monforte": "ourense",
    }


def test_it_leaves_the_line_to_valladolid_at_the_same_junction(line: BuiltNetwork) -> None:
    """La bifurcación Medina la define la línea de Valladolid: esta la incorpora sin moverla, la
    conexión a trazos desaparece de allí y las dos líneas se nombran una a otra."""
    assert {n.spec.id for n in line.nodes if n.spec.shared} == {"bif-medina"}
    valladolid = load_network_spec(LAV_VALLADOLID_SPEC)
    theirs = build_network(valladolid, DATA_DIR).node("bif-medina")
    ours = line.node("bif-medina")
    assert not theirs.spec.shared
    assert haversine_km((ours.lon, ours.lat), (theirs.lon, theirs.lat)) < 0.001
    assert ours.km == 0.0
    assert ours.spec.reference_pk_km == theirs.spec.reference_pk_km == 133.884
    assert all(c.node_id != "bif-medina" for c in valladolid.connections)
    # desde la línea de Valladolid, las cinco estaciones de esta son salidas por la bifurcación
    # que siguen por esta línea, ya sin kilómetros de vía declarados a mano
    for stop_id in (MEDINA, ZAMORA, SANABRIA, GUDINA, OURENSE):
        mapping = valladolid.stop_mappings[stop_id]
        assert mapping.exits == ["bif-medina"] and mapping.track_km is None
        assert [(v.line, v.node) for v in mapping.via] == [(LINE, "bif-medina")]
    # y desde esta, Madrid y Segovia siguen por la de Valladolid
    for stop_id in (CHAMARTIN, SEGOVIA):
        mapping = line.spec.stop_mappings[stop_id]
        assert mapping.exits == ["bif-medina"]
        assert [(v.line, v.node) for v in mapping.via] == [("lav-madrid-valladolid", "bif-medina")]
    # los trenes de Ourense a Alicante: desde Levante, Zamora y Ourense se alcanzan por Chamartín,
    # la línea de Valladolid y esta
    for stop_id in (ZAMORA, OURENSE):
        valencia = load_network_spec(LAV_VALENCIA_SPEC).stop_mappings[stop_id]
        assert [(v.line, v.node) for v in valencia.via] == [
            ("lav-madrid-valladolid", "madrid-chamartin"),
            (LINE, "bif-medina"),
        ]
        alicante = load_network_spec(LAV_ALICANTE_SPEC).stop_mappings[stop_id]
        assert [(v.line, v.node) for v in alicante.via][-2:] == [
            ("lav-madrid-valladolid", "madrid-chamartin"),
            (LINE, "bif-medina"),
        ]


def test_kilometre_points_continue_those_of_the_line_to_valladolid(line: BuiltNetwork) -> None:
    """La numeración sigue la de la línea de Madrid a Valladolid: el origen es el PK 133,884 de la
    bifurcación, y los PK de las cinco estaciones quedan a menos de medio kilómetro del trazado."""
    origin = line.spec.line.pk_origin_km
    assert origin == 133.884
    assert {n.spec.id: n.spec.reference_pk_km for n in line.nodes if n.spec.kind == "estacion"} == {
        "medina-del-campo-av": 155.458,
        "zamora": 232.463,
        "sanabria-av": 333.588,
        "a-gudina-porta-de-galicia": 382.613,
        "ourense": 462.533,
    }
    for node in line.nodes:
        assert node.spec.reference_pk_km is not None
        tolerance = 1.1 if node.spec.id == "vilavella" else 0.5
        assert node.km + origin == pytest.approx(node.spec.reference_pk_km, abs=tolerance)


def test_single_track_where_the_sources_say_so(line: BuiltNetwork) -> None:
    """Cuatro trechos de vía única: de Medina del Campo AV a Coreses, la salida de Zamora, de
    Pedralba a Vilavella y la llegada a Ourense, que además es de ancho mixto."""
    assert [s.id.removeprefix(f"{LINE}:") for s in line.segments] == ALL_SEGMENTS
    assert {s.id.removeprefix(f"{LINE}:") for s in line.segments if s.tracks == 1} == SINGLE_TRACK
    sources = {
        s.id.removeprefix(f"{LINE}:"): s.attributes["tracks"].source_id
        for s in line.segments
        if s.tracks == 1
    }
    assert sources == {
        "medina-del-campo-av:toro-av": WIKIPEDIA,
        "toro-av:coreses": WIKIPEDIA,
        "zamora:bif-los-conforcos": WIKIPEDIA,
        "pedralba:vilavella": HIGH_SPEED,
        "taboadela:ourense": CONVENTIONAL,
    }
    mixed = [s for s in line.segments if "gauge" in s.attributes]
    assert [s.id.removeprefix(f"{LINE}:") for s in mixed] == ["taboadela:ourense"]
    assert mixed[0].attributes["gauge"].value == "mixto"
    assert sum(s.length_km for s in line.segments if s.tracks == 1) == pytest.approx(125.8, abs=0.5)
    # las vías de OSM traen la velocidad en todos los tramos
    assert [s.max_speed_kmh for s in line.segments] == [300] * 11 + [260, 190]
    assert all(s.typical_speed_kmh for s in line.segments)
    assert line.segments[-1].typical_speed_kmh == 90


def test_signalling_as_the_map_draws_it(line: BuiltNetwork) -> None:
    """Mapa 4 de la Declaración sobre la Red: BCA y «ERTMS N2» con ASFA hasta Taboadela; de allí a
    Ourense, por la vía convencional con tercer carril, el trazo de «BAU ctc»."""
    for segment in line.segments:
        last = segment.id.endswith("taboadela:ourense")
        assert segment.attributes["proteccion_tren"].value == "ertms_n2_asfa"
        assert segment.attributes["bloqueo"].value == ("bau" if last else "bca")
        assert segment.attributes["mando"].value == ("ctc" if last else "sin_dato_publicado")
        for key in ("proteccion_tren", "bloqueo", "mando"):
            assert segment.attributes[key].source_id == MAP
    # el bloqueo de vía única cae en un tramo de vía única
    assert line.segments[-1].tracks == 1


def test_sources_and_operators_are_registered(spec: NetworkSpec) -> None:
    sources = {s.id: s for s in load_sources(SOURCES)}
    for source_id in (HIGH_SPEED, CONVENTIONAL):
        geometry = sources[source_id]
        assert geometry.license == "ODbL 1.0" and geometry.retrieved_on == "2026-11-14"
        assert geometry.file is not None and (DATA_DIR / geometry.file).exists()
    assert spec.line.geometry_source.source_id == HIGH_SPEED
    assert spec.line.verification_source_id == WIKIPEDIA
    assert sources[WIKIPEDIA].retrieved_on == "2026-11-14"
    for section in spec.attribute_sections:
        assert section.source_id in sources
    # solo Renfe: ni el fichero de Ouigo ni la página de destinos de Iryo nombran sus estaciones
    operators = {o.id: o for o in spec.operators if o.role == "operador"}
    assert set(operators) == {"renfe"}
    assert operators["renfe"].timetable == "cargado"
    assert "Zamora" not in str(sources["iryo-web"].coverage)
    assert all(o.source_id in sources for o in spec.operators)
    assert spec.line.zone == "galicia"
    assert (DATA_DIR / "raw/osm/instalaciones_olmedo_zamora_ourense_2026-11-14.json").exists()
    assert (DATA_DIR / "raw/interrupciones/consultas_2026-11-14_olmedo_ourense.json").exists()


def test_the_filter_takes_the_trains_of_the_line_and_leaves_the_conventional_ones(
    feed: GtfsFeed, ouigo_feed: GtfsFeed, spec: NetworkSpec
) -> None:
    """Entran 210 viajes de Renfe y ninguno de Ouigo. Zamora y Ourense no sirven de filtro: en
    ellas paran también los trenes de las líneas convencionales."""
    assert spec.corridor_filter.any_of_stop_ids == [MEDINA, SANABRIA, GUDINA]
    trips = select_trips_for_spec(feed, spec)
    assert len(trips) == 210
    assert Counter(t.product for t in trips) == {"AVE": 106, "Alvia": 58, "AVLO": 46}
    selected = {t.trip_id for t in trips}
    # todo tren que para en una estación propia de la línea, o que va de Zamora a Ourense sin
    # paradas, está dentro
    for trip in feed.trips.values():
        own = set(_stops(trip)) & {MEDINA, SANABRIA, GUDINA}
        if own or (ZAMORA, OURENSE) in _pairs(trip):
            assert trip.trip_id in selected, trip.train_number
    # quedan fuera los que paran en Zamora o en Ourense sin venir de Madrid por esta línea: los
    # regionales de la línea convencional y los trenes de Galicia. Ninguno para en Chamartín
    left_out = [
        t
        for t in feed.trips.values()
        if {ZAMORA, OURENSE} & set(_stops(t)) and t.trip_id not in selected
    ]
    assert left_out
    assert all(CHAMARTIN not in _stops(t) for t in left_out)
    assert not {t.product for t in left_out} & {"AVE", "AVLO"}
    assert select_trips_for_spec(ouigo_feed, spec) == []


def test_trains_that_do_not_stop_in_its_own_stations_enter_through_the_rules(
    feed: GtfsFeed, spec: NetworkSpec
) -> None:
    rules = {r.id: r.consecutive_stop_ids for r in spec.route_overrides}
    assert rules == {
        "madrid-zamora-sin-parada": [CHAMARTIN, ZAMORA],
        "madrid-ourense-sin-parada": [CHAMARTIN, OURENSE],
    }
    trips = select_trips_for_spec(feed, spec)
    matched = Counter(
        route.override.id for trip in trips if (route := route_for_trip(spec, trip)) is not None
    )
    assert matched == {"madrid-zamora-sin-parada": 115, "madrid-ourense-sin-parada": 6}
    # los mismos viajes que la línea de Valladolid recoge con sus reglas del mismo nombre
    valladolid = load_network_spec(LAV_VALLADOLID_SPEC)
    theirs = Counter(
        route.override.id
        for trip in select_trips_for_spec(feed, valladolid)
        if (route := route_for_trip(valladolid, trip)) is not None
    )
    assert {k: theirs[k] for k in matched} == dict(matched)
    # todo tren de esta línea que llega de Madrid o de Segovia está también en la de Valladolid
    in_valladolid = {t.trip_id for t in select_trips_for_spec(feed, valladolid)}
    assert {t.trip_id for t in trips} <= in_valladolid


def test_each_train_counts_on_the_segments_it_runs(feed: GtfsFeed, line: BuiltNetwork) -> None:
    """Los trenes de Galicia recorren la línea entera, paren donde paren; los de Salamanca, solo
    el primer tramo, hasta Medina del Campo AV."""
    trips = select_trips_for_spec(feed, line.spec)

    def having(pair: tuple[str, str]) -> list[GtfsTrip]:
        return [t for t in trips if pair in _pairs(t)]

    whole = having((CHAMARTIN, ZAMORA))[:5] + having((CHAMARTIN, OURENSE))[:3]
    whole += having((SANABRIA, GUDINA))[:5]
    assert len(whole) == 13
    for trip in whole:
        assert _short(_passes(trip, feed, line)) == ALL_SEGMENTS
    salamanca = having((MEDINA, SALAMANCA))
    assert len(salamanca) == 50
    for trip in salamanca:
        assert _short(_passes(trip, feed, line)) == ALL_SEGMENTS[:1]
    # nadie más: todo viaje de la línea va a Ourense o a Salamanca
    assert all(OURENSE in _stops(t) or SALAMANCA in _stops(t) for t in trips)


def test_stops_beyond_the_line_leave_by_the_right_node(spec: NetworkSpec) -> None:
    """Madrid y Segovia, por la bifurcación Medina; Salamanca, por Medina del Campo AV, donde sale
    su enlace; Santiago, A Coruña, Vigo y Lugo, por Ourense. Santiago sigue por la línea de alta
    velocidad de Ourense a Santiago, y A Coruña, Vilagarcía, Pontevedra y Vigo, además, por la
    de A Coruña a Vigo; la línea de Lugo no está cargada."""
    assert spec.stop_mappings[SALAMANCA].exits == ["medina-del-campo-av"]
    assert not spec.stop_mappings[SALAMANCA].via
    for stop_id in ("20300", "20305", "20309"):
        mapping = spec.stop_mappings[stop_id]
        assert mapping.exits == ["ourense"] and not mapping.via
    santiago = spec.stop_mappings["31400"]
    assert santiago.exits == ["ourense"]
    assert [(v.line, v.node) for v in santiago.via] == [("lav-ourense-santiago", "ourense")]
    for stop_id in ("31412", "08223", "23004", "23008"):
        mapping = spec.stop_mappings[stop_id]
        assert mapping.exits == ["ourense"]
        assert [(v.line, v.node) for v in mapping.via] == [
            ("lav-ourense-santiago", "ourense"),
            ("eje-atlantico", "santiago"),
        ]
    assert {s: m.node for s, m in spec.stop_mappings.items() if m.node} == {
        MEDINA: "medina-del-campo-av",
        ZAMORA: "zamora",
        SANABRIA: "sanabria-av",
        GUDINA: "a-gudina-porta-de-galicia",
        OURENSE: "ourense",
    }
