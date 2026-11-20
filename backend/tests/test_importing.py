"""Huella de la importación: `import all --if-changed` se salta el trabajo si ni los datos ni el código cambiaron.

Y lo que tarda: escribe en la base por lotes y el arranque de producción no exporta la instantánea.
"""

from __future__ import annotations

import datetime as dt
from collections.abc import AsyncIterator
from contextlib import asynccontextmanager
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
    count_round_trips,
    database_url_for_tests,
    requires_db,
)
from logfire.testing import CaptureLogfire
from typer.testing import CliRunner

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
        # los 409, los de las cuatro líneas de Extremadura que no estaban en otra; los 114 del
        # final, los de la línea de Barcelona a Figueres: los Avant de Barcelona a Figueres y los
        # AVE de Barcelona a Lyon
        assert (
            first["gtfs"][0]["trips_imported"]
            == 317
            + 432
            - 22
            + 26
            + 15
            + 37
            + 555
            + 8
            + 13
            + 465
            + 92
            + 181
            + 661
            + 409
            + 66
            + 33
            + 77
            + 293
            + 136
            + 114
            + 115  # los Avant de Toledo que no estaban en la línea de Valencia
            + 117  # los regionales de Barcelona a Girona y Portbou
            + 63  # los regionales de la costa de Tarragona que no estaban en otra línea
            + 426  # los de la línea de València a Alicante por Xàtiva que no estaban en otra
            + 475  # los de la línea de Madrid a Valladolid por Ávila que no estaban en otra
            + 20  # los regionales de Valladolid a Santander, que no estaban en otra
            + 84  # los regionales de Zaragoza a Logroño, Pamplona, Vitoria y Calatayud y los de Logroño a Alfaro
        )
        # misma huella: se salta sin tocar la base
        second = await run(if_changed=True)
        assert second["skipped"] is True
        assert second["fingerprint"] == first["fingerprint"]
        assert await conn.fetchval("SELECT count(*) FROM import_runs") == 1
        # sin --if-changed siempre se importa
        with count_round_trips() as round_trips:
            third = await run(if_changed=False)
        assert third["skipped"] is False
        assert await conn.fetchval("SELECT count(*) FROM import_runs") == 2
        # Las filas van por lotes: una copia por tabla de servicios y una sentencia agrupada por
        # tabla de la red. Con una sentencia por tren, por nodo y por fuente eran unas 20.000 idas
        # y vueltas para lo mismo; agrupadas son unas 600 con 25 líneas (unas 20 por línea).
        assert round_trips["copy_records_to_table"] == 4
        assert sum(round_trips.values()) < 40 * len(SPECS)
        # y guardan lo mismo: los trenes, con sus días, sus paradas y sus pasos por tramo
        trips = first["gtfs"][0]["trips_imported"]
        assert await conn.fetchval("SELECT count(*) FROM services") == trips
        for table in ("service_dates", "service_stops", "service_segment_passes"):
            assert (
                await conn.fetchval(f"SELECT count(DISTINCT service_id) FROM {table}") == trips
            ), table

    # un tramo por importación, con su resultado y sus recuentos; las consultas cuelgan de él
    runs = [
        s["attributes"]
        for s in capfire.exporter.exported_spans_as_dict()
        if s["name"] == "import all"
    ]
    assert [r["outcome"] for r in runs] == ["completed", "skipped", "completed"]
    assert (
        runs[0]["trips_imported"]
        == (
            317
            + 432
            - 22
            + 26
            + 15
            + 37
            + 555
            + 8
            + 13
            + 465
            + 92
            + 181
            + 661
            + 409
            + 66
            + 33
            + 77
            + 293
            + 136
            + 114
            + 115
            + 117
            + 63  # los regionales de la costa de Tarragona que no estaban en otra línea
            + 426
            + 475
            + 20  # los regionales de Valladolid a Santander
            + 84  # los regionales de Zaragoza a Logroño, Pamplona, Vitoria y Calatayud y los de Logroño a Alfaro
        )
    )
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


@pytest.mark.parametrize(
    ("args", "exports"), [([], True), (["--no-snapshot"], False), (["--if-changed"], True)]
)
def test_import_all_exports_the_snapshot_unless_told_not_to(
    monkeypatch: pytest.MonkeyPatch, args: list[str], exports: bool
) -> None:
    import oniel.cli.main as cli
    import oniel.importing as importing

    seen: dict[str, Any] = {}

    @asynccontextmanager
    async def no_database(dsn: str) -> AsyncIterator[None]:
        yield None

    async def fake_import(conn: Any, **kwargs: Any) -> dict[str, Any]:
        seen.update(kwargs)
        return {"skipped": True}

    monkeypatch.setattr(cli, "connect", no_database)
    monkeypatch.setattr(importing, "run_import_all", fake_import)
    result = CliRunner().invoke(cli.app, ["import", "all", *args])
    assert result.exit_code == 0, result.output
    assert seen["snapshot_dir"] == (cli.SNAPSHOT_DEFAULT if exports else None)
    assert seen["if_changed"] is ("--if-changed" in args)


def test_production_start_does_not_export_the_snapshot() -> None:
    # La instantánea la sirve Vercel desde el repositorio; en el contenedor de la API no la lee
    # nadie, y exportarla era un tercio de la importación al arrancar (docs/despliegue.md).
    entrypoint = (DATA_DIR.parent / "docker-entrypoint.sh").read_text(encoding="utf-8")
    assert "oniel-data import all --if-changed --no-snapshot\n" in entrypoint
