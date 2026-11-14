"""Extremadura: las cuatro líneas que llevan de Madrid a Badajoz.

La convencional Madrid – Talavera de la Reina – Plasencia (líneas 500 y 530 de Adif), la de alta
velocidad Plasencia – Cáceres – Badajoz, el ramal por el que se entra en Mérida y el trazado
antiguo de Monfragüe a Cáceres por Cañaveral.
"""

from __future__ import annotations

import datetime as dt
from collections import Counter
from dataclasses import dataclass

import pytest
from conftest import (
    CONV_SPEC,
    DATA_DIR,
    LAV_BADAJOZ_SPEC,
    MADRID_PLASENCIA_SPEC,
    MONFRAGUE_CACERES_SPEC,
    RAMAL_MERIDA_SPEC,
    SOURCES,
)

from oniel.geo import haversine_km
from oniel.gtfs.reader import GtfsFeed, GtfsTrip
from oniel.gtfs.trips import (
    LoadedLine,
    calls_for_trip,
    calls_on_line,
    route_for_trip,
    select_trips_for_spec,
)
from oniel.network.build import BuiltNetwork, build_network
from oniel.network.spec import NetworkSpec, load_network_spec, load_sources
from oniel.sim.passes import LineSegment, SegmentPass, resolve_passes
from oniel.validate import expected_pk_km, loaded_line

MADRID = "madrid-plasencia"
LAV = "lav-plasencia-badajoz"
MERIDA = "ramal-merida"
OLD = "monfrague-caceres"
SPEC_PATHS = {
    MADRID: MADRID_PLASENCIA_SPEC,
    LAV: LAV_BADAJOZ_SPEC,
    MERIDA: RAMAL_MERIDA_SPEC,
    OLD: MONFRAGUE_CACERES_SPEC,
}

WIKIPEDIA_500 = "wikipedia-linea-500"
WIKIPEDIA_LAV = "wikipedia-lav-madrid-extremadura"
MAP = "adif-declaracion-red-2026-mapas"
CHECKED = dt.date(2026, 11, 13)

#: Los nodos de cada línea, en orden.
NODES = {
    MADRID: [
        "bif-planetario",
        "leganes",
        "fuenlabrada",
        "humanes",
        "illescas",
        "torrijos",
        "montearagon",
        "talavera-de-la-reina",
        "oropesa-de-toledo",
        "navalmoral-de-la-mata",
        "casatejada",
        "monfrague",
        "bif-el-chaparral",
        "bif-san-esteban",
    ],
    LAV: [
        "plasencia",
        "bif-san-esteban",
        "arroyo-de-la-herrera",
        "bif-el-palmeral",
        "bif-casa-de-la-torre",
        "caceres",
        "bif-la-aldihuela",
        "bif-penas-blancas",
        "bif-granja-las-encinas",
        "garrovilla-las-vegas",
        "montijo",
        "montijo-el-molino",
        "guadiana",
        "bif-san-nicolas",
        "badajoz",
    ],
    MERIDA: ["bif-granja-las-encinas", "aljucen", "merida"],
    OLD: ["monfrague", "mirabel", "casas-de-millan", "canaveral", "bif-casa-de-la-torre"],
}
#: Longitud medida de cada línea, en km, y las relaciones de OSM de las que sale, por partes.
LENGTH_KM = {MADRID: 259.8, LAV: 190.9, MERIDA: 7.5, OLD: 71.0}
PARTS = {
    # la salida de Madrid, la línea 500 hasta Monfragüe (con 3,5 km de la plataforma de la línea
    # nueva a la entrada de Navalmoral de la Mata) y la 530 hasta la bifurcación San Esteban
    MADRID: [
        "osm-relation-18369030",
        "osm-relation-11717892",
        "osm-relation-8117446",
        "osm-relation-11717892",
        "osm-relation-6759679",
    ],
    # la línea nueva, con la entrada a Plasencia por la línea 530 y el paso por Cáceres y la
    # entrada a Badajoz por el recorrido del Alvia
    LAV: [
        "osm-relation-6759679",
        "osm-relation-8117446",
        "osm-relation-6759731",
        "osm-relation-8117446",
        "osm-relation-8117446",
        "osm-relation-6759731",
    ],
    # el enlace de Aljucén, que no está entero en ninguna relación, y la línea de Ciudad Real
    MERIDA: ["osm-vias-enlace-aljucen", "osm-relation-6759901"],
    OLD: ["osm-relation-11717892"],
}
#: Nodos que una línea toma de otra, que es la que los declara: (línea, nodo) -> línea dueña.
SHARED = {
    (MADRID, "bif-planetario"): "convencional-madrid-alcazar-cordoba",
    (LAV, "bif-san-esteban"): MADRID,
    (MERIDA, "bif-granja-las-encinas"): LAV,
    (OLD, "monfrague"): MADRID,
    (OLD, "bif-casa-de-la-torre"): LAV,
}
#: Tramos de vía única de la línea de alta velocidad, los que declara; el resto es de vía doble.
LAV_SINGLE = {
    "plasencia:bif-san-esteban",
    "bif-san-esteban:arroyo-de-la-herrera",
    "bif-el-palmeral:bif-casa-de-la-torre",
    "bif-casa-de-la-torre:caceres",
    "caceres:bif-la-aldihuela",
    "bif-penas-blancas:bif-granja-las-encinas",
    "montijo:montijo-el-molino",
    "montijo-el-molino:guadiana",
    "guadiana:bif-san-nicolas",
    "bif-san-nicolas:badajoz",
}

