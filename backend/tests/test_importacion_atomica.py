"""Una carga fallida o simultánea conserva la correspondencia entre los datos y su huella."""

from __future__ import annotations

import asyncio
import json
from collections.abc import AsyncIterator
from pathlib import Path
from typing import Any
from uuid import uuid4

import asyncpg
import pytest
import pytest_asyncio
from conftest import DATA_DIR, SOURCES, SPEC, database_url_for_tests, requires_db

from oniel.db.pool import connect
from oniel.importing import last_import_fingerprint, run_import_all

pytestmark = requires_db


@pytest_asyncio.fixture
async def connections() -> AsyncIterator[tuple[asyncpg.Connection, asyncpg.Connection]]:
    dsn = database_url_for_tests()
    assert dsn is not None
    schema = f"importacion_{uuid4().hex}"
    async with connect(dsn) as writer, connect(dsn) as reader:
        await writer.execute(f"CREATE SCHEMA {schema}")
        try:
            for conn in (writer, reader):
                await conn.execute(f"SET search_path TO {schema}")
            yield writer, reader
        finally:
            await writer.execute(f"DROP SCHEMA {schema} CASCADE")


async def _run(
    conn: asyncpg.Connection, specs: list[Path], snapshot: Path | None = None
) -> dict[str, Any]:
    return await run_import_all(
        conn,
        specs=specs,
        sources=SOURCES,
        feeds=[],
        data_dir=DATA_DIR,
        snapshot_dir=snapshot,
        if_changed=True,
    )


@pytest.mark.parametrize("stage", ["segunda línea", "instantánea"])
async def test_un_fallo_conserva_la_version_anterior_y_permite_reintentar(
    connections: tuple[asyncpg.Connection, asyncpg.Connection],
    monkeypatch: pytest.MonkeyPatch,
    tmp_path: Path,
    stage: str,
) -> None:
    writer, reader = connections
    line = json.loads(SPEC.read_text(encoding="utf-8"))
    line_id = line["line"]["id"]
    old_name = line["line"]["name"]
    by_id = "SELECT name FROM lines WHERE id = $1"
    version = "SELECT version FROM data_version"
    monkeypatch.setenv("RENDER_GIT_COMMIT", "anterior")
    assert not (await _run(writer, [SPEC]))["skipped"]
    old_version = await reader.fetchval(version)
    assert isinstance(old_version, int)

    changed = tmp_path / SPEC.name
    line["line"]["name"] = "Nombre modificado"
    changed.write_text(json.dumps(line), encoding="utf-8")
    monkeypatch.setenv("RENDER_GIT_COMMIT", "nueva")
    if stage == "segunda línea":
        with pytest.raises(FileNotFoundError):
            await _run(writer, [changed, tmp_path / "ausente.json"])
    else:
        # Un fichero impide crear el directorio de salida de la instantánea.
        output = tmp_path / "salida"
        output.touch()
        with pytest.raises(FileExistsError):
            await _run(writer, [changed], output)

    monkeypatch.setenv("RENDER_GIT_COMMIT", "anterior")
    assert (await _run(writer, [SPEC]))["skipped"]
    assert await reader.fetchval(by_id, line_id) == old_name
    assert await reader.fetchval(version) == old_version
    assert await last_import_fingerprint(reader) == "git:anterior"

    monkeypatch.setenv("RENDER_GIT_COMMIT", "nueva")
    assert not (await _run(writer, [changed]))["skipped"]
    assert await reader.fetchval(by_id, line_id) == "Nombre modificado"
    assert await reader.fetchval(version) == old_version + 1
    assert await last_import_fingerprint(reader) == "git:nueva"


async def test_dos_arranques_en_una_base_vacia_solo_importan_una_vez(
    connections: tuple[asyncpg.Connection, asyncpg.Connection],
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    writer, reader = connections
    monkeypatch.setenv("RENDER_GIT_COMMIT", "compartida")
    async with asyncio.timeout(30):
        results = await asyncio.gather(_run(writer, [SPEC]), _run(reader, [SPEC]))
    assert sorted(result["skipped"] for result in results) == [False, True]
    assert await writer.fetchval("SELECT version FROM data_version") == 1
    assert await last_import_fingerprint(reader) == "git:compartida"
