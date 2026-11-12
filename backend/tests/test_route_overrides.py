"""Trenes que cambian de línea a mitad de recorrido: los Intercity y Alvia Madrid-Atocha Cercanías –
Andalucía del GTFS van por la convencional hasta Manzanares, por la línea Manzanares – Ciudad Real
hasta Ciudad Real y por la alta velocidad desde allí."""

from __future__ import annotations

import json
import re
from collections.abc import Iterable
from pathlib import Path

import pytest
from conftest import (
    ALBACETE_SPEC,
    CONV_SPEC,
    DATA_DIR,
    FEED,
    JAEN_SPEC,
    LAV_GRANADA_SPEC,
    LAV_MALAGA_SPEC,
    LBMG_SPEC,
    MZCR_SPEC,
    SPEC,
    SPECS,
)
from pydantic import ValidationError

from oniel.geo import haversine_km
from oniel.gtfs.reader import GtfsFeed, GtfsTrip
from oniel.gtfs.trips import (
    LoadedLine,
    MatchedRoute,
    calls_for_trip,
    calls_on_line,
    match_override,
    route_for_trip,
    select_trips_for_spec,
    via_legs,
)
from oniel.network.build import BuiltNetwork, build_network
from oniel.network.spec import NetworkSpec, RouteOverride, StopMapping, load_network_spec
from oniel.sim.passes import LineSegment, SegmentPass, StopCall, resolve_passes
from oniel.validate import loaded_line, validate_all

LAV, CONV, MZCR = (
    "lav-madrid-sevilla",
    "convencional-madrid-alcazar-cordoba",
    "manzanares-ciudad-real",
)
RULES = {
    "atocha-cercanias-ciudad-real-por-manzanares": 20,
    "atocha-cercanias-cordoba-por-manzanares": 2,
}
#: La convencional tiene además la regla de los trenes de Jaén que solo paran una vez en ella.
JAEN_RULES = {"cordoba-jaen-sin-paradas": 42}


def hm(h: int, m: int) -> int:
    return h * 3600 + m * 60


# --- reglas en abstracto ---------------------------------------------------------------------


def rule(**kwargs: object) -> RouteOverride:
    base: dict[str, object] = {
        "id": "r",
        "description": "prueba",
        "consecutive_stop_ids": ["a", "b", "c"],
    }
    return RouteOverride.model_validate({**base, **kwargs})


def test_match_is_consecutive_and_works_in_both_directions() -> None:
    r = rule(from_stop_id="b")
    assert match_override(r, ["x", "a", "b", "c", "y"]) is False
    assert match_override(r, ["y", "c", "b", "a"]) is True
    assert match_override(r, ["a", "x", "b", "c"]) is None  # no van seguidas
    assert match_override(r, ["a", "b"]) is None


def test_calls_on_line_keeps_the_declared_span_in_the_trip_direction() -> None:
    def call(seq: int, stop: str) -> StopCall:
        return StopCall(seq, stop, stop, 0, 0)

    forward = [call(i, s) for i, s in enumerate(["x", "a", "b", "c", "y"])]
    backward = [call(i, s) for i, s in enumerate(["y", "c", "b", "a", "x"])]
    r = rule(from_stop_id="b")
    assert [c.stop_id for c in calls_on_line(forward, MatchedRoute(r, False))] == ["b", "c", "y"]
    assert [c.stop_id for c in calls_on_line(backward, MatchedRoute(r, True))] == ["y", "c", "b"]
    r = rule(to_stop_id="b")
    assert [c.stop_id for c in calls_on_line(forward, MatchedRoute(r, False))] == ["x", "a", "b"]
    assert [c.stop_id for c in calls_on_line(backward, MatchedRoute(r, True))] == ["b", "a", "x"]
    assert calls_on_line(forward, None) == forward


def test_rule_validation() -> None:
    with pytest.raises(ValidationError, match="misma parada"):
        rule(from_stop_id="a", to_stop_id="a")
    with pytest.raises(ValidationError, match="consecutive_stop_ids"):
        rule(from_stop_id="z")
    with pytest.raises(ValidationError, match="no cambia nada"):
        rule()
    with pytest.raises(ValidationError, match="solo tiene sentido"):
        StopMapping.model_validate({"node": "n", "via": {"line": "l", "node": "m"}})


