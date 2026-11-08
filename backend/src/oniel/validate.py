"""Validaciones sin base de datos: red construida, PK de referencia y resolución de horarios."""

from __future__ import annotations

from collections import Counter
from pathlib import Path
from typing import Any

from oniel.gtfs.importer import calls_for_trip
from oniel.gtfs.reader import read_feed, select_corridor_trips
from oniel.network.build import build_network
from oniel.network.spec import load_network_spec
from oniel.sim.passes import LineNode, LineSegment, resolve_passes

PK_TOLERANCE_KM = 1.5
LENGTH_TOLERANCE_KM = 3.0


def validate_all(spec_path: Path, feed_path: Path, data_dir: Path) -> dict[str, Any]:
    spec = load_network_spec(spec_path)
    net = build_network(spec, data_dir)
    problems: list[str] = []
    length = net.line.polyline.length_km
    if (
        spec.line.reference_length_km
        and abs(length - spec.line.reference_length_km) > LENGTH_TOLERANCE_KM
    ):
        problems.append(
            f"longitud {length:.1f} km frente a {spec.line.reference_length_km} km de referencia"
        )
    if net.line.gaps_km:
        problems.append(f"{len(net.line.gaps_km)} huecos en la geometría")
    pk_checks = []
    for n in net.nodes:
        ref = n.spec.reference_pk_km
        delta = None if ref is None else round(n.km - ref, 2)
        pk_checks.append(
            {
                "node": n.spec.id,
                "km": round(n.km, 2),
                "reference_pk_km": ref,
                "delta_km": delta,
                "offset_m": round(n.offset_m),
            }
        )
        if delta is not None and abs(delta) > PK_TOLERANCE_KM and n.spec.position.km is None:
            problems.append(
                f"el nodo {n.spec.id} queda en el km {n.km:.1f} y la referencia es {ref}"
            )

    feed = read_feed(feed_path)
    trips = select_corridor_trips(
        feed, spec.corridor_filter.required_stop_ids, spec.corridor_filter.any_of_stop_ids
    )
    nodes = {n.spec.id: LineNode(n.spec.id, n.km, n.lon, n.lat) for n in net.nodes}
    segments = [LineSegment(s.id, s.km_from, s.km_to) for s in net.segments]
    kinds: Counter[str] = Counter()
    resolutions: Counter[str] = Counter()
    unmapped: Counter[str] = Counter()
    for trip in trips:
        calls = calls_for_trip(trip, feed, spec)
        for c in calls:
            if c.node_id is None and not c.exit_node_ids:
                unmapped[f"{c.stop_id} {c.stop_name}"] += 1
        passes, resolution = resolve_passes(calls, nodes, segments)
        resolutions[resolution] += 1
        kinds.update(p.kind for p in passes)
    if unmapped:
        problems.append(f"paradas sin asignar: {sorted(unmapped)}")
    return {
        "line": spec.line.id,
        "length_km": round(length, 3),
        "reference_length_km": spec.line.reference_length_km,
        "nodes": pk_checks,
        "segments": [
            {
                "id": s.id,
                "length_km": round(s.length_km, 2),
                "max_speed_kmh": s.max_speed_kmh,
                "typical_speed_kmh": s.typical_speed_kmh,
            }
            for s in net.segments
        ],
        "gtfs": {
            "trips": len(trips),
            "train_numbers": len({t.train_number for t in trips}),
            "passes": dict(kinds),
            "resolution": dict(resolutions),
            "feed": [feed.feed_start.isoformat(), feed.feed_end.isoformat()],
        },
        "problems": problems,
    }
