"""La línea de Valencia a Camp de Tarragona por Castellón (Adif 600 y 640): el Corredor
Mediterráneo entre la alta velocidad de Madrid a Valencia y la de Madrid a Barcelona."""

from __future__ import annotations

import pytest
from conftest import BCN_SPEC, DATA_DIR, LAV_VALENCIA_SPEC, MEDITERRANEO_SPEC, SOURCES, SPEC

from oniel.gtfs.reader import GtfsFeed, GtfsTrip
from oniel.gtfs.trips import (
    LoadedLine,
    calls_for_trip,
    calls_on_line,
    route_for_trip,
    select_trips_for_spec,
)
from oniel.network.build import BuiltNetwork, build_network
from oniel.network.spec import load_network_spec, load_sources
from oniel.sim.passes import LineSegment, SegmentPass, resolve_passes
from oniel.validate import loaded_line

LINE = "valencia-castello-tarragona"
NORD = "valencia-estacio-del-nord"
SOROLLA = "valencia-joaquin-sorolla"
CASTELLO = "castello-de-la-plana"
BOELLA = "cambiador-la-boella"
CAMP = "camp-de-tarragona"
FEREDAT = "bif-la-feredat"
#: Entre qué dos nodos recorre la línea cada viaje del fichero de pruebas, y cuántos son.
SHAPES = {
    # regionales de València a Castelló y Vinaròs
    (NORD, "vinaros"): 129,
    # Euromed, Intercity y Alvia de València a Barcelona por Camp de Tarragona
    (CAMP, NORD): 53,
    # regionales de València a Tortosa: dejan la línea en L'Aldea-Amposta-Tortosa
    ("l-aldea-amposta-tortosa", NORD): 18,
    # regionales de Tortosa a Barcelona por Tarragona ciudad
    (FEREDAT, "l-aldea-amposta-tortosa"): 18,
    # AVE de Madrid, de València-Joaquín Sorolla a Castelló
    (CASTELLO, SOROLLA): 17,
    # Intercity y regionales de València a Barcelona por Tarragona ciudad
    (FEREDAT, NORD): 8,
    # Media Distancia de València a Teruel y Zaragoza: hasta Sagunt
    ("sagunt", NORD): 6,
    (FEREDAT, "vinaros"): 2,
    # Avant Exprés de Tortosa a Barcelona por la alta velocidad
    (CAMP, "l-aldea-amposta-tortosa"): 2,
}


@pytest.fixture(scope="module")
def coast() -> BuiltNetwork:
    return build_network(load_network_spec(MEDITERRANEO_SPEC), DATA_DIR)


@pytest.fixture(scope="module")
def lines(coast: BuiltNetwork) -> list[LoadedLine]:
    specs = (SPEC, BCN_SPEC, LAV_VALENCIA_SPEC)
    others = [build_network(load_network_spec(p), DATA_DIR) for p in specs]
    return [loaded_line(net) for net in (*others, coast)]


def _stops(trip: GtfsTrip) -> list[str]:
    return [st.stop_id for st in trip.stop_times]


def _passes(
    trip: GtfsTrip, feed: GtfsFeed, net: BuiltNetwork, lines: list[LoadedLine]
) -> list[SegmentPass]:
    own = loaded_line(net)
    others = [line for line in lines if line.line_id != own.line_id]
    route = route_for_trip(net.spec, trip)
    calls = calls_on_line(
        calls_for_trip(trip, feed, net.spec, nodes=own.nodes, others=others, route=route), route
    )
    assert all(c.node_id or c.exit_node_ids for c in calls), trip.train_number
    segments = [LineSegment(s.id, s.km_from, s.km_to) for s in net.segments]
    passes, resolution = resolve_passes(calls, own.nodes, segments)
    assert resolution == "completa", trip.train_number
    return passes


def _ends(passes: list[SegmentPass]) -> tuple[str, str]:
    short = [p.segment_id.split(":", 1)[1] for p in passes]
    first, last = sorted({short[0].split(":")[0], short[-1].split(":")[1]})
    return first, last


