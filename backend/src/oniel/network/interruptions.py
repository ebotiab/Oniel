"""Interrupciones del servicio: comprobación contra la red y carga en la base de datos.

El fichero curado (``data/curated/interrupciones.json``) se valida en dos pasos. El modelo
``InterruptionSpec`` comprueba cada entrada por separado (campos, orden de las fechas);
``check_interruptions`` la contrasta con las líneas cargadas y con el registro de fuentes. Lo usan
``oniel-data validate``, con la red construida en memoria, y la importación, con la de la base.
"""

from __future__ import annotations

from collections.abc import Mapping, Sequence
from pathlib import Path
from typing import Any

import asyncpg
import logfire

from oniel.network.importer import upsert_sources
from oniel.network.spec import InterruptionSpec, load_interruptions, load_sources


def check_interruptions(
    interruptions: Sequence[InterruptionSpec],
    line_nodes: Mapping[str, Sequence[str]],
    source_urls: Mapping[str, str | None],
) -> list[str]:
    """Problemas de las interrupciones frente a la red y las fuentes; lista vacía si no hay.

    ``line_nodes`` da, por línea cargada, los ids de sus nodos en el orden del kilometraje;
    ``source_urls``, la URL de cada fuente registrada.
    """
    problems: list[str] = []
    for i in interruptions:
        nodes = line_nodes.get(i.line_id)
        if nodes is None:
            problems.append(
                f"la interrupción {i.id} apunta a la línea {i.line_id}, que no está cargada"
            )
        else:
            missing = [n for n in (i.from_node, i.to_node) if n not in nodes]
            for node in missing:
                problems.append(
                    f"la interrupción {i.id}: el nodo {node} no pertenece a la línea {i.line_id}"
                )
            if not missing and nodes.index(i.from_node) > nodes.index(i.to_node):
                problems.append(
                    f"la interrupción {i.id}: {i.from_node} está después de {i.to_node} en la"
                    f" línea {i.line_id}; los nodos van en el orden del kilometraje"
                )
        for source_id in i.source_ids:
            if source_id not in source_urls:
                problems.append(
                    f"la interrupción {i.id} cita la fuente {source_id}, que no está en sources.json"
                )
        primary = i.source_ids[0]
        if primary in source_urls and not source_urls[primary]:
            problems.append(f"la interrupción {i.id}: su fuente principal, {primary}, no tiene URL")
    return problems


async def import_interruptions(
    conn: asyncpg.Connection, path: Path, sources_path: Path, data_dir: Path
) -> dict[str, Any]:
    """Sustituye las interrupciones de la base por las del fichero. Necesita la red ya importada."""
    interruptions = load_interruptions(path)
    sources = load_sources(sources_path)
    with logfire.span("import interruptions"):
        async with conn.transaction():
            await upsert_sources(conn, sources, data_dir)
            rows = await conn.fetch("SELECT line_id, node_id FROM line_nodes ORDER BY line_id, seq")
            line_nodes: dict[str, list[str]] = {}
            for r in rows:
                line_nodes.setdefault(r["line_id"], []).append(r["node_id"])
            problems = check_interruptions(
                interruptions, line_nodes, {s.id: s.url for s in sources}
            )
            if problems:
                raise ValueError(
                    f"{path.name} no encaja con la red cargada: " + "; ".join(problems)
                )
            await conn.execute("DELETE FROM interruptions")
            for i in interruptions:
                await conn.execute(
                    """
                    INSERT INTO interruptions (id, line_id, from_node_id, to_node_id, start_date,
                        expected_end_date, expected_end_text, ended_on, reason, note, source_ids, checked_on)
                    VALUES ($1,$2,$3,$4,$5,$6,$7,$8,$9,$10,$11,$12)
                    """,
                    i.id,
                    i.line_id,
                    i.from_node,
                    i.to_node,
                    i.start_date,
                    i.expected_end_date,
                    i.expected_end_text,
                    i.ended_on,
                    i.reason,
                    i.note,
                    i.source_ids,
                    i.checked_on,
                )
        stats: dict[str, Any] = {
            "interruptions": len(interruptions),
            "open": sum(1 for i in interruptions if i.ended_on is None),
            "ended": sum(1 for i in interruptions if i.ended_on is not None),
            "ids": [i.id for i in interruptions],
        }
        logfire.info("interruptions imported", **stats)
        return stats
