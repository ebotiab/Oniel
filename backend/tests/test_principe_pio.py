"""El acceso de Pozuelo comparte Pinar con la línea 100 y los viajes con sus horarios."""

import json
from pathlib import Path

import pytest
from conftest import DATA_DIR, MADRID_AVILA_VALLADOLID_SPEC

from oniel.gtfs.reader import read_feed
from oniel.gtfs.trips import route_for_trip, select_trips_for_spec
from oniel.network.build import build_network
from oniel.network.spec import load_network_spec
from oniel.validate import validate_all

LINK = "enlace-principe-pio-pinar"
SPEC = DATA_DIR / "curated" / f"{LINK}.json"
PP = "madrid-principe-pio"
PINAR = "pinar-de-las-rozas"


def test_trazado_y_conexiones_del_acceso() -> None:
    spec = load_network_spec(SPEC)
    main = load_network_spec(MADRID_AVILA_VALLADOLID_SPEC)
    net = build_network(spec, DATA_DIR)
    assert net.length_km == pytest.approx(20.48, abs=0.01)
    assert net.line.polyline.length_km == pytest.approx(net.length_km, abs=0.01)
    assert max(n.offset_m for n in net.nodes) < 25
    assert net.node(PINAR).spec.shared
    assert net.node(PINAR).spec.position == next(n.position for n in main.nodes if n.id == PINAR)
    assert spec.line.link_of == main.line.id and spec.line.link_towards == "las-matas"
    assert [c.status for c in spec.connections] == ["no_cargada", "no_cargada"]
    assert "conv-pinar-principe-pio" not in {c.id for c in main.connections}
    for code in ("10000", "10001", "10002", "10005"):
        mapping = main.stop_mappings[code]
        assert [(hop.line, hop.node) for hop in mapping.via] == [(LINK, PINAR)]
    assert all(s.tracks == 2 and s.attributes["gauge"].value == "iberico" for s in net.segments)
    assert all(s.attributes["max_speed_kmh"].value == s.max_speed_kmh for s in net.segments)
    assert max(s.max_speed_kmh or 0 for s in net.segments) == spec.line.max_speed_kmh == 140


@pytest.mark.parametrize(("date", "express"), [("08", 141), ("12", 137), ("17", 140)])
def test_identidad_y_paradas_en_los_tres_horarios(date: str, express: int) -> None:
    spec = load_network_spec(SPEC)
    main = load_network_spec(MADRID_AVILA_VALLADOLID_SPEC)
    feed = read_feed(DATA_DIR / "raw/renfe" / f"google_transit_av_ld_md_2026-11-{date}.zip")
    trips = select_trips_for_spec(feed, spec)
    assert len(trips) == len({t.trip_id for t in trips}) == express + 12
    assert {t.trip_id for t in trips} <= {t.trip_id for t in select_trips_for_spec(feed, main)}
    for trip in trips:
        assert trip.product in {"Regional", "Regional Exprés", "Media Distancia"}
        stops = [s.stop_id for s in trip.stop_times]
        if stops.index("10000") > stops.index("10200"):
            stops.reverse()
        on_access = stops[stops.index("10000") : stops.index("10200") + 1]
        assert on_access in (
            ["10000", "10200"],
            ["10000", "10001", "10002", "10005", "10100", "10200"],
        )
        route = route_for_trip(spec, trip)
        assert route and route.override.from_stop_id == "10000"
        if on_access[1] == "10001":
            assert route.override.to_stop_id == "10100"
            assert route_for_trip(main, trip) is not None
        else:
            assert route.override.to_stop_id == "10200"


def test_la_incorporacion_exige_un_nodo_contiguo_de_la_principal(tmp_path: Path) -> None:
    raw = json.loads(SPEC.read_text())
    raw["line"]["link_towards"] = "avila"
    wrong = tmp_path / SPEC.name
    wrong.write_text(json.dumps(raw))
    report = validate_all(
        wrong,
        DATA_DIR / "raw/renfe/google_transit_av_ld_md_2026-11-08.zip",
        DATA_DIR,
        [MADRID_AVILA_VALLADOLID_SPEC],
    )
    assert any("avila no es un nodo contiguo" in p for p in report["problems"])
