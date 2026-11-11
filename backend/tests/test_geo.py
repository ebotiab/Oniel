from oniel.geo import Polyline, haversine_km


def test_haversine_madrid_sevilla_rough() -> None:
    # Atocha → Santa Justa en línea recta: unos 390 km
    d = haversine_km((-3.6909, 40.4064), (-5.9749, 37.3925))
    assert 385 < d < 395


def test_polyline_project_and_point_at_roundtrip() -> None:
    line = Polyline([(0.0, 0.0), (1.0, 0.0), (1.0, 1.0)])
    p = line.project((0.5, 0.01))
    assert p.index == 0 and 0.45 < p.km / line.cum_km[1] < 0.55
    x, y = line.point_at(p.km)
    assert abs(x - 0.5) < 1e-6 and abs(y) < 1e-9
    sl = line.slice(0, line.length_km)
    assert sl[0] == (0.0, 0.0) and sl[-1] == (1.0, 1.0) and len(sl) == 3


def test_simplify_keeps_ends_and_stays_within_tolerance() -> None:
    from oniel.geo import Polyline, simplify

    # Una recta con un quiebro de unos 40 m y otro de unos 900 m.
    coords = [(-3.70, 40.0), (-3.65, 40.0004), (-3.60, 40.0), (-3.55, 40.008), (-3.50, 40.0)]
    out = simplify(coords, 200)
    assert out[0] == coords[0] and out[-1] == coords[-1]
    assert out == [coords[0], coords[2], coords[3], coords[4]]
    # ningún vértice original queda a más de la tolerancia de la línea simplificada
    line = Polyline(out)
    assert max(line.project(c).offset_m for c in coords) <= 200
    assert simplify(coords, 0) == coords
    assert simplify(coords[:2], 200) == coords[:2]
