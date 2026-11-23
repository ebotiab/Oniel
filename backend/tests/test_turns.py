"""De qué lado de un nodo sale cada tramo (``oniel.routing.turns``), con trazados dibujados a mano."""

from __future__ import annotations

from dataclasses import dataclass
from typing import Any

from oniel.routing.turns import turn_sides

#: Un grado de longitud a 40° de latitud son unos 85 km: 0,02° pasan de sobra de los 500 m.
LAT = 40.0


@dataclass(frozen=True)
class Tramo:
    id: str
    from_node_id: str
    to_node_id: str
    status: str = "disponible"


def _line(*points: tuple[float, float]) -> dict[str, Any]:
    return {"type": "LineString", "coordinates": [[lon, LAT + lat] for lon, lat in points]}


#: Una bifurcación en Y: el tronco llega por el oeste y dos ramas salen hacia el este.
TRONCO = (Tramo("tronco", "oeste", "bif"), _line((-0.05, 0.0), (0.0, 0.0)))
RAMA_NORTE = (Tramo("norte", "bif", "nordeste"), _line((0.0, 0.0), (0.05, 0.005)))
RAMA_SUR = (Tramo("sur", "bif", "sudeste"), _line((0.0, 0.0), (0.05, -0.005)))


def test_the_two_branches_of_a_junction_leave_by_the_same_side() -> None:
    turns, problems = turn_sides([TRONCO, RAMA_NORTE, RAMA_SUR], station_ids=[])
    assert problems == []
    sides = turns["bif"]
    assert sides["norte"] == sides["sur"] != sides["tronco"]


def test_stations_have_no_sides() -> None:
    turns, _ = turn_sides([TRONCO, RAMA_NORTE, RAMA_SUR], station_ids=["bif"])
    assert "bif" not in turns


def test_the_side_is_read_from_the_end_of_the_segment_that_touches_the_node() -> None:
    """El tronco llega al nodo por su final y las ramas salen por su principio: da igual."""
    reversed_branch = (Tramo("sur", "sudeste", "bif"), _line((0.05, -0.005), (0.0, 0.0)))
    turns, problems = turn_sides([TRONCO, RAMA_NORTE, reversed_branch], station_ids=[])
    assert problems == []
    assert turns["bif"]["norte"] == turns["bif"]["sur"] != turns["bif"]["tronco"]


def test_segments_that_are_not_available_do_not_count() -> None:
    planned = (Tramo("sur", "bif", "sudeste", status="prevista"), RAMA_SUR[1])
    turns, _ = turn_sides([TRONCO, RAMA_NORTE, planned], station_ids=[])
    assert set(turns["bif"]) == {"tronco", "norte"}


def test_two_segments_follow_each_other_even_round_a_sharp_curve() -> None:
    """Con dos tramos no hay nada que elegir: uno sigue al otro aunque la vía doble 90°."""
    curve = (Tramo("curva", "bif", "norte"), _line((0.0, 0.0), (0.0, 0.05)))
    turns, problems = turn_sides([TRONCO, curve], station_ids=[])
    assert problems == []
    assert turns["bif"]["tronco"] != turns["bif"]["curva"]


def test_two_segments_that_leave_together_are_on_the_same_side() -> None:
    """Dos ramas sin su tronco cargado: de una a otra no se pasa sin invertir la marcha."""
    turns, problems = turn_sides([RAMA_NORTE, RAMA_SUR], station_ids=[])
    assert problems == []
    assert turns["bif"]["norte"] == turns["bif"]["sur"]


def test_a_junction_with_a_doubtful_angle_is_reported_and_left_out() -> None:
    """Tres tramos y uno sale a 90° de los otros: no se sabe de qué lado está."""
    across = (Tramo("travesia", "bif", "norte"), _line((0.0, 0.0), (0.0, 0.05)))
    turns, problems = turn_sides([TRONCO, RAMA_NORTE, across], station_ids=[])
    assert "bif" not in turns
    assert [p.node_id for p in problems] == ["bif"]
    assert "travesia" in problems[0].detail and "°" in problems[0].detail


def test_the_heading_is_taken_500_m_along_the_track_not_at_the_first_vertex() -> None:
    """Un quiebro de unos metros junto al nodo no cambia el lado: se mira a 500 m por el trazado."""
    kinked = (Tramo("norte", "bif", "nordeste"), _line((0.0, 0.0), (0.0, 0.0001), (0.05, 0.005)))
    turns, problems = turn_sides([TRONCO, kinked, RAMA_SUR], station_ids=[])
    assert problems == []
    assert turns["bif"]["norte"] == turns["bif"]["sur"] != turns["bif"]["tronco"]
