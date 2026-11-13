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
from oniel.network.spec import SourceSpec, ZoneSpec, load_network_spec, load_sources, load_zones


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


#: El registro de zonas, dentro del directorio de datos.
ZONES_FILE = Path("curated") / "zonas.json"


async def upsert_zones(conn: asyncpg.Connection, zones: list[ZoneSpec]) -> int:
    for z in zones:
        await conn.execute(
            """
            INSERT INTO zones (id, name, sort_order, cities) VALUES ($1,$2,$3,$4)
            ON CONFLICT (id) DO UPDATE SET name=EXCLUDED.name, sort_order=EXCLUDED.sort_order,
              cities=EXCLUDED.cities
            """,
            z.id,
            z.name,
            z.sort_order,
            z.cities,
        )
    return len(zones)


async def import_network(
    conn: asyncpg.Connection, spec_path: Path, sources_path: Path, data_dir: Path
) -> dict[str, Any]:
    spec = load_network_spec(spec_path)
    sources = load_sources(sources_path)
    zones = load_zones(data_dir / ZONES_FILE)
    if spec.line.zone not in {z.id for z in zones}:
        raise ValueError(
            f"{spec.line.id} declara la zona {spec.line.zone}, que no está en zonas.json"
        )
    with logfire.span("import network {line}", line=spec.line.id):
        net = build_network(spec, data_dir)
        async with conn.transaction():
            await upsert_sources(conn, sources, data_dir)
            await upsert_zones(conn, zones)
            for op in spec.operators:
                await conn.execute(
                    """
                    INSERT INTO operators (id, name, role, source_id, timetable) VALUES ($1,$2,$3,$4,$5)
                    ON CONFLICT (id) DO UPDATE SET name=EXCLUDED.name, role=EXCLUDED.role,
                      source_id=EXCLUDED.source_id, timetable=EXCLUDED.timetable
                    """,
                    op.id,
                    op.name,
                    op.role,
                    op.source_id,
                    op.timetable if op.role == "operador" else None,
                )
            await _upsert_line(conn, net)
            # Los operadores de trenes de la especificación son los que circulan por la línea.
            await conn.execute("DELETE FROM line_operators WHERE line_id = $1", spec.line.id)
            await conn.executemany(
                "INSERT INTO line_operators (line_id, operator_id) VALUES ($1, $2)",
                [(spec.line.id, op.id) for op in spec.operators if op.role == "operador"],
            )
            await _replace_nodes_and_segments(conn, net)
            await _replace_connections(conn, net)
            await _upsert_stop_mappings(conn, net)
        stats: dict[str, Any] = {
            "line_id": spec.line.id,
            "length_km": round(net.line.polyline.length_km, 3),
            "reference_length_km": spec.line.reference_length_km,
            "nodes": len(net.nodes),
            "shared_nodes": sum(1 for n in net.nodes if n.spec.shared),
            "segments": len(net.segments),
            "single_track_segments": sum(1 for s in net.segments if s.tracks == 1),
            "connections": len(spec.connections),
            "gaps": len(net.line.gaps_km),
            "joins_m": [round(j * 1000) for j in net.line.joins_km],
            "max_snap_offset_m": round(max(n.offset_m for n in net.nodes), 1),
        }
        logfire.info("network imported", **stats)
        return stats


async def _upsert_line(conn: asyncpg.Connection, net: BuiltNetwork) -> None:
    line = net.spec.line
    geometry = {"type": "LineString", "coordinates": round_coords(net.line.polyline.coords)}
    await conn.execute(
        """
        INSERT INTO lines (id, name, short_name, sort_order, zone_id, mode, infrastructure_manager_id, gauge_mm, electrification,
                           max_speed_kmh, opened_on, length_km, reference_length_km, status, description, geometry, source_id)
        VALUES ($1,$2,$3,$4,$17,$5,$6,$7,$8,$9,$10,$11,$12,$13,$14,$15,$16)
        ON CONFLICT (id) DO UPDATE SET name=EXCLUDED.name, short_name=EXCLUDED.short_name, sort_order=EXCLUDED.sort_order,
          zone_id=EXCLUDED.zone_id,
          mode=EXCLUDED.mode, infrastructure_manager_id=EXCLUDED.infrastructure_manager_id, gauge_mm=EXCLUDED.gauge_mm,
          electrification=EXCLUDED.electrification, max_speed_kmh=EXCLUDED.max_speed_kmh, opened_on=EXCLUDED.opened_on,
          length_km=EXCLUDED.length_km, reference_length_km=EXCLUDED.reference_length_km, status=EXCLUDED.status,
          description=EXCLUDED.description, geometry=EXCLUDED.geometry, source_id=EXCLUDED.source_id, updated_at=now()
        """,
        line.id,
        line.name,
        line.short_name,
        line.sort_order,
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
        line.zone,
    )


