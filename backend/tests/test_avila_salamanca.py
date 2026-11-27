"""Controles del horario de viajeros por Ávila en las tres ediciones de Renfe."""

import json
from collections import Counter
from datetime import date

import pytest
from conftest import DATA_DIR, MADRID_AVILA_VALLADOLID_SPEC

from oniel.domain.station_closures import STATION_CLOSURES
from oniel.gtfs.reader import parse_gtfs_time, read_feed
from oniel.gtfs.trips import select_trips_for_spec
from oniel.network.build import build_network, trace_osm_relation
from oniel.network.spec import load_network_spec, load_sources
from oniel.sim.closure import ClosureWindow, classify
from oniel.sim.passes import LineNode, LineSegment, StopCall, resolve_passes

PRINCIPE_PIO = "10000"
AVILA = "10400"
PENARANDA = "34010"
SALAMANCA = "30100"
ALAMEDILLA = "30110"
INTERMEDIAS = ["34002", "34005", "34007", "34008", PENARANDA, "34011", "34012", "34013", "34014"]
CONTROL = date(2026, 11, 26)


def test_distancia_hasta_las_dos_terminales_por_el_recorrido_regional() -> None:
    """Contraste independiente con la R-20, en los dos sentidos, desde la parte ya cargada."""
    principal = build_network(load_network_spec(MADRID_AVILA_VALLADOLID_SPEC), DATA_DIR)
    enlace = build_network(
        load_network_spec(DATA_DIR / "curated/enlace-principe-pio-pinar.json"), DATA_DIR
    )
    hasta_avila = (
        enlace.length_km + principal.node("avila").km - principal.node("pinar-de-las-rozas").km
    )
    sources = load_sources(DATA_DIR / "curated/sources.json")
    source = next(s for s in sources if s.id == "osm-relation-1210118")
    assert source.file and source.license == "ODbL 1.0"
    raw = json.loads((DATA_DIR / source.file).read_text())
    points = {e["id"]: (e["lon"], e["lat"]) for e in raw["elements"] if e["type"] == "node"}
    avila = points[244749631]
    distancias = []
    for destino, referencia in [(points[33246281], 231.4), (points[495082202], 232.3)]:
        ida = trace_osm_relation(raw, 1210118, avila, destino).polyline
        vuelta = trace_osm_relation(raw, 1210118, destino, avila).polyline
        assert ida.coords[0] == avila and ida.coords[-1] == destino
        assert ida.coords == vuelta.coords[::-1]
        total = hasta_avila + ida.length_km
        assert total == pytest.approx(referencia, abs=0.1)
        distancias.append(total)
    assert distancias[1] - distancias[0] == pytest.approx(0.833, abs=0.001)


@pytest.mark.parametrize(
    ("edicion", "producto", "idas", "vueltas"),
    [
        ("08", "Media Distancia", 37, 36),
        ("12", "Media Distancia", 36, 35),
        ("17", "Regional", 36, 35),
    ],
)
def test_terminales_y_calendarios_comerciales(
    edicion: str, producto: str, idas: int, vueltas: int
) -> None:
    feed = read_feed(DATA_DIR / "raw/renfe" / f"google_transit_av_ld_md_2026-11-{edicion}.zip")
    regionales = [t for t in feed.trips.values() if PENARANDA in feed.stop_ids_of(t)]
    principal = load_network_spec(MADRID_AVILA_VALLADOLID_SPEC)
    enlace = load_network_spec(DATA_DIR / "curated/enlace-principe-pio-pinar.json")
    ids = {t.trip_id for t in regionales}
    for spec in (principal, enlace):
        assert ids <= {t.trip_id for t in select_trips_for_spec(feed, spec)}

    linea = load_network_spec(DATA_DIR / "curated/avila-salamanca.json")
    seleccionados = select_trips_for_spec(feed, linea)
    assert len(seleccionados) == (167 if edicion == "08" else 162)
    assert {t.trip_id for t in seleccionados} == {
        t.trip_id for t in feed.trips.values() if SALAMANCA in feed.stop_ids_of(t)
    }
    assert {t.product for t in regionales} == {producto}
    assert Counter((t.stop_times[0].stop_id, t.stop_times[-1].stop_id) for t in regionales) == {
        (PRINCIPE_PIO, ALAMEDILLA): idas,
        (SALAMANCA, PRINCIPE_PIO): vueltas,
    }
    dias = [(t.train_number, dia) for t in regionales for dia in feed.service_dates[t.service_id]]
    assert len(dias) == len(set(dias))
    for t in regionales:
        paradas = [s.stop_id for s in t.stop_times]
        if paradas[0] == PRINCIPE_PIO:
            assert paradas[-2:] == [SALAMANCA, ALAMEDILLA]
        else:
            assert ALAMEDILLA not in paradas
            paradas.reverse()
        assert paradas.index("10200") < paradas.index(AVILA) < paradas.index(PENARANDA)
        interior = paradas[paradas.index(AVILA) + 1 : paradas.index(SALAMANCA)]
        assert interior == (
            INTERMEDIAS if t.train_number in {"18901", "18904", "18921"} else [PENARANDA]
        )

    hoy = [t for t in feed.trips.values() if CONTROL in feed.service_dates[t.service_id]]
    por_avila = [t for t in hoy if t.trip_id in ids]
    assert Counter(t.stop_times[0].stop_id for t in por_avila) == {PRINCIPE_PIO: 7, SALAMANCA: 7}
    hasta_apeadero = [t for t in hoy if t.stop_times[-1].stop_id == ALAMEDILLA]
    assert Counter(PENARANDA in feed.stop_ids_of(t) for t in hasta_apeadero) == {True: 7, False: 5}
    for viaje in hasta_apeadero:
        parada = viaje.stop_times[-2]
        assert (parada.stop_id, parada.pickup_type, parada.drop_off_type) == (SALAMANCA, 1, 0)
    assert all("10500" in feed.stop_ids_of(t) for t in hasta_apeadero if t.trip_id not in ids)
    por_medina = {t.train_number: t for t in hoy if t.train_number in {"18308", "00631", "04899"}}
    assert set(por_medina) == {"18308", "00631", "04899"}
    for numero, medina in [("18308", "10500"), ("00631", "10500"), ("04899", "08240")]:
        paradas_medina = feed.stop_ids_of(por_medina[numero])
        assert medina in paradas_medina and paradas_medina.isdisjoint(INTERMEDIAS)
        assert (ALAMEDILLA in paradas_medina) == (numero == "18308")
    assert por_medina["04899"].product == ("Intercity" if edicion == "17" else "Alvia")

    ida = next(t for t in por_avila if t.train_number == "18901")
    principal_sal, apeadero = ida.stop_times[-2:]
    assert (principal_sal.arrival_s, principal_sal.departure_s) == (
        parse_gtfs_time("10:40:00"),
        parse_gtfs_time("10:42:00"),
    )
    assert (principal_sal.pickup_type, principal_sal.drop_off_type) == (1, 0)
    assert apeadero.arrival_s == parse_gtfs_time("10:45:00")
    vuelta = next(t for t in por_avila if t.train_number == "18904")
    salida = vuelta.stop_times[0]
    assert (salida.stop_id, salida.pickup_type, salida.drop_off_type) == (SALAMANCA, 0, 1)
    assert salida.departure_s == parse_gtfs_time("16:42:00")


