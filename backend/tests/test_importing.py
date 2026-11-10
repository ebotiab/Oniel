"""Huella de la importación: `import all --if-changed` se salta el trabajo si ni los datos ni el código cambiaron."""

from __future__ import annotations

from pathlib import Path
from typing import Any

import pytest
from conftest import DATA_DIR, FEED, SOURCES, SPECS, database_url_for_tests, requires_db

from oniel.importing import import_fingerprint


def _tree(root: Path) -> tuple[Path, Path]:
    data = root / "data"
    src = root / "src"
    (data / "curated").mkdir(parents=True)
    (data / "curated" / "linea.json").write_text('{"id": "linea"}', encoding="utf-8")
    src.mkdir()
    (src / "importer.py").write_text("print('v1')\n", encoding="utf-8")
    return data, src


def test_render_commit_is_the_fingerprint(tmp_path: Path) -> None:
    data, src = _tree(tmp_path)
    assert import_fingerprint(data, src, env={"RENDER_GIT_COMMIT": "abc123"}) == "git:abc123"


def test_file_fingerprint_is_stable_and_tracks_data_and_code(tmp_path: Path) -> None:
    data, src = _tree(tmp_path)
    first = import_fingerprint(data, src, env={})
    assert first.startswith("files:")
    assert import_fingerprint(data, src, env={}) == first

    (data / "curated" / "linea.json").write_text('{"id": "linea", "v": 2}', encoding="utf-8")
    after_data = import_fingerprint(data, src, env={})
    assert after_data != first

    (src / "importer.py").write_text("print('v2')\n", encoding="utf-8")
    assert import_fingerprint(data, src, env={}) != after_data


def test_file_fingerprint_ignores_bytecode(tmp_path: Path) -> None:
    data, src = _tree(tmp_path)
    before = import_fingerprint(data, src, env={})
    cache = src / "__pycache__"
    cache.mkdir()
    (cache / "importer.cpython-313.pyc").write_bytes(b"\x00\x01")
    assert import_fingerprint(data, src, env={}) == before


@requires_db
@pytest.mark.asyncio
async def test_import_all_skips_when_nothing_changed() -> None:
    from oniel.db.migrate import drop_everything
    from oniel.db.pool import connect
    from oniel.importing import run_import_all

    dsn = database_url_for_tests()
    assert dsn is not None
    async with connect(dsn) as conn:

        async def run(if_changed: bool) -> dict[str, Any]:
            return await run_import_all(
                conn,
                specs=SPECS,
                sources=SOURCES,
                feed=FEED,
                data_dir=DATA_DIR,
                snapshot_dir=None,
                if_changed=if_changed,
            )

        await drop_everything(conn)
        # base vacía: aunque se pida saltar, hay que importar
        first = await run(if_changed=True)
        assert first["skipped"] is False
        assert first["gtfs"]["trips_imported"] == 335 + 503 - 24
        # misma huella: se salta sin tocar la base
        second = await run(if_changed=True)
        assert second["skipped"] is True
        assert second["fingerprint"] == first["fingerprint"]
        assert await conn.fetchval("SELECT count(*) FROM import_runs") == 1
        # sin --if-changed siempre se importa
        third = await run(if_changed=False)
        assert third["skipped"] is False
        assert await conn.fetchval("SELECT count(*) FROM import_runs") == 2