#: Prefijo de las tres reglas de la línea nueva para los trenes que van de Mérida hacia Badajoz.
MERIDA_RULE = "merida-hacia-badajoz-"
#: El tramo de la línea nueva que une la bifurcación Granja-Las Encinas con Garrovilla-Las Vegas.
CURVE = "bif-granja-las-encinas:garrovilla-las-vegas"

#: Los viajes del fichero de pruebas por línea: cuántos son y de qué producto («PROXIMDAD» es
#: como lo escribe el fichero de Renfe).
PRODUCTS = {
    MADRID: {"MD": 92, "PROXIMDAD": 64, "ALVIA": 55, "REGIONAL": 30, "REG.EXP.": 26},
    LAV: {"MD": 190, "REG.EXP.": 71, "ALVIA": 55, "REGIONAL": 14},
    MERIDA: {"MD": 89, "REG.EXP.": 58, "ALVIA": 37, "REGIONAL": 14},
    OLD: {"REG.EXP.": 13},
}
#: Cuántos viajes casa cada regla de recorrido.
RULES = {
    MADRID: {"a-plasencia-desde-navalmoral": 37, "a-plasencia-desde-monfrague": 59},
    LAV: {
        "plasencia-caceres-por-la-linea-antigua": 13,
        # los que van de Mérida hacia Badajoz, o al revés, según su parada siguiente a Mérida
        "merida-hacia-badajoz-garrovilla": 50,
        "merida-hacia-badajoz-montijo": 41,
        "merida-hacia-badajoz-badajoz": 37,
        "desde-plasencia-tras-navalmoral": 37,
        "desde-plasencia-tras-monfrague": 46,
    },
    MERIDA: {},
    OLD: {},
}
#: Entre qué dos nodos recorre cada viaje su línea (por orden alfabético), y cuántos son.
SHAPES = {
    MADRID: {
        # los que entran en Plasencia llegan al final de la línea
        ("bif-planetario", "bif-san-esteban"): 96,
        # los que no, pasan a la línea nueva por el enlace de El Chaparral
        ("bif-el-chaparral", "bif-planetario"): 76,
        # trenes de Proximidad de Madrid a Illescas
        ("bif-planetario", "illescas"): 64,
        # regionales de Madrid a Talavera de la Reina
        ("bif-planetario", "talavera-de-la-reina"): 31,
    },
    LAV: {
        # de Plasencia: a Mérida, a Badajoz, a Cáceres y, los 13 del trazado antiguo, solo hasta
        # la bifurcación San Esteban
        ("bif-granja-las-encinas", "plasencia"): 63,
        ("badajoz", "plasencia"): 18,
        ("caceres", "plasencia"): 19,
        ("bif-san-esteban", "plasencia"): 13,
        # de Madrid sin entrar en Plasencia: se incorporan en Arroyo de la Herrera
        ("arroyo-de-la-herrera", "badajoz"): 37,
        ("arroyo-de-la-herrera", "caceres"): 39,
        # de Cáceres a Badajoz y a Mérida
        ("badajoz", "caceres"): 82,
        ("bif-granja-las-encinas", "caceres"): 7,
        # de Mérida a Badajoz: salen de Mérida por Aljucén y entran junto a Garrovilla-Las Vegas
        ("badajoz", "garrovilla-las-vegas"): 52,
    },
    MERIDA: {
        # los que vienen de Cáceres o van hacia ella, por el enlace
        ("bif-granja-las-encinas", "merida"): 146,
        # los de Mérida a Badajoz, que no pasan por el enlace
        ("aljucen", "merida"): 52,
    },
    OLD: {("bif-casa-de-la-torre", "monfrague"): 13},
}
#: Viajes por tramo, en el orden de la línea.
BY_SEGMENT = {
    MADRID: [267] * 4 + [203] * 3 + [172] * 5 + [96],
    # los 52 de Mérida a Badajoz no pasan por el tramo de Granja-Las Encinas a Garrovilla-Las Vegas
    LAV: [113, 100] + [176] * 3 + [207] * 3 + [137] + [189] * 5,
    MERIDA: [146, 198],
    OLD: [13] * 4,
}
#: Pasos de cada clase.
KINDS = {
    MADRID: {"estimado": 2051, "publicado": 582},
    LAV: {"estimado": 2310, "publicado": 134},
    MERIDA: {"estimado": 344},
    OLD: {"estimado": 26, "publicado": 26},
}


@dataclass(frozen=True)
class Resolved:
    """Un viaje resuelto sobre una línea: la regla que casa, si casa alguna, y sus pasos."""

    trip: GtfsTrip
    rule: str | None
    passes: list[SegmentPass]

    @property
    def stops(self) -> list[str]:
        return [st.stop_id for st in self.trip.stop_times]

    @property
    def crossed(self) -> list[str]:
        return [p.segment_id.split(":", 1)[1] for p in self.passes]


