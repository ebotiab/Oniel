"""Lectura de la red desde PostgreSQL."""

from __future__ import annotations

import datetime as dt
import json
from collections.abc import Sequence
from typing import Any

import asyncpg

from oniel.db.pool import fetch_int
from oniel.domain.annotations import ANNOTATION_KINDS, INTERRUPTION, schedule_note
from oniel.domain.schemas import (
    AnnotationOut,
    ConnectionOut,
    CoverageOut,
    Feature,
    FeatureCollection,
    InterruptionOut,
    LineDetailOut,
    LineSummary,
    NetworkIndexOut,
    NetworkOut,
    NodeIndexOut,
    NodeOut,
    Operator,
    SegmentOut,
    Source,
    SourceRef,
)
from oniel.geo import simplify
from oniel.repo import datasets_repo, services_repo
from oniel.repo.datasets_repo import CURRENT_IDS_SQL
from oniel.routing import Graph, build_graph


def _listed(names: list[str]) -> str:
    return names[0] if len(names) == 1 else ", ".join(names[:-1]) + f" y {names[-1]}"


def coverage_notice(lines: list[LineSummary], operators: Sequence[Operator] = ()) -> str:
    """Aviso de cobertura construido a partir de las líneas cargadas y de sus operadores."""
    loaded = [o.name for o in operators if o.timetable == "cargado"] or ["Renfe"]
    missing = [o.name for o in operators if o.timetable == "no_publicado"]
    names = [line.name[0].lower() + line.name[1:] for line in lines]
    if not names:
        listed = "ninguna línea todavía"
    elif len(names) == 1:
        listed = f"únicamente la {names[0]}"
    else:
        listed = "la " + ", la ".join(names[:-1]) + f" y la {names[-1]}"
    absent = (
        f" No están los trenes de {_listed(missing)}, que no publica"
        f"{'n' if len(missing) > 1 else ''} sus horarios en un formato abierto."
        if missing
        else ""
    )
    return (
        f"Esta versión de Oniel carga {listed}, con los servicios de {_listed(loaded)} que las"
        f" recorren.{absent} Los horarios son los publicados por"
        f" {'cada operador' if len(loaded) > 1 else loaded[0]} y no reflejan interrupciones ni"
        " alteraciones del servicio; las interrupciones que Oniel conoce se señalan aparte, con"
        " su fuente y la fecha en que se comprobaron."
    )


#: Tolerancia de la geometría del índice. A la escala a la que el visor la dibuja (hasta el zoom 8,
#: unos 230 m por píxel) 200 m quedan por debajo de un píxel; más cerca ya se ha pedido la línea.
INDEX_TOLERANCE_M = 200.0


def simplified_geometry(geometry: dict[str, Any], tolerance_m: float) -> dict[str, Any]:
    """La misma geometría con menos vértices; los extremos no se mueven."""
    if geometry.get("type") != "LineString":
        return geometry
    coords = simplify([(c[0], c[1]) for c in geometry["coordinates"]], tolerance_m)
    return {"type": "LineString", "coordinates": [[lon, lat] for lon, lat in coords]}


def _geom(value: Any) -> dict[str, Any]:
    return value if isinstance(value, dict) else json.loads(value)


async def fetch_sources(conn: asyncpg.Connection) -> list[Source]:
    rows = await conn.fetch("SELECT * FROM sources ORDER BY id")
    return [Source(**{k: r[k] for k in Source.model_fields}) for r in rows]


async def fetch_operators(conn: asyncpg.Connection) -> list[Operator]:
    rows = await conn.fetch(
        "SELECT id, name, role, source_id, timetable FROM operators ORDER BY id"
    )
    return [Operator(**dict(r)) for r in rows]


