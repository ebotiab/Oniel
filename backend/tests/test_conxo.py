"""Geometría, lados de las agujas y circulaciones fechadas de la 842."""

from __future__ import annotations

import datetime as dt
import json
from collections import Counter
from pathlib import Path

import pytest
from conftest import CONXO_SPEC, DATA_DIR, EJE_ATLANTICO_SPEC, LAV_SANTIAGO_SPEC

from oniel.gtfs.reader import read_feed
from oniel.gtfs.trips import route_for_trip, select_trips_for_spec
from oniel.network.build import build_network
from oniel.network.spec import load_network_spec, load_sources

NOVIEMBRE = dt.date(2026, 11, 17)
DICIEMBRE = dt.date(2026, 12, 11)


def test_la_842_une_las_agujas_sin_duplicar_el_acceso_compartido() -> None:
    enlace, ourense, eje = (
        build_network(load_network_spec(path), DATA_DIR)
        for path in (CONXO_SPEC, LAV_SANTIAGO_SPEC, EJE_ATLANTICO_SPEC)
    )
    assert enlace.spec.line.link_of == eje.spec.line.id
    assert enlace.spec.line.link_reversal_at == "santiago"
    assert all(n.spec.shared and n.spec.kind == "bifurcacion" for n in enlace.nodes)
    assert len(enlace.segments) == 1
    tramo = enlace.segments[0]
    assert len(tramo.coords) == 32
    assert (tramo.tracks, tramo.max_speed_kmh, enlace.spec.line.gauge_mm) == (1, 50, 1668)
    assert tramo.length_km == pytest.approx(1.011, abs=0.001)
    assert enlace.spec.line.reference_length_km == 1.054
    for node, madre, km in ((enlace.nodes[0], ourense, 85.702), (enlace.nodes[-1], eje, 63.502)):
        propietario = madre.node(node.spec.id)
        assert propietario.spec.position == node.spec.position
        assert propietario.km == pytest.approx(km, abs=0.001)
        assert propietario.offset_m < 5
    assert ourense.node("bif-conxo").km - ourense.node("bif-a-grandeira").km == pytest.approx(
        0.735, abs=0.001
    )
    assert not any(c.id == enlace.spec.line.id for c in ourense.spec.connections)
    for madre, km in ((ourense, 87.841), (eje, 155.201)):
        assert sum(t.length_km for t in madre.segments) == pytest.approx(km, abs=0.001)


@pytest.mark.parametrize(
    ("fecha", "con_parada"), [("08", (29, 18)), ("12", (28, 17)), ("17", (28, 17))]
)
def test_ediciones_de_renfe_y_vigencia_de_las_posiciones(
    fecha: str, con_parada: tuple[int, int]
) -> None:
    spec = load_network_spec(CONXO_SPEC)
    feed = read_feed(DATA_DIR / f"raw/renfe/google_transit_av_ld_md_2026-11-{fecha}.zip")
    candidatas = select_trips_for_spec(feed, spec, include_unconfirmed=True)
    assert Counter(t.train_number for t in candidatas) == {"04515": 6, "04384": 4}
    en_santiago: Counter[bool] = Counter()
    for trip in feed.trips.values():
        ids = [s.stop_id for s in trip.stop_times]
        if {"22100", "31400", "08223"} <= set(ids):
            en_santiago[ids.index("22100") < ids.index("08223")] += 1
    assert (en_santiago[True], en_santiago[False]) == con_parada
    observados = select_trips_for_spec(feed, spec)
    assert sorted(t.train_number for t in observados) == ["04384", "04515"]
    fuentes = {s.id: s for s in load_sources(DATA_DIR / "curated/sources.json")}
    for trip in observados:
        regla = route_for_trip(spec, trip)
        assert regla is not None
        dias = feed.service_dates[trip.service_id]
        assert regla.observed_sources(trip, dias, "renfe") == {
            NOVIEMBRE: f"renfe-conxo-{trip.train_number}"
        }
        assert regla.observed_sources(trip, dias, "ouigo") == {}
        assert regla.observed_sources(trip, {DICIEMBRE}, "renfe") == {}
        assert regla.first_stop_id == ("22100" if trip.train_number == "04515" else "23008")
        fichero = fuentes[f"renfe-conxo-{trip.train_number}"].file
        assert fichero
        captura = json.loads((DATA_DIR / Path(fichero)).read_text())
        registro = next(r for r in captura["tr"] if r[0] == trip.train_number)
        assert captura["f"][:10] == NOVIEMBRE.isoformat()
        assert registro[1:3] == (
            [4285663, -854723] if trip.train_number == "04515" else [4285580, -854557]
        )


def test_el_permiso_solo_vale_entre_los_brazos_de_santiago() -> None:
    from oniel.domain.schemas import NetworkIndexOut, SegmentOut
    from oniel.routing.graph import build_graph, find_routes
    from oniel.routing.scenario import Scenario

    index = NetworkIndexOut.model_validate_json(
        (DATA_DIR.parents[1] / "frontend/public/data/index.json").read_bytes()
    )
    segments = [SegmentOut(id=f.id, **f.properties) for f in index.segment_features.features]
    graph = build_graph(index.lines, index.nodes, segments, index.turns)
    enlace = "enlace-conxo:bif-conxo:bif-rio-sar"
    for aguja, brazo, otro in (
        ("bif-conxo", "lav-ourense-santiago:bif-conxo:santiago", "bif-rio-sar"),
        ("bif-rio-sar", "eje-atlantico:santiago:bif-rio-sar", "bif-conxo"),
    ):
        cierre = Scenario(closures=[brazo])
        for a, b in ((aguja, "santiago"), ("santiago", aguja)):
            assert find_routes(graph, a, b, cierre) == []
        assert [r.segment_ids for r in find_routes(graph, aguja, otro)] == [[enlace]]
    sin_permiso = [
        line.model_copy(update={"link_reversal_at": None}) if line.id == "enlace-conxo" else line
        for line in index.lines
    ]
    ordinario = build_graph(sin_permiso, index.nodes, segments, index.turns)
    for a, b in (("ourense", "vigo-urzaiz"), ("vigo-urzaiz", "ourense")):
        rutas = find_routes(graph, a, b)
        assert [(r.length_km, r.time_min, r.reverse_node_ids) for r in rutas] == [
            (178.4, 52, []),
            (181.6, 55, ["santiago"]),
        ]
        assert [r.segment_ids for r in find_routes(ordinario, a, b)] == [rutas[0].segment_ids]
        assert find_routes(ordinario, a, b, Scenario(closures=[enlace])) == []
