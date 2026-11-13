"""Quinta línea: la alta velocidad Madrid – Zaragoza – Barcelona (línea 050 de Adif), dibujada
por las estaciones de Zaragoza-Delicias y Lleida-Pirineus, con sus dos baipases cargados aparte
(``test_baipases.py``)."""

from __future__ import annotations

from collections import Counter

import pytest
from conftest import BCN_SPEC, BYPASS_LLEIDA_SPEC, BYPASS_ZARAGOZA_SPEC, DATA_DIR, SOURCES, SPEC

from oniel.geo import haversine_km
from oniel.gtfs.reader import GtfsFeed
from oniel.gtfs.trips import bypasses_of, calls_for_trip, route_for_trip, select_trips_for_spec
from oniel.network.build import BuiltNetwork, build_network
from oniel.network.spec import NetworkSpec, load_network_spec, load_sources
from oniel.sim.passes import resolve_passes
from oniel.validate import expected_pk_km, loaded_line

LINE = "lav-madrid-barcelona"
BYPASS_ZARAGOZA = "baipas-zaragoza:bif-moncasi:bif-canal-imperial"
BYPASS_LLEIDA = "baipas-lleida:bif-les-torres-de-sanui:bif-artesa-de-lleida"
#: Los tramos que entran y salen de cada estación: los que deja de recorrer el tren que no para.
THROUGH_ZARAGOZA = (
    "bif-moncasi:zaragoza-delicias",
    "zaragoza-delicias:bif-huesca",
    "bif-huesca:bif-canal-imperial",
)
THROUGH_LLEIDA = ("bif-les-torres-de-sanui:lleida-pirineus", "lleida-pirineus:bif-artesa-de-lleida")
RELATION = "osm-relation-11082425"
STATIONS = [
    "madrid-puerta-de-atocha",
    "guadalajara-yebes",
    "calatayud",
    "zaragoza-delicias",
    "lleida-pirineus",
    "camp-de-tarragona",
    "barcelona-sants",
]


@pytest.fixture(scope="module")
def bcn_spec() -> NetworkSpec:
    return load_network_spec(BCN_SPEC)


@pytest.fixture(scope="module")
def bcn(bcn_spec: NetworkSpec) -> BuiltNetwork:
    return build_network(bcn_spec, DATA_DIR)


@pytest.fixture(scope="module")
def bypasses() -> list[BuiltNetwork]:
    return [
        build_network(load_network_spec(path), DATA_DIR)
        for path in (BYPASS_ZARAGOZA_SPEC, BYPASS_LLEIDA_SPEC)
    ]


def _segments_of(
    feed: GtfsFeed, spec: NetworkSpec, net: BuiltNetwork, bypasses: list[BuiltNetwork]
) -> dict[tuple[str, ...], Counter[tuple[str, ...]]]:
    """Por secuencia de paradas, los tramos que recorre cada viaje: los de la línea, sin su
    prefijo, y detrás los de los baipases por los que va."""
    own = loaded_line(net)
    around = bypasses_of(own, [loaded_line(b) for b in bypasses])
    out: dict[tuple[str, ...], Counter[tuple[str, ...]]] = {}
    for trip in select_trips_for_spec(feed, spec):
        route = route_for_trip(spec, trip)
        calls = calls_for_trip(trip, feed, spec, route=route)
        assert all(c.node_id or c.exit_node_ids for c in calls), trip.train_number
        passes, resolution = resolve_passes(calls, own.nodes, own.segments, around)
        assert resolution == "completa" and all(p.kind == "estimado" for p in passes)
        stops = tuple(st.stop_id for st in trip.stop_times)
        ids = tuple(p.segment_id.removeprefix(f"{LINE}:") for p in passes)
        out.setdefault(stops, Counter())[ids] += 1
    return out


