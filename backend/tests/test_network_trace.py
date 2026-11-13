"""Trazado de una relación OSM con dos vías sin orden y empalme de partes."""

from __future__ import annotations

from pathlib import Path
from typing import Any

import pytest
from conftest import DATA_DIR

from oniel.network.build import (
    BuiltNetwork,
    build_network,
    chain_osm_relation,
    concat_parts,
    trace_osm_relation,
)
from oniel.network.spec import NetworkSpec, load_network_spec

CONV_SPEC = DATA_DIR / "curated" / "convencional-madrid-alcazar-cordoba.json"


def _two_track_relation() -> dict[str, Any]:
    """Línea de dos vías paralelas entre x=0 y x=0.03, más un ramal que se separa en x=0.02.

    Los miembros van desordenados y la vía 2 está mapeada al revés, como pasa en OSM.
    """
    nodes = [
        # vía 1 (y=0)
        {"type": "node", "id": 1, "lon": 0.0, "lat": 0.0},
        {"type": "node", "id": 2, "lon": 0.01, "lat": 0.0},
        {"type": "node", "id": 3, "lon": 0.02, "lat": 0.0},
        {"type": "node", "id": 4, "lon": 0.03, "lat": 0.0},
        # vía 2 (y=0.0001), unida a la vía 1 solo en los extremos
        {"type": "node", "id": 12, "lon": 0.01, "lat": 0.0001},
        {"type": "node", "id": 13, "lon": 0.02, "lat": 0.0001},
        # ramal hacia el norte desde el nodo 3
        {"type": "node", "id": 23, "lon": 0.02, "lat": 0.01},
    ]
    ways = [
        {"type": "way", "id": 100, "nodes": [1, 2], "tags": {"railway": "rail", "maxspeed": "160"}},
        {"type": "way", "id": 101, "nodes": [2, 3], "tags": {"railway": "rail", "maxspeed": "160"}},
        {"type": "way", "id": 102, "nodes": [3, 4], "tags": {"railway": "rail", "maxspeed": "100"}},
        {
            "type": "way",
            "id": 200,
            "nodes": [4, 13],
            "tags": {"railway": "rail", "maxspeed": "160"},
        },
        {
            "type": "way",
            "id": 201,
            "nodes": [13, 12],
            "tags": {"railway": "rail", "maxspeed": "160"},
        },
        {
            "type": "way",
            "id": 202,
            "nodes": [12, 1],
            "tags": {"railway": "rail", "maxspeed": "160"},
        },
        {"type": "way", "id": 300, "nodes": [3, 23], "tags": {"railway": "rail", "maxspeed": "80"}},
        {"type": "way", "id": 400, "nodes": [3, 23], "tags": {"railway": "platform"}},
    ]
    relation = {
        "type": "relation",
        "id": 7,
        "members": [
            {"type": "way", "ref": w["id"], "role": ""}
            for w in (ways[3], ways[0], ways[6], ways[2], ways[1], ways[4], ways[5], ways[7])
        ],
    }
    return {"elements": [*nodes, *ways, relation]}


def test_trace_follows_one_track_and_ignores_the_branch() -> None:
    raw = _two_track_relation()
    line = trace_osm_relation(raw, 7, start=(0.0, 0.00005), end=(0.03, -0.00002))
    assert line.polyline.coords[0] == (0.0, 0.0)
    assert line.polyline.coords[-1] == (0.03, 0.0)
    # no pasa por el ramal ni se desvía a la otra vía
    assert all(abs(lat) < 0.0002 for _, lat in line.polyline.coords)
    assert not line.gaps_km
    assert [s.maxspeed_kmh for s in line.speed_spans] == [160, 100]
    assert line.speed_spans[0].km_from == 0.0
    assert line.speed_spans[-1].km_to == pytest.approx(line.polyline.length_km)


def test_trace_can_start_mid_line_and_end_on_the_branch() -> None:
    raw = _two_track_relation()
    line = trace_osm_relation(raw, 7, start=(0.01, 0.0), end=(0.02, 0.01))
    assert line.polyline.coords == [(0.01, 0.0), (0.02, 0.0), (0.02, 0.01)]
    assert [s.maxspeed_kmh for s in line.speed_spans] == [160, 80]


def test_trace_without_a_relation_uses_every_way_of_the_file() -> None:
    """Un extracto de vías sin relación (el enlace de Aljucén, en el ramal de Mérida): sin
    ``relation_id`` el camino se busca por todas las vías ferroviarias del fichero."""
    raw = _two_track_relation()
    ways_only = {"elements": [e for e in raw["elements"] if e["type"] != "relation"]}
    line = trace_osm_relation(ways_only, None, (0.0, 0.00005), (0.03, -0.00002))
    with_relation = trace_osm_relation(raw, 7, start=(0.0, 0.00005), end=(0.03, -0.00002))
    assert line.polyline.coords == with_relation.polyline.coords
    assert line.polyline.coords[0] == (0.0, 0.0) and line.polyline.coords[-1] == (0.03, 0.0)
    assert not line.gaps_km
    assert [s.maxspeed_kmh for s in line.speed_spans] == [160, 100]
    # también por el ramal, y sin contar el andén, que no es una vía
    branch = trace_osm_relation(ways_only, None, (0.01, 0.0), (0.02, 0.01))
    assert branch.polyline.coords == [(0.01, 0.0), (0.02, 0.0), (0.02, 0.01)]
    assert [s.maxspeed_kmh for s in branch.speed_spans] == [160, 80]
    # con relación, una vía que no es miembro suyo no se usa; sin ella, sí
    extra_node = {"type": "node", "id": 50, "lon": 0.04, "lat": 0.0}
    extra_way = {"type": "way", "id": 500, "nodes": [4, 50], "tags": {"railway": "rail"}}
    extended = {"elements": [*raw["elements"], extra_node, extra_way]}
    assert trace_osm_relation(extended, None, (0.0, 0.0), (0.04, 0.0)).polyline.coords[-1] == (
        0.04,
        0.0,
    )
    assert trace_osm_relation(extended, 7, (0.0, 0.0), (0.04, 0.0)).polyline.coords[-1] == (
        0.03,
        0.0,
    )
    # los mensajes de error hablan del extracto, no de una relación
    with pytest.raises(ValueError, match="el extracto de vías no tiene vías ferroviarias"):
        trace_osm_relation({"elements": []}, None, (0.0, 0.0), (0.03, 0.0))
    with pytest.raises(ValueError, match="la relación 8 no está en el fichero"):
        trace_osm_relation(raw, 8, (0.0, 0.0), (0.03, 0.0))


