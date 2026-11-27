"""Los accesos de Medina comparten el tramo salmantino y cada viaje conserva su identidad."""

import json
from collections import Counter
from datetime import date

import pytest
from conftest import DATA_DIR

from oniel.domain.station_closures import STATION_CLOSURES
from oniel.gtfs.reader import read_feed
from oniel.gtfs.trips import calls_for_trip, calls_on_line, route_for_trip, select_trips_for_spec
from oniel.network.build import build_network, trace_osm_relation
from oniel.network.spec import load_network_spec
from oniel.sim.passes import resolve_passes
from oniel.validate import loaded_line

MEDINA = "medina-del-campo-salamanca"
ENLACE = "enlace-medina-av-salamanca"
AVILA = "avila-salamanca"
LAV = "lav-olmedo-ourense"
GOLOSA = "bif-arroyo-de-la-golosa"
SALIDA = "bif-medina-av-salamanca"
DIA = date(2026, 11, 26)


def test_la_190_y_la_188_se_unen_en_ambos_sentidos() -> None:
    for rel, anden, limite, distancia in [
        (20685324, 6329564866, 4934361912, 1.130),
        (20685325, 6340046033, 4934361913, 1.115),
    ]:
        raw = json.loads(next((DATA_DIR / "raw/osm").glob(f"relation_{rel}_*.json")).read_text())
        xy = {e["id"]: (e["lon"], e["lat"]) for e in raw["elements"] if e["type"] == "node"}
        for a, b, km in [
            (anden, 4934361918, distancia),
            (4934361918, 2232327713, 2.948),
            (2232327713, 33246283, 69.207),
            (33246283, 13829159897, 0.484),
        ]:
            ida = trace_osm_relation(raw, rel, xy[a], xy[b]).polyline
            vuelta = trace_osm_relation(raw, rel, xy[b], xy[a]).polyline
            assert (ida.coords[0], ida.coords[-1]) == (xy[a], xy[b])
            assert ida.coords == vuelta.coords[::-1]
            assert ida.length_km == pytest.approx(km, abs=0.001)
            if a == anden:
                assert xy[limite] in ida.coords


def test_secciones_ancladas_y_con_fuentes() -> None:
    redes = {
        id: build_network(load_network_spec(DATA_DIR / f"curated/{id}.json"), DATA_DIR)
        for id in (MEDINA, ENLACE, LAV, AVILA, "madrid-avila-valladolid")
    }
    medina, enlace = redes[MEDINA], redes[ENLACE]
    for nuevo, vecino in [(medina, redes["madrid-avila-valladolid"]), (enlace, redes[LAV])]:
        nodo = vecino.node(nuevo.nodes[0].spec.id)
        assert nuevo.segments[0].coords[0] == pytest.approx((nodo.lon, nodo.lat))
    assert medina.segments[-1].coords[-1] == redes[AVILA].segments[-2].coords[0]
    assert not medina.line.joins_km and not enlace.line.joins_km
    assert [n.spec.adif_code for n in medina.nodes if n.spec.kind == "estacion"] == [
        "10500",
        "32001",
        "32002",
        "32003",
        "32004",
        "32006",
        "32007",
        "32008",
        "32009",
    ]
    assert [s.attributes["electrification"].value for s in medina.segments] == [
        "3 kV CC",
        *(["25 kV 50 Hz"] * 10),
    ]
    assert [
        s.from_node.spec.id for s in medina.segments if s.attributes["bloqueo"].value == "bau"
    ] == [GOLOSA]
    assert [s.attributes["gauge"].value for s in enlace.segments] == ["estandar", "iberico"]
    for tramo in [*medina.segments, *enlace.segments]:
        assert tramo.id in STATION_CLOSURES and tramo.tracks == 1
        assert all(a.source_id and a.checked_on for a in tramo.attributes.values())


@pytest.mark.parametrize(("edicion", "convencionales"), [("08", 44), ("12", 41), ("17", 41)])
def test_los_dos_accesos_y_el_tramo_compartido(edicion: str, convencionales: int) -> None:
    feed = read_feed(next((DATA_DIR / "raw/renfe").glob(f"*11-{edicion}.zip")))
    redes = {
        id: loaded_line(build_network(load_network_spec(DATA_DIR / f"curated/{id}.json"), DATA_DIR))
        for id in (MEDINA, ENLACE, AVILA, LAV, "madrid-avila-valladolid")
    }
    distintos = {
        codigo: {t.trip_id for t in feed.trips.values() if {codigo, "30100"} <= feed.stop_ids_of(t)}
        for codigo in ("10500", "08240", "34010")
    }
    assert [len(distintos[k]) for k in distintos] == [
        convencionales,
        50,
        73 if edicion == "08" else 71,
    ]
    for id, ids in [
        (MEDINA, distintos["10500"] | distintos["08240"]),
        (ENLACE, distintos["08240"]),
        (AVILA, set.union(*distintos.values())),
    ]:
        assert {t.trip_id for t in select_trips_for_spec(feed, redes[id].spec)} == ids
    pasos: dict[str, list[tuple[str, bool]]] = {}
    for red in redes.values():
        for t in select_trips_for_spec(feed, red.spec):
            if DIA not in feed.service_dates[t.service_id] or "30100" not in feed.stop_ids_of(t):
                continue
            regla = route_for_trip(red.spec, t)
            llamadas = calls_for_trip(
                t, feed, red.spec, nodes=red.nodes, others=list(redes.values()), route=regla
            )
            recorridos, estado = resolve_passes(
                calls_on_line(llamadas, regla), red.nodes, red.segments
            )
            assert estado == "completa"
            for paso in recorridos:
                assert paso.km_increasing is not None
                pasos.setdefault(paso.segment_id, []).append((t.train_number, paso.km_increasing))
    for viajes in pasos.values():
        assert len(viajes) == len({n for n, _ in viajes})
    comun = pasos[f"{MEDINA}:{GOLOSA}:campillo"]
    convencional = pasos[f"{MEDINA}:medina-del-campo:cambio-tension-medina"]
    av = pasos[f"{ENLACE}:{SALIDA}:cambiador-medina-av"]
    for viajes, total in [(convencional, 7), (av, 4), (comun, 11)]:
        assert Counter(sentido for _, sentido in viajes) == {True: total, False: total}
    assert set(comun) == set(convencional) | set(av)
    assert set(convencional).isdisjoint(av)
    assert {"18308", "18312"} <= {n for n, _ in convencional}
    assert {"04899", "04868"} <= {n for n, _ in av}
    entrada = pasos[f"{AVILA}:bif-acceso-salamanca:salamanca"]
    assert len(entrada) == 36 and set(comun) <= set(entrada)
    assert {n for n, _ in entrada if n.startswith("189")} >= {"18901", "18904"}
    urbano = pasos[f"{AVILA}:salamanca:salamanca-la-alamedilla"]
    assert len(urbano) == 12
    assert {n for n, _ in urbano if not n.startswith("189")} == {
        "18300",
        "18304",
        "18308",
        "18316",
        "18318",
    }
    assert not pasos.get(f"{LAV}:{SALIDA}:toro-av")
