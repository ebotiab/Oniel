"""Anotaciones de red: comprobación contra la red y carga en la base de datos.

El fichero curado (``data/curated/anotaciones.json``) se valida en dos pasos. El modelo
``AnnotationSpec`` comprueba cada entrada por separado (tipo, estado, alcance, campos, orden de las
fechas); ``check_annotations`` la contrasta con las líneas cargadas y con el registro de fuentes.
Lo usan ``oniel-data validate``, con la red construida en memoria, y la importación, con la de la
base.
"""

from __future__ import annotations

from collections import Counter
from collections.abc import Mapping, Sequence
from pathlib import Path
from typing import Any

import asyncpg
import logfire

from oniel.network.importer import upsert_sources
from oniel.network.spec import AnnotationSpec, load_annotations, load_sources


def check_annotations(
    annotations: Sequence[AnnotationSpec],
    line_nodes: Mapping[str, Sequence[str]],
    source_urls: Mapping[str, str | None],
) -> list[str]:
    """Problemas de las anotaciones frente a la red y las fuentes; lista vacía si no hay.

    ``line_nodes`` da, por línea cargada, los ids de sus nodos en el orden del kilometraje;
    ``source_urls``, la URL de cada fuente registrada.
    """
    problems: list[str] = []
    known_nodes = {node for nodes in line_nodes.values() for node in nodes}
    for a in annotations:
        if a.line_id is not None and a.from_node is not None and a.to_node is not None:
            nodes = line_nodes.get(a.line_id)
            if nodes is None:
                problems.append(f"{a.label} apunta a la línea {a.line_id}, que no está cargada")
            else:
                missing = [n for n in (a.from_node, a.to_node) if n not in nodes]
                for node in missing:
                    problems.append(
                        f"{a.label}: el nodo {node} no pertenece a la línea {a.line_id}"
                    )
                if not missing and nodes.index(a.from_node) > nodes.index(a.to_node):
                    problems.append(
                        f"{a.label}: {a.from_node} está después de {a.to_node} en la"
                        f" línea {a.line_id}; los nodos van en el orden del kilometraje"
                    )
        if a.node_id is not None and a.node_id not in known_nodes:
            problems.append(
                f"{a.label} apunta al nodo {a.node_id}, que no está en ninguna línea cargada"
            )
        for source_id in a.source_ids:
            if source_id not in source_urls:
                problems.append(
                    f"{a.label} cita la fuente {source_id}, que no está en sources.json"
                )
        primary = a.source_ids[0]
        if primary in source_urls and not source_urls[primary]:
            problems.append(f"{a.label}: su fuente principal, {primary}, no tiene URL")
    return problems


async def import_annotations(
    conn: asyncpg.Connection, path: Path, sources_path: Path, data_dir: Path
) -> dict[str, Any]:
    """Sustituye las anotaciones de la base por las del fichero. Necesita la red ya importada."""
    annotations = load_annotations(path)
    sources = load_sources(sources_path)
    with logfire.span("import annotations"):
        async with conn.transaction():
            await upsert_sources(conn, sources, data_dir)
            rows = await conn.fetch("SELECT line_id, node_id FROM line_nodes ORDER BY line_id, seq")
            line_nodes: dict[str, list[str]] = {}
            for r in rows:
                line_nodes.setdefault(r["line_id"], []).append(r["node_id"])
            problems = check_annotations(annotations, line_nodes, {s.id: s.url for s in sources})
            if problems:
                raise ValueError(
                    f"{path.name} no encaja con la red cargada: " + "; ".join(problems)
                )
            await conn.execute("DELETE FROM annotations")
            for a in annotations:
                await conn.execute(
                    """
                    INSERT INTO annotations (id, kind, status, line_id, from_node_id, to_node_id,
                        node_id, geometry, start_date, expected_end_date, expected_end_text,
                        ended_on, title, reason, note, source_ids, checked_on)
                    VALUES ($1,$2,$3,$4,$5,$6,$7,$8,$9,$10,$11,$12,$13,$14,$15,$16,$17)
                    """,
                    a.id,
                    a.kind,
                    a.status,
                    a.line_id,
                    a.from_node,
                    a.to_node,
                    a.node_id,
                    a.geometry,
                    a.start_date,
                    a.expected_end_date,
                    a.expected_end_text,
                    a.ended_on,
                    a.title,
                    a.reason,
                    a.note,
                    a.source_ids,
                    a.checked_on,
                )
        stats: dict[str, Any] = {
            "annotations": len(annotations),
            "by_kind": dict(sorted(Counter(a.kind for a in annotations).items())),
            "open": sum(1 for a in annotations if a.ended_on is None),
            "ended": sum(1 for a in annotations if a.ended_on is not None),
            "ids": [a.id for a in annotations],
        }
        logfire.info("annotations imported", **stats)
        return stats
