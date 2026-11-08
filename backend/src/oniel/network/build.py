"""Construye el modelo lineal de una línea a partir de la geometría cruda y la especificación curada.

Pasos: encadenar las vías de la relación OSM en una sola polilínea, situar cada nodo sobre ella
(por proyección o por kilómetro), cortar la línea en tramos entre nodos consecutivos y resumir la
velocidad máxima de cada tramo a partir de las etiquetas de las vías.
"""

from __future__ import annotations

import json
from collections import defaultdict
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any

from oniel.geo import Coord, Polyline, haversine_km
from oniel.network.spec import NetworkSpec, NodeSpec

MAX_SNAP_OFFSET_M = 400.0


@dataclass(frozen=True)
class SpeedSpan:
    km_from: float
    km_to: float
    maxspeed_kmh: int | None


@dataclass
class ChainedLine:
    polyline: Polyline
    speed_spans: list[SpeedSpan]
    gaps_km: list[float] = field(default_factory=list)


@dataclass(frozen=True)
class BuiltNode:
    spec: NodeSpec
    lon: float
    lat: float
    km: float
    offset_m: float


@dataclass(frozen=True)
class BuiltSegment:
    id: str
    seq: int
    from_node: BuiltNode
    to_node: BuiltNode
    km_from: float
    km_to: float
    length_km: float
    max_speed_kmh: int | None
    typical_speed_kmh: int | None
    coords: list[Coord]


@dataclass
class BuiltNetwork:
    spec: NetworkSpec
    line: ChainedLine
    nodes: list[BuiltNode]
    segments: list[BuiltSegment]

    def node(self, node_id: str) -> BuiltNode:
        for n in self.nodes:
            if n.spec.id == node_id:
                return n
        raise KeyError(node_id)


def chain_osm_relation(raw: dict[str, Any], relation_id: int) -> ChainedLine:
    """Encadena las vías de una relación OSM (descarga Overpass con nodos) en una polilínea."""
    elements = raw["elements"]
    relations = [e for e in elements if e["type"] == "relation" and e["id"] == relation_id]
    if not relations:
        raise ValueError(f"la relación {relation_id} no está en el fichero")
    ways = {e["id"]: e for e in elements if e["type"] == "way"}
    nodes: dict[int, Coord] = {
        e["id"]: (e["lon"], e["lat"]) for e in elements if e["type"] == "node"
    }
    member_ids = [
        m["ref"] for m in relations[0]["members"] if m["type"] == "way" and m["ref"] in ways
    ]

    coords: list[Coord] = []
    spans: list[tuple[int, int, int | None]] = []  # (índice inicial, índice final, maxspeed)
    gaps: list[float] = []
    for wid in member_ids:
        way = ways[wid]
        pts = [nodes[n] for n in way["nodes"] if n in nodes]
        if len(pts) < 2:
            continue
        if coords:
            last = coords[-1]
            if haversine_km(last, pts[-1]) < haversine_km(last, pts[0]):
                pts = pts[::-1]
            gap = haversine_km(last, pts[0])
            if gap > 0.001:
                gaps.append(gap)
            else:
                pts = pts[1:]
        start = max(0, len(coords) - 1)
        coords.extend(pts)
        spans.append((start, len(coords) - 1, _parse_maxspeed(way.get("tags", {}).get("maxspeed"))))

    polyline = Polyline(coords)
    speed_spans = [
        SpeedSpan(polyline.cum_km[a], polyline.cum_km[b], ms) for a, b, ms in spans if b > a
    ]
    return ChainedLine(polyline=polyline, speed_spans=speed_spans, gaps_km=gaps)


def _parse_maxspeed(value: str | None) -> int | None:
    if not value:
        return None
    digits = "".join(ch for ch in value if ch.isdigit())
    return int(digits) if digits else None


def place_nodes(spec: NetworkSpec, line: ChainedLine) -> list[BuiltNode]:
    built: list[BuiltNode] = []
    for n in spec.nodes:
        if n.position.km is not None:
            lon, lat = line.polyline.point_at(n.position.km)
            built.append(BuiltNode(n, lon, lat, n.position.km, 0.0))
        else:
            assert n.position.lon is not None and n.position.lat is not None
            proj = line.polyline.project((n.position.lon, n.position.lat))
            if proj.offset_m > MAX_SNAP_OFFSET_M:
                raise ValueError(
                    f"el nodo {n.id} está a {proj.offset_m:.0f} m de la línea (máximo {MAX_SNAP_OFFSET_M:.0f} m)"
                )
            lon, lat = line.polyline.point_at(proj.km)
            built.append(BuiltNode(n, lon, lat, proj.km, proj.offset_m))
    built.sort(key=lambda b: b.km)
    return built


def speed_summary(line: ChainedLine, km_from: float, km_to: float) -> tuple[int | None, int | None]:
    """Velocidad máxima y velocidad predominante (por longitud) entre dos kilómetros."""
    weights: dict[int, float] = defaultdict(float)
    for span in line.speed_spans:
        lo, hi = max(km_from, span.km_from), min(km_to, span.km_to)
        if hi > lo and span.maxspeed_kmh is not None:
            weights[span.maxspeed_kmh] += hi - lo
    if not weights:
        return None, None
    return max(weights), max(weights, key=lambda k: weights[k])


def cut_segments(
    spec: NetworkSpec, line: ChainedLine, nodes: list[BuiltNode]
) -> list[BuiltSegment]:
    segments: list[BuiltSegment] = []
    for seq, (a, b) in enumerate(zip(nodes, nodes[1:], strict=False), start=1):
        if b.km - a.km < 0.05:
            raise ValueError(f"los nodos {a.spec.id} y {b.spec.id} están en el mismo punto")
        max_speed, typical = speed_summary(line, a.km, b.km)
        segments.append(
            BuiltSegment(
                id=f"{spec.line.id}:{a.spec.id}:{b.spec.id}",
                seq=seq,
                from_node=a,
                to_node=b,
                km_from=a.km,
                km_to=b.km,
                length_km=b.km - a.km,
                max_speed_kmh=max_speed,
                typical_speed_kmh=typical,
                coords=line.polyline.slice(a.km, b.km),
            )
        )
    return segments


def build_network(spec: NetworkSpec, data_dir: Path) -> BuiltNetwork:
    raw_path = data_dir / spec.line.geometry_source.file
    raw = json.loads(raw_path.read_text(encoding="utf-8"))
    line = chain_osm_relation(raw, spec.line.geometry_source.relation_id)
    nodes = place_nodes(spec, line)
    segments = cut_segments(spec, line, nodes)
    return BuiltNetwork(spec=spec, line=line, nodes=nodes, segments=segments)


def round_coords(coords: list[Coord], ndigits: int = 6) -> list[list[float]]:
    return [[round(x, ndigits), round(y, ndigits)] for x, y in coords]
