"""Trenes que cambian de línea a mitad de recorrido: los Intercity y Alvia Madrid-Atocha Cercanías –
Andalucía del GTFS van por la convencional hasta Manzanares y por la alta velocidad desde Ciudad Real."""

from __future__ import annotations

import re
from collections.abc import Iterable

import pytest
from conftest import DATA_DIR, FEED, SPEC
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
)
from oniel.network.build import BuiltNetwork, build_network
from oniel.network.spec import NetworkSpec, RouteOverride, StopMapping, load_network_spec
from oniel.sim.passes import LineSegment, SegmentPass, StopCall, resolve_passes
from oniel.validate import loaded_line, validate_all

CONV_SPEC = DATA_DIR / "curated" / "convencional-madrid-alcazar-cordoba.json"
LAV, CONV = "lav-madrid-sevilla", "convencional-madrid-alcazar-cordoba"


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


@pytest.fixture(scope="module")
def conv_spec() -> NetworkSpec:
    return load_network_spec(CONV_SPEC)


@pytest.fixture(scope="module")
def lines(spec: NetworkSpec, conv_spec: NetworkSpec) -> dict[str, tuple[BuiltNetwork, LoadedLine]]:
    nets = {s.line.id: build_network(s, DATA_DIR) for s in (spec, conv_spec)}
    return {k: (net, loaded_line(net)) for k, net in nets.items()}


def passes_for(
    trip: GtfsTrip, feed: GtfsFeed, line_id: str, lines: dict[str, tuple[BuiltNetwork, LoadedLine]]
) -> tuple[list[StopCall], dict[str, SegmentPass]]:
    """Pasos del viaje por una línea, por id corto de tramo («ciudad-real:puertollano»)."""
    net, loaded = lines[line_id]
    others = [ln for k, (_, ln) in lines.items() if k != line_id]
    route = route_for_trip(loaded.spec, trip)
    calls = calls_for_trip(trip, feed, loaded.spec, nodes=loaded.nodes, others=others, route=route)
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


def test_the_diverted_trains_enter_both_lines(
    feed: GtfsFeed, spec: NetworkSpec, conv_spec: NetworkSpec
) -> None:
    lav_trips = select_trips_for_spec(feed, spec)
    conv_trips = select_trips_for_spec(feed, conv_spec)
    assert len(lav_trips) == 335  # ya entraban por el filtro de corredor
    assert len(conv_trips) == 479 + 24  # ahora entran por las reglas de recorrido
    for line_spec, trips in ((spec, lav_trips), (conv_spec, conv_trips)):
        matched = [route_for_trip(line_spec, t) for t in trips]
        by_rule = {
            r.id: sum(1 for m in matched if m is not None and m.override.id == r.id)
            for r in line_spec.route_overrides
        }
        assert by_rule == {
            "atocha-cercanias-ciudad-real-por-manzanares": 20,
            "atocha-cercanias-cordoba-por-manzanares": 4,
        }
    diverted = {t.trip_id for t in conv_trips} & {t.trip_id for t in lav_trips}
    assert len(diverted) == 24
    assert {feed.trips[t].product for t in diverted} == {"Intercity", "ALVIA"}


