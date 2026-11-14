"""El enlace de Monforte del Cid (048 de Adif): la vía corta por la que los trenes que salen de
Alicante entran en la línea de alta velocidad de Murcia sin retroceder a la bifurcación de Murcia.

Es un enlace entre dos líneas (``link_of``): cuelga de la de Murcia, pero elige sus trenes con su
propio filtro."""

from __future__ import annotations

import json
from collections import Counter
from pathlib import Path

import pytest
from conftest import (
    DATA_DIR,
    FEED,
    LAV_ALICANTE_SPEC,
    LAV_MURCIA_SPEC,
    LAV_VALENCIA_SPEC,
    LINK_MONFORTE_SPEC,
    SOURCES,
    SPEC,
)

from oniel.geo import haversine_km
from oniel.gtfs.reader import GtfsFeed, GtfsTrip
from oniel.gtfs.trips import (
    LoadedLine,
    calls_for_trip,
    link_far_node,
    select_trips_for_spec,
)
from oniel.network.build import BuiltNetwork, build_network
from oniel.network.spec import NetworkSpec, load_network_spec, load_sources
from oniel.sim.passes import LineSegment, SegmentPass, resolve_passes
from oniel.validate import loaded_line, validate_all

LINE = "enlace-monforte-del-cid"
SEGMENT = f"{LINE}:monforte-del-cid-av:bif-vinalopo"
MURCIA = "lav-monforte-murcia"
ALICANTE = "lav-albacete-alicante"
ALICANTE_STOP = "60911"
#: Estaciones a las que solo se llega por la línea de alta velocidad de Murcia.
ONLY_MURCIA_LINE = {"03410", "03412"}


@pytest.fixture(scope="module")
def spec() -> NetworkSpec:
    return load_network_spec(LINK_MONFORTE_SPEC)


@pytest.fixture(scope="module")
def line(spec: NetworkSpec) -> BuiltNetwork:
    return build_network(spec, DATA_DIR)


@pytest.fixture(scope="module")
def murcia() -> BuiltNetwork:
    return build_network(load_network_spec(LAV_MURCIA_SPEC), DATA_DIR)


@pytest.fixture(scope="module")
def alicante() -> BuiltNetwork:
    return build_network(load_network_spec(LAV_ALICANTE_SPEC), DATA_DIR)


@pytest.fixture(scope="module")
def lines(line: BuiltNetwork, murcia: BuiltNetwork, alicante: BuiltNetwork) -> list[LoadedLine]:
    others = [build_network(load_network_spec(p), DATA_DIR) for p in (LAV_VALENCIA_SPEC, SPEC)]
    return [loaded_line(net) for net in (line, murcia, alicante, *others)]


def _stops(trip: GtfsTrip) -> list[str]:
    return [st.stop_id for st in trip.stop_times]


def _pass(
    trip: GtfsTrip, feed: GtfsFeed, net: BuiltNetwork, lines: list[LoadedLine]
) -> SegmentPass:
    own = loaded_line(net)
    others = [other for other in lines if other.line_id != own.line_id]
    calls = calls_for_trip(trip, feed, net.spec, nodes=own.nodes, others=others)
    assert all(c.node_id or c.exit_node_ids for c in calls), trip.train_number
    segments = [LineSegment(s.id, s.km_from, s.km_to) for s in net.segments]
    passes, resolution = resolve_passes(
        calls, own.nodes, segments, link_far_node=link_far_node(own, others)
    )
    assert resolution == "completa", trip.train_number
    (only,) = passes
    return only


def test_it_is_one_single_track_segment_between_the_two_lines(
    line: BuiltNetwork, murcia: BuiltNetwork, alicante: BuiltNetwork
) -> None:
    """Un tramo de vía única entre el puesto de Monforte del Cid, que es de la línea de Alicante,
    y la bifurcación Vinalopó, que es de la de Murcia."""
    assert line.spec.line.link_of == MURCIA and line.spec.line.bypass_of is None
    assert [n.spec.id for n in line.nodes] == ["monforte-del-cid-av", "bif-vinalopo"]
    assert all(n.spec.shared for n in line.nodes)
    assert "monforte-del-cid-av" not in {n.spec.id for n in murcia.nodes}
    assert "bif-vinalopo" not in {n.spec.id for n in alicante.nodes}
    (segment,) = line.segments
    assert segment.id == SEGMENT
    assert (segment.tracks, segment.max_speed_kmh, segment.typical_speed_kmh) == (1, 100, 100)
    # las vías del enlace miden 2,6 km; los primeros 500 m corren junto a la vía de Alicante
    # dentro del puesto, y el trazado se corta a la altura del nodo: 2,1 km
    assert line.line.polyline.length_km == pytest.approx(2.14, abs=0.02)
    assert segment.length_km == pytest.approx(line.line.polyline.length_km, abs=0.001)
    # empieza a menos de 30 m del nodo de la línea de Alicante y acaba en el de la de Murcia
    coords = line.line.polyline.coords
    monforte, vinalopo = alicante.node("monforte-del-cid-av"), murcia.node("bif-vinalopo")
    assert haversine_km(coords[0], (monforte.lon, monforte.lat)) < 0.03
    assert haversine_km(coords[-1], (vinalopo.lon, vinalopo.lat)) < 0.001


