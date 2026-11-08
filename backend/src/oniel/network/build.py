"""Construye el modelo lineal de una línea a partir de la geometría cruda y la especificación curada.

Pasos: obtener una sola polilínea de la geometría OSM (encadenando las vías de una relación en
el orden de sus miembros, o trazando el camino más corto entre dos puntos cuando la relación
trae las dos vías sin orden), situar cada nodo sobre ella (por proyección o por kilómetro),
cortar la línea en tramos entre nodos consecutivos y resumir la velocidad máxima y el número de
vías de cada tramo.
"""

from __future__ import annotations

import heapq
import json
from collections import defaultdict
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any

from oniel.geo import Coord, Polyline, haversine_km
from oniel.network.spec import NetworkSpec, NodeSpec

MAX_SNAP_OFFSET_M = 400.0
#: Hueco máximo admitido al empalmar dos partes de la geometría (las vías de dos relaciones
#: distintas no comparten nodo exactamente en la estación de empalme).
MAX_JOIN_M = 500.0
#: Cuántos nodos cercanos se prueban como arranque y final del trazado.
TRACE_CANDIDATES = 8


@dataclass(frozen=True)
class SpeedSpan:
    km_from: float
    km_to: float
    maxspeed_kmh: int | None


@dataclass(frozen=True)
class PartSpan:
    km_from: float
    km_to: float
    source_id: str


@dataclass
class ChainedLine:
    polyline: Polyline
    speed_spans: list[SpeedSpan]
    gaps_km: list[float] = field(default_factory=list)
    part_spans: list[PartSpan] = field(default_factory=list)
    #: Empalmes rectos añadidos entre partes, en kilómetros.
    joins_km: list[float] = field(default_factory=list)


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
    tracks: int | None
    source_id: str
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


def _relation_ways(
    raw: dict[str, Any], relation_id: int
) -> tuple[list[dict[str, Any]], dict[int, Coord]]:
    elements = raw["elements"]
    relations = [e for e in elements if e["type"] == "relation" and e["id"] == relation_id]
    if not relations:
        raise ValueError(f"la relación {relation_id} no está en el fichero")
    ways = {e["id"]: e for e in elements if e["type"] == "way"}
    nodes: dict[int, Coord] = {
        e["id"]: (e["lon"], e["lat"]) for e in elements if e["type"] == "node"
    }
    members = [
        ways[m["ref"]] for m in relations[0]["members"] if m["type"] == "way" and m["ref"] in ways
    ]
    return members, nodes


def chain_osm_relation(raw: dict[str, Any], relation_id: int) -> ChainedLine:
    """Encadena las vías de una relación OSM (descarga Overpass con nodos) en una polilínea."""
    members, nodes = _relation_ways(raw, relation_id)

    coords: list[Coord] = []
    spans: list[tuple[int, int, int | None]] = []  # (índice inicial, índice final, maxspeed)
    gaps: list[float] = []
    for way in members:
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


def trace_osm_relation(
    raw: dict[str, Any], relation_id: int, start: Coord, end: Coord
) -> ChainedLine:
    """Camino más corto por las vías de una relación OSM entre dos puntos.

    Sirve para relaciones que incluyen las dos vías de una línea doble, ramales o miembros sin
    orden: el grafo son los nodos de las vías ``railway=rail`` y las aristas sus tramos; se
    prueban los nodos más cercanos a cada extremo hasta encontrar un camino.
    """
    members, nodes = _relation_ways(raw, relation_id)
    adjacency: dict[int, list[tuple[int, float, int]]] = defaultdict(list)
    way_speed: dict[int, int | None] = {}
    for way in members:
        if way.get("tags", {}).get("railway") != "rail":
            continue
        way_speed[way["id"]] = _parse_maxspeed(way["tags"].get("maxspeed"))
        ids = [n for n in way["nodes"] if n in nodes]
        for a, b in zip(ids, ids[1:], strict=False):
            length = haversine_km(nodes[a], nodes[b])
            adjacency[a].append((b, length, way["id"]))
            adjacency[b].append((a, length, way["id"]))
    if not adjacency:
        raise ValueError(f"la relación {relation_id} no tiene vías ferroviarias")

    def nearest(p: Coord) -> list[int]:
        return sorted(adjacency, key=lambda n: haversine_km(nodes[n], p))[:TRACE_CANDIDATES]

    # Para cada extremo se toma el nodo más cercano que esté conectado con el otro: así, si las
    # dos vías de una línea doble solo se tocan en los extremos, el trazado no salta de una a otra.
    best: tuple[int, int, dict[int, tuple[int, int]]] | None = None
    for s in nearest(start):
        dist, prev = _dijkstra(adjacency, s)
        reachable = [e for e in nearest(end) if e in dist and e != s]
        if reachable:
            best = (s, reachable[0], prev)
            break
    if best is None:
        raise ValueError(
            f"no hay camino en la relación {relation_id} entre {start} y {end}; "
            "¿están los dos puntos sobre la misma vía?"
        )
    s, e, prev = best
    path = [e]
    ways_used: list[int] = []
    while path[-1] != s:
        u, w = prev[path[-1]]
        path.append(u)
        ways_used.append(w)
    path.reverse()
    ways_used.reverse()
    coords = [nodes[n] for n in path]
    polyline = Polyline(coords)
    speed_spans: list[SpeedSpan] = []
    for i, w in enumerate(ways_used):
        ms = way_speed.get(w)
        if speed_spans and speed_spans[-1].maxspeed_kmh == ms:
            prev_span = speed_spans[-1]
            speed_spans[-1] = SpeedSpan(prev_span.km_from, polyline.cum_km[i + 1], ms)
        else:
            speed_spans.append(SpeedSpan(polyline.cum_km[i], polyline.cum_km[i + 1], ms))
    return ChainedLine(polyline=polyline, speed_spans=speed_spans)