@pytest.fixture(scope="module")
def nets() -> dict[str, BuiltNetwork]:
    return {
        line: build_network(load_network_spec(path), DATA_DIR) for line, path in SPEC_PATHS.items()
    }


@pytest.fixture(scope="module")
def conv_spec() -> NetworkSpec:
    return load_network_spec(CONV_SPEC)


@pytest.fixture(scope="module")
def resolved(
    feed: GtfsFeed, nets: dict[str, BuiltNetwork], conv_spec: NetworkSpec
) -> dict[str, list[Resolved]]:
    """Los viajes del fichero de pruebas resueltos sobre cada línea, midiendo por las otras tres
    y por la convencional de Andalucía, de la que sale la de Extremadura."""
    lines: list[LoadedLine] = [loaded_line(net) for net in nets.values()]
    lines.append(loaded_line(build_network(conv_spec, DATA_DIR)))
    out: dict[str, list[Resolved]] = {}
    for line_id, net in nets.items():
        own = next(line for line in lines if line.line_id == line_id)
        others = [line for line in lines if line is not own]
        segments = [LineSegment(s.id, s.km_from, s.km_to) for s in net.segments]
        out[line_id] = []
        for trip in select_trips_for_spec(feed, net.spec):
            route = route_for_trip(net.spec, trip)
            calls = calls_on_line(
                calls_for_trip(trip, feed, net.spec, nodes=own.nodes, others=others, route=route),
                route,
            )
            assert all(c.node_id or c.exit_node_ids for c in calls), trip.train_number
            passes, resolution = resolve_passes(calls, own.nodes, segments)
            assert resolution == "completa", trip.train_number
            out[line_id].append(Resolved(trip, route.override.id if route else None, passes))
    return out


def _short(net: BuiltNetwork) -> list[str]:
    return [s.id.split(":", 1)[1] for s in net.segments]


@pytest.mark.parametrize("line_id", [MADRID, LAV, MERIDA, OLD])
def test_each_line_is_traced_from_end_to_end(nets: dict[str, BuiltNetwork], line_id: str) -> None:
    """El trazado empieza en el primer nodo y acaba en el último, sin huecos, y cada parte sale de
    la relación de OSM que declara la especificación."""
    net = nets[line_id]
    assert [n.spec.id for n in net.nodes] == NODES[line_id]
    coords = net.line.polyline.coords
    first, last = net.nodes[0], net.nodes[-1]
    assert haversine_km(coords[0], (first.lon, first.lat)) < 0.05
    assert haversine_km(coords[-1], (last.lon, last.lat)) < 0.05
    assert net.line.polyline.length_km == pytest.approx(LENGTH_KM[line_id], abs=0.1)
    assert not net.line.gaps_km
    assert [p.source_id for p in net.line.part_spans] == PARTS[line_id]
    assert [p.source_id for p in net.spec.line.geometry_source.parts] == PARTS[line_id]
    assert all(n.offset_m < 35 for n in net.nodes)
    assert all(s.id.startswith(f"{line_id}:") for s in net.segments)
    assert len(net.segments) == len(NODES[line_id]) - 1
    # los tramos van de nodo a nodo: el trazado sobra unos metros en los extremos
    assert sum(s.length_km for s in net.segments) == pytest.approx(
        net.line.polyline.length_km, abs=0.05
    )


def test_parts_are_joined_where_two_relations_do_not_share_a_node(
    nets: dict[str, BuiltNetwork],
) -> None:
    """Dos empalmes, de unos metros: en la convencional, donde pasa a la plataforma de la línea
    nueva a la entrada de Navalmoral de la Mata, y en la de alta velocidad, en la bifurcación
    Granja-Las Encinas. Las demás partes comparten el nodo en el que se unen."""
    madrid, lav = nets[MADRID], nets[LAV]
    assert [round(j * 1000) for j in madrid.line.joins_km] == [35]
    assert madrid.line.part_spans[1].km_to == pytest.approx(195.41, abs=0.05)
    assert madrid.line.part_spans[2].km_from == pytest.approx(195.44, abs=0.05)
    assert [round(j * 1000) for j in lav.line.joins_km] == [23]
    assert lav.line.part_spans[4].km_from == pytest.approx(
        lav.node("bif-granja-las-encinas").km, abs=0.01
    )
    assert not nets[MERIDA].line.joins_km and not nets[OLD].line.joins_km
    # el ramal de Mérida empieza por un extracto de vías, sin relación: las que llevan ref=510
    link, to_merida = nets[MERIDA].spec.line.geometry_source.parts
    assert (link.relation_id, link.way_ref) == (None, "510")
    assert (to_merida.relation_id, to_merida.way_ref) == (6759901, None)
    assert nets[MERIDA].line.part_spans[0].km_to == pytest.approx(
        nets[MERIDA].node("aljucen").km, abs=0.01
    )


