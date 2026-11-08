"""Importación idempotente de la red: fuentes, operadores, línea, nodos, tramos y conexiones."""

from __future__ import annotations

import datetime as dt
import hashlib
import json
from pathlib import Path
from typing import Any

import asyncpg
import logfire

from oniel.network.build import BuiltNetwork, build_network, round_coords
from oniel.network.spec import SourceSpec, load_network_spec, load_sources


def _sha256(path: Path) -> str | None:
    if not path.exists():
        return None
    h = hashlib.sha256()
    with path.open("rb") as fh:
        for chunk in iter(lambda: fh.read(1 << 20), b""):
            h.update(chunk)
    return h.hexdigest()


async def upsert_sources(
    conn: asyncpg.Connection, sources: list[SourceSpec], data_dir: Path
) -> int:
    for s in sources:
        await conn.execute(
            """
            INSERT INTO sources (id, name, publisher, url, license, license_url, retrieved_on, coverage, notes, checksum_sha256)
            VALUES ($1,$2,$3,$4,$5,$6,$7,$8,$9,$10)
            ON CONFLICT (id) DO UPDATE SET name=EXCLUDED.name, publisher=EXCLUDED.publisher, url=EXCLUDED.url,
              license=EXCLUDED.license, license_url=EXCLUDED.license_url, retrieved_on=EXCLUDED.retrieved_on,
              coverage=EXCLUDED.coverage, notes=EXCLUDED.notes, checksum_sha256=EXCLUDED.checksum_sha256, updated_at=now()
            """,
            s.id,
            s.name,
            s.publisher,
            s.url,
            s.license,
            s.license_url,
            dt.date.fromisoformat(s.retrieved_on) if s.retrieved_on else None,
            s.coverage,
            s.notes,
            _sha256(data_dir / s.file) if s.file else None,
        )
    return len(sources)


async def import_network(
    conn: asyncpg.Connection, spec_path: Path, sources_path: Path, data_dir: Path
) -> dict[str, Any]:
    spec = load_network_spec(spec_path)
    sources = load_sources(sources_path)
    with logfire.span("import network {line}", line=spec.line.id):
        net = build_network(spec, data_dir)
        async with conn.transaction():
            await upsert_sources(conn, sources, data_dir)
            for op in spec.operators:
                await conn.execute(
                    """
                    INSERT INTO operators (id, name, role, source_id) VALUES ($1,$2,$3,$4)
                    ON CONFLICT (id) DO UPDATE SET name=EXCLUDED.name, role=EXCLUDED.role, source_id=EXCLUDED.source_id
                    """,
                    op.id,
                    op.name,
                    op.role,
                    op.source_id,
                )
            await _upsert_line(conn, net)
            await _replace_nodes_and_segments(conn, net)
            await _replace_connections(conn, net)
            await _upsert_stop_mappings(conn, net)
        stats: dict[str, Any] = {
            "line_id": spec.line.id,
            "length_km": round(net.line.polyline.length_km, 3),
            "reference_length_km": spec.line.reference_length_km,
            "nodes": len(net.nodes),
            "segments": len(net.segments),
            "connections": len(spec.connections),
            "gaps": len(net.line.gaps_km),
            "max_snap_offset_m": round(max(n.offset_m for n in net.nodes), 1),
        }
        logfire.info("network imported", **stats)
        return stats


async def _upsert_line(conn: asyncpg.Connection, net: BuiltNetwork) -> None:
    line = net.spec.line
    geometry = {"type": "LineString", "coordinates": round_coords(net.line.polyline.coords)}
    await conn.execute(
        """
        INSERT INTO lines (id, name, short_name, mode, infrastructure_manager_id, gauge_mm, electrification, max_speed_kmh,
                           opened_on, length_km, reference_length_km, status, description, geometry, source_id)
        VALUES ($1,$2,$3,$4,$5,$6,$7,$8,$9,$10,$11,$12,$13,$14,$15)
        ON CONFLICT (id) DO UPDATE SET name=EXCLUDED.name, short_name=EXCLUDED.short_name, mode=EXCLUDED.mode,
          infrastructure_manager_id=EXCLUDED.infrastructure_manager_id, gauge_mm=EXCLUDED.gauge_mm,
          electrification=EXCLUDED.electrification, max_speed_kmh=EXCLUDED.max_speed_kmh, opened_on=EXCLUDED.opened_on,
          length_km=EXCLUDED.length_km, reference_length_km=EXCLUDED.reference_length_km, status=EXCLUDED.status,
          description=EXCLUDED.description, geometry=EXCLUDED.geometry, source_id=EXCLUDED.source_id, updated_at=now()
        """,
        line.id,
        line.name,
        line.short_name,
        line.mode,
        line.infrastructure_manager,
        line.gauge_mm,
        line.electrification,
        line.max_speed_kmh,
        dt.date.fromisoformat(line.opened_on) if line.opened_on else None,
        round(net.line.polyline.length_km, 3),
        line.reference_length_km,
        line.status,
        line.description,
        geometry,
        line.geometry_source.source_id,
    )


