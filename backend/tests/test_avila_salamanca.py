"""Controles del horario de viajeros por Ávila en las tres ediciones de Renfe."""

import json
from collections import Counter
from datetime import date

import pytest
from conftest import DATA_DIR, MADRID_AVILA_VALLADOLID_SPEC

from oniel.gtfs.reader import parse_gtfs_time, read_feed
from oniel.gtfs.trips import select_trips_for_spec
from oniel.network.build import build_network, trace_osm_relation
from oniel.network.spec import load_network_spec, load_sources

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
