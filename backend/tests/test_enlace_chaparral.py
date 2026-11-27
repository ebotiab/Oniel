"""Las vías de la 534 y la elección del recorrido en cada edición del horario."""

import json
from datetime import date
from itertools import pairwise

import pytest
from conftest import CHAPARRAL_SPEC, DATA_DIR, LAV_BADAJOZ_SPEC, MADRID_PLASENCIA_SPEC

from oniel.gtfs.reader import read_feed
from oniel.gtfs.trips import calls_for_trip, select_trips_for_spec
from oniel.network.build import build_network, trace_osm_relation
from oniel.network.spec import load_network_spec
from oniel.sim.passes import resolve_passes
from oniel.validate import loaded_line

CHAPARRAL = "bif-el-chaparral"
ARROYO = "arroyo-de-la-herrera"
DIA = date(2026, 11, 20)
IDA = {"00190", "00192", "37090", "37492"}
VUELTA = {"00293", "00295", "37093", "37095"}


def test_las_cuatro_vias_y_la_aguja_llegan_al_eje_de_la_026_en_ambos_sentidos() -> None:
    enlace, madrid, lav = [
        build_network(load_network_spec(path), DATA_DIR)
        for path in (CHAPARRAL_SPEC, MADRID_PLASENCIA_SPEC, LAV_BADAJOZ_SPEC)
    ]
    parte = enlace.spec.line.geometry_source.parts[0]
    raw = json.loads((DATA_DIR / parte.file).read_text())
    vias = {e["id"]: e for e in raw["elements"] if e["type"] == "way"}
    nodos = {e["id"]: (e["lon"], e["lat"]) for e in raw["elements"] if e["type"] == "node"}
    ids = [570083420, 863767829, 863767828, 754709650]
    assert {i for i, via in vias.items() if via["tags"].get("ref") == "534"} == set(ids)
    cadena = [8047113244]
    for i in [*ids, 1046552626]:
        tramo = vias[i]["nodes"]
        if tramo[-1] == cadena[-1]:
            tramo = tramo[::-1]
        assert tramo[0] == cadena[-1]
        cadena.extend(tramo[1:])
    assert cadena[-1] == 9624185392
    xy = [nodos[n] for n in cadena]
    for desde, hasta in ((0, -1), (-1, 0)):
        completa = trace_osm_relation(raw, 6759731, xy[desde], xy[hasta]).polyline
        assert completa.coords == (xy if desde == 0 else xy[::-1])
        rotulada = trace_osm_relation(raw, None, xy[desde], xy[hasta], way_ref="534").polyline
        assert rotulada.length_km == pytest.approx(4.830209, abs=0.000001)
        assert completa.length_km - rotulada.length_km == pytest.approx(0.150797, abs=0.000001)
    assert enlace.segments[0].coords == xy
    for red, nodo, extremo, km in [
        (madrid, CHAPARRAL, xy[0], 257.182),
        (lav, ARROYO, xy[-1], 11.967),
    ]:
        assert red.node(nodo).km == pytest.approx(km, abs=0.001)
        assert enlace.node(nodo).spec.shared
        antes = next(s for s in red.segments if s.to_node.spec.id == nodo)
        despues = next(s for s in red.segments if s.from_node.spec.id == nodo)
        assert antes.coords[-1] == despues.coords[0] == extremo
    assert not enlace.line.joins_km and not enlace.spec.connections
    assert enlace.spec.line.reference_length_km == 4.8
    assert (enlace.segments[0].max_speed_kmh, enlace.segments[0].typical_speed_kmh) == (200, 85)


@pytest.mark.parametrize(("edicion", "entran"), [("08", 96), ("12", 95), ("17", 95)])
def test_el_enlace_solo_anade_pasos_estimados_entre_monfrague_y_caceres(
    edicion: str, entran: int
) -> None:
    feed = read_feed(DATA_DIR / f"raw/renfe/google_transit_av_ld_md_2026-11-{edicion}.zip")
    enlace, madrid, lav = [
        loaded_line(build_network(load_network_spec(path), DATA_DIR))
        for path in (CHAPARRAL_SPEC, MADRID_PLASENCIA_SPEC, LAV_BADAJOZ_SPEC)
    ]
    anteriores = {t.trip_id for t in select_trips_for_spec(feed, madrid.spec)}
    ingresan = [
        t for t in select_trips_for_spec(feed, madrid.spec) if "30002" in feed.stop_ids_of(t)
    ]
    assert len(ingresan) == entran
    esperados = {
        t.trip_id
        for t in feed.trips.values()
        if any({a.stop_id, b.stop_id} == {"30000", "35400"} for a, b in pairwise(t.stop_times))
    }
    candidatos = select_trips_for_spec(feed, enlace.spec)
    assert {t.trip_id for t in candidatos} == esperados
    assert len(candidatos) == 76 and esperados <= anteriores
    diarios: list[tuple[str, bool]] = []
    for t in candidatos:
        assert feed.stop_ids_of(t).isdisjoint({"30002", "35301", "35302", "35303"})
        inicio, fin = [s for s in t.stop_times if s.stop_id in {"30000", "35400"}]
        llamadas = calls_for_trip(t, feed, enlace.spec, nodes=enlace.nodes, others=[madrid, lav])
        pasos, estado = resolve_passes(llamadas, enlace.nodes, enlace.segments)
        assert estado == "completa" and len(pasos) == 1
        paso = pasos[0]
        ida = inicio.stop_id == "30000"
        assert paso.km_increasing is ida and paso.kind == "estimado"
        assert paso.enter_s is not None and paso.exit_s is not None
        assert inicio.departure_s < paso.enter_s < paso.exit_s < fin.arrival_s
        if DIA in feed.service_dates[t.service_id]:
            diarios.append((t.train_number, ida))
    assert sorted(diarios) == sorted([(n, True) for n in IDA] + [(n, False) for n in VUELTA])
