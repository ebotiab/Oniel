"""Validaciones sin base de datos: red construida, PK de referencia, horarios e interrupciones."""

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
    via_legs,
)
from oniel.network.build import BuiltNetwork, build_network
from oniel.network.interruptions import check_interruptions
from oniel.network.spec import (
    OperatorSpec,
    load_feeds,
    load_interruptions,
    load_network_spec,
    load_sources,
)
from oniel.sim.passes import LineNode, LineSegment, resolve_passes

LENGTH_TOLERANCE_KM = 3.0


def loaded_line(net: BuiltNetwork) -> LoadedLine:
    nodes = {n.spec.id: LineNode(n.spec.id, n.km, n.lon, n.lat, n.spec.name) for n in net.nodes}
    return LoadedLine(net.spec, nodes)


def validate_interruptions(
    path: Path, sources_path: Path, spec_paths: Sequence[Path], data_dir: Path
) -> dict[str, Any]:
    """Comprueba el fichero de interrupciones contra las líneas cargadas y el registro de fuentes.

    Un fichero que no cumple el esquema (campos, orden de las fechas, ids repetidos) no llega a
    contrastarse con la red: el error del modelo es el único problema que se devuelve.
    """
    try:
        interruptions = load_interruptions(path)
    except (ValueError, OSError) as error:
        return {"interruptions": path.name, "entries": [], "problems": [str(error)]}
    line_nodes: dict[str, list[str]] = {}
    for spec_path in spec_paths:
        net = build_network(load_network_spec(spec_path), data_dir)
        line_nodes[net.spec.line.id] = [n.spec.id for n in sorted(net.nodes, key=lambda n: n.km)]
    sources = {s.id: s.url for s in load_sources(sources_path)}
    return {
        "interruptions": path.name,
        "entries": [
            {
                "id": i.id,
                "line": i.line_id,
                "from": i.from_node,
                "to": i.to_node,
                "start_date": i.start_date.isoformat(),
                "ended_on": i.ended_on.isoformat() if i.ended_on else None,
                "checked_on": i.checked_on.isoformat(),
                "sources": i.source_ids,
            }
            for i in interruptions
        ],
        "problems": check_interruptions(interruptions, line_nodes, sources),
    }


def validate_operators(
    spec_paths: Sequence[Path], sources_path: Path, data_dir: Path
) -> dict[str, Any]:
    """Comprueba los operadores de trenes de las líneas contra los ficheros de horarios declarados.

    Cada operador con horarios cargados tiene al menos un fichero y cada fichero es de un operador
    declarado en alguna línea; un operador que no publica sus horarios no tiene ninguno. Los
    ficheros vigentes (el más reciente de cada fuente) han de coincidir en algún día: de esos días
    sale el de referencia, que así cae dentro de la validez de todos.
    """
    problems: list[str] = []
    operators: dict[str, OperatorSpec] = {}
    for path in spec_paths:
        for op in load_network_spec(path).operators:
            if op.role != "operador":
                continue
            known = operators.setdefault(op.id, op)
            if known != op:
                problems.append(f"el operador {op.id} no se declara igual en todas las líneas")
    sources = {s.id for s in load_sources(sources_path)}
    for op in operators.values():
        if op.source_id not in sources:
            problems.append(f"el operador {op.id} no cita una fuente registrada")
    feeds = load_feeds(sources_path)
    for feed in feeds:
        declared = operators.get(feed.operator_id)
        if declared is None:
            problems.append(
                f"{feed.file} es del operador {feed.operator_id}, que no está en ninguna línea"
            )
        elif declared.timetable != "cargado":
            problems.append(
                f"{feed.file} es de {feed.operator_id}, declarado sin horarios publicados"
            )
    with_feed = {f.operator_id for f in feeds}
    for op in operators.values():
        if op.timetable == "cargado" and op.id not in with_feed:
            problems.append(f"el operador {op.id} no tiene ningún fichero de horarios declarado")
    # el vigente de cada fuente es el último de la lista, que va del más antiguo al más reciente
    current = {f.source_id: f for f in feeds}
    windows = []
    for feed in current.values():
        read = read_feed(data_dir / feed.file)
        windows.append((feed, read.feed_start, read.feed_end))
    common: list[str] | None = None
    if windows:
        start, end = max(w[1] for w in windows), min(w[2] for w in windows)
        if start > end:
            problems.append(
                "los ficheros de horarios vigentes no coinciden en ningún día: no hay un día de"
                " referencia dentro de la validez de todos"
            )
        else:
            common = [start.isoformat(), end.isoformat()]
    return {
        "operators": [
            {"id": op.id, "timetable": op.timetable, "source_id": op.source_id}
            for op in operators.values()
        ],
        "feeds": [
            {
                "file": feed.file,
                "operator_id": feed.operator_id,
                "valid": [start.isoformat(), end.isoformat()],
            }
            for feed, start, end in windows
        ],
        "common_validity": common,
        "problems": problems,
    }


def unused_route_overrides(reports: Sequence[dict[str, Any]]) -> list[str]:
    """Reglas de recorrido que no encajan con ningún viaje de ninguno de los ficheros validados."""
    used: Counter[tuple[str, str]] = Counter()
    for report in reports:
        for rule_id, count in report.get("gtfs", {}).get("route_overrides", {}).items():
            used[(report["line"], rule_id)] += count
    return [
        f"la regla de recorrido {rule_id} de {line} no encaja con ningún viaje de ningún GTFS"
        for (line, rule_id), count in used.items()
        if count == 0
    ]


def validate_all(
    spec_path: Path,
    feed_path: Path,
    data_dir: Path,
    other_spec_paths: Sequence[Path] = (),
    *,
    stop_id_prefix: str | None = None,
    require_rules: bool = True,
) -> dict[str, Any]:
    """Comprueba una línea; las demás (``other_spec_paths``) solo se usan para medir por ellas.

    Con ``require_rules`` cada regla de recorrido tiene que encajar con algún viaje del fichero.
    Cuando se validan varios ficheros se desactiva y se comprueba después, con todos a la vez
    (:func:`unused_route_overrides`): una regla escrita para los trenes de un operador no encaja
    con el fichero de otro.
    """
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
        # el PK de referencia se compara con el kilómetro medido más el PK del origen de la línea
        delta = None if ref is None else round(n.km + spec.line.pk_origin_km - ref, 2)
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
                f"el nodo {n.spec.id} queda en el km {n.km + spec.line.pk_origin_km:.1f} y la"
                f" referencia es {ref}"
            )

    feed = read_feed(feed_path, stop_id_prefix=stop_id_prefix)
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
        if count == 0 and require_rules:
            problems.append(f"la regla de recorrido {rule_id} no encaja con ningún viaje del GTFS")
    # Una parada que sale hacia otra línea cargada tiene que poder seguirse hasta ella; si no,
    # el reparto volvería a la línea recta sin avisar.
    for where, mappings in [
        ("stop_mappings", spec.stop_mappings),
        *[(f"la regla {r.id}", r.stop_mappings) for r in spec.route_overrides],
    ]:
        for stop_id, m in mappings.items():
            if not m.via:
                continue
            legs = via_legs(stop_id, m, others)
            if isinstance(legs, str):
                problems.append(f"{where}: el «via» de la parada {stop_id} no se sostiene: {legs}")
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
            "file": feed_path.name,
            "feed": [feed.feed_start.isoformat(), feed.feed_end.isoformat()],
        },
        "problems": problems,
    }
