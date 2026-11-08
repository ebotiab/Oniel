import datetime as dt

from oniel.sim.closure import ClosureWindow, classify
from oniel.sim.passes import SegmentPass


def hm(h: int, m: int) -> int:
    return h * 3600 + m * 60


def make(kind, enter, exit_, margin):
    return SegmentPass("s", kind, enter, exit_, margin, margin, True, "base")


def test_window_crossing_midnight():
    w = ClosureWindow.from_times(dt.time(23, 0), dt.time(1, 0))
    assert (w.start_s, w.end_s) == (hm(23, 0), hm(25, 0))


def test_published_inside_window_is_affected():
    w = ClosureWindow.from_times(dt.time(8, 0), dt.time(9, 0))
    assert classify(make("publicado", hm(8, 11), hm(8, 53), 0), w).status == "afectado_publicado"


def test_outside_window_even_with_margin():
    w = ClosureWindow.from_times(dt.time(8, 0), dt.time(9, 0))
    assert classify(make("estimado", hm(9, 10), hm(9, 30), 300), w).status == "no_afectado"


def test_overlap_only_inside_margin_is_indeterminate():
    w = ClosureWindow.from_times(dt.time(8, 0), dt.time(9, 0))
    # pasa de 9:02 a 9:20 con ±5 min: toca la ventana solo por el margen
    assert classify(make("estimado", hm(9, 2), hm(9, 20), 300), w).status == "indeterminado"
    # pasa de 8:50 a 9:20 con ±5 min: el solape existe aunque se descuente el margen
    assert classify(make("estimado", hm(8, 50), hm(9, 20), 300), w).status == "afectado_estimado"


def test_indeterminate_pass_stays_indeterminate():
    w = ClosureWindow.from_times(dt.time(0, 0), dt.time(23, 59))
    assert (
        classify(
            SegmentPass("s", "indeterminado", None, None, 0, 0, None, "sin recorrido"), w
        ).status
        == "indeterminado"
    )


def test_previous_day_train_is_shifted():
    w = ClosureWindow.from_times(dt.time(0, 0), dt.time(1, 0))
    late = make("publicado", hm(24, 20), hm(24, 50), 0)  # 00:20–00:50 del día siguiente al suyo
    assert classify(late, w, day_offset_s=-86400).status == "afectado_publicado"
    assert classify(late, w).status == "no_afectado"


def test_hand_calculated_case_ave_02070():
    """Cierre de Villanueva de Córdoba–Adamuz el 13/11/2026 de 8:00 a 9:00.

    El AVE 02070 sale de Puertollano a las 8:11 y llega a Córdoba a las 8:53 (42 min, 133,8 km).
    Villanueva–Adamuz empieza a 75,4 km de Puertollano: 8:11 + 42·75,4/133,8 = 8:34:40,
    y termina a 108 km: 8:11 + 42·108/133,8 = 8:44:54. Margen ±6,3 min. Afectado (estimado).
    """
    w = ClosureWindow.from_times(dt.time(8, 0), dt.time(9, 0))
    enter = hm(8, 11) + 42 * 60 * 75.4 / 133.8
    exit_ = hm(8, 11) + 42 * 60 * 108.0 / 133.8
    v = classify(make("estimado", enter, exit_, 378), w)
    assert v.status == "afectado_estimado"
    assert "08:34" in v.explanation and "08:44" in v.explanation
