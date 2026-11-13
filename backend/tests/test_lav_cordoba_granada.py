"""El camino de alta velocidad a Granada: las líneas Córdoba – Málaga (Adif 030, cargada hasta
Antequera-Santa Ana) y Antequera – Granada (Adif 036)."""

from __future__ import annotations

import pytest
from conftest import DATA_DIR, LAV_GRANADA_SPEC, LAV_MALAGA_SPEC, SOURCES

from oniel.geo import haversine_km
from oniel.gtfs.reader import GtfsFeed, GtfsTrip
from oniel.gtfs.trips import LoadedLine, calls_for_trip, select_trips_for_spec
from oniel.network.build import BuiltNetwork, build_network
from oniel.network.spec import NetworkSpec, load_network_spec, load_sources
from oniel.sim.passes import LineSegment, SegmentPass, resolve_passes
from oniel.validate import loaded_line

MALAGA, GRANADA = "lav-cordoba-malaga", "lav-antequera-granada"


@pytest.fixture(scope="module")
def malaga() -> BuiltNetwork:
    return build_network(load_network_spec(LAV_MALAGA_SPEC), DATA_DIR)


@pytest.fixture(scope="module")
def granada() -> BuiltNetwork:
    return build_network(load_network_spec(LAV_GRANADA_SPEC), DATA_DIR)


@pytest.fixture(scope="module")
def lines(built: BuiltNetwork, malaga: BuiltNetwork, granada: BuiltNetwork) -> list[LoadedLine]:
    """Las tres líneas de alta velocidad, para medir por ellas el camino hasta cada parada."""
    return [loaded_line(built), loaded_line(malaga), loaded_line(granada)]


def _passes(
    trip: GtfsTrip, feed: GtfsFeed, net: BuiltNetwork, lines: list[LoadedLine]
) -> list[SegmentPass]:
    own = loaded_line(net)
    others = [line for line in lines if line.line_id != own.line_id]
    calls = calls_for_trip(trip, feed, net.spec, nodes=own.nodes, others=others)
    assert all(c.node_id or c.exit_node_ids for c in calls), trip.train_number
    segments = [LineSegment(s.id, s.km_from, s.km_to) for s in net.segments]
    passes, resolution = resolve_passes(calls, own.nodes, segments)
    assert resolution == "completa", trip.train_number
    return passes


def _stops(trip: GtfsTrip) -> list[str]:
    return [st.stop_id for st in trip.stop_times]


def test_the_two_lines_chain_from_the_malaga_junction_to_granada(
    malaga: BuiltNetwork, granada: BuiltNetwork, spec: NetworkSpec
) -> None:
    """La primera sale de la bifurcación de la línea Madrid – Sevilla y llega a Antequera-Santa Ana;
    la segunda sigue desde allí hasta Granada. Miden lo que dicen sus puntos kilométricos."""
    junction = next(n for n in spec.nodes if n.id == "bif-malaga")
    assert not junction.shared and malaga.node("bif-malaga").spec.shared
    assert malaga.node("bif-malaga").spec.position == junction.position
    assert [n.spec.id for n in malaga.nodes] == [
        "bif-malaga",
        "la-marota",
        "santaella",
        "puente-genil-herrera",
        "antequera-santa-ana",
    ]
    assert [n.spec.id for n in granada.nodes] == [
        "antequera-santa-ana",
        "bif-bobadilla",
        "antequera-av",
        "bif-archidona",
        "bif-riofrio",
        "loja",
        "bif-tocon",
        "bif-la-chana",
        "granada",
    ]
    # Antequera-Santa Ana la define la línea de Málaga y la de Granada la incorpora
    ours, theirs = granada.node("antequera-santa-ana").spec, malaga.node("antequera-santa-ana").spec
    assert ours.shared and not theirs.shared and ours.position == theirs.position
    assert haversine_km(malaga.line.polyline.coords[-1], granada.line.polyline.coords[0]) < 0.05
    assert malaga.line.polyline.length_km == pytest.approx(96.772, abs=0.2)
    assert granada.line.polyline.length_km == pytest.approx(211.021 - 96.772, abs=0.2)
    assert all(n.offset_m < 20 for n in (*malaga.nodes, *granada.nodes))
    # la entrada a Granada sale de otra relación de OSM, y empalma sin hueco
    assert [p.source_id for p in malaga.line.part_spans] == ["osm-relation-11143233"]
    assert [p.source_id for p in granada.line.part_spans] == [
        "osm-relation-2869549",
        "osm-relation-16228313",
    ]
    assert not granada.line.joins_km and not granada.line.gaps_km
    assert granada.segments[-1].source_id == "osm-relation-16228313"


