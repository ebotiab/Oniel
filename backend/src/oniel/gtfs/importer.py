"""Importación idempotente de servicios GTFS que recorren las líneas cargadas.

Un mismo fichero GTFS alimenta todas las líneas: cada viaje se guarda una sola vez y su paso
por los tramos se calcula línea a línea con la asignación de paradas de cada especificación. Un
tren que cambia de línea a mitad de recorrido (``route_overrides``) produce pasos en cada una
solo entre las paradas que le corresponden.
"""

from __future__ import annotations

import datetime as dt
from collections import Counter
from collections.abc import Sequence
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any, Literal

import asyncpg
import logfire

from oniel.db.pool import fetch_int
from oniel.gtfs.reader import GtfsTrip, read_feed
from oniel.gtfs.trips import (
    LoadedLine,
    calls_for_trip,
    calls_on_line,
    route_for_trip,
    select_trips_for_spec,
)
from oniel.network.spec import load_network_spec
from oniel.sim.passes import LineNode, LineSegment, SegmentPass, StopCall, resolve_passes

__all__ = ["calls_for_trip", "import_gtfs", "load_line_model", "select_trips_for_spec"]


async def load_line_model(
    conn: asyncpg.Connection, line_id: str
) -> tuple[dict[str, LineNode], list[LineSegment]]:
    node_rows = await conn.fetch(
        "SELECT n.id, n.name, ln.km, n.lon, n.lat FROM nodes n JOIN line_nodes ln ON ln.node_id = n.id WHERE ln.line_id = $1",
        line_id,
    )
    seg_rows = await conn.fetch(
        "SELECT id, km_from, km_to FROM segments WHERE line_id = $1 ORDER BY seq", line_id
    )
    nodes = {
        r["id"]: LineNode(r["id"], float(r["km"]), r["lon"], r["lat"], r["name"]) for r in node_rows
    }
    segments = [LineSegment(r["id"], float(r["km_from"]), float(r["km_to"])) for r in seg_rows]
    return nodes, segments


@dataclass
class _TripPlan:
    trip: GtfsTrip
    calls: list[StopCall]
    passes: list[SegmentPass] = field(default_factory=list)
    resolutions: list[Literal["completa", "parcial"]] = field(default_factory=list)
    lines: list[str] = field(default_factory=list)

    @property
    def resolution(self) -> Literal["completa", "parcial"]:
        return "completa" if all(r == "completa" for r in self.resolutions) else "parcial"