def test_the_line_runs_through_the_two_stations_and_not_along_the_bypasses(
    bcn: BuiltNetwork, spec: NetworkSpec
) -> None:
    """Tres partes de la misma relación: hasta Zaragoza-Delicias, hasta Lleida-Pirineus y hasta
    Barcelona-Sants. Un solo camino de Atocha a Sants iría por los baipases, 6,9 km más corto."""
    atocha = next(n for n in spec.nodes if n.id == "madrid-puerta-de-atocha").position
    assert atocha.lon is not None and atocha.lat is not None
    coords = bcn.line.polyline.coords
    assert haversine_km(coords[0], (atocha.lon, atocha.lat)) < 0.1
    assert haversine_km(coords[-1], (2.1400042, 41.3790068)) < 0.1
    assert [p.source_id for p in bcn.line.part_spans] == [RELATION] * 3
    assert [round(p.km_to, 1) for p in bcn.line.part_spans] == [306.5, 446.5, 627.0]
    assert not bcn.line.gaps_km and not bcn.line.joins_km
    assert bcn.line.polyline.length_km == pytest.approx(627.0, abs=0.1)
    # la línea principal de Adif va por los baipases y acaba en el PK 621,0: la especificación no
    # declara longitud de referencia, porque no hay una para el recorrido por las estaciones
    assert bcn.spec.line.reference_length_km is None


def test_nodes_stations_paet_and_junctions(bcn: BuiltNetwork, spec: NetworkSpec) -> None:
    assert len(bcn.nodes) == 21 and len(bcn.segments) == 20
    assert [n.spec.id for n in bcn.nodes if n.spec.kind == "estacion"] == STATIONS
    assert all(n.offset_m < 100 for n in bcn.nodes)
    # la cabecera es el nodo de la alta velocidad de Sevilla, sin cambios
    assert {n.spec.id for n in bcn.nodes if n.spec.shared} == {"madrid-puerta-de-atocha"}
    theirs = next(n for n in spec.nodes if n.id == "madrid-puerta-de-atocha")
    assert bcn.node("madrid-puerta-de-atocha").spec.position == theirs.position
    # los siete PAET son secundarios; estaciones, bifurcaciones y el cambiador, principales
    paet = [n.spec.id for n in bcn.nodes if n.spec.kind == "paet"]
    assert paet == [
        "las-inviernas",
        "ariza-av",
        "bujaraloz",
        "ballobar",
        "l-espluga-de-francoli",
        "l-arboc",
        "vilafranca-del-penedes",
    ]
    assert {n.spec.id for n in bcn.nodes if n.spec.rank == "secundario"} == set(paet)
    order = [n.spec.id for n in bcn.nodes]
    for before, station, after in [
        ("bif-moncasi", "zaragoza-delicias", "bif-huesca"),
        ("bif-huesca", "bif-canal-imperial", "bujaraloz"),
        ("bif-les-torres-de-sanui", "lleida-pirineus", "bif-artesa-de-lleida"),
    ]:
        i = order.index(station)
        assert (order[i - 1], order[i + 1]) == (before, after)


def test_reference_pk_match_all_along_once_the_numbering_follows_the_bypasses(
    bcn: BuiltNetwork,
) -> None:
    """Los PK de Adif siguen la línea principal, por los baipases, y Oniel mide por las estaciones.
    Hasta la bifurcación Huesca las dos cuentas coinciden. Después, la numeración se retoma en la
    bifurcación en la que cada baipás vuelve a la línea (``pk_restarts``): Canal Imperial, PK
    315,783, y Artesa de Lleida, PK 448,979. Así todos los nodos guardan su PK de referencia."""
    assert [(r.node, r.pk_km) for r in bcn.spec.line.pk_restarts] == [
        ("bif-canal-imperial", 315.783),
        ("bif-artesa-de-lleida", 448.979),
    ]
    # las dos bifurcaciones en las que se retoma guardan su PK en el baipás, que es por donde
    # se cuenta hasta ellas (test_baipases.py)
    without = [n.spec.id for n in bcn.nodes if n.spec.reference_pk_km is None]
    assert without == ["bif-canal-imperial", "bif-artesa-de-lleida"]
    for n in bcn.nodes:
        if n.spec.reference_pk_km is not None:
            assert expected_pk_km(bcn, n.km) == pytest.approx(n.spec.reference_pk_km, abs=0.4)
    # sin retomarla, el kilometraje por las estaciones se adelanta al PK: 4,4 km tras Zaragoza y
    # 6,0 km al llegar a Barcelona
    assert bcn.node("ballobar").km - 396.799 == pytest.approx(4.4, abs=0.1)
    assert bcn.node("barcelona-sants").km - 621.0 == pytest.approx(6.0, abs=0.1)
    # de la bifurcación Moncasi a la de Canal Imperial por Zaragoza-Delicias, y de Les Torres de
    # Sanui a Artesa de Lleida por Lleida-Pirineus
    km = {n.spec.id: n.km for n in bcn.nodes}
    assert km["bif-canal-imperial"] - km["bif-moncasi"] == pytest.approx(25.6, abs=0.1)
    assert km["bif-artesa-de-lleida"] - km["bif-les-torres-de-sanui"] == pytest.approx(
        16.2, abs=0.1
    )