def test_via_is_one_leg_or_a_chain_of_them() -> None:
    one = StopMapping.model_validate({"exits": ["n"], "via": {"line": "l", "node": "m"}})
    assert [(v.line, v.node) for v in one.via] == [("l", "m")]
    chain = StopMapping.model_validate(
        {"exits": ["n"], "via": [{"line": "l", "node": "m"}, {"line": "k", "node": "o"}]}
    )
    assert [(v.line, v.node) for v in chain.via] == [("l", "m"), ("k", "o")]
    assert StopMapping.model_validate({"exits": ["n"]}).via == []
    with pytest.raises(ValidationError, match="repite la misma línea"):
        StopMapping.model_validate(
            {"exits": ["n"], "via": [{"line": "l", "node": "m"}, {"line": "l", "node": "o"}]}
        )


def test_spec_rejects_rules_that_point_nowhere(spec: NetworkSpec) -> None:
    raw = spec.model_dump(by_alias=True, exclude_none=True)
    bad = {
        **raw,
        "route_overrides": [
            {
                "id": "x",
                "description": "",
                "consecutive_stop_ids": ["18000", "99999"],
                "to_stop_id": "99999",
            }
        ],
    }
    with pytest.raises(ValidationError, match="no tiene asignación"):
        NetworkSpec.model_validate(bad)
    bad = {
        **raw,
        "route_overrides": [
            {
                "id": "x",
                "description": "",
                "consecutive_stop_ids": ["18000", "50500"],
                "stop_mappings": {
                    "18000": {"exits": ["ciudad-real"], "via": {"line": LAV, "node": "cordoba"}}
                },
            }
        ],
    }
    with pytest.raises(ValidationError, match="esta misma línea"):
        NetworkSpec.model_validate(bad)


# --- con los datos reales --------------------------------------------------------------------

Lines = dict[str, tuple[BuiltNetwork, LoadedLine]]


@pytest.fixture(scope="module")
def conv_spec() -> NetworkSpec:
    return load_network_spec(CONV_SPEC)


@pytest.fixture(scope="module")
def mzcr_spec() -> NetworkSpec:
    return load_network_spec(MZCR_SPEC)


@pytest.fixture(scope="module")
def lines(spec: NetworkSpec, conv_spec: NetworkSpec, mzcr_spec: NetworkSpec) -> Lines:
    nets = {s.line.id: build_network(s, DATA_DIR) for s in (spec, conv_spec, mzcr_spec)}
    return {k: (net, loaded_line(net)) for k, net in nets.items()}


def others_of(line_id: str, lines: Lines) -> list[LoadedLine]:
    return [ln for k, (_, ln) in lines.items() if k != line_id]


def passes_for(
    trip: GtfsTrip, feed: GtfsFeed, line_id: str, lines: Lines
) -> tuple[list[StopCall], dict[str, SegmentPass]]:
    """Pasos del viaje por una línea, por id corto de tramo («ciudad-real:puertollano»)."""
    net, loaded = lines[line_id]
    route = route_for_trip(loaded.spec, trip)
    calls = calls_for_trip(
        trip, feed, loaded.spec, nodes=loaded.nodes, others=others_of(line_id, lines), route=route
    )
    segments = [LineSegment(s.id, s.km_from, s.km_to) for s in net.segments]
    passes, resolution = resolve_passes(calls_on_line(calls, route), loaded.nodes, segments)
    assert resolution == "completa"
    return calls, {p.segment_id.split(":", 1)[1]: p for p in passes}


def trip_named(feed: GtfsFeed, number: str, first_stop: str, last_stop: str) -> GtfsTrip:
    trips = [
        t
        for t in feed.trips.values()
        if t.train_number == number
        and t.stop_times[0].stop_id == first_stop
        and t.stop_times[-1].stop_id == last_stop
    ]
    assert len(trips) == 1, number
    return trips[0]


def ids(passes: Iterable[str]) -> set[str]:
    return set(passes)


MZCR_SEGMENTS = {"manzanares:daimiel", "daimiel:almagro", "almagro:ciudad-real"}


