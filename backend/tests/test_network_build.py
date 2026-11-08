import pytest

from oniel.network.build import BuiltNetwork, chain_osm_relation


def test_line_is_continuous_and_matches_adif_length(built: BuiltNetwork) -> None:
    assert not built.line.gaps_km
    assert abs(built.line.polyline.length_km - 471.8) < 3.0


@pytest.mark.parametrize(
    ("node_id", "reference_pk"),
    [
        ("urda", 119.7),
        ("ciudad-real", 170.7),
        ("puertollano", 209.4),
        ("villanueva-de-cordoba", 285.2),
        ("cordoba", 343.7),
        ("bif-malaga", 358.0),
        ("sevilla-santa-justa", 470.5),
    ],
)
def test_nodes_sit_on_adif_kilometre_points(
    built: BuiltNetwork, node_id: str, reference_pk: float
) -> None:
    node = built.node(node_id)
    assert abs(node.km - reference_pk) < 1.0
    assert node.offset_m < 200


def test_segments_are_consecutive_and_cover_the_line(built: BuiltNetwork) -> None:
    segs = built.segments
    assert segs[0].km_from == pytest.approx(0.0)
    for a, b in zip(segs, segs[1:], strict=False):
        assert a.km_to == pytest.approx(b.km_from)
        assert a.to_node.spec.id == b.from_node.spec.id
    assert segs[-1].to_node.spec.id == "sevilla-santa-justa"
    assert all(s.max_speed_kmh is not None for s in segs)


def test_chain_reverses_ways_when_needed() -> None:
    raw = {
        "elements": [
            {"type": "node", "id": 1, "lon": 0.0, "lat": 0.0},
            {"type": "node", "id": 2, "lon": 0.01, "lat": 0.0},
            {"type": "node", "id": 3, "lon": 0.02, "lat": 0.0},
            {"type": "way", "id": 10, "nodes": [1, 2], "tags": {"maxspeed": "200"}},
            {"type": "way", "id": 11, "nodes": [3, 2], "tags": {"maxspeed": "160"}},  # al revés
            {
                "type": "relation",
                "id": 99,
                "members": [
                    {"type": "way", "ref": 10, "role": ""},
                    {"type": "way", "ref": 11, "role": ""},
                ],
            },
        ]
    }
    line = chain_osm_relation(raw, 99)
    assert line.polyline.coords == [(0.0, 0.0), (0.01, 0.0), (0.02, 0.0)]
    assert not line.gaps_km
    assert [s.maxspeed_kmh for s in line.speed_spans] == [200, 160]
