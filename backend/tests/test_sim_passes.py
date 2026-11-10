"""Reglas de paso por tramo, comprobadas con casos que se pueden calcular a mano."""

from collections.abc import Iterable, Sequence

import pytest

from oniel.sim.passes import (
    ExitDistance,
    LineNode,
    LineSegment,
    SegmentPass,
    StopCall,
    resolve_passes,
)

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


def test_known_distance_along_another_line_replaces_the_straight_line() -> None:
    """Un tren que sale de la línea en Córdoba hacia una parada de otra línea cargada.

    Córdoba 9:00 → parada X 10:00 (60 min). Si la asignación trae 86,4 km reales desde Córdoba
    hasta X por la otra línea, Adamuz–Córdoba (25,8 km) se reparte con 25,8 / (25,8 + 86,4):
    el tren sale de Córdoba... no: entra en Córdoba a las 9:00 publicadas y, en sentido inverso,
    el tramo Córdoba→Adamuz se recorre en 60 × 25,8 / 112,2 = 13,8 min → sale a las 9:13:48.
    Con la línea recta (0 km, porque X no lleva coordenadas) el reparto daría los 60 min enteros.
    """
    calls = [
        call(1, "51003", "Sevilla", hm(8, 0), hm(8, 0), node="sevilla"),
        call(2, "50500", "Córdoba", hm(8, 55), hm(9, 0), node="cordoba"),
        StopCall(
            3,
            "x",
            "Parada X",
            hm(10, 0),
            hm(10, 0),
            node_id=None,
            exit_node_ids=("adamuz",),
            exit_distances={"adamuz": ExitDistance(86.4, "86 km por esa línea hasta Parada X")},
            exit_note="está en la otra línea, con la que este tren enlaza en Adamuz",
        ),
    ]
    p = by_id(resolve_passes(calls, NODES, SEGMENTS)[0])
    ad_co = p["ad-co"]
    assert ad_co.kind == "estimado" and ad_co.km_increasing is False
    assert ad_co.enter_s == hm(9, 0) and ad_co.enter_margin_s == 0
    assert ad_co.exit_s == pytest.approx(hm(9, 0) + 60 * 60 * 25.8 / (25.8 + 86.4), abs=1)
    assert ad_co.exit_margin_s == 300  # 30 % de 13,8 min < mínimo de 5 min
    assert "Parada X está en la otra línea, con la que este tren enlaza en Adamuz" in ad_co.basis
    assert "sale de esta línea por adamuz" in ad_co.basis  # sin nombre, se usa el id
    assert "y, desde adamuz, 86 km por esa línea hasta Parada X;" in ad_co.basis
    assert "vi-ad" not in p  # no sigue hacia Villanueva


def _through(
    seq: int, name: str, when: int, exit_node: str, km: float | None, note: str | None
) -> StopCall:
    """Parada fuera de la línea, a la que se llega (o no) por otra línea cargada."""
    distances = {} if km is None else {exit_node: ExitDistance(km, f"{km:.0f} km por otra línea")}
    return StopCall(
        seq,
        name,
        name,
        when,
        when,
        exit_node_ids=(exit_node,),
        exit_distances=distances,
        exit_note=note,
    )


def test_a_train_that_crosses_the_line_between_two_other_loaded_lines_is_estimated() -> None:
    """Parada A 8:00 → parada B 10:00 (120 min), las dos en otras líneas cargadas.

    El tren entra por Ciudad Real, a 100 km de A, recorre 172,8 km hasta Córdoba y sigue 50 km
    hasta B: 322,8 km en total. Entra a los 120 × 100 / 322,8 = 37,2 min (8:37:10) y sale a los
    120 × 272,8 / 322,8 = 101,4 min (9:41:25). Pasa fuera 37,2 min antes y 18,6 min después:
    el margen es el 30 % del mayor, 11,2 min (669 s), en todos los tramos.
    """
    calls = [
        _through(1, "Parada A", hm(8, 0), "ciudad-real", 100.0, "está en la línea A"),
        _through(2, "Parada B", hm(10, 0), "cordoba", 50.0, "está en la línea B"),
    ]
    passes, resolution = resolve_passes(calls, NODES, SEGMENTS)
    p = by_id(passes)
    assert resolution == "completa"
    assert set(p) == {"cr-pu", "pu-vi", "vi-ad", "ad-co"}
    assert all(x.kind == "estimado" and x.km_increasing for x in p.values())
    enter = hm(8, 0) + 120 * 60 * 100 / 322.8
    leave = hm(8, 0) + 120 * 60 * 272.8 / 322.8
    assert p["cr-pu"].enter_s == pytest.approx(enter, abs=1)
    assert p["ad-co"].exit_s == pytest.approx(leave, abs=1)
    assert p["pu-vi"].enter_s == pytest.approx(p["cr-pu"].exit_s)
    margin = 0.3 * (enter - hm(8, 0))
    assert all(
        x.enter_margin_s == pytest.approx(margin) and x.exit_margin_s == pytest.approx(margin)
        for x in p.values()
    )
    basis = p["vi-ad"].basis
    assert "recorre la línea sin parar en ella; entra por ciudad-real y sale por cordoba" in basis
    assert "Parada A está en la línea A y Parada B está en la línea B." in basis
    assert "usa 100 km antes de ciudad-real, 173 km por la línea y 50 km después de" in basis
    assert "margen de ±11 min" in basis

    # en sentido contrario, el mismo recorrido al revés
    back = [
        _through(1, "Parada B", hm(8, 0), "cordoba", 50.0, "está en la línea B"),
        _through(2, "Parada A", hm(10, 0), "ciudad-real", 100.0, "está en la línea A"),
    ]
    q = by_id(resolve_passes(back, NODES, SEGMENTS)[0])
    assert set(q) == set(p) and all(x.km_increasing is False for x in q.values())
    assert q["ad-co"].enter_s == pytest.approx(hm(8, 0) + 120 * 60 * 50 / 322.8, abs=1)
    assert "entra por cordoba y sale por ciudad-real" in q["ad-co"].basis


def test_two_stops_outside_the_network_stay_indeterminate() -> None:
    """Sin una distancia conocida a cada lado no se puede fijar el recorrido: sigue indeterminado."""
    for km_a, km_b in ((None, None), (100.0, None), (None, 50.0)):
        calls = [
            _through(1, "Parada A", hm(8, 0), "ciudad-real", km_a, None),
            _through(2, "Parada B", hm(10, 0), "cordoba", km_b, None),
        ]
        passes, _ = resolve_passes(calls, NODES, SEGMENTS)
        assert {x.kind for x in passes} == {"indeterminado"}
        assert {x.segment_id for x in passes} == {"cr-pu", "pu-vi", "vi-ad", "ad-co"}