def test_declared_speeds_fill_what_the_geometry_does_not_say(bcn: BuiltNetwork) -> None:
    """Las vías de entrada a Zaragoza y a Lleida no traen velocidad en OpenStreetMap: sin una
    velocidad declarada, el comparador no podría dar tiempo entre Madrid y Barcelona."""
    by_id = {s.id.removeprefix(f"{LINE}:"): s for s in bcn.segments}
    declared = {
        "bif-huesca:bif-canal-imperial": 220,
        "bif-les-torres-de-sanui:lleida-pirineus": 140,
        "lleida-pirineus:bif-artesa-de-lleida": 220,
    }
    for segment_id, speed in declared.items():
        segment = by_id[segment_id]
        assert (segment.max_speed_kmh, segment.typical_speed_kmh) == (speed, speed)
        value = segment.attributes["max_speed_kmh"]
        assert value.source_id == "commons-velocidades-lav-zaragoza-lleida" and value.checked_on
    assert {k for k, s in by_id.items() if "max_speed_kmh" in s.attributes} == set(declared)
    # los demás conservan la velocidad de las vías de la geometría, y ninguno se queda sin ella
    assert by_id["zaragoza-delicias:bif-huesca"].max_speed_kmh == 70
    assert by_id["bif-moncasi:zaragoza-delicias"].typical_speed_kmh == 200
    assert all(s.typical_speed_kmh for s in bcn.segments)
    assert Counter(s.typical_speed_kmh for s in bcn.segments)[300] == 14
    assert {s.tracks for s in bcn.segments} == {2}


def test_signalling_is_what_the_network_statement_map_says(bcn: BuiltNetwork) -> None:
    for segment in bcn.segments:
        values = {k: segment.attributes[k].value for k in ("proteccion_tren", "bloqueo", "mando")}
        assert values == {
            "proteccion_tren": "ertms_n1_asfa",
            "bloqueo": "bca",
            "mando": "sin_dato_publicado",
        }


def test_sources_and_operators_are_registered(bcn_spec: NetworkSpec) -> None:
    sources = {s.id: s for s in load_sources(SOURCES)}
    geometry = sources[bcn_spec.line.geometry_source.source_id]
    assert geometry.license == "ODbL 1.0" and geometry.retrieved_on == "2026-11-12"
    assert geometry.file is not None and (DATA_DIR / geometry.file).exists()
    assert {p.file for p in bcn_spec.line.geometry_source.parts} == {geometry.file}
    assert bcn_spec.line.verification_source_id == "wikipedia-lav-madrid-barcelona"
    facilities = sources["osm-instalaciones-lav-madrid-barcelona"]
    assert facilities.file is not None and (DATA_DIR / facilities.file).exists()
    for section in bcn_spec.attribute_sections:
        assert section.source_id in sources
    operators = {o.id: o for o in bcn_spec.operators if o.role == "operador"}
    assert {k: o.timetable for k, o in operators.items()} == {
        "renfe": "cargado",
        "ouigo": "cargado",
        "iryo": "no_publicado",
    }
    assert all(o.source_id in sources for o in bcn_spec.operators)
    # la fuente de Iryo dice ya que opera también en esta línea
    assert "Zaragoza y Barcelona" in str(sources["iryo-web"].coverage)