async def fetch_lines(conn: asyncpg.Connection) -> list[LineSummary]:
    rows = await conn.fetch(
        """
        SELECT l.*, o.id AS op_id, o.name AS op_name, o.role AS op_role,
               (SELECT count(*) FROM line_nodes ln WHERE ln.line_id = l.id) AS node_count,
               (SELECT count(*) FROM segments s WHERE s.line_id = l.id) AS segment_count,
               ARRAY(SELECT lo.operator_id FROM line_operators lo
                     WHERE lo.line_id = l.id ORDER BY lo.operator_id) AS operator_ids
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
                operator_ids=list(r["operator_ids"]),
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


async def fetch_annotations(
    conn: asyncpg.Connection,
    *,
    kind: str | None = None,
    day: dt.date | None = None,
    segment_id: str | None = None,
    line_id: str | None = None,
) -> list[AnnotationOut]:
    """Anotaciones registradas, con sus tramos y sus fuentes.

    ``kind`` deja solo las de ese tipo; ``day``, las vigentes ese día; ``segment_id``, las que
    afectan a ese tramo; ``line_id``, las de esa línea o de alguno de sus nodos. Los tramos
    afectados son los que quedan entre los dos nodos de la anotación según su orden en la línea.
    """
    rows = await conn.fetch(
        """
        SELECT a.*, fa.name AS from_name, tb.name AS to_name, n.name AS node_name,
               lf.km AS km_from, lt.km AS km_to,
               ARRAY(SELECT s.id FROM segments s
                     WHERE s.line_id = a.line_id AND s.seq >= lf.seq AND s.seq < lt.seq
                     ORDER BY s.seq) AS segment_ids
        FROM annotations a
        LEFT JOIN lines l ON l.id = a.line_id
        LEFT JOIN line_nodes lf ON lf.line_id = a.line_id AND lf.node_id = a.from_node_id
        LEFT JOIN line_nodes lt ON lt.line_id = a.line_id AND lt.node_id = a.to_node_id
        LEFT JOIN nodes fa ON fa.id = a.from_node_id
        LEFT JOIN nodes tb ON tb.id = a.to_node_id
        LEFT JOIN nodes n ON n.id = a.node_id
        WHERE ($1::date IS NULL OR ((a.start_date IS NULL OR a.start_date <= $1)
                                    AND (a.ended_on IS NULL OR $1 < a.ended_on)))
          AND ($2::text IS NULL OR a.line_id = $2 OR EXISTS (
                SELECT 1 FROM line_nodes x WHERE x.line_id = $2 AND x.node_id = a.node_id))
          AND ($3::text IS NULL OR a.kind = $3)
        ORDER BY l.sort_order NULLS LAST, a.line_id NULLS LAST, lf.seq NULLS LAST,
                 a.start_date NULLS LAST, a.id
        """,
        day,
        line_id,
        kind,
    )
    source_rows = await conn.fetch("SELECT id, name, publisher, url FROM sources")
    sources = {r["id"]: SourceRef(**dict(r)) for r in source_rows}
    out: list[AnnotationOut] = []
    for r in rows:
        segment_ids = list(r["segment_ids"])
        if segment_id is not None and segment_id not in segment_ids:
            continue
        refs = [sources[s] for s in r["source_ids"] if s in sources]
        publisher = refs[0].publisher if refs else "fuente sin registrar"
        declared = ANNOTATION_KINDS.get(r["kind"])
        cuts = declared is not None and declared.cuts_service and r["start_date"] is not None
        out.append(
            AnnotationOut(
                id=r["id"],
                kind=r["kind"],
                status=r["status"],
                line_id=r["line_id"],
                from_node_id=r["from_node_id"],
                to_node_id=r["to_node_id"],
                from_name=r["from_name"],
                to_name=r["to_name"],
                km_from=float(r["km_from"]) if r["km_from"] is not None else None,
                km_to=float(r["km_to"]) if r["km_to"] is not None else None,
                segment_ids=segment_ids,
                node_id=r["node_id"],
                node_name=r["node_name"],
                geometry=_geom(r["geometry"]) if r["geometry"] else None,
                start_date=r["start_date"],
                expected_end_date=r["expected_end_date"],
                expected_end_text=r["expected_end_text"],
                ended_on=r["ended_on"],
                title=r["title"],
                reason=r["reason"],
                note=r["note"],
                sources=refs,
                checked_on=r["checked_on"],
                schedule_note=(
                    schedule_note(r["start_date"], r["ended_on"], publisher) if cuts else None
                ),
            )
        )
    return out


async def fetch_interruptions(
    conn: asyncpg.Connection,
    *,
    day: dt.date | None = None,
    segment_id: str | None = None,
    line_id: str | None = None,
) -> list[InterruptionOut]:
    """Las anotaciones de tipo ``interrupcion``: lo que corta la circulación en sus tramos."""
    return await fetch_annotations(
        conn, kind=INTERRUPTION, day=day, segment_id=segment_id, line_id=line_id
    )


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
        connection_features=_connection_features(connections),
        annotations=await fetch_annotations(conn),
    )


def _connection_features(
    connections: list[tuple[ConnectionOut, dict[str, Any] | None]],
) -> FeatureCollection:
    return FeatureCollection(
        features=[
            Feature(id=c.id, geometry=g, properties=c.model_dump(exclude={"id"}))
            for c, g in connections
            if g is not None
        ]
    )


async def fetch_index(
    conn: asyncpg.Connection, tolerance_m: float = INDEX_TOLERANCE_M
) -> NetworkIndexOut:
    """Índice ligero de la red: todo salvo los textos de los nodos y la geometría completa."""
    nodes = await fetch_nodes(conn)
    segments = await fetch_segments(conn)
    connections = await fetch_connections(conn)
    return NetworkIndexOut(
        lines=await fetch_lines(conn),
        nodes=[NodeIndexOut(**n.model_dump(exclude={"description", "details"})) for n in nodes],
        segment_features=FeatureCollection(
            features=[
                Feature(
                    id=s.id,
                    geometry=simplified_geometry(g, tolerance_m),
                    properties=s.model_dump(exclude={"id"}),
                )
                for s, g in segments
            ]
        ),
        connections=[c for c, _ in connections],
        connection_features=_connection_features(connections),
        annotations=await fetch_annotations(conn),
        simplify_tolerance_m=tolerance_m,
    )


async def fetch_line_detail(
    conn: asyncpg.Connection, line_id: str, day: dt.date | None = None
) -> LineDetailOut | None:
    """El detalle de una línea, con los pasos por tramo de ``day`` (por defecto, el de referencia)."""
    line = next((ln for ln in await fetch_lines(conn) if ln.id == line_id), None)
    if line is None:
        return None
    nodes = await fetch_nodes(conn, line_id)
    segments = await fetch_segments(conn, line_id)
    node_ids = {n.id for n in nodes}
    segment_ids = {s.id for s, _ in segments}
    if day is None:
        _, _, day = await feed_bounds(conn)
    counts = await services_repo.daily_counts(conn, day) if day else {}
    by_operator = await services_repo.daily_counts_by_operator(conn, day) if day else {}
    return LineDetailOut(
        line=line,
        nodes=nodes,
        segments=[s for s, _ in segments],
        segment_features=FeatureCollection(
            features=[
                Feature(id=s.id, geometry=g, properties=s.model_dump(exclude={"id"}))
                for s, g in segments
            ]
        ),
        connections=[c for c, _ in await fetch_connections(conn) if c.node_id in node_ids],
        annotations=await fetch_annotations(conn, line_id=line_id),
        date=day,
        counts={k: v for k, v in counts.items() if k in segment_ids},
        counts_by_operator={k: v for k, v in by_operator.items() if k in segment_ids},
        network_max_count=max(counts.values(), default=0),
    )


async def fetch_graph(conn: asyncpg.Connection) -> Graph:
    """Grafo de rutas de todas las líneas cargadas (``oniel.routing``)."""
    return build_graph(
        await fetch_lines(conn),
        await fetch_nodes(conn),
        [s for s, _ in await fetch_segments(conn)],
    )


async def feed_bounds(
    conn: asyncpg.Connection,
) -> tuple[dt.date | None, dt.date | None, dt.date | None]:
    """Primer y último día con servicio y día de referencia de los conjuntos de datos vigentes."""
    return await datasets_repo.feed_bounds(conn)


async def fetch_coverage(conn: asyncpg.Connection) -> CoverageOut:
    lines = await fetch_lines(conn)
    station_count = await fetch_int(conn, "SELECT count(*) FROM nodes WHERE kind = 'estacion'")
    service_count = await fetch_int(
        conn,
        f"SELECT count(DISTINCT train_number) FROM services WHERE dataset_id IN {CURRENT_IDS_SQL}",
    )
    start, end, ref = await feed_bounds(conn)
    operators = await fetch_operators(conn)
    return CoverageOut(
        lines=lines,
        total_length_km=round(sum(line.length_km for line in lines), 1),
        station_count=station_count,
        service_count=service_count,
        operators=operators,
        feed_start=start,
        feed_end=end,
        reference_date=ref,
        datasets=await datasets_repo.fetch_active_datasets(conn, ref) if ref else [],
        sources=await fetch_sources(conn),
        notice=coverage_notice(lines, operators),
    )
