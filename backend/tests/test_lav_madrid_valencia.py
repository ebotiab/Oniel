"""La línea de alta velocidad Madrid – Cuenca – Valencia (Adif 040), de la bifurcación de Torrejón
de Velasco, que comparte con la de Sevilla, a València-Joaquín Sorolla."""

from __future__ import annotations

import pytest
from conftest import DATA_DIR, LAV_VALENCIA_SPEC, SOURCES

from oniel.gtfs.reader import GtfsFeed, GtfsTrip
from oniel.gtfs.trips import (
    LoadedLine,
    calls_for_trip,
    calls_on_line,
    route_for_trip,
    select_trips_for_spec,
)
from oniel.network.build import BuiltNetwork, build_network
from oniel.network.spec import NetworkSpec, load_network_spec, load_sources
from oniel.sim.passes import LineSegment, SegmentPass, resolve_passes
from oniel.validate import loaded_line

#: Entre qué dos nodos recorre la línea cada viaje del fichero de pruebas, y cuántos son.
SHAPES = {
    # Madrid – Valencia, pare o no en Cuenca y en Requena-Utiel
    ("bif-torrejon-de-velasco", "valencia-joaquin-sorolla"): 189,
    # Madrid – Albacete, Alicante y Murcia: dejan la línea en la bifurcación de Albacete
    ("bif-albacete", "bif-torrejon-de-velasco"): 215,
    # Avant de Requena-Utiel a Valencia
    ("requena-utiel", "valencia-joaquin-sorolla"): 61,
    # Valencia – Sevilla, por el enlace de la bifurcación Blancales
    ("bif-blancales", "valencia-joaquin-sorolla"): 4,
}
#: PK del nodo de la bifurcación: el arranque de la línea 040 (34,698) más los 1,374 km que hay
#: hasta el nodo que ya tenía la línea de Sevilla.
PK_ORIGIN = 36.072


@pytest.fixture(scope="module")
def valencia() -> BuiltNetwork:
    return build_network(load_network_spec(LAV_VALENCIA_SPEC), DATA_DIR)


@pytest.fixture(scope="module")
def lines(built: BuiltNetwork, valencia: BuiltNetwork) -> list[LoadedLine]:
    return [loaded_line(built), loaded_line(valencia)]


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


def _short(passes: list[SegmentPass]) -> list[str]:
    return [p.segment_id.split(":", 1)[1] for p in passes]


def test_the_line_leaves_the_seville_line_at_torrejon_and_ends_in_valencia(
    valencia: BuiltNetwork, spec: NetworkSpec
) -> None:
    """Sale del nodo que ya tenía la línea Madrid – Sevilla, sin moverlo, y la conexión a trazos
    que anunciaba el camino de Levante ya no está en ella."""
    junction = next(n for n in spec.nodes if n.id == "bif-torrejon-de-velasco")
    ours = valencia.node("bif-torrejon-de-velasco")
    assert not junction.shared and ours.spec.shared
    assert ours.spec.position == junction.position and ours.km < 0.05
    assert "lav-madrid-levante" not in {c.id for c in spec.connections}
    assert [n.spec.id for n in valencia.nodes] == [
        "bif-torrejon-de-velasco",
        "bif-blancales",
        "valdemoro-av",
        "villarrubia-de-santiago-av",
        "tarancon-av",
        "horcajada",
        "cuenca-fernando-zobel",
        "monteagudo-de-las-salinas",
        "bif-albacete",
        "iniesta",
        "requena-utiel",
        "siete-aguas-av",
        "valencia-joaquin-sorolla",
    ]
    stations = [n.spec.id for n in valencia.nodes if n.spec.kind == "estacion"]
    assert stations == ["cuenca-fernando-zobel", "requena-utiel", "valencia-joaquin-sorolla"]
    assert {n.spec.id for n in valencia.nodes if n.spec.rank == "principal"} == {
        "bif-torrejon-de-velasco",
        "bif-albacete",
        *stations,
    }
    assert valencia.line.polyline.length_km == pytest.approx(361.0, abs=0.2)
    assert [p.source_id for p in valencia.line.part_spans] == ["osm-relation-11146316"]
    assert not valencia.line.gaps_km and not valencia.line.joins_km
    assert all(n.offset_m < 60 for n in valencia.nodes)
    # lo que sigue sin cargar: el enlace con la línea de Sevilla y el ramal de Albacete; la
    # línea de Castelló ya está cargada y no sale a trazos
    assert {c.node_id for c in valencia.spec.connections} == {
        "bif-blancales",
        "bif-albacete",
    }