def test_the_diverted_trains_enter_the_three_lines(
    feed: GtfsFeed, spec: NetworkSpec, conv_spec: NetworkSpec, mzcr_spec: NetworkSpec
) -> None:
    lav_trips = select_trips_for_spec(feed, spec)
    conv_trips = select_trips_for_spec(feed, conv_spec)
    mzcr_trips = select_trips_for_spec(feed, mzcr_spec)
    assert len(lav_trips) == 317  # ya entraban por el filtro de corredor
    assert len(conv_trips) == 368 + 22 + 42  # los 22 y los 42 de Jaén entran por las reglas
    assert len(mzcr_trips) == 124 + 22  # no paran en la línea: también por las reglas
    for line_spec, trips in ((spec, lav_trips), (conv_spec, conv_trips), (mzcr_spec, mzcr_trips)):
        matched = [route_for_trip(line_spec, t) for t in trips]
        by_rule = {
            r.id: sum(1 for m in matched if m is not None and m.override.id == r.id)
            for r in line_spec.route_overrides
        }
        assert by_rule == (RULES | JAEN_RULES if line_spec is conv_spec else RULES)
    diverted = (
        {t.trip_id for t in conv_trips}
        & {t.trip_id for t in lav_trips}
        & {t.trip_id for t in mzcr_trips}
    )
    assert len(diverted) == 22
    assert {feed.trips[t].product for t in diverted} == {"Intercity", "ALVIA"}


def test_intercity_10270_runs_madrid_manzanares_on_the_conventional_line(
    feed: GtfsFeed, lines: Lines
) -> None:
    """Madrid-Atocha Cercanías 6:00 → Ciudad Real 8:35/8:50 → Córdoba 9:45/9:50 → Sevilla 10:53."""
    trip = trip_named(feed, "10270", "18000", "51003")
    calls, conv = passes_for(trip, feed, CONV, lines)
    conv_nodes = [n.spec.id for n in lines[CONV][0].nodes]
    up_to_manzanares = {f"{a}:{b}" for a, b in zip(conv_nodes, conv_nodes[1:], strict=False)}
    up_to_manzanares = {
        s
        for s in up_to_manzanares
        if conv_nodes.index(s.split(":")[0]) < conv_nodes.index("manzanares")
    }
    assert ids(conv) == up_to_manzanares  # 11 tramos, ninguno más allá de Manzanares
    assert all(p.kind == "estimado" and p.km_increasing for p in conv.values())
    first, last = conv["madrid-puerta-de-atocha:bif-planetario"], conv["cinco-casas:manzanares"]
    assert first.enter_s == hm(6, 0) and first.enter_margin_s == 0  # sale a hora publicada
    # 2 h 35 hasta Ciudad Real repartidas entre 196,1 km por esta línea y 64,4 km por la de
    # Manzanares a Ciudad Real: sale de Manzanares a los 155 × 196,1 / 260,5 = 116,7 min
    mzcr_km = lines[MZCR][0].line.polyline.length_km
    by_conv = lines[CONV][1].nodes["manzanares"].km
    expected = hm(6, 0) + 155 * 60 * by_conv / (by_conv + mzcr_km)
    assert last.exit_s is not None and last.exit_s == pytest.approx(expected, abs=1)
    assert hm(7, 56) < expected < hm(7, 58)
    assert last.exit_margin_s == pytest.approx(0.3 * (last.exit_s - hm(6, 0)))
    assert "Ciudad Real está en la línea convencional Manzanares – Ciudad Real;" in last.basis
    assert "sale de esta línea por Manzanares" in last.basis
    assert (
        "usa 196 km por la línea y, desde Manzanares, 64 km por esa línea hasta Ciudad Real;"
        in (last.basis)
    )
    assert not any("línea recta" in p.basis for p in conv.values())
    # Ciudad Real se alcanza por la línea de Manzanares a Ciudad Real, entera
    ciudad_real = next(c for c in calls if c.stop_id == "37200")
    assert ciudad_real.exit_node_ids == ("manzanares",)
    assert ciudad_real.exit_distances["manzanares"].km == pytest.approx(mzcr_km, abs=0.01)