def test_chain_in_member_order_is_not_enough_for_unordered_relations() -> None:
    chained = chain_osm_relation(_two_track_relation(), 7)
    assert chained.gaps_km  # el encadenado ingenuo deja huecos: por eso existe el trazado


def test_concat_parts_joins_with_a_short_straight_segment() -> None:
    raw = _two_track_relation()
    a = trace_osm_relation(raw, 7, start=(0.0, 0.0), end=(0.01, 0.0))
    b = trace_osm_relation(raw, 7, start=(0.01, 0.0001), end=(0.03, 0.0))
    joined = concat_parts([(a, "fuente-a"), (b, "fuente-b")])
    assert len(joined.joins_km) == 1 and joined.joins_km[0] * 1000 < 20
    assert [p.source_id for p in joined.part_spans] == ["fuente-a", "fuente-b"]
    assert joined.part_spans[1].km_from == pytest.approx(a.polyline.length_km + joined.joins_km[0])
    assert joined.polyline.length_km == pytest.approx(
        a.polyline.length_km + b.polyline.length_km + joined.joins_km[0]
    )


def test_concat_parts_refuses_a_large_gap() -> None:
    raw = _two_track_relation()
    a = trace_osm_relation(raw, 7, start=(0.0, 0.0), end=(0.01, 0.0))
    b = trace_osm_relation(raw, 7, start=(0.02, 0.01), end=(0.03, 0.0))
    with pytest.raises(ValueError, match="empalme"):
        concat_parts([(a, "a"), (b, "b")])


@pytest.fixture(scope="module")
def conv_spec() -> NetworkSpec:
    return load_network_spec(CONV_SPEC)


@pytest.fixture(scope="module")
def conv(conv_spec: NetworkSpec) -> BuiltNetwork:
    return build_network(conv_spec, DATA_DIR)


def test_conventional_line_is_built_from_two_relations(conv: BuiltNetwork) -> None:
    assert abs(conv.line.polyline.length_km - 442.0) < 3.0
    assert not conv.line.gaps_km
    assert len(conv.line.part_spans) == 2
    assert all(j * 1000 < 100 for j in conv.line.joins_km)
    first, second = conv.line.part_spans
    assert (
        first.source_id == "osm-relation-18368327" and second.source_id == "osm-relation-11351144"
    )
    assert abs(first.km_to - 148.1) < 2.0  # Alcázar de San Juan, PK 148,1 de Adif


@pytest.mark.parametrize(
    ("node_id", "reference_pk"),
    [
        ("aranjuez", 48.7),
        ("alcazar-de-san-juan", 148.1),
        ("manzanares", 197.3),
        ("santa-cruz-de-mudela", 239.0),
        ("linares-baeza", 314.7),
        ("espeluy", 340.9),
        ("andujar", 362.8),
        ("cordoba", 442.0),
    ],
)
def test_conventional_nodes_sit_near_adif_kilometre_points(
    conv: BuiltNetwork, node_id: str, reference_pk: float
) -> None:
    node = conv.node(node_id)
    # Adif conserva la numeración histórica (origen en Atocha y variantes), de ahí la tolerancia.
    assert abs(node.km - reference_pk) < 2.0
    assert node.offset_m < 400


def test_shared_nodes_reuse_the_high_speed_ids(conv: BuiltNetwork) -> None:
    shared = {n.spec.id for n in conv.nodes if n.spec.shared}
    assert shared == {"madrid-puerta-de-atocha", "cordoba"}
    assert conv.nodes[0].spec.id == "madrid-puerta-de-atocha"
    assert conv.nodes[-1].spec.id == "cordoba"


def test_attribute_sections_mark_single_track_segments(conv: BuiltNetwork) -> None:
    by_id = {s.id.split(":", 1)[1]: s for s in conv.segments}
    assert by_id["manzanares:valdepenas"].tracks == 2
    assert by_id["santa-cruz-de-mudela:almuradiel-viso-del-marques"].tracks == 1
    assert by_id["vilches:vadollano"].tracks == 1
    assert by_id["vadollano:linares-baeza"].tracks == 2
    assert by_id["linares-baeza:espeluy"].tracks == 1
    assert by_id["rabanales:cordoba"].tracks == 1
    single_km = sum(s.length_km for s in conv.segments if s.tracks == 1)
    assert 180 < single_km < 200


def test_segments_carry_the_source_of_their_part(conv: BuiltNetwork) -> None:
    sources = [(s.from_node.spec.id, s.source_id) for s in conv.segments]
    assert ("quero", "osm-relation-18368327") in sources
    assert ("alcazar-de-san-juan", "osm-relation-11351144") in sources


def test_the_two_lines_share_the_data_dir_layout(conv_spec: NetworkSpec) -> None:
    for part in conv_spec.line.geometry_source.parts:
        assert (DATA_DIR / part.file).exists(), part.file
    assert Path(CONV_SPEC).exists()