def test_the_lines_meet_at_shared_nodes(
    nets: dict[str, BuiltNetwork], conv_spec: NetworkSpec
) -> None:
    """Cada nodo común lo declara una línea y las demás lo toman de ella, en el mismo sitio: la
    bifurcación Planetario es de la convencional de Andalucía; la de San Esteban y Monfragüe, de
    la convencional de Extremadura; Casa de la Torre y Granja-Las Encinas, de la línea nueva."""
    specs = {line: net.spec for line, net in nets.items()} | {conv_spec.line.id: conv_spec}
    shared = {(line, n.spec.id) for line, net in nets.items() for n in net.nodes if n.spec.shared}
    assert shared == set(SHARED)
    for (line, node_id), owner in SHARED.items():
        ours = nets[line].node(node_id).spec
        theirs = next(n for n in specs[owner].nodes if n.id == node_id)
        assert not theirs.shared, node_id
        assert ours.position == theirs.position, node_id
        assert ours.adif_code == theirs.adif_code, node_id
    # los nodos comunes son extremos de la línea que los toma, salvo San Esteban, que queda a
    # 7 km de la estación de Plasencia
    assert nets[MADRID].nodes[0].spec.id == "bif-planetario"
    assert nets[MADRID].nodes[-1].spec.id == nets[LAV].nodes[1].spec.id == "bif-san-esteban"
    assert nets[LAV].node("bif-san-esteban").km == pytest.approx(7.46, abs=0.05)
    assert nets[MERIDA].nodes[0].spec.id == "bif-granja-las-encinas"
    assert (nets[OLD].nodes[0].spec.id, nets[OLD].nodes[-1].spec.id) == (
        "monfrague",
        "bif-casa-de-la-torre",
    )
    # con la línea cargada, de la bifurcación Planetario ya no sale una conexión a trazos
    assert "conv-madrid-extremadura" not in {c.id for c in conv_spec.connections}
    assert all(c.node_id != "bif-planetario" for c in conv_spec.connections)
    # lo que sigue sin cargar: el enlace de El Chaparral, las líneas de Valencia de Alcántara y de
    # Elvas, la de Aljucén a La Garrovilla y las de Mérida a Zafra y a Ciudad Real
    assert {(line, c.node_id) for line, net in nets.items() for c in net.spec.connections} == {
        (MADRID, "bif-el-chaparral"),
        (LAV, "caceres"),
        (LAV, "badajoz"),
        (MERIDA, "aljucen"),
        (MERIDA, "merida"),
    }


def test_stations_and_junctions(nets: dict[str, BuiltNetwork]) -> None:
    stations = {
        line: [n.spec.id for n in net.nodes if n.spec.kind == "estacion"]
        for line, net in nets.items()
    }
    assert stations == {
        MADRID: NODES[MADRID][1:12],
        LAV: [
            "plasencia",
            "caceres",
            "garrovilla-las-vegas",
            "montijo",
            "montijo-el-molino",
            "guadiana",
            "badajoz",
        ],
        MERIDA: ["merida"],
        OLD: ["monfrague", "mirabel", "casas-de-millan", "canaveral"],
    }
    codes = {n.spec.id: n.spec.adif_code for net in nets.values() for n in net.nodes}
    assert {k: codes[k] for k in ("plasencia", "caceres", "merida", "badajoz", "monfrague")} == {
        "plasencia": "30002",
        "caceres": "35400",
        "merida": "37500",
        "badajoz": "37606",
        "monfrague": "30000",
    }
    # las bifurcaciones no llevan código de estación
    junctions = [n.spec for net in nets.values() for n in net.nodes if n.spec.kind != "estacion"]
    assert len(junctions) == 3 + 8 + 2 + 1
    assert all(n.kind == "bifurcacion" and n.adif_code is None for n in junctions)


def test_kilometre_points_of_the_conventional_line_restart_at_leganes(
    nets: dict[str, BuiltNetwork],
) -> None:
    """Los PK de la línea 500 se cuentan desde Madrid-Atocha: la bifurcación Planetario es el
    3,7. El trazado cargado sale por Villaverde Alto y mide 12,6 km hasta Leganés, que es el 13,2
    de Adif: allí vuelve a empezar la cuenta. Desde Leganés el medido queda a menos de 100 m."""
    madrid = nets[MADRID]
    line = madrid.spec.line
    assert line.pk_origin_km == 3.7
    assert [(r.node, r.pk_km) for r in line.pk_restarts] == [("leganes", 13.2)]
    references = {n.spec.id: n.spec.reference_pk_km for n in madrid.nodes}
    assert references == {
        "bif-planetario": 3.7,
        "leganes": None,
        "fuenlabrada": 18.8,
        "humanes": 22.8,
        "illescas": 38.4,
        "torrijos": 85.4,
        "montearagon": 118.3,
        "talavera-de-la-reina": 134.2,
        "oropesa-de-toledo": 169.2,
        "navalmoral-de-la-mata": 200.4,
        "casatejada": 211.7,
        "monfrague": 251.6,
        "bif-el-chaparral": None,
        "bif-san-esteban": None,
    }
    for node in madrid.nodes:
        if node.spec.reference_pk_km is not None:
            assert expected_pk_km(madrid, node.km) == pytest.approx(
                node.spec.reference_pk_km, abs=0.1
            ), node.spec.id
    # hasta Leganés la cuenta es la del origen: 3,7 más los 12,6 km medidos, 3 km más que Adif
    leganes = madrid.node("leganes")
    assert leganes.km == pytest.approx(12.6, abs=0.05)
    assert expected_pk_km(madrid, leganes.km) == pytest.approx(16.3, abs=0.05)