async def _replace_nodes_and_segments(conn: asyncpg.Connection, net: BuiltNetwork) -> None:
    line_id = net.spec.line.id
    source_id = net.spec.line.verification_source_id or net.spec.line.geometry_source.source_id
    await conn.execute("DELETE FROM segments WHERE line_id = $1", line_id)
    await conn.execute("DELETE FROM line_nodes WHERE line_id = $1", line_id)
    for seq, n in enumerate(net.nodes, start=1):
        await conn.execute(
            """
            INSERT INTO nodes (id, name, kind, lon, lat, adif_code, description, details, source_id)
            VALUES ($1,$2,$3,$4,$5,$6,$7,$8,$9)
            ON CONFLICT (id) DO UPDATE SET name=EXCLUDED.name, kind=EXCLUDED.kind, lon=EXCLUDED.lon, lat=EXCLUDED.lat,
              adif_code=EXCLUDED.adif_code, description=EXCLUDED.description, details=EXCLUDED.details, source_id=EXCLUDED.source_id
            """,
            n.spec.id,
            n.spec.name,
            n.spec.kind,
            round(n.lon, 6),
            round(n.lat, 6),
            n.spec.adif_code,
            n.spec.description,
            n.spec.details,
            source_id,
        )
        await conn.execute(
            "INSERT INTO line_nodes (line_id, node_id, seq, km, reference_pk_km) VALUES ($1,$2,$3,$4,$5)",
            line_id,
            n.spec.id,
            seq,
            round(n.km, 3),
            n.spec.reference_pk_km,
        )
    for s in net.segments:
        await conn.execute(
            """
            INSERT INTO segments (id, line_id, seq, from_node_id, to_node_id, km_from, km_to, length_km, max_speed_kmh,
                                  typical_speed_kmh, tracks, status, geometry, source_id)
            VALUES ($1,$2,$3,$4,$5,$6,$7,$8,$9,$10,$11,$12,$13,$14)
            """,
            s.id,
            line_id,
            s.seq,
            s.from_node.spec.id,
            s.to_node.spec.id,
            round(s.km_from, 3),
            round(s.km_to, 3),
            round(s.length_km, 3),
            s.max_speed_kmh,
            s.typical_speed_kmh,
            2,
            net.spec.line.status,
            {"type": "LineString", "coordinates": round_coords(s.coords)},
            net.spec.line.geometry_source.source_id,
        )


async def _replace_connections(conn: asyncpg.Connection, net: BuiltNetwork) -> None:
    node_ids = [n.spec.id for n in net.nodes]
    await conn.execute("DELETE FROM connections WHERE node_id = ANY($1::text[])", node_ids)
    for c in net.spec.connections:
        node = net.node(c.node_id)
        coords = [(node.lon, node.lat), *[(x, y) for x, y in c.sketch]]
        # si el croquis empieza en el propio nodo, no lo repetimos
        if (
            len(coords) > 1
            and abs(coords[0][0] - coords[1][0]) < 1e-6
            and abs(coords[0][1] - coords[1][1]) < 1e-6
        ):
            coords = coords[1:]
        geometry = (
            {"type": "LineString", "coordinates": round_coords(coords)} if len(coords) > 1 else None
        )
        await conn.execute(
            "INSERT INTO connections (id, node_id, name, towards, status, line_id, geometry) VALUES ($1,$2,$3,$4,$5,$6,$7)",
            c.id,
            c.node_id,
            c.name,
            c.towards,
            c.status,
            None,
            geometry,
        )


async def _upsert_stop_mappings(conn: asyncpg.Connection, net: BuiltNetwork) -> None:
    for stop_id, m in net.spec.stop_mappings.items():
        await conn.execute(
            """
            INSERT INTO stop_mappings (stop_id, node_id, exit_node_ids) VALUES ($1,$2,$3)
            ON CONFLICT (stop_id) DO UPDATE SET node_id=EXCLUDED.node_id, exit_node_ids=EXCLUDED.exit_node_ids
            """,
            stop_id,
            m.node,
            m.exits,
        )


def network_as_json(net: BuiltNetwork) -> dict[str, Any]:
    """Resumen serializable del modelo construido (para validar sin base de datos)."""
    return {
        "line": net.spec.line.id,
        "length_km": round(net.line.polyline.length_km, 3),
        "nodes": [
            {
                "id": n.spec.id,
                "km": round(n.km, 3),
                "offset_m": round(n.offset_m),
                "reference_pk_km": n.spec.reference_pk_km,
            }
            for n in net.nodes
        ],
        "segments": [
            {
                "id": s.id,
                "km_from": round(s.km_from, 3),
                "km_to": round(s.km_to, 3),
                "length_km": round(s.length_km, 3),
                "max_speed_kmh": s.max_speed_kmh,
                "typical_speed_kmh": s.typical_speed_kmh,
            }
            for s in net.segments
        ],
    }


def dumps(obj: Any) -> str:
    return json.dumps(obj, ensure_ascii=False, indent=2)