def test_continuations_are_connections_not_loaded_and_the_bypasses_no_longer_are(
    bcn_spec: NetworkSpec,
) -> None:
    by_node = {c.id: c.node_id for c in bcn_spec.connections}
    # los dos baipases ya no son conexiones a trazos: son líneas cargadas
    assert by_node == {
        "enlace-vallecas-perales-del-rio": "bif-vallecas-av",
        "convencional-plasencia-de-jalon-tudela": "cambiador-plasencia-de-jalon",
        "convencional-zaragoza-norte": "zaragoza-delicias",
        "zaragoza-huesca": "bif-huesca",
        "lav-barcelona-frontera-francesa": "barcelona-sants",
    }
    assert all(c.status == "no_cargada" and len(c.sketch) >= 2 for c in bcn_spec.connections)


def test_the_filter_takes_high_speed_trains_and_leaves_out_the_regional_ones(
    feed: GtfsFeed, bcn_spec: NetworkSpec
) -> None:
    trips = select_trips_for_spec(feed, bcn_spec)
    # un viaje por número de tren y día: el fichero trae muchos de estos trenes en dos viajes (el
    # recorrido entero y un trozo, como Madrid – Figueres y Madrid – Barcelona) y el lector los junta
    assert len(trips) == 571
    assert Counter(t.product for t in trips) == {
        "AVE": 264,
        "ALVIA": 105,
        "AVANT": 84,
        "AVE INT": 55,
        "EUROMED": 37,
        "Intercity": 24,
        "AVANT EXP": 2,
    }
    # los regionales que comparten estaciones (Calatayud – Zaragoza, Zaragoza – Lleida, Lleida –
    # Barcelona) quedan fuera por las paradas que solo ellos tienen
    excluded = set(bcn_spec.corridor_filter.exclude_stop_ids)
    assert excluded == {"70500", "70607", "70700", "70806", "73002"}
    node_stops = bcn_spec.node_stop_ids
    regional = [
        t
        for t in feed.trips.values()
        if t.product in {"MD", "REGIONAL", "REG.EXP."}
        and len(feed.stop_ids_of(t) & node_stops) >= 2
    ]
    assert len(regional) == 77 and all(feed.stop_ids_of(t) & excluded for t in regional)
    assert not any(feed.stop_ids_of(t) & excluded for t in trips)
    # 53 viajes entran por una regla aunque solo paran en una estación de la línea. Los trozos
    # Zaragoza – Huesca que traía el fichero van ya dentro de su AVE Madrid – Huesca
    one_stop = [t for t in trips if len(feed.stop_ids_of(t) & node_stops) == 1]
    assert Counter(r.override.id for t in one_stop if (r := route_for_trip(bcn_spec, t))) == {
        "madrid-tudela-por-plasencia-de-jalon": 53,
    }


