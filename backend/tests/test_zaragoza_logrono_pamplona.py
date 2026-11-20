"""Las dos líneas convencionales del valle del Ebro: la de Zaragoza a Logroño por Tudela y
Castejón (el trecho de Zaragoza a Casetas de la línea 200 de Adif y la 700 hasta Logroño) y la
de Castejón a Pamplona (la 710). Van aparte porque en Castejón el camino se abre en dos."""

from __future__ import annotations

from collections import Counter

import pytest
from conftest import (
    BCN_SPEC,
    BURGOS_VITORIA_SPEC,
    CASTEJON_PAMPLONA_SPEC,
    DATA_DIR,
    SOURCES,
    ZARAGOZA_LOGRONO_SPEC,
)

from oniel.geo import haversine_km
from oniel.gtfs.reader import GtfsFeed, GtfsTrip
from oniel.gtfs.trips import calls_for_trip, calls_on_line, route_for_trip, select_trips_for_spec
from oniel.network.build import BuiltNetwork, build_network
from oniel.network.spec import NetworkSpec, load_network_spec, load_sources
from oniel.sim.passes import LineSegment, resolve_passes
from oniel.validate import loaded_line

EBRO = "zaragoza-castejon-logrono"
PAMPLONA_LINE = "castejon-pamplona"
LAV = "lav-madrid-barcelona"
MAP = "adif-declaracion-red-2026-mapas"
DELICIAS, UTEBO, CASETAS, GRISEN, CALATAYUD = "04040", "70801", "70800", "70706", "70600"
TUDELA, CASTEJON, ALFARO, CALAHORRA, LOGRONO = "81202", "81200", "81110", "81108", "81100"
TAFALLA, PAMPLONA, VITORIA, MIRANDA, HARO = "80108", "80100", "11208", "11200", "81002"
ATOCHA, LLEIDA, BARCELONA, CHAMARTIN = "60000", "78400", "71801", "17000"
EBRO_NODES = [
    "zaragoza-delicias",
    "utebo",
    "casetas",
    "alagon",
    "cabanas-de-ebro",
    "pedrola",
    "luceni",
    "gallur",
    "cortes-de-navarra",
    "ribaforada",
    "tudela-de-navarra",
    "castejon-de-ebro",
    "alfaro",
    "rincon-de-soto",
    "calahorra",
    "feculas-navarra",
    "alcanadre",
    "agoncillo",
    "logrono",
]
PAMPLONA_NODES = [
    "castejon-de-ebro",
    "villafranca-de-navarra",
    "marcilla-de-navarra",
    "olite",
    "tafalla",
    "pamplona",
]


def _segments(nodes: list[str]) -> list[str]:
    return [f"{a}:{b}" for a, b in zip(nodes, nodes[1:], strict=False)]


@pytest.fixture(scope="module")
def ebro() -> BuiltNetwork:
    return build_network(load_network_spec(ZARAGOZA_LOGRONO_SPEC), DATA_DIR)


@pytest.fixture(scope="module")
def navarra() -> BuiltNetwork:
    return build_network(load_network_spec(CASTEJON_PAMPLONA_SPEC), DATA_DIR)


def _stops(trip: GtfsTrip) -> list[str]:
    return [st.stop_id for st in trip.stop_times]


def _counts(feed: GtfsFeed, net: BuiltNetwork) -> Counter[str]:
    """Viajes del fichero de las pruebas que pasan por cada tramo de la línea."""
    own = loaded_line(net)
    segments = [LineSegment(s.id, s.km_from, s.km_to) for s in net.segments]
    counts: Counter[str] = Counter()
    for trip in select_trips_for_spec(feed, net.spec):
        route = route_for_trip(net.spec, trip)
        calls = calls_on_line(
            calls_for_trip(trip, feed, net.spec, nodes=own.nodes, others=[], route=route), route
        )
        passes, resolution = resolve_passes(calls, own.nodes, segments)
        assert resolution == "completa", trip.train_number
        counts.update(p.segment_id.split(":", 1)[1] for p in passes)
    return counts