async def import_gtfs(
    conn: asyncpg.Connection,
    feed_path: Path,
    spec_paths: Path | Sequence[Path],
    *,
    source_id: str,
    operator_id: str,
) -> dict[str, Any]:
    paths = [spec_paths] if isinstance(spec_paths, Path) else list(spec_paths)
    specs = [load_network_spec(p) for p in paths]
    with logfire.span("import gtfs {feed}", feed=feed_path.name):
        feed = read_feed(feed_path)
        plans: dict[str, _TripPlan] = {}
        per_line: dict[str, dict[str, Any]] = {}
        unmapped: Counter[str] = Counter()
        models = {spec.line.id: await load_line_model(conn, spec.line.id) for spec in specs}
        loaded = [LoadedLine(spec, models[spec.line.id][0]) for spec in specs]
        for spec in specs:
            nodes, segments = models[spec.line.id]
            if not segments:
                raise RuntimeError(
                    f"primero hay que importar la red de {spec.line.id} (oniel-data import network)"
                )
            others = [line for line in loaded if line.line_id != spec.line.id]
            kinds: Counter[str] = Counter()
            resolutions: Counter[str] = Counter()
            rules: Counter[str] = Counter()
            trips = select_trips_for_spec(feed, spec)
            for trip in trips:
                route = route_for_trip(spec, trip)
                if route is not None:
                    rules[route.override.id] += 1
                calls = calls_for_trip(trip, feed, spec, nodes=nodes, others=others, route=route)
                line_calls = calls_on_line(calls, route)
                for c in line_calls:
                    if c.node_id is None and not c.exit_node_ids:
                        unmapped[f"{spec.line.id}: {c.stop_id} {c.stop_name}"] += 1
                passes, resolution = resolve_passes(line_calls, nodes, segments)
                resolutions[resolution] += 1
                kinds.update(p.kind for p in passes)
                plan = plans.setdefault(trip.trip_id, _TripPlan(trip, calls))
                plan.passes.extend(passes)
                plan.resolutions.append(resolution)
                plan.lines.append(spec.line.id)
            per_line[spec.line.id] = {
                "trips": len(trips),
                "train_numbers": len({t.train_number for t in trips}),
                "passes": dict(kinds),
                "resolution": dict(resolutions),
                "route_overrides": dict(rules),
            }
        feed_version = (
            f"{feed_path.name}:{feed.feed_start.isoformat()}..{feed.feed_end.isoformat()}"
        )
        async with conn.transaction():
            run_id = await fetch_int(
                conn,
                "INSERT INTO import_runs (command, source_id, status, feed_version) VALUES ('import gtfs', $1, 'running', $2) RETURNING id",
                source_id,
                feed_version,
            )
            await conn.execute("DELETE FROM services WHERE source_id = $1", source_id)
            for plan in plans.values():
                dates = sorted(feed.service_dates.get(plan.trip.service_id, set()))
                if not dates:
                    continue
                await _insert_service(
                    conn, plan, dates, source_id, operator_id, run_id, feed_version
                )
            for spec in specs:
                for stop_id in spec.stop_mappings:
                    stop = feed.stops.get(stop_id)
                    if stop:
                        await conn.execute(
                            "UPDATE stop_mappings SET stop_name=$2, lon=$3, lat=$4, source_id=$5 WHERE stop_id=$1",
                            stop_id,
                            stop.name,
                            stop.lon,
                            stop.lat,
                            source_id,
                        )
            all_kinds: Counter[str] = Counter()
            for plan in plans.values():
                all_kinds.update(p.kind for p in plan.passes)
            stats: dict[str, Any] = {
                "feed_version": feed_version,
                "trips_in_feed": len(feed.trips),
                "trips_imported": len(plans),
                "train_numbers": len({p.trip.train_number for p in plans.values()}),
                "passes": dict(all_kinds),
                "resolution": dict(Counter(p.resolution for p in plans.values())),
                "lines": per_line,
                "unmapped_stops": dict(unmapped),
                "feed_start": feed.feed_start.isoformat(),
                "feed_end": feed.feed_end.isoformat(),
            }
            await conn.execute(
                "UPDATE import_runs SET status='ok', finished_at=now(), stats=$2 WHERE id=$1",
                run_id,
                stats,
            )
        logfire.info("gtfs imported", **{k: v for k, v in stats.items() if k != "unmapped_stops"})
        return stats


async def _insert_service(
    conn: asyncpg.Connection,
    plan: _TripPlan,
    dates: list[dt.date],
    source_id: str,
    operator_id: str,
    run_id: int,
    feed_version: str,
) -> None:
    trip, calls = plan.trip, plan.calls
    first, last = calls[0], calls[-1]
    await conn.execute(
        """
        INSERT INTO services (id, operator_id, train_number, product, origin_stop_id, origin_name, destination_stop_id,
                              destination_name, valid_from, valid_to, gtfs_route_id, gtfs_service_id, resolution,
                              source_id, import_run_id, feed_version)
        VALUES ($1,$2,$3,$4,$5,$6,$7,$8,$9,$10,$11,$12,$13,$14,$15,$16)
        """,
        trip.trip_id,
        operator_id,
        trip.train_number,
        trip.product or "tren",
        first.stop_id,
        first.stop_name,
        last.stop_id,
        last.stop_name,
        dates[0],
        dates[-1],
        trip.route_id,
        trip.service_id,
        plan.resolution,
        source_id,
        run_id,
        feed_version,
    )
    await conn.executemany(
        "INSERT INTO service_dates (service_id, service_date) VALUES ($1, $2)",
        [(trip.trip_id, d) for d in dates],
    )
    await conn.executemany(
        """
        INSERT INTO service_stops (service_id, seq, stop_id, stop_name, arrival_s, departure_s, pickup_type, drop_off_type)
        VALUES ($1,$2,$3,$4,$5,$6,$7,$8)
        """,
        [
            (
                trip.trip_id,
                c.seq,
                c.stop_id,
                c.stop_name,
                c.arrival_s,
                c.departure_s,
                st.pickup_type,
                st.drop_off_type,
            )
            for c, st in zip(calls, trip.stop_times, strict=True)
        ],
    )
    await conn.executemany(
        """
        INSERT INTO service_segment_passes (service_id, segment_id, kind, enter_s, exit_s, enter_margin_s, exit_margin_s,
                                            km_increasing, basis)
        VALUES ($1,$2,$3,$4,$5,$6,$7,$8,$9)
        """,
        [
            (
                trip.trip_id,
                p.segment_id,
                p.kind,
                p.enter_s,
                p.exit_s,
                p.enter_margin_s,
                p.exit_margin_s,
                p.km_increasing,
                p.basis,
            )
            for p in plan.passes
        ],
    )