async def _replace_nodes_and_segments(conn: asyncpg.Connection, net: BuiltNetwork) -> None:
    line_id = net.spec.line.id
    source_id = net.spec.line.verification_source_id or net.spec.line.geometry_source.source_id
    await conn.execute("DELETE FROM segments WHERE line_id = $1", line_id)
    await conn.execute("DELETE FROM line_nodes WHERE line_id = $1", line_id)
    for seq, n in enumerate(net.nodes, start=1):
        # Un nodo compartido lo define otra línea: si ya existe no se toca; si aún no, se crea
        # con lo que trae esta especificación y la línea propietaria lo completará al importarse.
        conflict = (
            "DO NOTHING"
            if n.spec.shared
            else """DO UPDATE SET name=EXCLUDED.name, kind=EXCLUDED.kind, rank=EXCLUDED.rank, lon=EXCLUDED.lon,
              lat=EXCLUDED.lat, adif_code=EXCLUDED.adif_code, description=EXCLUDED.description,
              details=EXCLUDED.details, source_id=EXCLUDED.source_id"""
        )
        await conn.execute(
            f"""
            INSERT INTO nodes (id, name, kind, rank, lon, lat, adif_code, description, details, source_id)
            VALUES ($1,$2,$3,$4,$5,$6,$7,$8,$9,$10)
            ON CONFLICT (id) {conflict}
            """,
            n.spec.id,
            n.spec.name,
            n.spec.kind,
            n.spec.rank,
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
            s.tracks,
            net.spec.line.status,
            {"type": "LineString", "coordinates": round_coords(s.coords)},
            s.source_id,
        )
    # Las filas anteriores se han ido con sus tramos (ON DELETE CASCADE).
    await conn.executemany(
        """
        INSERT INTO segment_attributes (segment_id, attribute, value, source_id, checked_on)
        VALUES ($1,$2,$3,$4,$5)
        """,
        [
            (s.id, attribute, a.value, a.source_id, a.checked_on)
            for s in net.segments
            for attribute, a in sorted(s.attributes.items())
        ],
    )


async def _replace_connections(conn: asyncpg.Connection, net: BuiltNetwork) -> None:
    line_id = net.spec.line.id
    node_ids = [n.spec.id for n in net.nodes]
    # Se borran las conexiones de esta especificación y las de los nodos que solo pertenecen a
    # esta línea; las de un nodo compartido que declare otra línea se conservan.
    await conn.execute(
        "DELETE FROM connections WHERE id = ANY($1::text[])",
        [c.id for c in net.spec.connections],
    )
    await conn.execute(
        """
        DELETE FROM connections
        WHERE node_id = ANY($1::text[])
          AND node_id NOT IN (SELECT node_id FROM line_nodes WHERE line_id <> $2)
        """,
        node_ids,
        line_id,
    )
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
    # La tabla es común a todas las líneas y sirve para listar los trenes que paran en un nodo.
    # Si una parada ya está asignada a un nodo por otra línea, una asignación «de salida» no la
    # degrada: una estación compartida sigue siendo estación.
    for stop_id, m in net.spec.stop_mappings.items():
        await conn.execute(
            """
            INSERT INTO stop_mappings (stop_id, node_id, exit_node_ids) VALUES ($1,$2,$3)
            ON CONFLICT (stop_id) DO UPDATE SET
              node_id = COALESCE(EXCLUDED.node_id, stop_mappings.node_id),
              exit_node_ids = CASE WHEN COALESCE(EXCLUDED.node_id, stop_mappings.node_id) IS NULL
                                   THEN EXCLUDED.exit_node_ids ELSE '{}'::text[] END
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
                "tracks": s.tracks,
                "attributes": {k: a.value for k, a in sorted(s.attributes.items())},
            }
            for s in net.segments
        ],
    }


def dumps(obj: Any) -> str:
    return json.dumps(obj, ensure_ascii=False, indent=2)
