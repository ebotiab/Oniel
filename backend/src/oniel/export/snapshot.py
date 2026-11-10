"""Exporta la red y los servicios a JSON estático para el visor cuando no hay API."""

from __future__ import annotations

import datetime as dt
import json
from pathlib import Path
from typing import Any

import asyncpg

from oniel.domain.schemas import SegmentPassOut, SegmentServicesOut
from oniel.repo import network_repo, services_repo
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
    _write(out_dir / "network.json", network.model_dump(mode="json"))
    _write(out_dir / "coverage.json", coverage.model_dump(mode="json"))
    counts = await services_repo.daily_counts(conn, day)
    _write(out_dir / "segment-counts.json", {"date": day.isoformat(), "counts": counts})
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
        _write(
            out_dir / "nodes" / f"{node.id}.json",
            {"node": node.model_dump(mode="json"), "date": day.isoformat(), "calls": calls},
        )
    return {
        "out_dir": str(out_dir),
        "date": day.isoformat(),
        "segments": len(network.segments),
        "nodes": len(network.nodes),
        "interruptions": len(network.interruptions),
    }