def test_secciones_y_cabeceras_de_la_122() -> None:
    red = build_network(load_network_spec(DATA_DIR / "curated/avila-salamanca.json"), DATA_DIR)
    assert not red.line.gaps_km
    assert len(red.segments) == 15 and all(s.tracks == 1 for s in red.segments)
    assert [n.spec.adif_code for n in red.nodes if n.spec.kind == "estacion"] == [
        *INTERMEDIAS,
        SALAMANCA,
        ALAMEDILLA,
    ]
    for tramo in red.segments:
        assert tramo.id in STATION_CLOSURES
        if tramo.attributes["proteccion_tren"].value == "asfa":
            assert tramo.attributes["electrification"].value == "Sin electrificar"
        else:
            assert tramo.attributes["proteccion_tren"].value == "sin_dato_publicado"
            assert "electrification" not in tramo.attributes
    assert red.node("salamanca").spec.reference_pk_km is None
    assert red.node("salamanca-la-alamedilla").spec.reference_pk_km == 0.9


def test_la_franja_de_minutos_con_viajes_ficticios() -> None:
    """Dos sentidos del tronco y una continuación urbana, con horas y estaciones de prueba."""
    estaciones = ["origen-ficticio", "central-ficticia", "apeadero-ficticio"]
    nodos = {k: LineNode(k, float(i), 0, 0) for i, k in enumerate(estaciones)}
    tramos = [LineSegment("tronco-ficticio", 0, 1), LineSegment("urbano-ficticio", 1, 2)]
    viajes = {
        "ida": [(0, 480), (1, 487), (2, 491)],
        "vuelta": [(1, 607), (0, 614)],
        "urbano": [(1, 720), (2, 724)],
    }
    pasos = {}
    for viaje, secuencia in viajes.items():
        paradas = [
            StopCall(
                i, estaciones[n], estaciones[n], minuto * 60, minuto * 60, node_id=estaciones[n]
            )
            for i, (n, minuto) in enumerate(secuencia)
        ]
        pasos[viaje], estado = resolve_passes(paradas, nodos, tramos)
        assert estado == "completa"
    for tramo, inicio, fin, esperado in [
        ("tronco-ficticio", 480, 488, ["ida"]),
        ("tronco-ficticio", 607, 615, ["vuelta"]),
        ("urbano-ficticio", 720, 725, ["urbano"]),
        ("tronco-ficticio", 720, 725, []),
        ("urbano-ficticio", 724, 729, []),
    ]:
        franja = ClosureWindow(inicio * 60, fin * 60)
        afectados = [
            viaje
            for viaje, recorridos in pasos.items()
            for paso in recorridos
            if paso.segment_id == tramo and classify(paso, franja).status == "afectado_publicado"
        ]
        assert afectados == esperado