def _via(spec: NetworkSpec, stop_id: str) -> list[tuple[str, str]]:
    return [(v.line, v.node) for v in spec.stop_mappings[stop_id].via]


def test_the_ebro_line_joins_two_relations_at_casetas(ebro: BuiltNetwork) -> None:
    """De Zaragoza-Delicias a Casetas, la relación del Cercanías C-1, por las vías de la línea
    de Madrid; de Casetas a Logroño, la de la línea 700. Se empalman en un nodo común, sin
    salto: 165,7 km."""
    line = ebro.line
    assert [p.source_id for p in line.part_spans] == [
        "osm-relation-6205861",
        "osm-relation-9277501",
    ]
    assert not line.gaps_km
    assert line.polyline.length_km == pytest.approx(165.7, abs=0.1)
    assert line.part_spans[0].km_to == pytest.approx(11.9, abs=0.1)
    assert haversine_km(line.polyline.coords[-1], (-2.4408195, 42.4575743)) < 0.05
    assert all(n.offset_m < 45 for n in ebro.nodes)


def test_the_pamplona_line_leaves_the_ebro_line_past_castejon(navarra: BuiltNetwork) -> None:
    """La línea 710 se separa de la 700 a 400 m de la estación de Castejón: ese trecho sale de
    la relación de la 700 y el resto, hasta Pamplona, de la de la 710. 87,3 km."""
    line = navarra.line
    assert [p.source_id for p in line.part_spans] == [
        "osm-relation-9277501",
        "osm-relation-9392199",
    ]
    assert not line.gaps_km
    assert line.part_spans[0].km_to == pytest.approx(0.4, abs=0.05)
    assert line.polyline.length_km == pytest.approx(87.3, abs=0.1)
    assert all(n.offset_m < 25 for n in navarra.nodes)


def test_nodes_and_main_stations(ebro: BuiltNetwork, navarra: BuiltNetwork) -> None:
    assert [n.spec.id for n in ebro.nodes] == EBRO_NODES
    assert [n.spec.id for n in navarra.nodes] == PAMPLONA_NODES
    assert all(n.spec.kind == "estacion" for n in [*ebro.nodes, *navarra.nodes])
    assert {n.spec.id for n in ebro.nodes if n.spec.rank == "principal"} == {
        "zaragoza-delicias",
        "tudela-de-navarra",
        "castejon-de-ebro",
        "calahorra",
        "logrono",
    }
    assert {n.spec.id for n in navarra.nodes if n.spec.rank == "principal"} == {
        "castejon-de-ebro",
        "tafalla",
        "pamplona",
    }
    assert ebro.node("logrono").spec.adif_code == LOGRONO
    assert navarra.node("pamplona").spec.adif_code == PAMPLONA


def test_shared_stations_are_not_moved(ebro: BuiltNetwork, navarra: BuiltNetwork) -> None:
    """Zaragoza-Delicias la define la alta velocidad de Barcelona, y Castejón, la línea del
    Ebro: cada línea incorpora la que comparte con sus mismas coordenadas."""
    assert {n.spec.id for n in ebro.nodes if n.spec.shared} == {"zaragoza-delicias"}
    assert {n.spec.id for n in navarra.nodes if n.spec.shared} == {"castejon-de-ebro"}
    lav = load_network_spec(BCN_SPEC)
    theirs = next(n for n in lav.nodes if n.id == "zaragoza-delicias")
    assert ebro.node("zaragoza-delicias").spec.position == theirs.position
    assert (
        navarra.node("castejon-de-ebro").spec.position
        == ebro.node("castejon-de-ebro").spec.position
    )


