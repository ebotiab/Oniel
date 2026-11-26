"""Contraste de la cartografía de Grisén del 26-11-2026, previo a la carga de #310."""

from __future__ import annotations

import json
from itertools import pairwise

import pytest
from conftest import BCN_SPEC, DATA_DIR

from oniel.geo import Coord, haversine_km
from oniel.network.build import build_line_geometry, trace_osm_relation
from oniel.network.spec import load_network_spec

OSM = DATA_DIR / "raw/osm"
LAV = (-1.2639277, 41.6755238)
CAMBIADOR = (-1.2280962, 41.696325)
ENTRADA_200 = (-1.2208949, 41.7020179)
ENTRADA_702 = (-1.1709854, 41.7419109)
EBRO = (-1.166485, 41.7873295)


def test_recorrido_cartografiado_de_grisen_en_ambos_sentidos() -> None:
    """Cada corte es un vértice común. Las dos líneas cargadas solo aportan los extremos."""
    partes = [
        ("way", 75916844, LAV, (-1.23138, 41.6932018)),
        ("way", 138477723, (-1.23138, 41.6932018), CAMBIADOR),
        ("way", 204467779, CAMBIADOR, (-1.2237038, 41.6999597)),
        ("way", 1221613439, (-1.2237038, 41.6999597), ENTRADA_200),
        ("relation", 4830814, ENTRADA_200, ENTRADA_702),
        ("relation", 9696024, ENTRADA_702, EBRO),
    ]
    puntos: list[Coord] = []
    km = 0.0
    for tipo, identificador, inicio, fin in partes:
        relacion = identificador if tipo == "relation" else None
        nombre = (
            f"relation_{identificador}" if relacion else f"way_{identificador}_plasencia_de_jalon"
        )
        fichero = f"{nombre}_2026-11-26.json"
        original = json.loads((OSM / fichero).read_text())
        ids = None if relacion else [identificador]
        ida = trace_osm_relation(original, relacion, inicio, fin, way_ids=ids).polyline
        vuelta = trace_osm_relation(original, relacion, fin, inicio, way_ids=ids).polyline
        assert ida.coords[0] == inicio and ida.coords[-1] == fin
        assert ida.coords == vuelta.coords[::-1]
        assert not puntos or puntos[-1] == inicio
        puntos.extend(ida.coords[1:] if puntos else ida.coords)
        km += ida.length_km

    assert len(set(puntos)) == len(puntos)
    assert km == pytest.approx(17.188854, abs=0.000001)
    aristas = {frozenset(par) for par in pairwise(puntos)}
    for ficha, extremo in [
        (BCN_SPEC, LAV),
        (DATA_DIR / "curated/zaragoza-castejon-logrono.json", EBRO),
    ]:
        eje = build_line_geometry(load_network_spec(ficha), DATA_DIR).polyline
        assert extremo in eje.coords
        assert aristas.isdisjoint(frozenset(par) for par in pairwise(eje.coords))
        # Desde Madrid se entra de frente y se sale hacia Tudela sin invertir la marcha.
        i = eje.coords.index(extremo)
        a, b = (eje.coords[i - 1], puntos[1]) if extremo == LAV else (puntos[-2], eje.coords[i + 1])
        assert haversine_km(a, b) > 0.99 * (haversine_km(a, extremo) + haversine_km(extremo, b))


def test_el_anden_convencional_de_grisen_queda_fuera_del_eje_osm_de_la_702() -> None:
    datos = json.loads((OSM / "instalaciones_grisen_2026-11-26.json").read_text())
    anden = next(n for n in datos["elements"] if n["id"] == 26377463)
    posicion = (anden["lon"], anden["lat"])
    convencional = json.loads((OSM / "relation_4830814_2026-11-26.json").read_text())
    acceso = trace_osm_relation(convencional, 4830814, ENTRADA_702, posicion).polyline
    assert acceso.coords[-1] == posicion
    assert acceso.length_km == pytest.approx(0.594, abs=0.001)
    ramal = json.loads((OSM / "relation_9696024_2026-11-26.json").read_text())
    assert posicion not in trace_osm_relation(ramal, 9696024, ENTRADA_702, EBRO).polyline.coords
