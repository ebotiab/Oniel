"""Validaciones sin base de datos: red construida, PK de referencia y resolución de horarios."""

from __future__ import annotations

from collections import Counter
from collections.abc import Sequence
from pathlib import Path
from typing import Any

from oniel.gtfs.reader import read_feed
from oniel.gtfs.trips import (
    LoadedLine,
    calls_for_trip,
    calls_on_line,
    route_for_trip,
    select_trips_for_spec,
)
from oniel.network.build import BuiltNetwork, build_network
from oniel.network.spec import load_network_spec
from oniel.sim.passes import LineNode, LineSegment, resolve_passes

LENGTH_TOLERANCE_KM = 3.0


def loaded_line(net: BuiltNetwork) -> LoadedLine:
    nodes = {n.spec.id: LineNode(n.spec.id, n.km, n.lon, n.lat, n.spec.name) for n in net.nodes}
    return LoadedLine(net.spec, nodes)


def validate_all(
    spec_path: Path, feed_path: Path, data_dir: Path, other_spec_paths: Sequence[Path] = ()
) -> dict[str, Any]:
    """Comprueba una línea; las demás (``other_spec_paths``) solo se usan para medir por ellas."""
    spec = load_network_spec(spec_path)
    net = build_network(spec, data_dir)
    others = [
        loaded_line(build_network(load_network_spec(p), data_dir))
        for p in other_spec_paths
        if p != spec_path
    ]
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
        if (
            delta is not None
            and abs(delta) > spec.line.pk_tolerance_km
            and n.spec.position.km is None
        ):
            problems.append(
                f"el nodo {n.spec.id} queda en el km {n.km:.1f} y la referencia es {ref}"
            )

    feed = read_feed(feed_path)
    trips = select_trips_for_spec(feed, spec)
    nodes = loaded_line(net).nodes
    segments = [LineSegment(s.id, s.km_from, s.km_to) for s in net.segments]
    kinds: Counter[str] = Counter()
    resolutions: Counter[str] = Counter()
    unmapped: Counter[str] = Counter()
    products: Counter[str] = Counter()
    rules: Counter[str] = Counter({r.id: 0 for r in spec.route_overrides})
    for trip in trips:
        products[trip.product or "tren"] += 1
        route = route_for_trip(spec, trip)
        if route is not None:
            rules[route.override.id] += 1
        calls = calls_for_trip(trip, feed, spec, nodes=nodes, others=others, route=route)
        line_calls = calls_on_line(calls, route)
        for c in line_calls:
            if c.node_id is None and not c.exit_node_ids:
                unmapped[f"{c.stop_id} {c.stop_name}"] += 1
        passes, resolution = resolve_passes(line_calls, nodes, segments)
        resolutions[resolution] += 1
        kinds.update(p.kind for p in passes)
    if unmapped:
        problems.append(f"paradas sin asignar: {sorted(unmapped)}")
    for rule_id, count in rules.items():
        if count == 0:
            problems.append(f"la regla de recorrido {rule_id} no encaja con ningún viaje del GTFS")
    known_lines = {o.line_id for o in others}
    for where, mappings in [
        ("stop_mappings", spec.stop_mappings),
        *[(f"la regla {r.id}", r.stop_mappings) for r in spec.route_overrides],
    ]:
        for stop_id, m in mappings.items():
            if m.via is not None and m.via.line not in known_lines:
                problems.append(
                    f"{where}: la parada {stop_id} sale hacia la línea {m.via.line}, que no está"
                    " entre las líneas cargadas"
                )
    return {
        "line": spec.line.id,
        "length_km": round(length, 3),
        "reference_length_km": spec.line.reference_length_km,
        "parts": [
            {"source_id": p.source_id, "km_from": round(p.km_from, 2), "km_to": round(p.km_to, 2)}
            for p in net.line.part_spans
        ],
        "joins_m": [round(j * 1000) for j in net.line.joins_km],
        "nodes": pk_checks,
        "segments": [
            {
                "id": s.id,
                "length_km": round(s.length_km, 2),
                "max_speed_kmh": s.max_speed_kmh,
                "typical_speed_kmh": s.typical_speed_kmh,
                "tracks": s.tracks,
                "source_id": s.source_id,
            }
            for s in net.segments
        ],
        "gtfs": {
            "trips": len(trips),
            "train_numbers": len({t.train_number for t in trips}),
            "products": dict(products),
            "passes": dict(kinds),
            "resolution": dict(resolutions),
            "route_overrides": dict(rules),
            "feed": [feed.feed_start.isoformat(), feed.feed_end.isoformat()],
        },
        "problems": problems,
    }