def test_each_train_leaves_the_line_where_it_really_does(
    feed: GtfsFeed, bcn_spec: NetworkSpec, bcn: BuiltNetwork, bypasses: list[BuiltNetwork]
) -> None:
    by_stops = _segments_of(feed, bcn_spec, bcn, bypasses)
    all_segments = tuple(s.id.removeprefix(f"{LINE}:") for s in bcn.segments)

    def only(stops: tuple[str, ...]) -> tuple[str, ...]:
        (segments,) = by_stops[stops]
        return segments

    def without(skipped: tuple[str, ...], *around: str) -> tuple[str, ...]:
        return (*(s for s in all_segments if s not in skipped), *around)

    # Madrid – Barcelona sin paradas: por los dos baipases, sin los tramos de las dos estaciones
    direct = without(THROUGH_ZARAGOZA + THROUGH_LLEIDA, BYPASS_ZARAGOZA, BYPASS_LLEIDA)
    assert only(("60000", "71801")) == direct and len(direct) == 17
    # con parada en Zaragoza y no en Lleida: por la estación de Zaragoza y por el baipás de Lleida
    assert only(("60000", "04040", "71801")) == without(THROUGH_LLEIDA, BYPASS_LLEIDA)
    # con parada en las dos, la línea entera y ningún baipás
    assert only(("60000", "04040", "78400", "04104", "71801")) == all_segments
    # Alvia Madrid – Pamplona: hasta el cambiador de Plasencia de Jalón, sin llegar a Zaragoza
    to_plasencia = all_segments[: all_segments.index("cambiador-plasencia-de-jalon:bif-moncasi")]
    assert only(("60000", "04007", "70600", "81202", "80108", "80100")) == to_plasencia
    assert only(("60000", "81202", "80108", "80100")) == to_plasencia
    # Alvia Barcelona – Pamplona: sale por Zaragoza-Delicias, no por Plasencia de Jalón
    north = only(("71801", "04104", "78400", "04040", "81202", "81200", "80108", "80100"))
    assert north[0] == "zaragoza-delicias:bif-huesca" and len(north) == 12
    # AVE Madrid – Huesca: de Madrid a la bifurcación Huesca, pasada Zaragoza-Delicias
    to_huesca = all_segments[: all_segments.index("zaragoza-delicias:bif-huesca") + 1]
    assert only(("60000", "04007", "70600", "04040", "78200", "74200")) == to_huesca
    # AVE Barcelona – Sevilla sin parar en Madrid: entra en el enlace de Vallecas y no pisa el
    # tramo de Atocha; para en Zaragoza y en Lleida, así que no va por ningún baipás
    assert only(("71801", "04104", "78400", "04040", "50500", "51003")) == all_segments[1:]
    # Euromed Barcelona – València: de Barcelona a Camp de Tarragona
    euromed = only(("71801", "04104", "65300", "65000"))
    assert euromed == all_segments[all_segments.index("camp-de-tarragona:l-arboc") :]
    # el Alvia Barcelona – València – Córdoba sale también por Camp de Tarragona, aunque acabe
    # en Córdoba, que para los demás trenes es una salida por Vallecas
    alvia = next(stops for stops in by_stops if stops[:3] == ("71801", "04104", "65422"))
    assert alvia[-1] == "50500" and only(alvia) == euromed


def test_ouigo_trains_run_the_whole_line_and_follow_to_andalusia_from_atocha(
    ouigo_feed: GtfsFeed, bcn_spec: NetworkSpec, bcn: BuiltNetwork, bypasses: list[BuiltNetwork]
) -> None:
    by_stops = _segments_of(ouigo_feed, bcn_spec, bcn, bypasses)
    assert sum(sum(c.values()) for c in by_stops.values()) == 25
    # los 25 van de Madrid a Barcelona o al revés y ninguno para en Lleida: todos toman su baipás.
    # Diez tampoco paran en Zaragoza y toman además el suyo
    taken = Counter(
        tuple(i for i in ids if i in (BYPASS_ZARAGOZA, BYPASS_LLEIDA))
        for c in by_stops.values()
        for ids in c.elements()
    )
    assert taken == {(BYPASS_LLEIDA,): 15, (BYPASS_ZARAGOZA, BYPASS_LLEIDA): 10}
    assert {len(ids) for c in by_stops.values() for ids in c} == {17, 19}
    # cuatro siguen a Sevilla o a Málaga parando en Madrid: para ellos Córdoba es una salida por
    # Atocha, por la alta velocidad de Sevilla, y no por el enlace de Vallecas
    through = [stops for stops in by_stops if "50500" in stops]
    assert len(through) == 4
    rule = next(
        r for r in bcn_spec.route_overrides if r.id == "barcelona-andalucia-con-parada-en-madrid"
    )
    assert rule.stop_mappings["50500"].exits == ["madrid-puerta-de-atocha"]
    assert [(v.line, v.node) for v in rule.stop_mappings["50500"].via] == [
        ("lav-madrid-sevilla", "madrid-puerta-de-atocha")
    ]
    assert bcn_spec.stop_mappings["50500"].exits == ["bif-vallecas-av"]


def test_the_seville_line_reaches_zaragoza_and_barcelona_through_this_one() -> None:
    lav = load_network_spec(SPEC)
    for stop_id in ("04040", "71801"):
        mapping = lav.stop_mappings[stop_id]
        assert mapping.exits == ["madrid-puerta-de-atocha"]
        assert [(v.line, v.node) for v in mapping.via] == [(LINE, "madrid-puerta-de-atocha")]
