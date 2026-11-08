"""Lectura de la red desde PostgreSQL."""

from __future__ import annotations

import datetime as dt
import json
from typing import Any

import asyncpg

from oniel.db.pool import fetch_int
from oniel.domain.schemas import (
    ClosureAlternative,
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


def coverage_notice(lines: list[LineSummary]) -> str:
    """Aviso de cobertura construido a partir de las líneas cargadas."""
    names = [line.name[0].lower() + line.name[1:] for line in lines]
    if not names:
        listed = "ninguna línea todavía"
    elif len(names) == 1:
        listed = f"únicamente la {names[0]}"
    else:
        listed = "la " + ", la ".join(names[:-1]) + f" y la {names[-1]}"
    return (
        f"Esta versión de Oniel carga {listed}, con los servicios de Renfe que las recorren."
        " Los horarios son los publicados por Renfe y no reflejan interrupciones ni"
        " alteraciones del servicio."
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
        ORDER BY l.sort_order, l.id
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
                sort_order=r["sort_order"],
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
        FROM nodes n JOIN line_nodes ln ON ln.node_id = n.id JOIN lines l ON l.id = ln.line_id
        WHERE ($1::text IS NULL OR ln.line_id = $1)
        ORDER BY l.sort_order, ln.line_id, ln.seq
        """,
        line_id,
    )
    return [
        NodeOut(
            id=r["id"],
            name=r["name"],
            kind=r["kind"],
            rank=r["rank"],
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
        tracks=r["tracks"],
        status=r["status"],
        source_id=r["source_id"],
    )


SEGMENT_SQL = """
    SELECT s.*, a.name AS from_name, b.name AS to_name, l.sort_order
    FROM segments s JOIN nodes a ON a.id = s.from_node_id JOIN nodes b ON b.id = s.to_node_id
    JOIN lines l ON l.id = s.line_id
"""


async def fetch_segments(
    conn: asyncpg.Connection, line_id: str | None = None
) -> list[tuple[SegmentOut, dict[str, Any]]]:
    rows = await conn.fetch(
        SEGMENT_SQL
        + " WHERE ($1::text IS NULL OR s.line_id = $1) ORDER BY l.sort_order, s.line_id, s.seq",
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
    line_rows = await conn.fetch("SELECT id, name, geometry FROM lines ORDER BY sort_order, id")
    nodes = await fetch_nodes(conn)
    segments = await fetch_segments(conn)
    connections = await fetch_connections(conn)
    # Un nodo compartido por dos líneas aparece una vez por línea en `nodes` (con su km en cada
    # una) pero solo una vez en el mapa.
    node_features: list[Feature] = []
    seen: set[str] = set()
    for n in nodes:
        if n.id in seen:
            continue
        seen.add(n.id)
        node_features.append(
            Feature(
                id=n.id,
                geometry={"type": "Point", "coordinates": [n.lon, n.lat]},
                properties={
                    **n.model_dump(exclude={"id", "details", "description"}),
                    "line_ids": [m.line_id for m in nodes if m.id == n.id],
                },
            )
        )
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
        node_features=FeatureCollection(features=node_features),
        connection_features=FeatureCollection(
            features=[
                Feature(id=c.id, geometry=g, properties=c.model_dump(exclude={"id"}))
                for c, g in connections
                if g is not None
            ]
        ),
    )


async def fetch_alternatives(
    conn: asyncpg.Connection, segment: SegmentOut
) -> list[ClosureAlternative]:
    """Líneas cargadas que unen un nodo anterior y otro posterior al tramo cerrado.

    Se buscan, en la línea del tramo, los nodos compartidos con otra línea situados antes y
    después del tramo; si una misma línea tiene uno a cada lado, existe un recorrido alternativo
    entre ambos. Se eligen los nodos compartidos más cercanos al tramo.
    """
    rows = await conn.fetch(
        """
        SELECT ln.node_id, ln.km AS km_closed, other.line_id, other.km AS km_other, l.name AS line_name
        FROM line_nodes ln
        JOIN line_nodes other ON other.node_id = ln.node_id AND other.line_id <> ln.line_id
        JOIN lines l ON l.id = other.line_id
        WHERE ln.line_id = $1
        ORDER BY l.sort_order, other.line_id, ln.km
        """,
        segment.line_id,
    )
    by_line: dict[str, list[asyncpg.Record]] = {}
    for r in rows:
        by_line.setdefault(r["line_id"], []).append(r)
    out: list[ClosureAlternative] = []
    for line_id, shared in by_line.items():
        before = [r for r in shared if float(r["km_closed"]) <= segment.km_from + 0.05]
        after = [r for r in shared if float(r["km_closed"]) >= segment.km_to - 0.05]
        if not before or not after:
            continue
        a, b = before[-1], after[0]
        lo, hi = sorted((float(a["km_other"]), float(b["km_other"])))
        inner = await conn.fetch(
            """
            SELECT n.name, n.kind, n.rank, ln.km FROM line_nodes ln JOIN nodes n ON n.id = ln.node_id
            WHERE ln.line_id = $1 AND ln.km > $2 + 0.05 AND ln.km < $3 - 0.05 ORDER BY ln.km
            """,
            line_id,
            lo,
            hi,
        )
        single = await conn.fetchval(
            """
            SELECT coalesce(sum(length_km), 0) FROM segments
            WHERE line_id = $1 AND tracks = 1 AND km_from >= $2 - 0.05 AND km_to <= $3 + 0.05
            """,
            line_id,
            lo,
            hi,
        )
        names = await conn.fetch(
            "SELECT id, name FROM nodes WHERE id = ANY($1::text[])", [a["node_id"], b["node_id"]]
        )
        name_of = {r["id"]: r["name"] for r in names}
        via = [r["name"] for r in inner if r["kind"] == "estacion" and r["rank"] == "principal"]
        single_km = float(single or 0)
        note = (
            f"Recorrido alternativo cargado en Oniel entre {name_of[a['node_id']]} y"
            f" {name_of[b['node_id']]}: {hi - lo:.0f} km por la {a['line_name'][0].lower()}{a['line_name'][1:]}"
            f" frente a {float(b['km_closed']) - float(a['km_closed']):.0f} km por la línea cerrada."
        )
        if single_km > 0:
            note += f" Incluye {single_km:.0f} km de vía única."
        note += (
            " Oniel no reasigna los trenes afectados a esta alternativa; solo señala que existe."
        )
        out.append(
            ClosureAlternative(
                line_id=line_id,
                line_name=a["line_name"],
                from_node_id=a["node_id"],
                from_name=name_of[a["node_id"]],
                to_node_id=b["node_id"],
                to_name=name_of[b["node_id"]],
                length_km=round(hi - lo, 1),
                closed_line_length_km=round(float(b["km_closed"]) - float(a["km_closed"]), 1),
                via=via,
                single_track_km=round(single_km, 1),
                note=note,
            )
        )
    return out


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
    station_count = await fetch_int(conn, "SELECT count(*) FROM nodes WHERE kind = 'estacion'")
    service_count = await fetch_int(conn, "SELECT count(DISTINCT train_number) FROM services")
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
        notice=coverage_notice(lines),
    )