def test_kilometre_points_of_the_other_lines(nets: dict[str, BuiltNetwork]) -> None:
    """El trazado antiguo sigue la cuenta de la línea 500 desde Monfragüe (251,6). La línea nueva
    cuenta desde Plasencia; en la bifurcación Granja-Las Encinas el medido se queda 0,9 km corto,
    dentro del margen. El ramal de Mérida no tiene PK propios."""
    old, lav = nets[OLD], nets[LAV]
    assert old.spec.line.pk_origin_km == 251.6 and not old.spec.line.pk_restarts
    assert {n.spec.id: n.spec.reference_pk_km for n in old.nodes} == {
        "monfrague": 251.6,
        "mirabel": 265.4,
        "casas-de-millan": 277.3,
        "canaveral": 283.1,
        "bif-casa-de-la-torre": None,
    }
    for node in old.nodes[:-1]:
        assert expected_pk_km(old, node.km) == pytest.approx(node.spec.reference_pk_km, abs=0.1)
    with_pk = {n.spec.id: n for n in lav.nodes if n.spec.reference_pk_km is not None}
    assert {k: n.spec.reference_pk_km for k, n in with_pk.items()} == {
        "plasencia": 0.0,
        "bif-san-esteban": 7.2,
        "caceres": 78.6,
        "bif-granja-las-encinas": 139.3,
    }
    deltas = {
        k: round(expected_pk_km(lav, n.km) - (n.spec.reference_pk_km or 0.0), 1)
        for k, n in with_pk.items()
    }
    assert deltas == {
        "plasencia": 0.0,
        "bif-san-esteban": 0.3,
        "caceres": 0.4,
        "bif-granja-las-encinas": -0.9,
    }
    assert all(abs(d) < lav.spec.line.pk_tolerance_km for d in deltas.values())
    assert all(n.spec.reference_pk_km is None for n in nets[MERIDA].nodes)


def test_tracks_by_segment(nets: dict[str, BuiltNetwork]) -> None:
    """La convencional solo tiene vía doble de la bifurcación Planetario a Humanes. La línea nueva
    es de vía doble salvo en los tramos que declara: las entradas a Plasencia, Cáceres y Badajoz,
    la bajada a Granja-Las Encinas y de Montijo en adelante."""
    madrid, lav = nets[MADRID], nets[LAV]
    assert madrid.spec.line.tracks == 1
    assert [s.tracks for s in madrid.segments] == [2] * 3 + [1] * 10
    assert _short(madrid)[:3] == [
        "bif-planetario:leganes",
        "leganes:fuenlabrada",
        "fuenlabrada:humanes",
    ]
    for segment in madrid.segments:
        tracks = segment.attributes["tracks"]
        # la sección cita su fuente; donde no hay sección vale el número de vías de la línea
        assert tracks.source_id == (WIKIPEDIA_500 if segment.tracks == 2 else None)
    assert lav.spec.line.tracks == 2
    assert {k for k, s in zip(_short(lav), lav.segments, strict=True) if s.tracks == 1} == (
        LAV_SINGLE
    )
    assert {s.tracks for s in lav.segments} == {1, 2}
    for segment in lav.segments:
        tracks = segment.attributes["tracks"]
        assert tracks.source_id == (MAP if segment.tracks == 1 else None)
    double_km = sum(s.length_km for s in lav.segments if s.tracks == 2)
    assert double_km == pytest.approx(111.9, abs=0.2)
    assert all(s.tracks == 1 for line in (MERIDA, OLD) for s in nets[line].segments)


def test_only_the_way_out_of_madrid_is_electrified_on_the_conventional_line(
    nets: dict[str, BuiltNetwork],
) -> None:
    """El atributo ``electrification`` lo declaran los tres tramos de la bifurcación Planetario a
    Humanes, con catenaria a 3 kV. Los demás no lo llevan: vale el texto de la línea."""
    madrid = nets[MADRID]
    assert madrid.spec.line.electrification == "Sin electrificar"
    for segment in madrid.segments[:3]:
        electrification = segment.attributes["electrification"]
        assert electrification.value == "3kv_cc"
        assert (electrification.source_id, electrification.checked_on) == (WIKIPEDIA_500, CHECKED)
    assert all("electrification" not in s.attributes for s in madrid.segments[3:])
    # la vía doble y la catenaria acaban en el mismo sitio
    assert [s.tracks == 2 for s in madrid.segments] == [
        "electrification" in s.attributes for s in madrid.segments
    ]
    sections = [t for t in madrid.spec.attribute_sections if t.attribute == "electrification"]
    assert [(t.from_node, t.to_node, t.value) for t in sections] == [
        ("bif-planetario", "humanes", "3kv_cc")
    ]
    # las otras tres líneas no lo declaran en ningún tramo
    for line in (LAV, MERIDA, OLD):
        assert all("electrification" not in s.attributes for s in nets[line].segments)
    assert nets[LAV].spec.line.electrification == nets[MERIDA].spec.line.electrification
    assert nets[LAV].spec.line.electrification == "25 kV 50 Hz"
    assert nets[OLD].spec.line.electrification == "Sin electrificar"