def test_intercity_10270_crosses_manzanares_ciudad_real_on_the_third_line(
    feed: GtfsFeed, lines: Lines
) -> None:
    """No para en Daimiel ni en Almagro: entra por Manzanares a la hora en que sale de la
    convencional y llega a Ciudad Real a su hora publicada."""
    trip = trip_named(feed, "10270", "18000", "51003")
    _, conv = passes_for(trip, feed, CONV, lines)
    calls, mzcr = passes_for(trip, feed, MZCR, lines)
    assert ids(mzcr) == MZCR_SEGMENTS
    assert all(p.kind == "estimado" and p.km_increasing for p in mzcr.values())
    first, last = mzcr["manzanares:daimiel"], mzcr["almagro:ciudad-real"]
    assert first.enter_s == pytest.approx(conv["cinco-casas:manzanares"].exit_s, abs=1)
    assert last.exit_s == hm(8, 35) and last.exit_margin_s == 0  # llega a hora publicada
    assert first.enter_s is not None
    assert first.enter_margin_s == pytest.approx(0.3 * (hm(8, 35) - first.enter_s))
    assert (
        "Madrid-Atocha Cercanías está en la línea convencional Madrid – Alcázar de San Juan –"
        " Córdoba; el tren entra en esta línea por Manzanares" in first.basis
    )
    assert "usa 64 km por la línea y, desde Manzanares, 196 km por esa línea hasta" in first.basis
    assert not any("línea recta" in p.basis for p in mzcr.values())
    madrid = next(c for c in calls if c.stop_id == "18000")
    assert madrid.node_id is None and madrid.exit_node_ids == ("manzanares",)


def test_intercity_10270_runs_ciudad_real_sevilla_on_the_high_speed_line(
    feed: GtfsFeed, lines: Lines
) -> None:
    trip = trip_named(feed, "10270", "18000", "51003")
    _, lav = passes_for(trip, feed, LAV, lines)
    assert ids(lav) == {
        "ciudad-real:puertollano",
        "puertollano:villanueva-de-cordoba",
        "villanueva-de-cordoba:adamuz",
        "adamuz:cordoba",
        "cordoba:bif-malaga",
        "bif-malaga:majarabique",
        "majarabique:sevilla-santa-justa",
    }
    assert "urda:ciudad-real" not in lav and "bif-la-sagra:urda" not in lav
    cr_pu, ad_co = lav["ciudad-real:puertollano"], lav["adamuz:cordoba"]
    assert cr_pu.enter_s == hm(8, 50) and cr_pu.enter_margin_s == 0
    assert ad_co.exit_s == hm(9, 45) and ad_co.exit_margin_s == 0
    assert lav["majarabique:sevilla-santa-justa"].exit_s == hm(10, 53)


def test_the_return_trip_is_resolved_mirrored(feed: GtfsFeed, lines: Lines) -> None:
    """Intercity 10261: Sevilla 5:48 → Córdoba 6:31/6:41 → Ciudad Real 7:42/7:58 → Madrid-Atocha Cercanías 10:44."""
    trip = trip_named(feed, "10261", "51003", "18000")
    _, conv = passes_for(trip, feed, CONV, lines)
    _, mzcr = passes_for(trip, feed, MZCR, lines)
    _, lav = passes_for(trip, feed, LAV, lines)
    assert "cinco-casas:manzanares" in conv and "manzanares:valdepenas" not in conv
    assert all(p.km_increasing is False for p in conv.values())
    arrival = conv["madrid-puerta-de-atocha:bif-planetario"]
    assert arrival.exit_s == hm(10, 44) and arrival.exit_margin_s == 0
    assert "entra en esta línea por Manzanares" in conv["cinco-casas:manzanares"].basis
    # la línea de Manzanares a Ciudad Real, de Ciudad Real hacia Manzanares
    assert ids(mzcr) == MZCR_SEGMENTS
    assert all(p.km_increasing is False for p in mzcr.values())
    departure = mzcr["almagro:ciudad-real"]
    assert departure.enter_s == hm(7, 58) and departure.enter_margin_s == 0
    assert "sale de esta línea por Manzanares" in mzcr["manzanares:daimiel"].basis
    assert mzcr["manzanares:daimiel"].exit_s == pytest.approx(
        conv["cinco-casas:manzanares"].enter_s, abs=1
    )
    assert "urda:ciudad-real" not in lav and "majarabique:sevilla-santa-justa" in lav
    assert lav["ciudad-real:puertollano"].exit_s == hm(7, 42)
    assert all(p.km_increasing is False for p in lav.values())