def test_the_line_runs_from_valencia_nord_to_camp_de_tarragona(coast: BuiltNetwork) -> None:
    """Junta la línea 600 de Adif, de València-Estació del Nord al cambiador de La Boella, y la
    640, de allí a Camp de Tarragona. Las dos partes empalman en el mismo nodo de OSM."""
    assert coast.spec.line.id == LINE and coast.spec.line.zone == "levante"
    assert [p.source_id for p in coast.line.part_spans] == [
        "osm-relation-18368664",
        "osm-relation-11088348",
    ]
    assert not coast.line.gaps_km and not coast.line.joins_km
    # la línea 600 mide lo que dice Wikipedia: 254,1 km hasta el cambiador
    assert coast.node(BOELLA).km == pytest.approx(254.1, abs=0.1)
    assert coast.line.polyline.length_km == pytest.approx(266.6, abs=0.2)
    ids = [n.spec.id for n in coast.nodes]
    assert len(ids) == 36 and ids[:3] == [NORD, SOROLLA, "valencia-la-font-de-sant-lluis"]
    assert ids[-4:] == ["cambrils", FEREDAT, BOELLA, CAMP]
    kinds = {n.spec.id: n.spec.kind for n in coast.nodes if n.spec.kind != "estacion"}
    assert kinds == {FEREDAT: "bifurcacion", BOELLA: "cambiador"}
    # las estaciones en las que paran los trenes de largo recorrido y el cambiador son principales
    assert [n.spec.id for n in coast.nodes if n.spec.rank == "principal"] == [
        NORD,
        SOROLLA,
        "sagunt",
        CASTELLO,
        "benicassim",
        "orpesa",
        "benicarlo-peniscola",
        "vinaros",
        "l-aldea-amposta-tortosa",
        "cambrils",
        BOELLA,
        CAMP,
    ]
    # todas las estaciones están sobre el trazado, salvo la cabecera y las dos compartidas
    apart = {n.spec.id: round(n.offset_m) for n in coast.nodes if n.offset_m > 25}
    assert apart == {NORD: 70, SOROLLA: 148, CAMP: 62}
    # los tres puntos kilométricos de la numeración actual que dan las fuentes
    pks = {n.spec.id: (n.km, n.spec.reference_pk_km) for n in coast.nodes if n.spec.reference_pk_km}
    assert set(pks) == {"valencia-la-font-de-sant-lluis", CASTELLO, BOELLA}
    assert all(abs(km - pk) < 0.2 for km, pk in pks.values())
    # ningún tramo se queda sin velocidad: el comparador da tiempo para todos sus recorridos
    assert all(s.max_speed_kmh and s.typical_speed_kmh for s in coast.segments)
    assert max(s.max_speed_kmh or 0 for s in coast.segments) == 220


def test_both_ends_are_nodes_that_other_lines_define(coast: BuiltNetwork) -> None:
    """València-Joaquín Sorolla es de la alta velocidad de Madrid a Valencia y Camp de Tarragona,
    de la de Madrid a Barcelona: esta línea los incorpora sin moverlos ni cambiarles nada."""
    for path, node_id in ((LAV_VALENCIA_SPEC, SOROLLA), (BCN_SPEC, CAMP)):
        other = load_network_spec(path)
        theirs = next(n for n in other.nodes if n.id == node_id)
        ours = coast.node(node_id).spec
        assert not theirs.shared and ours.shared and ours.description is None
        assert ours.position == theirs.position and ours.name == theirs.name
        # la conexión a trazos que anunciaba esta línea ya no sale de la otra
        assert not [c for c in other.connections if c.node_id == node_id]
        # y sus paradas dicen por dónde sigue el tren
        via = other.stop_mappings["65300"].via
        assert [(v.line, v.node) for v in via] == [(LINE, node_id)]
    # la Estació del Nord es otra estación: la línea sale de ella y pasa junto a Joaquín Sorolla
    assert coast.node(NORD).km == 0 and coast.node(SOROLLA).km == pytest.approx(0.76, abs=0.05)
    assert not coast.node(NORD).spec.shared
    # lo que sigue sin cargar sale a trazos
    assert {c.id: c.node_id for c in coast.spec.connections} == {
        "valencia-nord-sur": NORD,
        "sagunt-teruel": "sagunt",
        "ramal-de-tortosa": "l-aldea-amposta-tortosa",
        "convencional-tarragona-costa": FEREDAT,
    }