@pytest.mark.parametrize(
    ("line", "node_id", "reference_pk"),
    [
        (MALAGA, "la-marota", 7.701),
        (MALAGA, "santaella", 34.64),
        (MALAGA, "puente-genil-herrera", 61.434),
        (MALAGA, "antequera-santa-ana", 96.772),
        (GRANADA, "antequera-santa-ana", 96.772),
        (GRANADA, "bif-bobadilla", 105.753),
        (GRANADA, "antequera-av", 113.417),
        (GRANADA, "loja", 159.45),
        (GRANADA, "granada", 211.021),
    ],
)
def test_nodes_sit_on_kilometre_points_that_run_on_from_one_line_to_the_next(
    malaga: BuiltNetwork, granada: BuiltNetwork, line: str, node_id: str, reference_pk: float
) -> None:
    """Los PK de la línea de Granada continúan los de la de Málaga: su origen es el 96,772."""
    net = malaga if line == MALAGA else granada
    assert (malaga.spec.line.pk_origin_km, granada.spec.line.pk_origin_km) == (0.0, 96.772)
    node = net.node(node_id)
    assert node.spec.reference_pk_km == reference_pk
    assert node.km + net.spec.line.pk_origin_km == pytest.approx(reference_pk, abs=0.2)


def test_single_track_starts_at_archidona_and_loja_is_crossed_on_the_old_line(
    malaga: BuiltNetwork, granada: BuiltNetwork
) -> None:
    assert all(s.tracks == 2 and s.max_speed_kmh == 300 for s in malaga.segments)
    tracks = {s.id.split(":", 1)[1]: s.tracks for s in granada.segments}
    assert tracks == {
        "antequera-santa-ana:bif-bobadilla": 2,
        "bif-bobadilla:antequera-av": 2,
        "antequera-av:bif-archidona": 2,
        "bif-archidona:bif-riofrio": 1,
        "bif-riofrio:loja": 1,
        "loja:bif-tocon": 1,
        "bif-tocon:bif-la-chana": 1,
        "bif-la-chana:granada": 1,
    }
    single = sum(s.length_km for s in granada.segments if s.tracks == 1)
    assert single == pytest.approx(81.0, abs=0.1)
    # el valor de cada tramo de vía única lleva su fuente; el de vía doble viene de la línea
    by_id = {s.id.split(":", 1)[1]: s for s in granada.segments}
    assert by_id["bif-archidona:bif-riofrio"].attributes["tracks"].source_id == "boe-b-2025-42383"
    assert by_id["bif-la-chana:granada"].attributes["tracks"].source_id == "osm-relation-16228313"
    assert by_id["antequera-av:bif-archidona"].attributes["tracks"].source_id is None
    # ancho mixto en el paso por Loja y en la entrada a Granada, y en ningún otro tramo
    mixed = {k for k, s in by_id.items() if "gauge" in s.attributes}
    assert mixed == {"bif-riofrio:loja", "loja:bif-tocon", "bif-la-chana:granada"}
    assert all(by_id[k].attributes["gauge"].value == "mixto" for k in mixed)
    # la bajada a Loja, a mucha menos velocidad que el resto de la línea
    down = by_id["bif-riofrio:loja"]
    assert (down.max_speed_kmh, down.typical_speed_kmh) == (95, 65)
    assert by_id["bif-archidona:bif-riofrio"].max_speed_kmh == 300


def test_sources_of_the_lines_are_registered(malaga: BuiltNetwork, granada: BuiltNetwork) -> None:
    sources = {s.id: s for s in load_sources(SOURCES)}
    for net in (malaga, granada):
        for part in net.spec.line.geometry_source.parts:
            source = sources[part.source_id]
            assert source.license == "ODbL 1.0" and source.retrieved_on == "2026-11-12"
            assert source.file == part.file and (DATA_DIR / part.file).exists()
        assert net.spec.line.verification_source_id in sources
        for section in net.spec.attribute_sections:
            assert section.source_id in sources and section.checked_on is not None
        for operator in net.spec.operators:
            assert operator.source_id in sources
    assert "Málaga" in (sources["iryo-web"].coverage or "")