@pytest.mark.parametrize(
    ("node_id", "reference_pk"),
    [
        ("bif-blancales", 40.273),
        ("valdemoro-av", 42.49),
        ("villarrubia-de-santiago-av", 84.587),
        ("tarancon-av", 118.59),
        ("horcajada", 164.76),
        ("cuenca-fernando-zobel", 195.1),
        ("monteagudo-de-las-salinas", 224.67),
        ("bif-albacete", 248.1),
        ("iniesta", 267.05),
        ("requena-utiel", 327.45),
        ("siete-aguas-av", 345.12),
        ("valencia-joaquin-sorolla", 397.55),
    ],
)
def test_nodes_sit_on_the_kilometre_points_counted_from_chamartin(
    valencia: BuiltNetwork, node_id: str, reference_pk: float
) -> None:
    """Los PK se cuentan desde Madrid-Chamartín; el nodo de la bifurcación es el 36,072."""
    assert valencia.spec.line.pk_origin_km == PK_ORIGIN
    node = valencia.node(node_id)
    assert node.spec.reference_pk_km == reference_pk
    assert node.km + PK_ORIGIN == pytest.approx(reference_pk, abs=0.6)


def test_double_track_at_300_and_the_signalling_of_the_map(valencia: BuiltNetwork) -> None:
    assert all(s.tracks == 2 for s in valencia.segments)
    by_id = {s.id.split(":", 1)[1]: s for s in valencia.segments}
    assert len(by_id) == 12
    assert [s.max_speed_kmh for s in valencia.segments] == [285, 285, *[300] * 10]
    for segment in valencia.segments:
        attributes = segment.attributes
        assert attributes["proteccion_tren"].value == "ertms_n1_asfa"
        assert attributes["mando"].value == "sin_dato_publicado"
        for name in ("proteccion_tren", "bloqueo", "mando"):
            assert attributes[name].source_id == "adif-declaracion-red-2026-mapas"
    # el bloqueo cambia a la entrada de Valencia, donde no hay nodo
    blocks = {k: s.attributes["bloqueo"].value for k, s in by_id.items()}
    assert blocks.pop("siete-aguas-av:valencia-joaquin-sorolla") == "bca_bsl"
    assert set(blocks.values()) == {"bca"}


def test_sources_of_the_line_are_registered(valencia: BuiltNetwork) -> None:
    sources = {s.id: s for s in load_sources(SOURCES)}
    for part in valencia.spec.line.geometry_source.parts:
        source = sources[part.source_id]
        assert source.license == "ODbL 1.0" and source.retrieved_on == "2026-11-12"
        assert source.file == part.file and (DATA_DIR / part.file).exists()
    assert valencia.spec.line.verification_source_id == "wikipedia-lav-madrid-levante"
    assert "wikipedia-lav-madrid-levante" in sources
    for section in valencia.spec.attribute_sections:
        assert section.source_id in sources and section.checked_on is not None
    operators = {o.id: o for o in valencia.spec.operators}
    assert all(o.source_id in sources for o in operators.values())
    assert operators["iryo"].timetable == "no_publicado"
    assert operators["renfe"].timetable == operators["ouigo"].timetable == "cargado"
    assert "Valencia" in (sources["iryo-web"].coverage or "")


