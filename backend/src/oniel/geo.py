"""Geometría mínima sin dependencias: distancias y proyección sobre una polilínea."""

from __future__ import annotations

import math
from dataclasses import dataclass

Coord = tuple[float, float]  # (lon, lat)

EARTH_RADIUS_KM = 6371.0088


def haversine_km(a: Coord, b: Coord) -> float:
    lon1, lat1, lon2, lat2 = map(math.radians, (a[0], a[1], b[0], b[1]))
    h = (
        math.sin((lat2 - lat1) / 2) ** 2
        + math.cos(lat1) * math.cos(lat2) * math.sin((lon2 - lon1) / 2) ** 2
    )
    return 2 * EARTH_RADIUS_KM * math.asin(math.sqrt(h))


@dataclass(frozen=True)
class Projection:
    km: float
    offset_m: float
    index: int  # índice del vértice anterior
    t: float  # fracción dentro del segmento [index, index+1]


class Polyline:
    """Polilínea con kilometraje acumulado; todo el modelo lineal de una línea cuelga de aquí."""

    def __init__(self, coords: list[Coord]):
        if len(coords) < 2:
            raise ValueError("una polilínea necesita al menos dos vértices")
        self.coords = coords
        self.cum_km = [0.0]
        for i in range(1, len(coords)):
            self.cum_km.append(self.cum_km[-1] + haversine_km(coords[i - 1], coords[i]))

    @property
    def length_km(self) -> float:
        return self.cum_km[-1]

    def project(self, p: Coord) -> Projection:
        """Punto más cercano de la polilínea (aproximación equirrectangular local)."""
        kx = math.cos(math.radians(p[1]))
        best: Projection | None = None
        for i in range(1, len(self.coords)):
            a, b = self.coords[i - 1], self.coords[i]
            ax, ay = (a[0] - p[0]) * kx, a[1] - p[1]
            bx, by = (b[0] - p[0]) * kx, b[1] - p[1]
            dx, dy = bx - ax, by - ay
            l2 = dx * dx + dy * dy
            t = 0.0 if l2 == 0 else max(0.0, min(1.0, -(ax * dx + ay * dy) / l2))
            px, py = ax + t * dx, ay + t * dy
            dist_m = math.hypot(px, py) * 111_320
            if best is None or dist_m < best.offset_m:
                km = self.cum_km[i - 1] + t * (self.cum_km[i] - self.cum_km[i - 1])
                best = Projection(km=km, offset_m=dist_m, index=i - 1, t=t)
        assert best is not None
        return best

    def point_at(self, km: float) -> Coord:
        km = max(0.0, min(self.length_km, km))
        i = self._index_for(km)
        a, b = self.coords[i], self.coords[i + 1]
        span = self.cum_km[i + 1] - self.cum_km[i]
        t = 0.0 if span == 0 else (km - self.cum_km[i]) / span
        return (a[0] + t * (b[0] - a[0]), a[1] + t * (b[1] - a[1]))

    def slice(self, km_from: float, km_to: float) -> list[Coord]:
        """Vértices entre dos kilómetros, con los extremos interpolados exactos."""
        if km_to < km_from:
            km_from, km_to = km_to, km_from
        start = self.point_at(km_from)
        end = self.point_at(km_to)
        inner = [c for c, k in zip(self.coords, self.cum_km, strict=True) if km_from < k < km_to]
        return [start, *inner, end]

    def _index_for(self, km: float) -> int:
        lo, hi = 0, len(self.cum_km) - 2
        while lo < hi:
            mid = (lo + hi + 1) // 2
            if self.cum_km[mid] <= km:
                lo = mid
            else:
                hi = mid - 1
        return lo
