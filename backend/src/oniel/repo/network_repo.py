"""Lectura de la red desde PostgreSQL."""

from __future__ import annotations

import datetime as dt
import json
from typing import Any

import asyncpg

from oniel.domain.schemas import (
    ConnectionOut,
    CoverageOut,
    Feature,
    FeatureCollection,
    LineSummary,
    NetworkOut,
    NodeOut,
    Operator,
    SegmentOut,
    Source,
)

NOTICE = (
    "Esta versión de Oniel carga únicamente la línea de alta velocidad Madrid–Sevilla y los"
    " servicios de Renfe que la recorren. Los horarios son los publicados por Renfe y no"
    " reflejan interrupciones ni alteraciones del servicio."
)


def _geom(value: Any) -> dict[str, Any]:
    return value if isinstance(value, dict) else json.loads(value)


async def fetch_sources(conn: asyncpg.Connection) -> list[Source]:
    rows = await conn.fetch("SELECT * FROM sources ORDER BY id")
    return [Source(**{k: r[k] for k in Source.model_fields}) for r in rows]


async def fetch_operators(conn: asyncpg.Connection) -> list[Operator]:
    rows = await conn.fetch("SELECT id, name, role FROM operators ORDER BY id")
    return [Operator(**dict(r)) for r in rows]


async def fetch_lines(conn: asyncpg.Connection) -> list[LineSummary]:
    rows = await conn.fetch(
        """
        SELECT l.*, o.id AS op_id, o.name AS op_name, o.role AS op_role,
               (SELECT count(*) FROM line_nodes ln WHERE ln.line_id = l.id) AS node_count,
               (SELECT count(*) FROM segments s WHERE s.line_id = l.id) AS segment_count
        FROM lines l LEFT JOIN operators o ON o.id = l.infrastructure_manager_id
        ORDER BY l.id
        """
    )
    out = []
    for r in rows:
        op = Operator(id=r["op_id"], name=r["op_name"], role=r["op_role"]) if r["op_id"] else None
        out.append(
            LineSummary(
                id=r["id"],
                name=r["name"],
                short_name=r["short_name"],
                mode=r["mode"],
                infrastructure_manager=op,
                gauge_mm=r["gauge_mm"],
                electrification=r["electrification"],
                max_speed_kmh=r["max_speed_kmh"],
                opened_on=r["opened_on"],
                length_km=float(r["length_km"]),
                reference_length_km=float(r["reference_length_km"])
                if r["reference_length_km"]
                else None,
                status=r["status"],
                description=r["description"],
                source_id=r["source_id"],
                node_count=r["node_count"],
                segment_count=r["segment_count"],
            )
        )
    return out


async def fetch_nodes(conn: asyncpg.Connection, line_id: str | None = None) -> list[NodeOut]:
    rows = await conn.fetch(
        """
        SELECT n.*, ln.line_id, ln.km, ln.reference_pk_km, ln.seq
        FROM nodes n JOIN line_nodes ln ON ln.node_id = n.id
        WHERE ($1::text IS NULL OR ln.line_id = $1)
        ORDER BY ln.line_id, ln.seq
        """,
        line_id,
    )
    return [
        NodeOut(
            id=r["id"],
            name=r["name"],
            kind=r["kind"],
            lon=r["lon"],
            lat=r["lat"],
            adif_code=r["adif_code"],
            description=r["description"],
            details=_geom(r["details"]) if r["details"] else {},
            line_id=r["line_id"],
            km=float(r["km"]),
            reference_pk_km=float(r["reference_pk_km"])
            if r["reference_pk_km"] is not None
            else None,
            seq=r["seq"],
        )
        for r in rows
    ]


def _segment(r: asyncpg.Record) -> SegmentOut:
    return SegmentOut(
        id=r["id"],
        line_id=r["line_id"],
        seq=r["seq"],
        from_node_id=r["from_node_id"],
        to_node_id=r["to_node_id"],
        from_name=r["from_name"],
        to_name=r["to_name"],
        km_from=float(r["km_from"]),
        km_to=float(r["km_to"]),
        length_km=float(r["length_km"]),
        max_speed_kmh=r["max_speed_kmh"],
        typical_speed_kmh=r["typical_speed_kmh"],
        status=r["status"],
        source_id=r["source_id"],
    )


