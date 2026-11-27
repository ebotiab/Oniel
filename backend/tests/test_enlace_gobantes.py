"""La línea 014 entre las dos agujas y los Avant que la recorren en cada edición."""

import json
from datetime import date

import pytest
from conftest import DATA_DIR, GOBANTES_SPEC, LAV_GRANADA_SPEC, LAV_MALAGA_SPEC

from oniel.gtfs.reader import read_feed
from oniel.gtfs.trips import calls_for_trip, route_for_trip, select_trips_for_spec
from oniel.network.build import build_network, trace_osm_relation
from oniel.network.spec import load_network_spec
from oniel.sim.passes import resolve_passes
from oniel.validate import loaded_line

GOBANTES, BOBADILLA = "bif-gobantes", "bif-bobadilla"
PARADAS = ["54413", "02030", "05012", "05000"]
IDA = {"08815", "08835", "08855"}
VUELTA = {"08915", "08935", "08955"}


def test_ocho_vias_contiguas_entre_las_agujas_de_la_030_y_la_036() -> None:
    enlace, malaga, granada = [
        build_network(load_network_spec(path), DATA_DIR)
        for path in (GOBANTES_SPEC, LAV_MALAGA_SPEC, LAV_GRANADA_SPEC)
    ]
    parte = enlace.spec.line.geometry_source.parts[0]
    raw = json.loads((DATA_DIR / parte.file).read_text())
    vias = {e["id"]: e for e in raw["elements"] if e["type"] == "way"}
    nodos = {e["id"]: (e["lon"], e["lat"]) for e in raw["elements"] if e["type"] == "node"}
    cadena = [2258256210]
    for via in (
        492843108,
        492843098,
        591274874,
        591274873,
        591274875,
        492843097,
        492843105,
        492843093,
    ):
        tramo = vias[via]["nodes"]
        if tramo[-1] == cadena[-1]:
            tramo = tramo[::-1]
        assert tramo[0] == cadena[-1]
        cadena.extend(tramo[1:])
    assert cadena[-1] == 4848128991 and len(cadena) == len(set(cadena)) == 86
    eje = [nodos[n] for n in cadena]
    for puntos in (eje, eje[::-1]):
        trazado = trace_osm_relation(raw, 16228313, puntos[0], puntos[-1]).polyline
        assert trazado.coords == puntos
        assert trazado.length_km == pytest.approx(8.856662, abs=0.000001)

    (segmento,) = enlace.segments
    assert segmento.coords == eje and segmento.tracks == 2
    assert (segmento.max_speed_kmh, segmento.typical_speed_kmh) == (220, 220)
    assert enlace.spec.line.reference_length_km == 8.6 and enlace.spec.line.opened_on is None
    for red, nodo, aguja, via in (
        (malaga, GOBANTES, cadena[0], 1200950762),
        (granada, BOBADILLA, cadena[-1], 218316743),
    ):
        original = json.loads((DATA_DIR / red.spec.line.geometry_source.parts[0].file).read_text())
        assert aguja in next(
            e["nodes"] for e in original["elements"] if e["type"] == "way" and e["id"] == via
        )
        antes = next(s for s in red.segments if s.to_node.spec.id == nodo)
        despues = next(s for s in red.segments if s.from_node.spec.id == nodo)
        assert antes.coords[-1] == despues.coords[0] == nodos[aguja]
        assert enlace.node(nodo).spec.shared and enlace.node(nodo).spec.reference_pk_km is None
    assert granada.node(BOBADILLA).km == pytest.approx(8.934, abs=0.001)
    assert granada.node(BOBADILLA).spec.reference_pk_km == 105.753
    assert malaga.node(GOBANTES).spec.reference_pk_km is None


@pytest.mark.parametrize("edicion", ["08", "12", "17"])
def test_solo_los_seis_avant_del_patron_cruzan_una_vez_por_la_014(edicion: str) -> None:
    feed = read_feed(DATA_DIR / f"raw/renfe/google_transit_av_ld_md_2026-11-{edicion}.zip")
    enlace, malaga, granada = [
        loaded_line(build_network(load_network_spec(path), DATA_DIR))
        for path in (GOBANTES_SPEC, LAV_MALAGA_SPEC, LAV_GRANADA_SPEC)
    ]
    candidatos = select_trips_for_spec(feed, enlace.spec)
    esperados = {
        t.trip_id
        for t in feed.trips.values()
        if [s.stop_id for s in t.stop_times] in (PARADAS, PARADAS[::-1])
    }
    assert {t.trip_id for t in candidatos} == esperados
    assert len(candidatos) == len(esperados) == 6
    for t in candidatos:
        assert t.product == "Avant" and date(2026, 11, 20) in feed.service_dates[t.service_id]
        ida = t.stop_times[0].stop_id == "54413"
        assert t.train_number in (IDA if ida else VUELTA)
        regla = route_for_trip(malaga.spec, t)
        assert regla and regla.override.id == "malaga-granada-por-gobantes"
        pasos_por_linea = []
        for linea in (malaga, enlace, granada):
            llamadas = calls_for_trip(
                t,
                feed,
                linea.spec,
                nodes=linea.nodes,
                others=[otra for otra in (malaga, enlace, granada) if otra != linea],
                route=route_for_trip(linea.spec, t),
            )
            pasos, estado = resolve_passes(llamadas, linea.nodes, linea.segments)
            assert estado == "completa"
            pasos_por_linea.append(pasos)
        pasos_malaga, (paso,), pasos_granada = pasos_por_linea
        assert len(pasos_malaga) == 3 and len(pasos_granada) == 7
        assert all(
            "antequera-santa-ana" not in p.segment_id for p in [*pasos_malaga, *pasos_granada]
        )
        por_gobantes = next(p for p in pasos_malaga if GOBANTES in p.segment_id)
        por_bobadilla = next(p for p in pasos_granada if BOBADILLA in p.segment_id)
        antes, despues = (por_gobantes, por_bobadilla) if ida else (por_bobadilla, por_gobantes)
        assert paso.kind == "estimado" and paso.km_increasing is ida
        assert paso.enter_s is not None and paso.exit_s is not None
        assert paso.enter_s == pytest.approx(antes.exit_s, abs=0.1)
        assert paso.exit_s == pytest.approx(despues.enter_s, abs=0.1)
        inicio, fin = [s for s in t.stop_times if s.stop_id in {"54413", "02030"}]
        assert inicio.departure_s < paso.enter_s < paso.exit_s < fin.arrival_s
    assert {t.train_number for t in candidatos} == IDA | VUELTA