def test_the_declared_speed_wins_over_the_platform_of_the_new_line(
    nets: dict[str, BuiltNetwork],
) -> None:
    """A la entrada de Navalmoral de la Mata los trenes van por 3,5 km de la plataforma de la
    línea de alta velocidad en construcción, que en OSM lleva la velocidad de proyecto: sin la
    sección, el tramo de Oropesa de Toledo a Navalmoral saldría con 300 km/h."""
    madrid = nets[MADRID]
    by_id = dict(zip(_short(madrid), madrid.segments, strict=True))
    segment = by_id["oropesa-de-toledo:navalmoral-de-la-mata"]
    assert segment.max_speed_kmh == 155
    declared = segment.attributes["max_speed_kmh"]
    assert (declared.value, declared.source_id, declared.checked_on) == (
        155,
        WIKIPEDIA_500,
        CHECKED,
    )
    assert [k for k, s in by_id.items() if "max_speed_kmh" in s.attributes] == [
        "oropesa-de-toledo:navalmoral-de-la-mata"
    ]
    assert [s.max_speed_kmh for s in madrid.segments] == [140, 140, *[155] * 9, 100, 100]
    assert madrid.spec.line.max_speed_kmh == 155
    bare = madrid.spec.model_copy(
        update={
            "attribute_sections": [
                t for t in madrid.spec.attribute_sections if t.attribute != "max_speed_kmh"
            ]
        }
    )
    speeds = [s.max_speed_kmh for s in build_network(bare, DATA_DIR).segments]
    assert speeds == [140, 140, *[155] * 6, 300, 155, 155, 100, 100]
    # las otras líneas: 200 km/h en la nueva, menos en la salida de Plasencia y la entrada a Cáceres
    assert [s.max_speed_kmh for s in nets[LAV].segments] == [130, *[200] * 3, 195, *[200] * 9]
    assert [s.max_speed_kmh for s in nets[MERIDA].segments] == [120, 100]
    assert [s.max_speed_kmh for s in nets[OLD].segments] == [155, 120, 120, 120]


def test_signalling_of_the_map(nets: dict[str, BuiltNetwork]) -> None:
    """Mapa 4 de la Declaración sobre la Red: protección del tren, bloqueo y mando, por tramos."""

    def read(line: str) -> list[tuple[object, object, object]]:
        out: list[tuple[object, object, object]] = []
        for segment in nets[line].segments:
            attributes = segment.attributes
            for key in ("proteccion_tren", "bloqueo", "mando"):
                assert (attributes[key].source_id, attributes[key].checked_on) == (MAP, CHECKED)
            out.append(
                (
                    attributes["proteccion_tren"].value,
                    attributes["bloqueo"].value,
                    attributes["mando"].value,
                )
            )
        return out

    # junto a Humanes el mapa no deja atribuir los símbolos a esta línea: «sin dato publicado»
    assert read(MADRID) == [
        *[("sin_dato_publicado", "bab", "sin_dato_publicado")] * 3,
        *[("asfa", "blau", "ctc")] * 9,
        ("asfa", "bau", "sin_ctc"),
    ]
    # en la línea nueva el bloqueo es BAB en los tramos de vía doble y BAU en los de vía única
    lav = read(LAV)
    assert {protection for protection, _, _ in lav} == {"asfa"}
    assert {control for _, _, control in lav} == {"ctc"}
    assert [block for _, block, _ in lav] == [
        "bab" if s.tracks == 2 else "bau" for s in nets[LAV].segments
    ]
    assert read(MERIDA) == [("asfa", "bau", "ctc")] * 2
    assert read(OLD) == [("asfa", "blau", "sin_ctc")] * 4


def test_sources_of_the_lines_are_registered(nets: dict[str, BuiltNetwork]) -> None:
    sources = {s.id: s for s in load_sources(SOURCES)}
    for line, net in nets.items():
        for part in net.spec.line.geometry_source.parts:
            geometry = sources[part.source_id]
            assert geometry.license == "ODbL 1.0", part.source_id
            assert (DATA_DIR / part.file).exists(), part.file
            # la relación de la línea de Ciudad Real a Badajoz ya estaba descargada: es la de
            # Manzanares a Ciudad Real
            old_download = part.source_id == "osm-relation-6759901"
            assert geometry.retrieved_on == ("2026-11-10" if old_download else "2026-11-13")
        verification = sources[str(net.spec.line.verification_source_id)]
        assert verification.id == (WIKIPEDIA_500 if line in (MADRID, OLD) else WIKIPEDIA_LAV)
        assert verification.license == "CC BY-SA 4.0"
        assert verification.retrieved_on == "2026-11-13"
        for section in net.spec.attribute_sections:
            assert section.source_id in sources and section.checked_on == CHECKED
        assert {o.id for o in net.spec.operators} == {"adif", "renfe"}
        assert all(o.source_id in sources for o in net.spec.operators)
    assert "3,7" in str(sources[WIKIPEDIA_500].coverage)
    assert "Plasencia" in str(sources[WIKIPEDIA_LAV].coverage)
    assert "1,7 km" in str(sources["osm-vias-enlace-aljucen"].coverage)