SEGMENT_SQL = """
    SELECT s.*, a.name AS from_name, b.name AS to_name
    FROM segments s JOIN nodes a ON a.id = s.from_node_id JOIN nodes b ON b.id = s.to_node_id
"""


async def fetch_segments(
    conn: asyncpg.Connection, line_id: str | None = None
) -> list[tuple[SegmentOut, dict[str, Any]]]:
    rows = await conn.fetch(
        SEGMENT_SQL + " WHERE ($1::text IS NULL OR s.line_id = $1) ORDER BY s.line_id, s.seq",
        line_id,
    )
    return [(_segment(r), _geom(r["geometry"])) for r in rows]


async def fetch_segment(conn: asyncpg.Connection, segment_id: str) -> SegmentOut | None:
    r = await conn.fetchrow(SEGMENT_SQL + " WHERE s.id = $1", segment_id)
    return _segment(r) if r else None


async def fetch_node(conn: asyncpg.Connection, node_id: str) -> NodeOut | None:
    nodes = [n for n in await fetch_nodes(conn) if n.id == node_id]
    return nodes[0] if nodes else None


async def fetch_connections(
    conn: asyncpg.Connection,
) -> list[tuple[ConnectionOut, dict[str, Any] | None]]:
    rows = await conn.fetch("SELECT * FROM connections ORDER BY id")
    return [
        (
            ConnectionOut(
                id=r["id"],
                node_id=r["node_id"],
                name=r["name"],
                towards=r["towards"],
                status=r["status"],
                line_id=r["line_id"],
            ),
            _geom(r["geometry"]) if r["geometry"] else None,
        )
        for r in rows
    ]


async def fetch_network(conn: asyncpg.Connection) -> NetworkOut:
    lines = await fetch_lines(conn)
    line_rows = await conn.fetch("SELECT id, name, geometry FROM lines ORDER BY id")
    nodes = await fetch_nodes(conn)
    segments = await fetch_segments(conn)
    connections = await fetch_connections(conn)
    return NetworkOut(
        lines=lines,
        nodes=nodes,
        segments=[s for s, _ in segments],
        connections=[c for c, _ in connections],
        line_features=FeatureCollection(
            features=[
                Feature(id=r["id"], geometry=_geom(r["geometry"]), properties={"name": r["name"]})
                for r in line_rows
            ]
        ),
        segment_features=FeatureCollection(
            features=[
                Feature(id=s.id, geometry=g, properties=s.model_dump(exclude={"id"}))
                for s, g in segments
            ]
        ),
        node_features=FeatureCollection(
            features=[
                Feature(
                    id=n.id,
                    geometry={"type": "Point", "coordinates": [n.lon, n.lat]},
                    properties=n.model_dump(exclude={"id", "details", "description"}),
                )
                for n in nodes
            ]
        ),
        connection_features=FeatureCollection(
            features=[
                Feature(id=c.id, geometry=g, properties=c.model_dump(exclude={"id"}))
                for c, g in connections
                if g is not None
            ]
        ),
    )


async def feed_bounds(
    conn: asyncpg.Connection,
) -> tuple[dt.date | None, dt.date | None, dt.date | None]:
    r = await conn.fetchrow(
        "SELECT min(service_date) AS a, max(service_date) AS b FROM service_dates"
    )
    if r is None or r["a"] is None:
        return None, None, None
    ref = await conn.fetchrow(
        """
        SELECT service_date FROM service_dates
        WHERE service_date BETWEEN $1 AND $1 + 30 AND extract(isodow FROM service_date) <= 5
        GROUP BY service_date ORDER BY count(*) DESC, service_date LIMIT 1
        """,
        r["a"],
    )
    return r["a"], r["b"], ref["service_date"] if ref else r["a"]


async def fetch_coverage(conn: asyncpg.Connection) -> CoverageOut:
    lines = await fetch_lines(conn)
    station_count = await conn.fetchval("SELECT count(*) FROM nodes WHERE kind = 'estacion'")
    service_count = await conn.fetchval("SELECT count(DISTINCT train_number) FROM services")
    start, end, ref = await feed_bounds(conn)
    return CoverageOut(
        lines=lines,
        total_length_km=round(sum(line.length_km for line in lines), 1),
        station_count=station_count,
        service_count=service_count,
        operators=await fetch_operators(conn),
        feed_start=start,
        feed_end=end,
        reference_date=ref,
        sources=await fetch_sources(conn),
        notice=NOTICE,
    )