def test_the_geometry_comes_from_the_ways_tagged_048() -> None:
    """El fichero crudo no trae relación: las vías se eligen por su etiqueta ``ref``."""
    spec = load_network_spec(LINK_MONFORTE_SPEC)
    (part,) = spec.line.geometry_source.parts
    assert (part.relation_id, part.way_ref, part.trim) == (None, "048", True)
    raw = json.loads((DATA_DIR / part.file).read_text(encoding="utf-8"))
    ways = [e for e in raw["elements"] if e["type"] == "way"]
    assert len(ways) == 6 and {w["tags"]["ref"] for w in ways} == {"048"}
    assert {w["tags"]["maxspeed"] for w in ways} == {"100"}
    assert {w["tags"]["railway:etcs"] for w in ways} == {"2"}
    sources = {s.id for s in load_sources(SOURCES)}
    assert {part.source_id, *(t.source_id for t in spec.attribute_sections)} <= sources
    values = {t.attribute: t.value for t in spec.attribute_sections}
    assert values == {
        "proteccion_tren": "ertms_n2_asfa",
        "bloqueo": "bca",
        "mando": "sin_dato_publicado",
    }


def test_a_line_is_a_bypass_or_a_link_but_not_both() -> None:
    raw = json.loads(LINK_MONFORTE_SPEC.read_text(encoding="utf-8"))
    raw["line"]["bypass_of"] = MURCIA
    with pytest.raises(ValueError, match="baipás y enlace a la vez"):
        NetworkSpec.model_validate(raw)
    del raw["line"]["bypass_of"]
    raw["line"]["link_of"] = LINE
    with pytest.raises(ValueError, match="enlace de sí misma"):
        NetworkSpec.model_validate(raw)


def test_it_carries_the_trains_between_alicante_and_the_murcia_line(
    feed: GtfsFeed, ouigo_feed: GtfsFeed, spec: NetworkSpec
) -> None:
    """Sus trenes son los que paran en Alicante y en Elche AV o en Callosa de Segura-Cox: los 72
    Avant de Alicante a Murcia y los de Madrid a Murcia que entran en Alicante. Son los de la
    línea de Murcia menos los que la toman en la bifurcación de Murcia."""
    trips = select_trips_for_spec(feed, spec)
    assert Counter(t.product for t in trips) == {"AVANT": 72, "AVE": 12, "AVLO": 7}
    assert all(ALICANTE_STOP in _stops(t) and ONLY_MURCIA_LINE & set(_stops(t)) for t in trips)
    on_murcia = select_trips_for_spec(feed, load_network_spec(LAV_MURCIA_SPEC))
    not_by_alicante = [t for t in on_murcia if ALICANTE_STOP not in _stops(t)]
    assert len(on_murcia) == 111 and len(not_by_alicante) == 20
    assert {t.trip_id for t in trips} == {
        t.trip_id for t in on_murcia if ALICANTE_STOP in _stops(t)
    }
    # de Ouigo, los 5 de sus 7 viajes a Murcia que paran en Alicante
    assert len(select_trips_for_spec(ouigo_feed, spec)) == 5


def test_the_pass_says_which_stop_makes_the_train_take_the_link(
    feed: GtfsFeed, line: BuiltNetwork, lines: list[LoadedLine]
) -> None:
    """El tren cruza el enlace entre Alicante y la primera parada de la línea de Murcia: el paso
    es estimado, se mide por las dos líneas y empieza diciendo por qué va por aquí."""
    trips = select_trips_for_spec(feed, line.spec)
    own = loaded_line(line)
    assert link_far_node(own, [o for o in lines if o is not own]) == "monforte-del-cid-av"
    seen: Counter[str] = Counter()
    for trip in trips:
        p = _pass(trip, feed, line, lines)
        assert p.segment_id == SEGMENT and p.kind == "estimado"
        stops = _stops(trip)
        after = stops[stops.index(ALICANTE_STOP) + 1 :]
        from_alicante = bool(ONLY_MURCIA_LINE & set(after))
        # el kilometraje del enlace crece de Monforte del Cid a Vinalopó
        assert p.km_increasing is from_alicante
        start = "Viene de Alicante" if from_alicante else "Va a Alicante"
        assert p.basis.startswith(start) and ": por eso va por aquí. Estimado:" in p.basis
        assert "en línea recta" not in p.basis
        seen[start] += 1
    assert seen == {"Viene de Alicante": 47, "Va a Alicante": 44}


def test_validate_checks_what_a_link_joins(tmp_path: Path) -> None:
    """`validate` da sus trenes y exige que uno de los dos extremos, y solo uno, sea un nodo de la
    línea de la que cuelga."""
    others = [LAV_MURCIA_SPEC, LAV_ALICANTE_SPEC, LAV_VALENCIA_SPEC, SPEC, LINK_MONFORTE_SPEC]
    report = validate_all(LINK_MONFORTE_SPEC, FEED, DATA_DIR, others)
    assert report["problems"] == []
    assert report["gtfs"]["trips"] == 91
    assert report["gtfs"]["passes"] == {"estimado": 91}
    assert report["gtfs"]["resolution"] == {"completa": 91}
    raw = json.loads(LINK_MONFORTE_SPEC.read_text(encoding="utf-8"))
    raw["line"]["link_of"] = "lav-madrid-sevilla"
    stray = tmp_path / "enlace-monforte-del-cid.json"
    stray.write_text(json.dumps(raw), encoding="utf-8")
    report = validate_all(stray, FEED, DATA_DIR, others)
    assert (
        "es un enlace de lav-madrid-sevilla: uno de sus dos extremos, y solo uno, tiene que ser"
        " un nodo suyo (monforte-del-cid-av y bif-vinalopo)"
    ) in report["problems"]
    raw["line"]["link_of"] = "lav-madrid-barcelona"
    stray.write_text(json.dumps(raw), encoding="utf-8")
    report = validate_all(stray, FEED, DATA_DIR, others)
    assert (
        "es un enlace de lav-madrid-barcelona, que no está entre las líneas cargadas"
        in report["problems"]
    )
