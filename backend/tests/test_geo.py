from oniel.geo import Polyline, haversine_km


def test_haversine_madrid_sevilla_rough():
    # Atocha → Santa Justa en línea recta: unos 390 km
    d = haversine_km((-3.6909, 40.4064), (-5.9749, 37.3925))
    assert 385 < d < 395


def test_polyline_project_and_point_at_roundtrip():
    line = Polyline([(0.0, 0.0), (1.0, 0.0), (1.0, 1.0)])
    p = line.project((0.5, 0.01))
    assert p.index == 0 and 0.45 < p.km / line.cum_km[1] < 0.55
    x, y = line.point_at(p.km)
    assert abs(x - 0.5) < 1e-6 and abs(y) < 1e-9
    sl = line.slice(0, line.length_km)
    assert sl[0] == (0.0, 0.0) and sl[-1] == (1.0, 1.0) and len(sl) == 3