@pytest.mark.parametrize("line_id", [MADRID, LAV, MERIDA, OLD])
def test_trips_and_passes_of_each_line(
    nets: dict[str, BuiltNetwork], resolved: dict[str, list[Resolved]], line_id: str
) -> None:
    """Los viajes del fichero del 8 de noviembre que recorren cada línea, las reglas de recorrido
    que casan, entre qué nodos la recorren y cuántos pasan por cada tramo."""
    trips = resolved[line_id]
    assert Counter(r.trip.product for r in trips) == PRODUCTS[line_id]
    assert len(trips) == sum(PRODUCTS[line_id].values())
    assert Counter(r.rule for r in trips if r.rule) == RULES[line_id]
    assert {o.id for o in nets[line_id].spec.route_overrides} == set(RULES[line_id])
    shapes: Counter[tuple[str, ...]] = Counter()
    by_segment: Counter[str] = Counter()
    kinds: Counter[str] = Counter()
    for r in trips:
        crossed = r.crossed
        shapes[tuple(sorted({crossed[0].split(":")[0], crossed[-1].split(":")[1]}))] += 1
        by_segment.update(crossed)
        kinds.update(p.kind for p in r.passes)
    assert shapes == SHAPES[line_id]
    assert [by_segment[k] for k in _short(nets[line_id])] == BY_SEGMENT[line_id]
    assert kinds == KINDS[line_id]
    assert sum(kinds.values()) == sum(BY_SEGMENT[line_id])


def test_trains_that_call_at_plasencia_reach_san_esteban_and_the_rest_leave_at_el_chaparral(
    resolved: dict[str, list[Resolved]],
) -> None:
    """De los 172 trenes que pasan de Monfragüe, 96 entran en Plasencia: recorren la convencional
    hasta la bifurcación San Esteban (regla de recorrido) y la línea nueva desde la estación. Los
    otros 76 dejan la convencional en la bifurcación El Chaparral y empiezan la línea nueva en
    Arroyo de la Herrera, sin pasar por sus dos primeros tramos."""
    madrid = {r.trip.trip_id: r for r in resolved[MADRID]}
    lav = {r.trip.trip_id: r for r in resolved[LAV]}
    beyond = [r for r in madrid.values() if "monfrague:bif-el-chaparral" in r.crossed]
    assert len(beyond) == 172
    by_plasencia = [r for r in beyond if "30002" in r.stops]
    direct = [r for r in beyond if "30002" not in r.stops]
    assert (len(by_plasencia), len(direct)) == (96, 76)
    for r in by_plasencia:
        assert r.rule in RULES[MADRID], r.trip.train_number
        assert len(r.crossed) == 13 and "bif-el-chaparral:bif-san-esteban" in r.crossed
        other = lav[r.trip.trip_id]
        assert other.rule in RULES[LAV], r.trip.train_number
        assert "plasencia:bif-san-esteban" in other.crossed
    for r in direct:
        assert r.rule is None and len(r.crossed) == 12
        assert "bif-el-chaparral:bif-san-esteban" not in r.crossed
        other = lav[r.trip.trip_id]
        # la única regla que les puede tocar es la de la salida de Mérida hacia Badajoz
        assert other.rule is None or other.rule.startswith(MERIDA_RULE), r.trip.train_number
        assert not {"plasencia:bif-san-esteban", "bif-san-esteban:arroyo-de-la-herrera"} & set(
            other.crossed
        )
        assert "arroyo-de-la-herrera:bif-el-palmeral" in other.crossed
        # el salto de una línea a otra por el enlace, que no está cargado, se mide en línea recta
        basis = " ".join(p.basis for p in other.passes)
        assert "enlaza en Bifurcación El Chaparral" in basis
    # las reglas de las dos líneas casan los mismos trenes
    assert {r.trip.trip_id for r in madrid.values() if r.rule} == {
        r.trip.trip_id for r in lav.values() if r.rule and not r.rule.startswith(MERIDA_RULE)
    }
    # los que no pasan de Monfragüe no llegan a la línea nueva: Proximidad a Illescas y
    # regionales a Talavera de la Reina
    short = [r for r in madrid.values() if r not in beyond]
    assert len(short) == 64 + 31 and not {r.trip.trip_id for r in short} & set(lav)


