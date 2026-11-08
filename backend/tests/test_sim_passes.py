"""Reglas de paso por tramo, comprobadas con casos que se pueden calcular a mano."""

from collections.abc import Iterable, Sequence

import pytest

from oniel.sim.passes import LineNode, LineSegment, SegmentPass, StopCall, resolve_passes

# Línea de juguete con los kilómetros reales de la LAV (redondeados)
NODES = {
    "madrid": LineNode("madrid", 0.0, -3.6909, 40.4064),
    "ciudad-real": LineNode("ciudad-real", 170.8, -3.9136, 38.9853),
    "puertollano": LineNode("puertollano", 209.8, -4.1117, 38.6913),
    "villanueva": LineNode("villanueva", 285.2, -4.5710, 38.2554),
    "adamuz": LineNode("adamuz", 317.8, -4.5410, 38.0410),
    "cordoba": LineNode("cordoba", 343.6, -4.7895, 37.8883),
    "bif-malaga": LineNode("bif-malaga", 358.0, -4.9417, 37.8399),
    "sevilla": LineNode("sevilla", 470.3, -5.9749, 37.3925),
}
SEGMENTS = [
    LineSegment("madrid-cr", 0.0, 170.8),
    LineSegment("cr-pu", 170.8, 209.8),
    LineSegment("pu-vi", 209.8, 285.2),
    LineSegment("vi-ad", 285.2, 317.8),
    LineSegment("ad-co", 317.8, 343.6),
    LineSegment("co-bif", 343.6, 358.0),
    LineSegment("bif-se", 358.0, 470.3),
]


def hm(h: int, m: int) -> int:
    return h * 3600 + m * 60


def call(
    seq: int,
    stop_id: str,
    name: str,
    arr: int,
    dep: int,
    node: str | None = None,
    exits: Sequence[str] = (),
    lon: float | None = None,
    lat: float | None = None,
) -> StopCall:
    return StopCall(seq, stop_id, name, arr, dep, lon, lat, node, tuple(exits))


# AVE 02070 del GTFS: Madrid 7:00 · Ciudad Real 7:53/7:55 · Puertollano 8:09/8:11 · Córdoba 8:53/8:55 · Sevilla 9:48
AVE_02070 = [
    call(1, "60000", "Madrid", hm(7, 0), hm(7, 0), node="madrid"),
    call(2, "37200", "Ciudad Real", hm(7, 53), hm(7, 55), node="ciudad-real"),
    call(3, "37300", "Puertollano", hm(8, 9), hm(8, 11), node="puertollano"),
    call(4, "50500", "Córdoba", hm(8, 53), hm(8, 55), node="cordoba"),
    call(5, "51003", "Sevilla", hm(9, 48), hm(9, 48), node="sevilla"),
]


def by_id(passes: Iterable[SegmentPass]) -> dict[str, SegmentPass]:
    return {p.segment_id: p for p in passes}


def test_published_pass_between_two_stops() -> None:
    passes, resolution = resolve_passes(AVE_02070, NODES, SEGMENTS)
    assert resolution == "completa"
    p = by_id(passes)["cr-pu"]
    assert p.kind == "publicado"
    assert (p.enter_s, p.exit_s) == (hm(7, 55), hm(8, 9))
    assert p.enter_margin_s == 0 and p.exit_margin_s == 0 and p.km_increasing is True


def test_estimated_pass_is_proportional_to_distance() -> None:
    """Puertollano 8:11 → Córdoba 8:53 son 42 min para 133,8 km.

    Puertollano–Villanueva mide 75,4 km → 23,66 min → sale a las 8:34:40.
    Villanueva–Adamuz mide 32,6 km → 10,23 min → sale a las 8:44:54.
    Margen: 15 % de 42 min = 6,3 min (378 s).
    """
    p = by_id(resolve_passes(AVE_02070, NODES, SEGMENTS)[0])
    pu_vi, vi_ad, ad_co = p["pu-vi"], p["vi-ad"], p["ad-co"]
    assert pu_vi.kind == vi_ad.kind == ad_co.kind == "estimado"
    assert pu_vi.enter_s == hm(8, 11) and pu_vi.enter_margin_s == 0  # entra con hora publicada
    assert pu_vi.exit_s == pytest.approx(hm(8, 11) + 42 * 60 * 75.4 / 133.8, abs=1)
    assert vi_ad.enter_s == pytest.approx(pu_vi.exit_s)
    assert vi_ad.exit_s == pytest.approx(hm(8, 11) + 42 * 60 * (75.4 + 32.6) / 133.8, abs=1)
    assert ad_co.exit_s == hm(8, 53) and ad_co.exit_margin_s == 0
    assert vi_ad.enter_margin_s == vi_ad.exit_margin_s == pytest.approx(378)