def test_gauge_and_signalling_change_along_the_line(coast: BuiltNetwork) -> None:
    """Ancho ibérico en la línea, con una vía de ancho mixto de València-Joaquín Sorolla a
    Castelló y ancho estándar a 25 kV del cambiador de La Boella a Camp de Tarragona."""
    assert coast.spec.line.gauge_mm == 1668 and coast.spec.line.electrification == "3 kV CC"
    by_id = {s.id.split(":", 1)[1]: s for s in coast.segments}
    assert len(by_id) == 35 and {s.tracks for s in by_id.values()} == {2}
    gauge = {k: s.attributes["gauge"].value for k, s in by_id.items() if "gauge" in s.attributes}
    last = f"{BOELLA}:{CAMP}"
    assert gauge.pop(last) == "estandar"
    assert len(gauge) == 18 and set(gauge.values()) == {"mixto"}
    assert f"{NORD}:{SOROLLA}" not in gauge and f"almassora:{CASTELLO}" in gauge
    assert f"{CASTELLO}:benicassim" not in gauge
    power = {k for k, s in by_id.items() if "electrification" in s.attributes}
    assert power == {last} and by_id[last].attributes["electrification"].value == "25 kV 50 Hz"
    # la señalización: ASFA hasta L'Ametlla de Mar y ERTMS de nivel 1 en la variante de Vandellòs;
    # bloqueo automático banalizado con CTC en la línea 600 y BCA en la 640
    protection = [s.attributes["proteccion_tren"].value for s in coast.segments]
    assert protection == ["asfa"] * 30 + ["ertms_n1_asfa"] * 5
    assert by_id["l-ametlla-de-mar:l-hospitalet-de-l-infant"].attributes[
        "proteccion_tren"
    ].value == ("ertms_n1_asfa")
    blocks = [s.attributes["bloqueo"].value for s in coast.segments]
    assert blocks == ["bab"] * 34 + ["bca"]
    control = [s.attributes["mando"].value for s in coast.segments]
    assert control == ["ctc"] * 34 + ["sin_dato_publicado"]


def test_sources_of_the_line_are_registered(coast: BuiltNetwork) -> None:
    sources = {s.id: s for s in load_sources(SOURCES)}
    for part in coast.spec.line.geometry_source.parts:
        source = sources[part.source_id]
        assert source.license == "ODbL 1.0" and source.retrieved_on == "2026-11-13"
        assert source.file == part.file and (DATA_DIR / part.file).exists()
    assert coast.spec.line.verification_source_id == "wikipedia-linea-valencia-tarragona"
    assert "oldid 174998420" in (sources["wikipedia-linea-valencia-tarragona"].notes or "")
    facilities = sources["osm-instalaciones-valencia-camp-de-tarragona"]
    assert facilities.file and (DATA_DIR / facilities.file).exists()
    for section in coast.spec.attribute_sections:
        assert section.source_id in sources and section.checked_on is not None
    # solo circula Renfe: ni Ouigo ni Iryo tienen trenes en la línea
    operators = {o.id: o for o in coast.spec.operators}
    assert set(operators) == {"adif", "renfe"} and operators["renfe"].timetable == "cargado"
    assert all(o.source_id in sources for o in operators.values())