def test_kilometre_points_follow_three_numberings(
    ebro: BuiltNetwork, navarra: BuiltNetwork
) -> None:
    """De Casetas (15,4) a Castejón (93,7) vale la numeración histórica de Zaragoza a Altsasu;
    de Castejón a Logroño, la de Castejón a Bilbao, que empieza en 0, y hacia Pamplona sigue la
    primera. De Zaragoza a Casetas los puntos son los de la línea de Madrid, que decrecen, y no
    se guardan."""
    spec = ebro.spec.line
    assert [(r.node, r.pk_km) for r in spec.pk_restarts] == [
        ("casetas", 15.4),
        ("castejon-de-ebro", 0.0),
    ]
    casetas, castejon = ebro.node("casetas").km, ebro.node("castejon-de-ebro").km
    for node in ebro.nodes:
        pk = node.spec.reference_pk_km
        if node.km <= casetas or node.spec.id == "logrono":
            assert pk is None, node.spec.id
        elif node.km <= castejon:
            assert 15.4 + node.km - casetas == pytest.approx(pk, abs=0.15), node.spec.id
        else:
            assert node.km - castejon == pytest.approx(pk, abs=0.5), node.spec.id
    assert navarra.spec.line.pk_origin_km == 93.7
    for node in navarra.nodes[1:]:
        assert 93.7 + node.km == pytest.approx(node.spec.reference_pk_km, abs=0.1), node.spec.id


def test_double_track_to_castejon_and_single_beyond(
    ebro: BuiltNetwork, navarra: BuiltNetwork
) -> None:
    names = [s.id.removeprefix(f"{EBRO}:") for s in ebro.segments]
    assert names == _segments(EBRO_NODES)
    split = names.index("castejon-de-ebro:alfaro")
    assert [s.tracks for s in ebro.segments] == [2] * split + [1] * (len(names) - split)
    assert all(s.tracks == 1 for s in navarra.segments)
    for line in (ebro, navarra):
        assert line.spec.line.gauge_mm == 1668 and line.spec.line.electrification == "3 kV CC"
    speeds = [s.max_speed_kmh or 0 for s in ebro.segments]
    assert speeds[:split] == [160] * split
    assert all(speeds[split:]) and max(speeds[split:]) == 140 and min(speeds) == 85
    assert [s.max_speed_kmh for s in navarra.segments] == [140] * 5


def test_signalling_as_the_map_draws_it(ebro: BuiltNetwork, navarra: BuiltNetwork) -> None:
    """Bloqueo banalizado en la vía doble, hasta Castejón, y de vía única de ahí a Logroño y a
    Pamplona; ASFA y control de tráfico centralizado en todo."""
    castejon = ebro.node("castejon-de-ebro").km
    for segment in ebro.segments:
        assert segment.attributes["bloqueo"].value == (
            "bab" if segment.km_to <= castejon else "bau"
        )
    assert {s.attributes["bloqueo"].value for s in navarra.segments} == {"bau"}
    for segment in [*ebro.segments, *navarra.segments]:
        assert segment.attributes["proteccion_tren"].value == "asfa"
        assert segment.attributes["mando"].value == "ctc"
        for key in ("proteccion_tren", "bloqueo", "mando"):
            assert segment.attributes[key].source_id == MAP


def test_sources_and_operators_are_registered(ebro: BuiltNetwork, navarra: BuiltNetwork) -> None:
    sources = {s.id: s for s in load_sources(SOURCES)}
    for spec in (ebro.spec, navarra.spec):
        for part in spec.line.geometry_source.parts:
            source = sources[part.source_id]
            assert source.license == "ODbL 1.0"
            assert source.file == part.file and (DATA_DIR / part.file).exists()
        for section in spec.attribute_sections:
            assert section.source_id in sources
        assert {o.id for o in spec.operators if o.role == "operador"} == {"renfe"}
        assert all(o.source_id in sources for o in spec.operators)
        assert spec.line.zone == "aragon-navarra-rioja"
    stations = sources["osm-instalaciones-zaragoza-logrono-pamplona"]
    assert stations.file and (DATA_DIR / stations.file).exists()
    assert ebro.spec.line.verification_source_id == "wikipedia-linea-casetas-bilbao"
    assert navarra.spec.line.verification_source_id == "wikipedia-linea-castejon-alsasua"