def test_intercity_10270_runs_madrid_manzanares_on_the_conventional_line(
    feed: GtfsFeed, lines: dict[str, tuple[BuiltNetwork, LoadedLine]]
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
    # 2 h 35 hasta Ciudad Real repartidas entre 196 km por la línea y ~48 km en línea recta
    assert last.exit_s is not None and hm(7, 55) < last.exit_s < hm(8, 15)
    assert last.exit_margin_s == pytest.approx(0.3 * (last.exit_s - hm(6, 0)))
    assert "Ciudad Real está en la línea de alta velocidad Madrid – Sevilla" in last.basis
    assert "sale de esta línea por Manzanares" in last.basis
    assert re.search(r"desde Manzanares, 4\d km en línea recta hasta Ciudad Real", last.basis)
    # Ciudad Real es el propio nodo de enlace con la LAV: no hay nada que medir por la otra línea
    ciudad_real = next(c for c in calls if c.stop_id == "37200")
    assert ciudad_real.exit_node_ids == ("manzanares",) and not ciudad_real.exit_distances


def test_intercity_10270_runs_ciudad_real_sevilla_on_the_high_speed_line(
    feed: GtfsFeed, lines: dict[str, tuple[BuiltNetwork, LoadedLine]]
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


def test_the_return_trip_is_resolved_mirrored(
    feed: GtfsFeed, lines: dict[str, tuple[BuiltNetwork, LoadedLine]]
) -> None:
    """Intercity 10261: Sevilla 5:48 → Córdoba 6:31/6:41 → Ciudad Real 7:42/7:58 → Madrid-Atocha Cercanías 10:44."""
    trip = trip_named(feed, "10261", "51003", "18000")
    _, conv = passes_for(trip, feed, CONV, lines)
    _, lav = passes_for(trip, feed, LAV, lines)
    assert "cinco-casas:manzanares" in conv and "manzanares:valdepenas" not in conv
    assert all(p.km_increasing is False for p in conv.values())
    arrival = conv["madrid-puerta-de-atocha:bif-planetario"]
    assert arrival.exit_s == hm(10, 44) and arrival.exit_margin_s == 0
    assert "entra en esta línea por Manzanares" in conv["cinco-casas:manzanares"].basis
    assert "urda:ciudad-real" not in lav and "majarabique:sevilla-santa-justa" in lav
    assert lav["ciudad-real:puertollano"].exit_s == hm(7, 42)
    assert all(p.km_increasing is False for p in lav.values())


def test_alvia_without_ciudad_real_stop_uses_the_distance_along_the_other_line(
    feed: GtfsFeed, lines: dict[str, tuple[BuiltNetwork, LoadedLine]]
) -> None:
    """Alvia 09366: Madrid-Atocha Cercanías 6:00 → Córdoba 9:45/10:05 → Antequera → Ronda → Algeciras.

    Sin parada en Ciudad Real: en la convencional, Córdoba pasa a ser salida por Manzanares; en la
    LAV, Madrid-Atocha Cercanías es salida por Ciudad Real. La distancia más allá de la salida se
    mide por la otra línea (Manzanares–Ciudad Real en línea recta más la LAV, o la convencional).
    """
    trip = trip_named(feed, "09366", "18000", "55007")  # el que termina en Algeciras
    lav_nodes, conv_nodes = lines[LAV][1].nodes, lines[CONV][1].nodes
    link = haversine_km(
        (conv_nodes["manzanares"].lon, conv_nodes["manzanares"].lat),
        (lav_nodes["ciudad-real"].lon, lav_nodes["ciudad-real"].lat),
    )
    conv_calls, conv = passes_for(trip, feed, CONV, lines)
    cordoba = next(c for c in conv_calls if c.stop_id == "50500")
    assert cordoba.node_id is None and cordoba.exit_node_ids == ("manzanares",)
    by_lav = lav_nodes["cordoba"].km - lav_nodes["ciudad-real"].km
    assert cordoba.exit_distances["manzanares"].km == pytest.approx(link + by_lav, abs=0.01)
    assert cordoba.exit_note == (
        "está en la línea de alta velocidad Madrid – Sevilla, con la que este tren enlaza en"
        " Ciudad Real"
    )
    assert "cinco-casas:manzanares" in conv and "manzanares:valdepenas" not in conv
    assert re.search(
        r"desde Manzanares, 4\d km en línea recta hasta Ciudad Real y 173 km por esa línea hasta"
        r" Córdoba-Julio Anguita;",
        conv["cinco-casas:manzanares"].basis,
    )

    lav_calls, lav = passes_for(trip, feed, LAV, lines)
    madrid = next(c for c in lav_calls if c.stop_id == "18000")
    assert madrid.exit_node_ids == ("ciudad-real",)
    by_conv = conv_nodes["manzanares"].km - conv_nodes["madrid-puerta-de-atocha"].km
    assert madrid.exit_distances["ciudad-real"].km == pytest.approx(link + by_conv, abs=0.01)
    assert "196 km por esa línea hasta Madrid-Atocha Cercanías" in (
        madrid.exit_distances["ciudad-real"].how
    )
    assert ids(lav) >= {"ciudad-real:puertollano", "adamuz:cordoba", "cordoba:bif-malaga"}
    assert "urda:ciudad-real" not in lav and "majarabique:sevilla-santa-justa" not in lav
    assert lav["adamuz:cordoba"].exit_s == hm(9, 45)
    # el mismo reparto en las dos líneas: sale de Manzanares antes de entrar en Ciudad Real
    out_of_conv = conv["cinco-casas:manzanares"].exit_s
    into_lav = lav["ciudad-real:puertollano"].enter_s
    assert out_of_conv is not None and into_lav is not None and out_of_conv < into_lav
    assert hm(7, 35) < out_of_conv < hm(8, 0) < into_lav < hm(8, 25)


def test_validate_reports_the_rules_and_no_problems() -> None:
    reports = {
        p.name: validate_all(p, FEED, DATA_DIR, [SPEC, CONV_SPEC]) for p in (SPEC, CONV_SPEC)
    }
    for r in reports.values():
        assert r["problems"] == []
        assert r["gtfs"]["route_overrides"] == {
            "atocha-cercanias-ciudad-real-por-manzanares": 20,
            "atocha-cercanias-cordoba-por-manzanares": 4,
        }
    assert reports[CONV_SPEC.name]["gtfs"]["trips"] == 503
    assert reports[SPEC.name]["gtfs"]["trips"] == 335