def test_trains_of_the_coast_enter_and_leave_where_they_do(
    feed: GtfsFeed, ouigo_feed: GtfsFeed, coast: BuiltNetwork, lines: list[LoadedLine]
) -> None:
    """Entran los trenes que paran en dos estaciones de la línea. Cada uno la recorre entre el
    nodo por el que entra y el nodo por el que sale."""
    trips = select_trips_for_spec(feed, coast.spec)
    assert len(trips) == 253 and select_trips_for_spec(ouigo_feed, coast.spec) == []
    products: dict[str, int] = {}
    rules: dict[str, int] = {}
    shapes: dict[tuple[str, str], int] = {}
    kinds: dict[str, int] = {}
    for trip in trips:
        products[trip.product or ""] = products.get(trip.product or "", 0) + 1
        route = route_for_trip(coast.spec, trip)
        if route is not None:
            rules[route.override.id] = rules.get(route.override.id, 0) + 1
        passes = _passes(trip, feed, coast, lines)
        for p in passes:
            kinds[p.kind] = kinds.get(p.kind, 0) + 1
        ends = _ends(passes)
        shapes[ends] = shapes.get(ends, 0) + 1
    assert products == {
        "REGIONAL": 131,
        "REG.EXP.": 38,
        "EUROMED": 37,
        "AVE": 17,
        "Intercity": 14,
        "ALVIA": 8,
        "MD": 6,
        "AVANT EXP": 2,
    }
    assert rules == {
        "cambrils-vila-seca-por-la-feredat": 22,
        "castello-tarragona-por-la-feredat": 4,
        "l-aldea-tarragona-por-la-feredat": 2,
    }
    assert kinds == {"estimado": 4223, "publicado": 2107}
    assert shapes == SHAPES
    # fuera quedan los trenes que solo tocan la línea en una estación: los de alta velocidad que
    # acaban en València-Joaquín Sorolla y los que paran en Camp de Tarragona sin bajar a la costa
    chosen = {t.trip_id for t in trips}
    to_valencia = [
        t for t in feed.trips.values() if "03216" in _stops(t) and "65300" not in _stops(t)
    ]
    past_camp = [
        t
        for t in feed.trips.values()
        if "04104" in _stops(t) and not {"65300", "65402"} & set(_stops(t))
    ]
    assert len(to_valencia) == 237 and len(past_camp) == 220
    assert not chosen & {t.trip_id for t in to_valencia + past_camp}


def test_trains_through_tarragona_city_leave_at_la_feredat(
    feed: GtfsFeed, coast: BuiltNetwork, lines: list[LoadedLine]
) -> None:
    """Barcelona-Sants es, para casi todos, una parada de la alta velocidad a la que se llega por
    Camp de Tarragona. Los trenes que van por Tarragona ciudad dejan la línea antes, en la
    bifurcación La Feredat, y no pasan por el cambiador de La Boella."""
    beyond = {f"{LINE}:{FEREDAT}:{BOELLA}", f"{LINE}:{BOELLA}:{CAMP}"}
    trips = select_trips_for_spec(feed, coast.spec)
    by_city = [t for t in trips if "71500" in _stops(t)]
    by_camp = [t for t in trips if "04104" in _stops(t)]
    assert (len(by_city), len(by_camp)) == (28, 55) and len(by_city + by_camp) == 83
    for trip in by_city:
        ids = {p.segment_id for p in _passes(trip, feed, coast, lines)}
        assert f"{LINE}:cambrils:{FEREDAT}" in ids and not ids & beyond
    for trip in by_camp:
        assert beyond <= {p.segment_id for p in _passes(trip, feed, coast, lines)}


def test_trains_from_madrid_join_at_joaquin_sorolla(
    feed: GtfsFeed, coast: BuiltNetwork, lines: list[LoadedLine]
) -> None:
    """Los AVE de Madrid a Castelló paran en València-Joaquín Sorolla, no en la Estació del Nord:
    recorren la línea desde ese nodo y no cuentan en el primer tramo."""
    trips = [t for t in select_trips_for_spec(feed, coast.spec) if "03216" in _stops(t)]
    assert len(trips) == 17 and all(t.product == "AVE" for t in trips)
    for trip in trips:
        passes = _passes(trip, feed, coast, lines)
        assert len(passes) == 18 and _ends(passes) == (CASTELLO, SOROLLA)
        assert {p.kind for p in passes} == {"estimado"}
    # los Euromed salen de la Estació del Nord y pasan junto a Joaquín Sorolla sin parar
    euromed = next(t for t in select_trips_for_spec(feed, coast.spec) if t.product == "EUROMED")
    by_id = {p.segment_id: p for p in _passes(euromed, feed, coast, lines)}
    assert by_id[f"{LINE}:{NORD}:{SOROLLA}"].kind == "estimado"