def test_margin_has_a_floor_of_three_minutes() -> None:
    calls = [
        call(1, "a", "Villanueva", hm(9, 0), hm(9, 0), node="villanueva"),
        call(2, "b", "Córdoba", hm(9, 14), hm(9, 14), node="cordoba"),
    ]
    p = by_id(resolve_passes(calls, NODES, SEGMENTS)[0])
    assert p["vi-ad"].exit_margin_s == 180  # 15 % de 14 min son 2,1 min → se aplica el mínimo


def test_exit_to_malaga_uses_straight_line_share() -> None:
    """Córdoba 9:00 → Málaga 9:50 (50 min). Hasta la bifurcación hay 14,4 km por la línea y desde
    ahí unos 130 km en línea recta hasta Málaga: el tren sale de la línea a los ~5 min."""
    calls = [
        call(1, "60000", "Madrid", hm(7, 0), hm(7, 0), node="madrid"),
        call(2, "50500", "Córdoba", hm(8, 55), hm(9, 0), node="cordoba"),
        call(
            3,
            "54413",
            "Málaga",
            hm(9, 50),
            hm(9, 50),
            exits=["bif-malaga"],
            lon=-4.4314,
            lat=36.7113,
        ),
    ]
    passes, resolution = resolve_passes(calls, NODES, SEGMENTS)
    p = by_id(passes)
    assert resolution == "completa"
    assert "bif-se" not in p  # no llega a Sevilla
    co_bif = p["co-bif"]
    assert co_bif.kind == "estimado" and co_bif.enter_s == hm(9, 0) and co_bif.enter_margin_s == 0
    assert co_bif.exit_s is not None and hm(9, 3) < co_bif.exit_s < hm(9, 9)
    assert co_bif.exit_margin_s == 300  # 30 % de ~5 min < mínimo de 5 min


def test_exit_choice_respects_direction() -> None:
    """Un tren Madrid → Córdoba → Huelva sale por Majarabique; si para en Sevilla, no vuelve atrás."""
    nodes = dict(NODES, majarabique=LineNode("majarabique", 462.5, -5.958, 37.459))
    segs = [
        *SEGMENTS[:-1],
        LineSegment("bif-maj", 358.0, 462.5),
        LineSegment("maj-se", 462.5, 470.3),
    ]

    def huelva(seq: int) -> StopCall:
        return call(
            seq,
            "43019",
            "Huelva",
            hm(11, 0),
            hm(11, 0),
            exits=["majarabique", "sevilla"],
            lon=-6.9448,
            lat=37.2526,
        )

    direct = [
        call(1, "60000", "Madrid", hm(7, 0), hm(7, 0), node="madrid"),
        call(2, "50500", "Córdoba", hm(8, 50), hm(8, 55), node="cordoba"),
        huelva(3),
    ]
    p = by_id(resolve_passes(direct, nodes, segs)[0])
    assert "bif-maj" in p and "maj-se" not in p
    via_sevilla = direct[:2] + [
        call(3, "51003", "Sevilla", hm(9, 40), hm(9, 45), node="sevilla"),
        huelva(4),
    ]
    p2 = by_id(resolve_passes(via_sevilla, nodes, segs)[0])
    assert "maj-se" in p2 and p2["maj-se"].kind == "estimado"
    assert all(v.km_increasing for v in p2.values())


def test_unknown_stop_makes_passes_indeterminate() -> None:
    calls = [
        call(1, "60000", "Madrid", hm(7, 0), hm(7, 0), node="madrid"),
        call(2, "xxx", "Parada desconocida", hm(7, 40), hm(7, 42)),
        call(3, "50500", "Córdoba", hm(8, 55), hm(9, 0), node="cordoba"),
    ]
    passes, resolution = resolve_passes(calls, NODES, SEGMENTS)
    assert resolution == "parcial"
    assert {p.kind for p in passes} == {"indeterminado"}
    assert {p.segment_id for p in passes} == {"madrid-cr", "cr-pu", "pu-vi", "vi-ad", "ad-co"}


def test_reverse_direction_sevilla_to_madrid() -> None:
    calls = [
        call(1, "51003", "Sevilla", hm(16, 0), hm(16, 0), node="sevilla"),
        call(2, "50500", "Córdoba", hm(16, 40), hm(16, 45), node="cordoba"),
        call(3, "60000", "Madrid", hm(18, 30), hm(18, 30), node="madrid"),
    ]
    p = by_id(resolve_passes(calls, NODES, SEGMENTS)[0])
    assert p["co-bif"].km_increasing is False
    assert (
        p["co-bif"].exit_s == hm(16, 40) and p["co-bif"].exit_margin_s == 0
    )  # llega a Córdoba a hora publicada
    assert p["ad-co"].enter_s == hm(16, 45) and p["ad-co"].enter_margin_s == 0
    assert p["madrid-cr"].exit_s == hm(18, 30)