def test_the_filters_take_the_trains_that_run_on_each_line(
    feed: GtfsFeed, ouigo_feed: GtfsFeed, ebro: BuiltNetwork, navarra: BuiltNetwork
) -> None:
    """208 viajes de Renfe en la línea del Ebro y 128 en la de Pamplona; ninguno de Ouigo. Los
    Intercity de Madrid-Chamartín a Logroño por Burgos, que solo tocan Logroño, quedan fuera."""
    trips = select_trips_for_spec(feed, ebro.spec)
    assert Counter(t.product for t in trips) == {
        "ALVIA": 97,
        "REG.EXP.": 33,
        "MD": 33,
        "REGIONAL": 23,
        "Intercity": 22,
    }
    assert not any(CHAMARTIN in _stops(t) for t in trips)
    to_pamplona = select_trips_for_spec(feed, navarra.spec)
    assert Counter(t.product for t in to_pamplona) == {
        "ALVIA": 77,
        "Intercity": 22,
        "REG.EXP.": 21,
        "MD": 8,
    }
    assert all(PAMPLONA in _stops(t) or TAFALLA in _stops(t) for t in to_pamplona)
    # los que no están en la línea del Ebro son los regionales de Vitoria que acaban en Castejón
    only_here = [t for t in to_pamplona if t.trip_id not in {x.trip_id for x in trips}]
    assert only_here and all(CASTEJON in (_stops(t)[0], _stops(t)[-1]) for t in only_here)
    assert all(t.product == "REG.EXP." for t in only_here)
    for spec in (ebro.spec, navarra.spec):
        assert select_trips_for_spec(ouigo_feed, spec) == []


def test_trains_per_segment_on_the_ebro_line(feed: GtfsFeed, ebro: BuiltNetwork) -> None:
    """De Zaragoza salen 114 trenes; 23, los regionales de Calatayud, dejan la línea en Casetas.
    En Cabañas de Ebro entran los 80 de Madrid, que vienen del cambiador de Plasencia de Jalón, y
    hasta Castejón son 171. Hacia Alfaro siguen 43, y allí se suman los 13 regionales de Logroño
    que acaban en Alfaro."""
    counts = _counts(feed, ebro)
    names = _segments(EBRO_NODES)
    expected = [114] * 2 + [91] * 2 + [171] * 7 + [43] + [56] * 6
    assert [counts[name] for name in names] == expected


def test_every_train_runs_the_whole_pamplona_line(feed: GtfsFeed, navarra: BuiltNetwork) -> None:
    counts = _counts(feed, navarra)
    assert [counts[name] for name in _segments(PAMPLONA_NODES)] == [128] * 5


def test_madrid_trains_join_at_cabanas_de_ebro(feed: GtfsFeed, ebro: BuiltNetwork) -> None:
    """Madrid, Guadalajara-Yebes y Calatayud salen por Cabañas de Ebro, hacia el cambiador de
    Plasencia de Jalón de la alta velocidad. Los regionales de Calatayud, en cambio, dejan la
    línea en Casetas: los distinguen dos reglas, por su parada en Grisén."""
    spec = ebro.spec
    for stop_id in (ATOCHA, "04007", CALATAYUD):
        assert spec.stop_mappings[stop_id].exits == ["cabanas-de-ebro"]
        assert _via(spec, stop_id) == [(LAV, "cambiador-plasencia-de-jalon")]
    assert spec.stop_mappings[GRISEN].exits == ["casetas"]
    rules = {r.id: r for r in spec.route_overrides}
    for rule_id in ("regionales-de-calatayud-por-utebo", "regionales-de-calatayud-por-casetas"):
        assert rules[rule_id].stop_mappings[CALATAYUD].exits == ["casetas"]
    matched = Counter(
        route.override.id
        for t in select_trips_for_spec(feed, spec)
        if (route := route_for_trip(spec, t))
    )
    assert matched == {
        "regionales-de-calatayud-por-utebo": 9,
        "regionales-de-calatayud-por-casetas": 14,
        "miranda-por-logrono": 22,
    }
    regionals = [t for t in select_trips_for_spec(feed, spec) if GRISEN in _stops(t)]
    assert len(regionals) == 23 and all(t.product == "REGIONAL" for t in regionals)