def _dijkstra(
    adjacency: dict[int, list[tuple[int, float, int]]], source: int
) -> tuple[dict[int, float], dict[int, tuple[int, int]]]:
    dist = {source: 0.0}
    prev: dict[int, tuple[int, int]] = {}
    queue = [(0.0, source)]
    while queue:
        d, u = heapq.heappop(queue)
        if d > dist.get(u, float("inf")):
            continue
        for v, length, way_id in adjacency[u]:
            nd = d + length
            if nd < dist.get(v, float("inf")):
                dist[v] = nd
                prev[v] = (u, way_id)
                heapq.heappush(queue, (nd, v))
    return dist, prev


def concat_parts(parts: list[tuple[ChainedLine, str]]) -> ChainedLine:
    """Une varias partes trazadas en una sola línea, empalmando con un tramo recto si hace falta."""
    coords: list[Coord] = []
    speed_spans: list[SpeedSpan] = []
    part_spans: list[PartSpan] = []
    joins: list[float] = []
    offset = 0.0
    for part, source_id in parts:
        pts = list(part.polyline.coords)
        if coords:
            join = haversine_km(coords[-1], pts[0])
            if join * 1000 > MAX_JOIN_M:
                raise ValueError(
                    f"las partes de la geometría quedan a {join * 1000:.0f} m en el empalme"
                    f" (máximo {MAX_JOIN_M:.0f} m)"
                )
            if join > 0.001:
                joins.append(join)
                offset += join
            else:
                pts = pts[1:]
        coords.extend(pts)
        speed_spans.extend(
            SpeedSpan(s.km_from + offset, s.km_to + offset, s.maxspeed_kmh)
            for s in part.speed_spans
        )
        part_spans.append(PartSpan(offset, offset + part.polyline.length_km, source_id))
        offset += part.polyline.length_km
    return ChainedLine(
        polyline=Polyline(coords), speed_spans=speed_spans, part_spans=part_spans, joins_km=joins
    )


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


def tracks_between(spec: NetworkSpec, nodes: list[BuiltNode], km_from: float, km_to: float) -> int:
    """Número de vías de un tramo: la sección declarada que lo contiene, o el valor de la línea."""
    km_of = {n.spec.id: n.km for n in nodes}
    mid = (km_from + km_to) / 2
    for section in spec.track_sections:
        lo, hi = sorted((km_of[section.from_node], km_of[section.to_node]))
        if lo <= mid <= hi:
            return section.tracks
    return spec.line.tracks


def source_at(line: ChainedLine, spec: NetworkSpec, km: float) -> str:
    for span in line.part_spans:
        if span.km_from <= km <= span.km_to:
            return span.source_id
    return spec.line.geometry_source.source_id


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
                tracks=tracks_between(spec, nodes, a.km, b.km),
                source_id=source_at(line, spec, (a.km + b.km) / 2),
                coords=line.polyline.slice(a.km, b.km),
            )
        )
    return segments


def build_line_geometry(spec: NetworkSpec, data_dir: Path) -> ChainedLine:
    source = spec.line.geometry_source
    if source.parts:
        parts: list[tuple[ChainedLine, str]] = []
        for part in source.parts:
            raw = json.loads((data_dir / part.file).read_text(encoding="utf-8"))
            traced = trace_osm_relation(raw, part.relation_id, part.from_point, part.to_point)
            parts.append((traced, part.source_id))
        return concat_parts(parts)
    assert source.file is not None and source.relation_id is not None
    raw = json.loads((data_dir / source.file).read_text(encoding="utf-8"))
    line = chain_osm_relation(raw, source.relation_id)
    line.part_spans = [PartSpan(0.0, line.polyline.length_km, source.source_id)]
    return line


def build_network(spec: NetworkSpec, data_dir: Path) -> BuiltNetwork:
    line = build_line_geometry(spec, data_dir)
    nodes = place_nodes(spec, line)
    segments = cut_segments(spec, line, nodes)
    return BuiltNetwork(spec=spec, line=line, nodes=nodes, segments=segments)


def round_coords(coords: list[Coord], ndigits: int = 6) -> list[list[float]]:
    return [[round(x, ndigits), round(y, ndigits)] for x, y in coords]
