"""Importación idempotente de servicios GTFS que recorren una línea cargada."""

from __future__ import annotations

import datetime as dt
from collections import Counter
from pathlib import Path
from typing import Any

import asyncpg
import logfire

from oniel.gtfs.reader import GtfsFeed, GtfsTrip, read_feed, select_corridor_trips
from oniel.network.spec import NetworkSpec, load_network_spec
from oniel.sim.passes import LineNode, LineSegment, SegmentPass, StopCall, resolve_passes


async def load_line_model(
    conn: asyncpg.Connection, line_id: str
) -> tuple[dict[str, LineNode], list[LineSegment]]:
    node_rows = await conn.fetch(
        "SELECT n.id, ln.km, n.lon, n.lat FROM nodes n JOIN line_nodes ln ON ln.node_id = n.id WHERE ln.line_id = $1",
        line_id,
    )
    seg_rows = await conn.fetch(
        "SELECT id, km_from, km_to FROM segments WHERE line_id = $1 ORDER BY seq", line_id
    )
    nodes = {r["id"]: LineNode(r["id"], float(r["km"]), r["lon"], r["lat"]) for r in node_rows}
    segments = [LineSegment(r["id"], float(r["km_from"]), float(r["km_to"])) for r in seg_rows]
    return nodes, segments


def calls_for_trip(trip: GtfsTrip, feed: GtfsFeed, spec: NetworkSpec) -> list[StopCall]:
    calls = []
    for st in trip.stop_times:
        stop = feed.stops.get(st.stop_id)
        mapping = spec.stop_mappings.get(st.stop_id)
        calls.append(
            StopCall(
                seq=st.seq,
                stop_id=st.stop_id,
                stop_name=stop.name if stop else st.stop_id,
                arrival_s=st.arrival_s,
                departure_s=st.departure_s,
                lon=stop.lon if stop else None,
                lat=stop.lat if stop else None,
                node_id=mapping.node if mapping else None,
                exit_node_ids=tuple(mapping.exits) if mapping else (),
            )
        )
    return calls


async def import_gtfs(
    conn: asyncpg.Connection, feed_path: Path, spec_path: Path, *, source_id: str, operator_id: str
) -> dict[str, Any]:
    spec = load_network_spec(spec_path)
    with logfire.span("import gtfs {feed}", feed=feed_path.name):
        feed = read_feed(feed_path)
        trips = select_corridor_trips(
            feed, spec.corridor_filter.required_stop_ids, spec.corridor_filter.any_of_stop_ids
        )
        nodes, segments = await load_line_model(conn, spec.line.id)
        if not segments:
            raise RuntimeError("primero hay que importar la red (oniel-data import network)")
        feed_version = (
            f"{feed_path.name}:{feed.feed_start.isoformat()}..{feed.feed_end.isoformat()}"
        )
        kinds: Counter[str] = Counter()
        resolutions: Counter[str] = Counter()
        unmapped: Counter[str] = Counter()
        async with conn.transaction():
            run_id = await conn.fetchval(
                "INSERT INTO import_runs (command, source_id, status, feed_version) VALUES ('import gtfs', $1, 'running', $2) RETURNING id",
                source_id,
                feed_version,
            )
            await conn.execute("DELETE FROM services WHERE source_id = $1", source_id)
            for trip in trips:
                calls = calls_for_trip(trip, feed, spec)
                for c in calls:
                    if c.node_id is None and not c.exit_node_ids:
                        unmapped[f"{c.stop_id} {c.stop_name}"] += 1
                passes, resolution = resolve_passes(calls, nodes, segments)
                resolutions[resolution] += 1
                for p in passes:
                    kinds[p.kind] += 1
                dates = sorted(feed.service_dates.get(trip.service_id, set()))
                if not dates:
                    continue
                await _insert_service(
                    conn,
                    trip,
                    calls,
                    passes,
                    resolution,
                    dates,
                    source_id,
                    operator_id,
                    run_id,
                    feed_version,
                )
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
            stats = {
                "feed_version": feed_version,
                "trips_in_feed": len(feed.trips),
                "trips_imported": len(trips),
                "train_numbers": len({t.train_number for t in trips}),
                "passes": dict(kinds),
                "resolution": dict(resolutions),
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
    trip: GtfsTrip,
    calls: list[StopCall],
    passes: list[SegmentPass],
    resolution: str,
    dates: list[dt.date],
    source_id: str,
    operator_id: str,
    run_id: int,
    feed_version: str,
) -> None:
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
        resolution,
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
            for p in passes
        ],
    )