def test_trains_to_malaga_and_to_granada_leave_the_main_line_at_the_junction(
    feed: GtfsFeed, malaga: BuiltNetwork, lines: list[LoadedLine]
) -> None:
    """A la línea de Málaga van los viajes que paran en Córdoba y siguen a Málaga, a Granada o a
    Algeciras. Todos recorren sus cuatro tramos, pare donde pare cada uno."""
    trips = select_trips_for_spec(feed, malaga.spec)
    assert len(trips) == 181
    assert all("50500" in _stops(t) for t in trips)
    assert {t.product for t in trips} == {"AVE", "AVLO", "ALVIA", "AVANT", "Intercity"}
    kinds: dict[str, int] = {}
    for trip in trips:
        passes = _passes(trip, feed, malaga, lines)
        assert len(passes) == 4, trip.train_number
        for p in passes:
            kinds[p.kind] = kinds.get(p.kind, 0) + 1
    assert kinds == {"estimado": 656, "publicado": 68}
    # los Media Distancia que paran en Antequera-Santa Ana por las vías convencionales no entran
    chosen = {t.trip_id for t in trips}
    regional = [t for t in feed.trips.values() if t.product == "MD" and "02003" in _stops(t)]
    assert regional and not chosen & {t.trip_id for t in regional}


def test_a_train_that_does_not_stop_between_cordoba_and_malaga_is_estimated(
    feed: GtfsFeed, ouigo_feed: GtfsFeed, malaga: BuiltNetwork, lines: list[LoadedLine]
) -> None:
    """Córdoba está en la línea Madrid – Sevilla y Málaga fuera de la red cargada: el tren cruza la
    línea entera sin parar, y el paso por sus tramos es estimado, no indeterminado."""
    nonstop = [
        t
        for t in select_trips_for_spec(feed, malaga.spec)
        if not {"02002", "02003", "02030", "05012", "05000"} & set(_stops(t))
    ]
    assert len(nonstop) == 37
    ouigo = select_trips_for_spec(ouigo_feed, malaga.spec)
    assert len(ouigo) == 15
    for source, trip in [(feed, t) for t in nonstop] + [(ouigo_feed, t) for t in ouigo]:
        passes = _passes(trip, source, malaga, lines)
        assert [p.kind for p in passes] == ["estimado"] * 4, trip.train_number
    basis = _passes(ouigo[0], ouigo_feed, malaga, lines)[0].basis
    assert "recorre la línea sin parar en ella" in basis
    assert "está fuera de la red cargada" in basis and "en línea recta" in basis


def test_trains_to_granada_and_the_link_from_malaga(
    feed: GtfsFeed, ouigo_feed: GtfsFeed, granada: BuiltNetwork, lines: list[LoadedLine]
) -> None:
    """A la línea de Granada van los AVE, Alvia y Avant que paran en dos de sus estaciones. Los
    Avant de Málaga entran por la bifurcación Bobadilla y no pasan por Antequera-Santa Ana."""
    trips = select_trips_for_spec(feed, granada.spec)
    assert len(trips) == 63
    assert {t.product for t in trips} == {"AVE", "ALVIA", "AVANT"}
    assert select_trips_for_spec(ouigo_feed, granada.spec) == []
    first = f"{GRANADA}:antequera-santa-ana:bif-bobadilla"
    from_malaga = [t for t in trips if "54413" in _stops(t)]
    assert len(from_malaga) == 6 and all(t.product == "AVANT" for t in from_malaga)
    for trip in trips:
        segments = [p.segment_id for p in _passes(trip, feed, granada, lines)]
        if trip in from_malaga:
            assert len(segments) == 7 and first not in segments, trip.train_number
        else:
            assert len(segments) == 8 and first in segments, trip.train_number
    # fuera quedan los Media Distancia de Antequera AV a Algeciras, que paran en dos estaciones
    # de la línea pero van por las vías convencionales, y los de Granada a Almería
    chosen = {t.trip_id for t in trips}
    by_ronda = [t for t in feed.trips.values() if {"02030", "55007"} <= set(_stops(t))]
    to_almeria = [t for t in feed.trips.values() if _stops(t)[0] == "05000" and t.product == "MD"]
    assert by_ronda and to_almeria
    assert not chosen & {t.trip_id for t in (*by_ronda, *to_almeria)}