def test_alvia_without_ciudad_real_stop_is_measured_along_the_three_lines(
    feed: GtfsFeed, lines: Lines
) -> None:
    """Alvia 09366: Madrid-Atocha Cercanías 6:00 → Córdoba 9:45/10:05 → Antequera → Ronda → Algeciras.

    Sin parada en Ciudad Real, las 3 h 45 se reparten entre las tres líneas: 196,1 km por la
    convencional hasta Manzanares, 64,4 km por la de Manzanares a Ciudad Real y 172,9 km por la
    alta velocidad hasta Córdoba. En la convencional, Córdoba es una salida por Manzanares; en la
    LAV, Madrid-Atocha Cercanías es una salida por Ciudad Real, y en los dos casos el camino cruza
    la tercera línea. En esta, el tren pasa de largo: las dos paradas están en las otras.
    """
    trip = trip_named(feed, "09366", "18000", "55020")  # termina en Algeciras
    lav_nodes, conv_nodes = lines[LAV][1].nodes, lines[CONV][1].nodes
    mzcr_km = lines[MZCR][0].line.polyline.length_km
    by_conv = conv_nodes["manzanares"].km - conv_nodes["madrid-puerta-de-atocha"].km
    by_lav = lav_nodes["cordoba"].km - lav_nodes["ciudad-real"].km
    total = by_conv + mzcr_km + by_lav
    at_manzanares = hm(6, 0) + 225 * 60 * by_conv / total
    at_ciudad_real = hm(6, 0) + 225 * 60 * (by_conv + mzcr_km) / total
    assert hm(7, 40) < at_manzanares < hm(7, 44) and hm(8, 13) < at_ciudad_real < hm(8, 17)

    conv_calls, conv = passes_for(trip, feed, CONV, lines)
    cordoba = next(c for c in conv_calls if c.stop_id == "50500")
    assert cordoba.node_id is None and cordoba.exit_node_ids == ("manzanares",)
    assert cordoba.exit_distances["manzanares"].km == pytest.approx(mzcr_km + by_lav, abs=0.01)
    assert cordoba.exit_note == "está en la línea de alta velocidad Madrid – Sevilla"
    assert "cinco-casas:manzanares" in conv and "manzanares:valdepenas" not in conv
    assert (
        "desde Manzanares, 64 km por la línea convencional Manzanares – Ciudad Real hasta Ciudad"
        " Real y 173 km por la línea de alta velocidad Madrid – Sevilla hasta Córdoba-Julio"
        " Anguita;" in conv["cinco-casas:manzanares"].basis
    )
    assert conv["cinco-casas:manzanares"].exit_s == pytest.approx(at_manzanares, abs=1)

    mzcr_calls, mzcr = passes_for(trip, feed, MZCR, lines)
    assert [c.stop_id for c in mzcr_calls if c.node_id is not None] == []  # no para en la línea
    assert ids(mzcr) == MZCR_SEGMENTS
    assert all(p.kind == "estimado" and p.km_increasing for p in mzcr.values())
    assert mzcr["manzanares:daimiel"].enter_s == pytest.approx(at_manzanares, abs=1)
    assert mzcr["almagro:ciudad-real"].exit_s == pytest.approx(at_ciudad_real, abs=1)
    # margen: 30 % del mayor de los tiempos fuera de la línea (aquí, el de Madrid a Manzanares)
    margin = 0.3 * max(at_manzanares - hm(6, 0), hm(9, 45) - at_ciudad_real)
    assert all(
        p.enter_margin_s == pytest.approx(margin, abs=1)
        and p.exit_margin_s == pytest.approx(margin, abs=1)
        for p in mzcr.values()
    )
    basis = mzcr["daimiel:almagro"].basis
    assert "recorre la línea sin parar en ella; entra por Manzanares y sale por Ciudad Real" in (
        basis
    )
    assert "usa 196 km antes de Manzanares, 64 km por la línea y 173 km después de Ciudad Real" in (
        basis
    )

    lav_calls, lav = passes_for(trip, feed, LAV, lines)
    madrid = next(c for c in lav_calls if c.stop_id == "18000")
    assert madrid.exit_node_ids == ("ciudad-real",)
    assert madrid.exit_distances["ciudad-real"].km == pytest.approx(mzcr_km + by_conv, abs=0.01)
    assert madrid.exit_distances["ciudad-real"].how == (
        "64 km por la línea convencional Manzanares – Ciudad Real hasta Manzanares y 196 km por"
        " la línea convencional Madrid – Alcázar de San Juan – Córdoba hasta Madrid-Atocha"
        " Cercanías"
    )
    assert ids(lav) >= {"ciudad-real:puertollano", "adamuz:cordoba", "cordoba:bif-malaga"}
    assert "urda:ciudad-real" not in lav and "majarabique:sevilla-santa-justa" not in lav
    assert lav["ciudad-real:puertollano"].enter_s == pytest.approx(at_ciudad_real, abs=1)
    assert lav["adamuz:cordoba"].exit_s == hm(9, 45)