def test_regional_trains_by_canaveral_take_the_old_line(
    resolved: dict[str, list[Resolved]],
) -> None:
    """13 Regional Exprés paran en Plasencia y siguen a Cáceres por Mirabel, Casas de Millán y
    Cañaveral: de la línea nueva solo cuentan la salida de Plasencia, y recorren entero el trazado
    antiguo, con paso publicado entre las tres estaciones."""
    old = resolved[OLD]
    assert len(old) == 13
    lav = {r.trip.trip_id: r for r in resolved[LAV]}
    madrid = {r.trip.trip_id: r for r in resolved[MADRID]}
    for r in old:
        assert {"30002", "35301", "35302", "35303", "35400"} <= set(r.stops)
        assert [p.kind for p in r.passes] == ["estimado", "publicado", "publicado", "estimado"]
        assert lav[r.trip.trip_id].rule == "plasencia-caceres-por-la-linea-antigua"
        assert lav[r.trip.trip_id].crossed == ["plasencia:bif-san-esteban"]
        # todos vienen de Madrid o van a Madrid, por Monfragüe
        assert madrid[r.trip.trip_id].rule == "a-plasencia-desde-monfrague"
    on_rule = [r for r in lav.values() if r.rule == "plasencia-caceres-por-la-linea-antigua"]
    assert {r.trip.trip_id for r in on_rule} == {r.trip.trip_id for r in old}


def test_trains_enter_merida_by_the_link_or_by_aljucen(
    resolved: dict[str, list[Resolved]],
) -> None:
    """Los trenes que vienen de Cáceres o van hacia ella recorren los dos tramos del ramal; los de
    Mérida a Badajoz, que salen por Aljucén hacia La Garrovilla, solo el de Aljucén a Mérida.
    Mérida no tiene estación vecina en el ramal: todos los pasos son estimados."""
    merida = resolved[MERIDA]
    for r in merida:
        assert "37500" in r.stops
        by_caceres = bool({"35400", "30002"} & set(r.stops))
        assert r.crossed == (
            ["bif-granja-las-encinas:aljucen", "aljucen:merida"]
            if by_caceres
            else ["aljucen:merida"]
        ), r.trip.train_number
    assert sum(1 for r in merida if len(r.crossed) == 2) == 146
    # todos están también en la línea nueva
    assert {r.trip.trip_id for r in merida} <= {r.trip.trip_id for r in resolved[LAV]}


def test_trains_between_merida_and_badajoz_join_the_new_line_at_garrovilla(
    resolved: dict[str, list[Resolved]],
) -> None:
    """Los trenes que van de Mérida hacia Badajoz, o al revés, casan una de las tres reglas de
    recorrido, según su parada siguiente a Mérida. Los 52 que no pasan por Cáceres (los que
    empiezan o acaban en Mérida y los que vienen de Ciudad Real, Cabeza del Buey o Villanueva de
    la Serena) entran en la línea nueva junto a Garrovilla-Las Vegas y no cuentan en el tramo de
    la bifurcación Granja-Las Encinas a Garrovilla-Las Vegas."""
    lav = resolved[LAV]
    on_rule = [r for r in lav if r.rule and r.rule.startswith(MERIDA_RULE)]
    assert len(on_rule) == 50 + 41 + 37
    by_merida = [r for r in lav if "37500" in r.stops and "37606" in r.stops]
    assert {r.trip.trip_id for r in by_merida} == {r.trip.trip_id for r in on_rule}
    only = [r for r in on_rule if not {"35400", "30002"} & set(r.stops)]
    assert len(only) == 52
    # los 50 que paran en Garrovilla-Las Vegas y 2 con Montijo como parada siguiente
    assert Counter(r.rule for r in only) == {
        f"{MERIDA_RULE}garrovilla": 50,
        f"{MERIDA_RULE}montijo": 2,
    }
    for r in only:
        assert CURVE not in r.crossed, r.trip.train_number
        assert {r.crossed[0], r.crossed[-1]} == {
            "garrovilla-las-vegas:montijo",
            "bif-san-nicolas:badajoz",
        }, r.trip.train_number
        assert len(r.crossed) == 5
    # de ellos, 50 vienen del este de Mérida o siguen hacia allí; los otros 2 empiezan o acaban
    # en Mérida
    beyond = [r for r in only if {r.stops[0], r.stops[-1]} != {"37500", "37606"}]
    assert len(beyond) == 50
    # los que paran en Garrovilla-Las Vegas llevan allí el horario publicado; los 2 que no, un
    # paso estimado posterior a la salida de Mérida
    for r in only:
        times = [s for p in r.passes for s in (p.enter_s, p.exit_s) if s is not None]
        assert len(times) == 2 * len(r.passes), r.trip.train_number
        merida = next(st for st in r.trip.stop_times if st.stop_id == "37500")
        if r.stops.index("37500") < r.stops.index("37606"):
            assert min(times) > merida.departure_s, r.trip.train_number
        else:
            assert max(times) < merida.arrival_s, r.trip.train_number
    # Los otros 76 pasan también por Cáceres: recorren la línea de Cáceres a Badajoz y siguen
    # contando en ese tramo, aunque entran y salen de Mérida
    through = [r for r in on_rule if r not in only]
    assert len(through) == 76 and all(CURVE in r.crossed for r in through)