def test_miranda_is_reached_by_two_ways(ebro: BuiltNetwork) -> None:
    """A Miranda de Ebro se llega por Pamplona y Vitoria, saliendo por Castejón, o por Logroño y
    Haro: la asignación general lleva la primera y una regla, que nombra Calahorra, Logroño y
    Haro seguidas, la segunda."""
    spec = ebro.spec
    assert spec.stop_mappings[MIRANDA].exits == ["castejon-de-ebro"]
    assert spec.stop_mappings[VITORIA].exits == ["castejon-de-ebro"]
    assert spec.stop_mappings[HARO].exits == ["logrono"]
    rule = next(r for r in spec.route_overrides if r.id == "miranda-por-logrono")
    assert rule.consecutive_stop_ids == [CALAHORRA, LOGRONO, HARO]
    assert rule.stop_mappings[MIRANDA].exits == ["logrono"]


def test_stops_on_the_neighbouring_lines_carry_their_way(
    ebro: BuiltNetwork, navarra: BuiltNetwork
) -> None:
    assert _via(ebro.spec, LLEIDA) == [(LAV, "zaragoza-delicias")]
    assert _via(ebro.spec, PAMPLONA) == [(PAMPLONA_LINE, "castejon-de-ebro")]
    assert _via(navarra.spec, TUDELA) == [(EBRO, "castejon-de-ebro")]
    assert _via(navarra.spec, BARCELONA) == [(EBRO, "castejon-de-ebro"), (LAV, "zaragoza-delicias")]
    # Madrid, desde la línea de Pamplona: el cambiador no es un nodo de la del Ebro
    assert navarra.spec.stop_mappings[ATOCHA].exits == ["castejon-de-ebro"]
    assert not navarra.spec.stop_mappings[ATOCHA].via
    assert navarra.spec.stop_mappings[VITORIA].exits == ["pamplona"]


def test_the_high_speed_line_reaches_them_by_zaragoza_or_by_the_gauge_changer() -> None:
    """La alta velocidad de Barcelona ya no sale a trazos de Zaragoza hacia Tudela: sus trenes
    siguen por la línea del Ebro, desde Zaragoza-Delicias o, los de Madrid, desde Cabañas de Ebro."""
    lav = load_network_spec(BCN_SPEC)
    assert _via(lav, LOGRONO) == [(EBRO, "zaragoza-delicias")]
    assert _via(lav, PAMPLONA) == [(EBRO, "zaragoza-delicias"), (PAMPLONA_LINE, "castejon-de-ebro")]
    rule = next(r for r in lav.route_overrides if r.id == "madrid-tudela-por-plasencia-de-jalon")
    by_changer = rule.stop_mappings
    assert by_changer[TUDELA].exits == ["cambiador-plasencia-de-jalon"]
    assert [(v.line, v.node) for v in by_changer[TUDELA].via] == [(EBRO, "cabanas-de-ebro")]
    assert [(v.line, v.node) for v in by_changer[PAMPLONA].via] == [
        (EBRO, "cabanas-de-ebro"),
        (PAMPLONA_LINE, "castejon-de-ebro"),
    ]
    assert [c.id for c in lav.connections if c.node_id == "zaragoza-delicias"] == []
    changer = next(c for c in lav.connections if c.node_id == "cambiador-plasencia-de-jalon")
    assert changer.sketch[-1] == (-1.1684037, 41.7883119)


def test_what_stays_dashed(ebro: BuiltNetwork, navarra: BuiltNetwork) -> None:
    """Quedan a trazos la línea de Madrid desde Casetas, la continuación de Pamplona a Altsasu y,
    desde Miranda de Ebro, la de Logroño, que acaba en la estación de Logroño."""
    assert [(c.id, c.node_id) for c in ebro.spec.connections] == [
        ("conv-casetas-calatayud", "casetas")
    ]
    assert [(c.id, c.node_id) for c in navarra.spec.connections] == [
        ("conv-pamplona-altsasu", "pamplona")
    ]
    burgos = load_network_spec(BURGOS_VITORIA_SPEC)
    dashed = next(c for c in burgos.connections if c.id == "conv-miranda-logrono")
    logrono = ebro.node("logrono").spec.position
    assert dashed.sketch[-1] == (logrono.lon, logrono.lat)