def test_no_diverted_train_is_explained_with_a_straight_line(
    feed: GtfsFeed, spec: NetworkSpec, lines: Lines
) -> None:
    """Entre Madrid y Córdoba los 22 viajes se miden por las líneas cargadas, nunca en línea recta."""
    diverted = [t for t in select_trips_for_spec(feed, spec) if route_for_trip(spec, t)]
    assert len(diverted) == 22
    lav_nodes = [n.spec.id for n in lines[LAV][0].nodes]
    up_to_cordoba = {
        f"{a}:{b}"
        for a, b in zip(lav_nodes, lav_nodes[1:], strict=False)
        if lav_nodes.index(b) <= lav_nodes.index("cordoba")
    }
    for trip in diverted:
        for line_id in (CONV, MZCR, LAV):
            _, passes = passes_for(trip, feed, line_id, lines)
            checked = {
                k: p for k, p in passes.items() if line_id != LAV or k in up_to_cordoba
            }  # más allá de Córdoba, Málaga o Algeciras sí quedan fuera de la red
            assert checked, (trip.train_number, line_id)
            assert not any("línea recta" in p.basis for p in checked.values())
            assert all(p.kind in ("publicado", "estimado") for p in checked.values())
        _, mzcr = passes_for(trip, feed, MZCR, lines)
        assert ids(mzcr) == MZCR_SEGMENTS


def test_an_exit_that_is_not_the_joining_node_adds_the_straight_link(
    feed: GtfsFeed, lines: Lines
) -> None:
    """Sin la tercera línea, el camino de Manzanares a Córdoba enlazaría con la LAV en Ciudad
    Real a 47 km en línea recta: la regla general sigue cubriendo ese caso."""
    trip = trip_named(feed, "09366", "18000", "55020")
    _, loaded = lines[CONV]
    override = RouteOverride.model_validate(
        {
            "id": "prueba",
            "description": "prueba",
            "consecutive_stop_ids": ["18000", "50500"],
            "to_stop_id": "50500",
            "stop_mappings": {
                "50500": {"exits": ["manzanares"], "via": {"line": LAV, "node": "ciudad-real"}}
            },
        }
    )
    calls = calls_for_trip(
        trip,
        feed,
        loaded.spec,
        nodes=loaded.nodes,
        others=others_of(CONV, lines),
        route=MatchedRoute(override, False),
    )
    cordoba = next(c for c in calls if c.stop_id == "50500")
    lav_nodes = lines[LAV][1].nodes
    link = haversine_km(
        (loaded.nodes["manzanares"].lon, loaded.nodes["manzanares"].lat),
        (lav_nodes["ciudad-real"].lon, lav_nodes["ciudad-real"].lat),
    )
    by_lav = lav_nodes["cordoba"].km - lav_nodes["ciudad-real"].km
    assert cordoba.exit_distances["manzanares"].km == pytest.approx(link + by_lav, abs=0.01)
    assert re.fullmatch(
        r"4\d km en línea recta hasta Ciudad Real y 173 km por esa línea hasta Córdoba-Julio"
        r" Anguita",
        cordoba.exit_distances["manzanares"].how,
    )
    assert cordoba.exit_note == (
        "está en la línea de alta velocidad Madrid – Sevilla, con la que este tren enlaza en"
        " Ciudad Real"
    )