def test_trains_of_valencia_and_of_alicante_share_the_line_as_far_as_the_albacete_junction(
    feed: GtfsFeed, valencia: BuiltNetwork, lines: list[LoadedLine]
) -> None:
    """Entran los trenes que paran en Cuenca o en Requena-Utiel y, por las reglas de recorrido,
    los que recorren la línea sin parar en ninguna de las dos. Los de Albacete y Alicante la
    dejan en la bifurcación de Albacete; los Avant de Requena-Utiel solo llegan a Valencia."""
    trips = select_trips_for_spec(feed, valencia.spec)
    assert len(trips) == 469
    products: dict[str, int] = {}
    rules: dict[str, int] = {}
    shapes: dict[tuple[str, str], int] = {}
    kinds: set[str] = set()
    for trip in trips:
        products[trip.product or ""] = products.get(trip.product or "", 0) + 1
        route = route_for_trip(valencia.spec, trip)
        if route is not None:
            rules[route.override.id] = rules.get(route.override.id, 0) + 1
        passes = _passes(trip, feed, valencia, lines)
        kinds |= {p.kind for p in passes}
        short = _short(passes)
        ends = sorted({short[0].split(":")[0], short[-1].split(":")[1]})
        shapes[(ends[0], ends[1])] = shapes.get((ends[0], ends[1]), 0) + 1
    assert products == {"AVE": 299, "AVLO": 61, "AVANT": 85, "ALVIA": 24}
    assert rules == {
        "madrid-valencia-sin-parada": 62,
        "madrid-albacete-sin-parada": 31,
        "madrid-alicante-sin-parada": 27,
    }
    # entre dos estaciones siempre hay un PAET o una bifurcación: ningún paso es publicado
    assert kinds == {"estimado"}
    assert shapes == SHAPES
    # fuera quedan los Media Distancia de Madrid a Albacete por Alcázar de San Juan
    chosen = {t.trip_id for t in trips}
    by_alcazar = [t for t in feed.trips.values() if {"17000", "60400", "60600"} <= set(_stops(t))]
    assert by_alcazar and not chosen & {t.trip_id for t in by_alcazar}


def test_a_train_from_chamartin_to_alicante_crosses_the_line_without_stopping(
    feed: GtfsFeed, ouigo_feed: GtfsFeed, valencia: BuiltNetwork, lines: list[LoadedLine]
) -> None:
    """Madrid-Chamartín y Alicante están fuera de la red cargada, pero de las dos se sabe cuánta
    vía hay hasta la línea (36 km y 238 km): el paso por los ocho tramos que van de la
    bifurcación de Torrejón de Velasco a la de Albacete es estimado, no indeterminado."""
    nonstop = [t for t in select_trips_for_spec(feed, valencia.spec) if "03208" not in _stops(t)]
    direct = [t for t in nonstop if {"17000", "60911"} <= set(_stops(t)) and len(_stops(t)) == 2]
    assert len(direct) == 27
    passes = _passes(direct[0], feed, valencia, lines)
    assert _short(passes)[0] == "bif-torrejon-de-velasco:bif-blancales"
    assert _short(passes)[-1] == "monteagudo-de-las-salinas:bif-albacete"
    assert [p.kind for p in passes] == ["estimado"] * 8
    basis = passes[0].basis
    assert "recorre la línea sin parar en ella" in basis
    assert "36 km antes de Bifurcación Torrejón de Velasco" in basis
    assert "238 km después de Bifurcación Albacete" in basis
    assert "línea recta" not in basis
    # los de Ouigo a Albacete y Murcia, igual
    ouigo = select_trips_for_spec(ouigo_feed, valencia.spec)
    assert len(ouigo) == 22
    crossing = [t for t in ouigo if not {"03208", "03216"} & set(_stops(t))]
    assert len(crossing) == 5
    for trip in crossing:
        assert [p.kind for p in _passes(trip, ouigo_feed, valencia, lines)] == ["estimado"] * 8


def test_trains_between_valencia_and_seville_join_at_blancales(
    feed: GtfsFeed, valencia: BuiltNetwork, lines: list[LoadedLine]
) -> None:
    """Los AVE de Valencia a Sevilla paran en Cuenca y en Ciudad Real sin pasar por Madrid: dejan
    la línea por el enlace de la bifurcación Blancales, que lleva a la de Yeles en la línea de
    Sevilla, y no recorren su primer tramo."""
    trips = [t for t in select_trips_for_spec(feed, valencia.spec) if "51003" in _stops(t)]
    assert len(trips) == 4
    for trip in trips:
        short = _short(_passes(trip, feed, valencia, lines))
        assert len(short) == 11 and "bif-torrejon-de-velasco:bif-blancales" not in short
    # Ciudad Real está en la línea de Sevilla: la distancia hasta ella se mide por esa línea
    basis = _passes(trips[0], feed, valencia, lines)[0].basis
    assert "Ciudad Real está en la línea de alta velocidad Madrid – Sevilla" in basis
    assert "línea recta hasta Bifurcación Yeles" in basis
