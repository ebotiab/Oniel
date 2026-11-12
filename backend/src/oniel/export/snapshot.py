"""Exporta la red y los servicios a JSON estático para el visor cuando no hay API.

El visor arranca con ``index.json`` (el índice ligero de toda la red) y pide ``lines/<id>.json``
al abrir cada línea, que trae también sus pasos por tramo. ``alternatives.json`` (trenes por
tramo y si la red cargada les ofrece otro camino) va aparte y tampoco se pide al arrancar. La red entera en una sola respuesta
solo la da la API (``GET /api/network``).
"""

from __future__ import annotations

import datetime as dt
import json
import shutil
from pathlib import Path
from typing import Any

import asyncpg

from oniel.domain.schemas import SegmentPassOut, SegmentServicesOut, ServiceHistoryOut
from oniel.repo import datasets_repo, network_repo, services_repo
from oniel.sim.service import direction_label, shifted_times


def safe_name(identifier: str) -> str:
    """Nombre de fichero sin dos puntos: Vite y algunos CDN no sirven rutas con ':'."""
    return identifier.replace(":", "--")


def _write(path: Path, payload: Any) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(payload, ensure_ascii=False, default=str), encoding="utf-8")


async def export_snapshot(
    conn: asyncpg.Connection, out_dir: Path, date: dt.date | None = None
) -> dict[str, Any]:
    network = await network_repo.fetch_network(conn)
    coverage = await network_repo.fetch_coverage(conn)
    day = date or coverage.reference_date or dt.date.today()
    _write(out_dir / "coverage.json", coverage.model_dump(mode="json"))
    index = await network_repo.fetch_index(conn)
    _write(out_dir / "index.json", index.model_dump(mode="json"))
    # Un fichero por línea; la carpeta se rehace entera para que no queden líneas retiradas.
    lines_dir = out_dir / "lines"
    if lines_dir.exists():
        shutil.rmtree(lines_dir)
    for line in network.lines:
        detail = await network_repo.fetch_line_detail(conn, line.id, day)
        assert detail is not None
        _write(lines_dir / f"{safe_name(line.id)}.json", detail.model_dump(mode="json"))
    # Trenes por tramo y alternativa en la red cargada: un fichero propio, que el visor solo pide
    # al abrir la ficha de un tramo o el panel de cobertura.
    alternatives = await network_repo.fetch_segment_alternatives(conn, day)
    _write(out_dir / "alternatives.json", alternatives.model_dump(mode="json"))
    # Histórico compacto, con cada conjunto de datos en su propio día de referencia: los pasos por
    # tramo de cada conjunto (los lee el resumen del refresco de horarios) y, por tramo y por nodo,
    # los trenes de cada conjunto, que es lo que la ficha compara y lo mismo que responde la API
    # en `/history`. La carpeta se rehace entera para que no queden conjuntos retirados.
    history_dir = out_dir / "historico"
    if history_dir.exists():
        shutil.rmtree(history_dir)
    datasets = await datasets_repo.fetch_datasets(conn)
    refs = await datasets_repo.reference_dates(conn)
    for segment in network.segments:
        history = ServiceHistoryOut(
            id=segment.id, points=await services_repo.segment_history(conn, segment.id, refs)
        )
        _write(
            history_dir / "segments" / f"{safe_name(segment.id)}.json",
            history.model_dump(mode="json"),
        )
    for node_id in dict.fromkeys(node.id for node in network.nodes):
        history = ServiceHistoryOut(
            id=node_id, points=await services_repo.node_history(conn, node_id, refs)
        )
        _write(history_dir / "nodes" / f"{node_id}.json", history.model_dump(mode="json"))
    for dataset in datasets:
        ref = refs.get(dataset.id)
        if ref is None:
            continue
        _write(
            history_dir / safe_name(dataset.id) / "segment-counts.json",
            {
                "dataset": dataset.model_dump(mode="json"),
                "date": ref.isoformat(),
                "counts": await services_repo.daily_counts(conn, ref, dataset.id),
            },
        )
    for segment in network.segments:
        dated = await services_repo.passes_on_segment(conn, segment.id, day)
        passes = []
        kinds = {"publicado": 0, "estimado": 0, "indeterminado": 0}
        for d in dated:
            enter, exit_ = shifted_times(d.segment_pass, d.from_previous_day)
            kinds[d.segment_pass.kind] += 1
            passes.append(
                SegmentPassOut(
                    service=d.service,
                    kind=d.segment_pass.kind,
                    enter=enter,
                    exit=exit_,
                    enter_margin_min=round(d.segment_pass.enter_margin_s / 60, 1),
                    exit_margin_min=round(d.segment_pass.exit_margin_s / 60, 1),
                    km_increasing=d.segment_pass.km_increasing,
                    direction_label=direction_label(segment, d.segment_pass.km_increasing),
                    basis=d.segment_pass.basis,
                )
            )
        payload = SegmentServicesOut(
            segment=segment,
            date=day,
            passes=passes,
            counts=kinds,
            interruptions=[
                i for i in network.interruptions if segment.id in i.segment_ids and i.active_on(day)
            ],
        )
        _write(
            out_dir / "segments" / f"{safe_name(segment.id)}.json", payload.model_dump(mode="json")
        )
    for node in network.nodes:
        calls = await services_repo.calls_at_node(conn, node.id, day)
        destinations = await services_repo.destinations_from_node(conn, node.id, day)
        _write(
            out_dir / "nodes" / f"{node.id}.json",
            {
                "node": node.model_dump(mode="json"),
                "date": day.isoformat(),
                "calls": calls,
                "destinations": [d.model_dump(mode="json") for d in destinations],
            },
        )
    return {
        "out_dir": str(out_dir),
        "date": day.isoformat(),
        "lines": [line.id for line in network.lines],
        "segments": len(network.segments),
        "nodes": len(network.nodes),
        "annotations": len(network.annotations),
        "interruptions": len(network.interruptions),
        "datasets": [d.id for d in datasets],
    }