def test_via_legs_say_why_a_chain_cannot_be_followed(lines: Lines) -> None:
    others = others_of(CONV, lines)

    def legs(stop_id: str, via: list[dict[str, str]]) -> object:
        mapping = StopMapping.model_validate({"exits": ["manzanares"], "via": via})
        return via_legs(stop_id, mapping, others)

    good = legs(
        "50500", [{"line": MZCR, "node": "manzanares"}, {"line": LAV, "node": "ciudad-real"}]
    )
    assert isinstance(good, list)
    assert [(leg.line.line_id, leg.join.id, leg.end.id) for leg in good] == [
        (MZCR, "manzanares", "ciudad-real"),
        (LAV, "ciudad-real", "cordoba"),
    ]
    assert legs("50500", [{"line": "otra", "node": "x"}]) == (
        "la línea otra no está entre las líneas cargadas"
    )
    assert legs("50500", [{"line": MZCR, "node": "cordoba"}]) == (
        f"cordoba no es un nodo de la línea {MZCR}"
    )
    # el enlace con el trecho siguiente tiene que ser un nodo de las dos líneas
    assert legs(
        "50500", [{"line": MZCR, "node": "manzanares"}, {"line": LAV, "node": "cordoba"}]
    ) == (f"cordoba no es un nodo de la línea {MZCR}")
    assert legs("94002", [{"line": LAV, "node": "ciudad-real"}]) == (
        f"la parada no es un nodo de la línea {LAV}"
    )


def test_validate_reports_the_rules_and_no_problems() -> None:
    reports = {p.name: validate_all(p, FEED, DATA_DIR, SPECS) for p in SPECS}
    expected = {
        SPEC.name: RULES,
        CONV_SPEC.name: RULES | JAEN_RULES,
        MZCR_SPEC.name: RULES,
        JAEN_SPEC.name: {},
        # la línea de Linares-Baeza a Granada tiene su propia regla: los trenes a Almería que
        # paran en Moreda salen por la estación y no por la bifurcación
        LBMG_SPEC.name: {"linares-baeza-almeria-por-moreda": 4},
        ALBACETE_SPEC.name: {},
        LAV_MALAGA_SPEC.name: {},
        LAV_GRANADA_SPEC.name: {},
    }
    for name, r in reports.items():
        assert r["problems"] == []
        assert r["gtfs"]["route_overrides"] == expected[name]
        assert "indeterminado" not in r["gtfs"]["passes"]
    granada = reports[LBMG_SPEC.name]["gtfs"]
    assert granada["trips"] == 38 and granada["passes"] == {"publicado": 18, "estimado": 62}
    assert reports[CONV_SPEC.name]["gtfs"]["trips"] == 432
    assert reports[SPEC.name]["gtfs"]["trips"] == 317
    assert reports[MZCR_SPEC.name]["gtfs"]["trips"] == 146
    assert reports[MZCR_SPEC.name]["gtfs"]["passes"] == {"publicado": 124 * 3, "estimado": 22 * 3}


def test_validate_reports_a_via_that_cannot_be_followed(tmp_path: Path) -> None:
    """Un «via» mal encadenado volvería a la línea recta sin avisar: validate lo señala."""
    raw = json.loads(CONV_SPEC.read_text(encoding="utf-8"))
    rule = raw["route_overrides"][1]
    rule["stop_mappings"]["50500"]["via"] = [
        {"line": MZCR, "node": "manzanares"},
        {"line": LAV, "node": "cordoba"},
    ]
    broken = tmp_path / CONV_SPEC.name
    broken.write_text(json.dumps(raw, ensure_ascii=False), encoding="utf-8")
    report = validate_all(
        broken, FEED, DATA_DIR, [SPEC, MZCR_SPEC, JAEN_SPEC, LBMG_SPEC, ALBACETE_SPEC]
    )
    assert report["problems"] == [
        f"la regla {rule['id']}: el «via» de la parada 50500 no se sostiene: cordoba no es un"
        f" nodo de la línea {MZCR}"
    ]
