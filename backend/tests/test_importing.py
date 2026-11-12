"""Huella de la importación: `import all --if-changed` se salta el trabajo si ni los datos ni el código cambiaron."""

from __future__ import annotations

import datetime as dt
from pathlib import Path
from typing import Any

import pytest
from conftest import (
    DATA_DIR,
    FEED,
    FEED_OPERATOR_ID,
    FEED_SOURCE_ID,
    SOURCES,
    SPECS,
    database_url_for_tests,
    requires_db,
)
from logfire.testing import CaptureLogfire

from oniel.importing import import_fingerprint, import_summary, run_import_all


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
async def test_import_all_skips_when_nothing_changed(capfire: CaptureLogfire) -> None:
    from oniel.db.migrate import drop_everything
    from oniel.db.pool import connect
    from oniel.network.spec import FeedSpec

    dsn = database_url_for_tests()
    assert dsn is not None
    async with connect(dsn) as conn:

        async def run(if_changed: bool) -> dict[str, Any]:
            return await run_import_all(
                conn,
                specs=SPECS,
                sources=SOURCES,
                feeds=[
                    FeedSpec(
                        file=str(FEED),
                        source_id=FEED_SOURCE_ID,
                        operator_id=FEED_OPERATOR_ID,
                        retrieved_on=dt.date(2026, 11, 8),
                    )
                ],
                data_dir=DATA_DIR,
                snapshot_dir=None,
                if_changed=if_changed,
            )

        await drop_everything(conn)
        # base vacía: aunque se pida saltar, hay que importar
        first = await run(if_changed=True)
        assert first["skipped"] is False
        assert first["gtfs"][0]["trips_imported"] == 335 + 503 - 24 + 26
        # misma huella: se salta sin tocar la base
        second = await run(if_changed=True)
        assert second["skipped"] is True
        assert second["fingerprint"] == first["fingerprint"]
        assert await conn.fetchval("SELECT count(*) FROM import_runs") == 1
        # sin --if-changed siempre se importa
        third = await run(if_changed=False)
        assert third["skipped"] is False
        assert await conn.fetchval("SELECT count(*) FROM import_runs") == 2

    # un tramo por importación, con su resultado y sus recuentos; las consultas cuelgan de él
    runs = [
        s["attributes"]
        for s in capfire.exporter.exported_spans_as_dict()
        if s["name"] == "import all"
    ]
    assert [r["outcome"] for r in runs] == ["completed", "skipped", "completed"]
    assert runs[0]["trips_imported"] == 335 + 503 - 24 + 26
    assert runs[0]["lines"] == len(SPECS) and runs[0]["snapshot_exported"] is False
    assert "trips_imported" not in runs[1]


def test_import_summary_counts_what_was_loaded() -> None:
    skipped = import_summary({"skipped": True, "fingerprint": "git:abc", "migrations": []})
    assert skipped == {"outcome": "skipped", "fingerprint": "git:abc", "migrations": 0}
    done = import_summary(
        {
            "skipped": False,
            "fingerprint": "git:abc",
            "migrations": ["0008"],
            "network": [{}, {}, {}],
            "gtfs": [{"trips_imported": 814}, {"trips_imported": 12}],
            "datasets_removed": ["viejo"],
            "snapshot": {"segments": 60},
        }
    )
    assert done["outcome"] == "completed"
    assert (done["lines"], done["feeds"], done["trips_imported"]) == (3, 2, 826)
    assert done["datasets_removed"] == 1 and done["snapshot_exported"] is True


@pytest.mark.asyncio
async def test_failed_import_leaves_a_failed_span(
    capfire: CaptureLogfire, monkeypatch: pytest.MonkeyPatch, tmp_path: Path
) -> None:
    async def boom(*args: Any, **kwargs: Any) -> dict[str, Any]:
        raise RuntimeError("fichero de horarios ilegible")

    monkeypatch.setattr("oniel.importing._import_all", boom)
    no_connection: Any = None  # la importación simulada no usa la conexión
    with pytest.raises(RuntimeError):
        await run_import_all(
            no_connection,
            specs=[],
            sources=tmp_path / "sources.json",
            feeds=[],
            data_dir=tmp_path,
            snapshot_dir=None,
        )
    spans = capfire.exporter.exported_spans_as_dict()
    assert [s["name"] for s in spans] == ["import all started", "import all"]
    failed = spans[1]
    assert failed["attributes"]["outcome"] == "failed"
    assert failed["events"][0]["attributes"]["exception.type"] == "RuntimeError"
