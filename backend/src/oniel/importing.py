"""Importación completa y repetible, con una huella para saltarla cuando nada ha cambiado.

En Render (plan gratuito) la API se suspende sin tráfico y cada despertar ejecuta `import all`,
que allí tarda alrededor de un minuto. La huella identifica lo que esa importación cargaría: el
commit desplegado (``RENDER_GIT_COMMIT``) o, fuera de Render, un hash de ``data/`` y ``src/oniel/``.
Si coincide con la última importación registrada, ``--if-changed`` deja la base como está.
"""

from __future__ import annotations

import hashlib
import os
from collections.abc import Mapping
from pathlib import Path
from typing import Any

import asyncpg

#: Código cuya modificación obliga a reimportar (reglas de recorrido, migraciones, exportación…).
SRC_DIR = Path(__file__).resolve().parent
FINGERPRINT_KEY = "import all"
_IGNORED_DIRS = {"__pycache__"}
_IGNORED_SUFFIXES = {".pyc", ".pyo"}


def _files(root: Path) -> list[Path]:
    return sorted(
        path
        for path in root.rglob("*")
        if path.is_file()
        and path.suffix not in _IGNORED_SUFFIXES
        and not _IGNORED_DIRS.intersection(path.relative_to(root).parts)
    )


def import_fingerprint(
    data_dir: Path, src_dir: Path = SRC_DIR, *, env: Mapping[str, str] | None = None
) -> str:
    """Huella de lo que importaría `import all`: el commit desplegado o un hash de datos y código."""
    environ = os.environ if env is None else env
    commit = environ.get("RENDER_GIT_COMMIT")
    if commit:
        return f"git:{commit}"
    digest = hashlib.sha256()
    for root in (data_dir, src_dir):
        for path in _files(root):
            digest.update(f"{root.name}/{path.relative_to(root).as_posix()}\0".encode())
            digest.update(path.read_bytes())
            digest.update(b"\0")
    return f"files:{digest.hexdigest()}"


async def last_import_fingerprint(conn: asyncpg.Connection) -> str | None:
    value: str | None = await conn.fetchval(
        "SELECT value FROM import_state WHERE key = $1", FINGERPRINT_KEY
    )
    return value


async def record_import_fingerprint(conn: asyncpg.Connection, fingerprint: str) -> None:
    await conn.execute(
        """
        INSERT INTO import_state (key, value, updated_at) VALUES ($1, $2, now())
        ON CONFLICT (key) DO UPDATE SET value = EXCLUDED.value, updated_at = now()
        """,
        FINGERPRINT_KEY,
        fingerprint,
    )


async def run_import_all(
    conn: asyncpg.Connection,
    *,
    specs: list[Path],
    sources: Path,
    feed: Path,
    data_dir: Path,
    snapshot_dir: Path | None,
    if_changed: bool = False,
    source_id: str = "renfe-gtfs-av-ld-md",
    operator_id: str = "renfe",
    src_dir: Path = SRC_DIR,
) -> dict[str, Any]:
    """Migra, importa la red y los horarios, exporta la instantánea y registra la huella.

    Con ``if_changed`` devuelve ``{"skipped": True}`` sin tocar los datos cuando la huella coincide
    con la de la última importación. Las migraciones se aplican siempre: son baratas y la tabla de
    estado sale de ellas.
    """
    # Importaciones perezosas, como en la CLI: la red y el GTFS cargan dependencias pesadas.
    from oniel.db.migrate import migrate
    from oniel.export.snapshot import export_snapshot
    from oniel.gtfs.importer import import_gtfs
    from oniel.network.importer import import_network

    migrations = await migrate(conn)
    fingerprint = import_fingerprint(data_dir, src_dir)
    if if_changed and await last_import_fingerprint(conn) == fingerprint:
        return {"skipped": True, "fingerprint": fingerprint, "migrations": migrations}

    nets = [await import_network(conn, path, sources, data_dir) for path in specs]
    gtfs = await import_gtfs(conn, feed, specs, source_id=source_id, operator_id=operator_id)
    snap = await export_snapshot(conn, snapshot_dir) if snapshot_dir else None
    await record_import_fingerprint(conn, fingerprint)
    return {
        "skipped": False,
        "fingerprint": fingerprint,
        "migrations": migrations,
        "network": nets,
        "gtfs": gtfs,
        "snapshot": snap,
    }
