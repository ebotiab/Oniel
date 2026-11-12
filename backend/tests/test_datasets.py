"""Conjuntos de datos fechados: cada fichero de horarios se guarda aparte y el visor lee el activo."""

from __future__ import annotations

import csv
import datetime as dt
import io
import json
import zipfile
from collections.abc import AsyncIterator
from pathlib import Path
from typing import Any

import asyncpg
import pytest
import pytest_asyncio
from conftest import (
    DATA_DIR,
    FEED,
    FEED_DATASET_ID,
    FEED_OPERATOR_ID,
    FEED_SOURCE_ID,
    SOURCES,
    SPECS,
    database_url_for_tests,
    requires_db,
)

from oniel.gtfs.importer import file_sha256, retrieved_on_from_name
from oniel.network.spec import FeedSpec, load_feeds

#: Día de referencia del fichero del 8 de noviembre de 2026 (un viernes).
REFERENCE = dt.date(2026, 11, 13)
NEWER_ID = "renfe-gtfs-av-ld-md-2026-11-20"


def test_declared_feeds_exist_and_cite_registered_sources() -> None:
    feeds = load_feeds(SOURCES)
    assert feeds, "sources.json tiene que declarar al menos un fichero de horarios"
    assert [f.retrieved_on for f in feeds] == sorted(f.retrieved_on for f in feeds)
    for feed in feeds:
        path = DATA_DIR / feed.file
        assert path.is_file(), feed.file
        # la fecha de descarga es la del nombre del fichero
        assert retrieved_on_from_name(path) == feed.retrieved_on
    # el fichero fijo de las pruebas sigue declarado: es el primer conjunto del histórico
    assert FEED in [DATA_DIR / f.file for f in feeds]


def _sources_file(tmp_path: Path, feeds: list[dict[str, str]]) -> Path:
    path = tmp_path / "sources.json"
    source = {"id": "horarios", "name": "Horarios", "publisher": "Operador"}
    path.write_text(json.dumps({"feeds": feeds, "sources": [source]}), encoding="utf-8")
    return path


def test_feeds_are_sorted_from_oldest_to_newest(tmp_path: Path) -> None:
    def feed(day: str) -> dict[str, str]:
        return {
            "file": f"raw/horarios_{day}.zip",
            "source_id": "horarios",
            "operator_id": "operador",
            "retrieved_on": day,
        }

    feeds = load_feeds(_sources_file(tmp_path, [feed("2026-12-01"), feed("2026-11-08")]))
    assert [f.retrieved_on.isoformat() for f in feeds] == ["2026-11-08", "2026-12-01"]
    assert load_feeds(_sources_file(tmp_path, [])) == []


@pytest.mark.parametrize(
    ("feeds", "message"),
    [
        (
            [
                {
                    "file": "raw/a.zip",
                    "source_id": "otra",
                    "operator_id": "operador",
                    "retrieved_on": "2026-11-08",
                }
            ],
            "no está registrada",
        ),
        (
            [
                {
                    "file": "raw/a.zip",
                    "source_id": "horarios",
                    "operator_id": "operador",
                    "retrieved_on": "2026-11-08",
                }
            ]
            * 2,
            "repetidos",
        ),
        (
            [{"file": "raw/a.zip", "source_id": "horarios", "operator_id": "operador"}],
            "retrieved_on",
        ),
    ],
)
def test_feeds_that_do_not_hold_are_rejected(
    tmp_path: Path, feeds: list[dict[str, str]], message: str
) -> None:
    with pytest.raises(ValueError, match=message):
        load_feeds(_sources_file(tmp_path, feeds))


def test_retrieved_on_comes_from_the_file_name() -> None:
    assert retrieved_on_from_name(FEED) == dt.date(2026, 11, 8)
    assert retrieved_on_from_name(Path("google_transit.zip")) is None


def feed_without_trip(source: Path, target: Path, trip_id: str) -> None:
    """Copia un GTFS quitándole un viaje: un fichero distinto, con un servicio menos."""
    with zipfile.ZipFile(source) as src, zipfile.ZipFile(target, "w", zipfile.ZIP_DEFLATED) as out:
        for info in src.infolist():
            data = src.read(info.filename)
            if info.filename == "trips.txt":
                lines = data.decode("utf-8-sig").splitlines(keepends=True)
                column = [c.strip() for c in next(csv.reader(io.StringIO(lines[0])))].index(
                    "trip_id"
                )
                kept = [lines[0]] + [
                    line
                    for line in lines[1:]
                    if next(csv.reader(io.StringIO(line)))[column].strip() != trip_id
                ]
                assert len(kept) == len(lines) - 1
                data = "".join(kept).encode("utf-8")
            out.writestr(info.filename, data)


in_db = pytest.mark.asyncio(loop_scope="module")


@pytest_asyncio.fixture(loop_scope="module", scope="module")
async def conn() -> AsyncIterator[asyncpg.Connection]:
    from oniel.db.migrate import drop_everything, migrate
    from oniel.db.pool import connect
    from oniel.network.importer import import_network

    dsn = database_url_for_tests()
    assert dsn is not None
    async with connect(dsn) as connection:
        await drop_everything(connection)
        await migrate(connection)
        for spec in SPECS:
            await import_network(connection, spec, SOURCES, DATA_DIR)
        yield connection


@pytest_asyncio.fixture(loop_scope="module", scope="module")
async def two_datasets(
    conn: asyncpg.Connection, tmp_path_factory: pytest.TempPathFactory
) -> dict[str, Any]:
    """El fichero fijo y, después, uno más reciente al que le falta un tren del día de referencia."""
    from oniel.gtfs.importer import import_gtfs
    from oniel.repo import services_repo

    first = await import_gtfs(
        conn,
        FEED,
        SPECS,
        source_id=FEED_SOURCE_ID,
        operator_id=FEED_OPERATOR_ID,
        data_dir=DATA_DIR,
    )
    segment_id = "lav-madrid-sevilla:ciudad-real:puertollano"
    before = await services_repo.daily_counts(conn, REFERENCE)
    removed = (await services_repo.passes_on_segment(conn, segment_id, REFERENCE))[0].service
    newer = tmp_path_factory.mktemp("gtfs") / "google_transit_av_ld_md_2026-11-20.zip"
    feed_without_trip(FEED, newer, removed.id)
    second = await import_gtfs(
        conn, newer, SPECS, source_id=FEED_SOURCE_ID, operator_id=FEED_OPERATOR_ID
    )
    return {
        "first": first,
        "second": second,
        "before": before,
        "removed": removed,
        "segment_id": segment_id,
        "newer": newer,
    }


async def _count(conn: asyncpg.Connection, table: str, dataset_id: str) -> int:
    from oniel.db.pool import fetch_int

    return await fetch_int(conn, f"SELECT count(*) FROM {table} WHERE dataset_id = $1", dataset_id)


@requires_db
@in_db
async def test_a_new_file_keeps_the_previous_dataset(
    conn: asyncpg.Connection, two_datasets: dict[str, Any]
) -> None:
    first, second = two_datasets["first"], two_datasets["second"]
    assert first["dataset"] == {
        "id": FEED_DATASET_ID,
        "sha256": file_sha256(FEED),
        "retrieved_on": "2026-11-08",
        "reused": False,
    }
    assert second["dataset"]["id"] == NEWER_ID and second["dataset"]["reused"] is False
    rows = await conn.fetch("SELECT * FROM datasets ORDER BY retrieved_on")
    assert [r["id"] for r in rows] == [FEED_DATASET_ID, NEWER_ID]
    old, new = rows
    assert old["file"] == "raw/renfe/google_transit_av_ld_md_2026-11-08.zip"
    assert old["source_id"] == new["source_id"] == FEED_SOURCE_ID
    assert old["operator_id"] == new["operator_id"] == FEED_OPERATOR_ID
    assert (old["valid_from"], old["valid_to"]) == (dt.date(2026, 11, 7), dt.date(2027, 9, 29))
    # el anterior sigue entero y el nuevo tiene un viaje menos
    assert await _count(conn, "services", FEED_DATASET_ID) == 814
    assert await _count(conn, "services", NEWER_ID) == 813
    passes = (3126 + 115) + (2469 + 683) + (72 + 390)
    assert await _count(conn, "service_segment_passes", FEED_DATASET_ID) == passes
    assert await _count(conn, "service_segment_passes", NEWER_ID) < passes


@requires_db
@in_db
async def test_counts_and_coverage_come_from_the_active_dataset(
    conn: asyncpg.Connection, two_datasets: dict[str, Any]
) -> None:
    from oniel.repo import network_repo, services_repo

    segment_id, removed = two_datasets["segment_id"], two_datasets["removed"]
    coverage = await network_repo.fetch_coverage(conn)
    assert coverage.reference_date == REFERENCE
    assert [d.id for d in coverage.datasets] == [NEWER_ID]
    # el tren retirado circulaba el día de referencia: en el conjunto activo ya no pasa
    before = two_datasets["before"]
    now = await services_repo.daily_counts(conn, REFERENCE)
    assert now[segment_id] == before[segment_id] - 1
    assert sum(now.values()) < sum(before.values())
    assert await services_repo.daily_counts(conn, REFERENCE, FEED_DATASET_ID) == before
    on_segment = await services_repo.passes_on_segment(conn, segment_id, REFERENCE)
    assert len(on_segment) == now[segment_id]
    assert removed.id not in {d.service.id for d in on_segment}
    # los viajes no se cuentan dos veces aunque estén en los dos conjuntos
    assert len({d.service.id for d in on_segment}) == len(on_segment)
    # la ficha de un viaje que solo está en el conjunto anterior se sigue pudiendo leer
    found = await services_repo.fetch_service(conn, removed.id)
    assert found is not None and found[0].train_number == removed.train_number


@requires_db
@in_db
async def test_history_compares_the_two_datasets_each_on_its_reference_day(
    conn: asyncpg.Connection, two_datasets: dict[str, Any]
) -> None:
    """Dos ficheros de la misma fuente: la ficha puede decir cuántos trenes daba cada uno."""
    from oniel.repo import datasets_repo, services_repo

    segment_id, removed = two_datasets["segment_id"], two_datasets["removed"]
    assert await datasets_repo.reference_dates(conn) == {
        FEED_DATASET_ID: REFERENCE,
        NEWER_ID: REFERENCE,
    }
    old, new = await services_repo.segment_history(conn, segment_id)
    assert (old.dataset_id, old.retrieved_on) == (FEED_DATASET_ID, dt.date(2026, 11, 8))
    assert (new.dataset_id, new.retrieved_on) == (NEWER_ID, dt.date(2026, 11, 20))
    assert old.source_id == new.source_id == FEED_SOURCE_ID
    assert old.operator_id == new.operator_id == FEED_OPERATOR_ID
    assert old.date == new.date == REFERENCE
    # al fichero nuevo le falta un tren del día de referencia: uno menos, y de su tipo
    assert old.trains == two_datasets["before"][segment_id]
    assert new.trains == old.trains - 1
    by_product = {p.product: p.trains for p in new.products}
    assert {p.product: p.trains for p in old.products} == {
        **by_product,
        removed.product: by_product.get(removed.product, 0) + 1,
    }
    assert sum(p.trains for p in new.products) == new.trains
    # el primero de la fuente no tiene con quién compararse; el segundo, con él y en los mismos
    # días: las cuatro primeras semanas que cubren los dos
    assert old.change is None and new.change is not None
    change = new.change
    assert (change.previous_dataset_id, change.previous_retrieved_on) == (
        FEED_DATASET_ID,
        dt.date(2026, 11, 8),
    )
    assert (change.date_from, change.date_to) == (dt.date(2026, 11, 7), dt.date(2026, 12, 4))
    # el tren retirado falta todos los días de esas semanas en los que circulaba
    days = await conn.fetchval(
        """
        SELECT count(*) FROM service_dates WHERE dataset_id = $1 AND service_id = $2
          AND service_date BETWEEN $3 AND $4
        """,
        FEED_DATASET_ID,
        removed.id,
        change.date_from,
        change.date_to,
    )
    assert days >= 1
    assert change.trains_after == change.trains_before - days
    assert change.trains_before > 28 * new.trains / 2
    # el punto del conjunto activo cuenta lo mismo que la ficha del tramo
    assert new.trains == len(await services_repo.passes_on_segment(conn, segment_id, REFERENCE))

    # en una estación en la que paraba el tren retirado, también uno menos
    found = await services_repo.fetch_service(conn, removed.id)
    assert found is not None
    node_id = next(s.node_id for s in found[1] if s.node_id)
    old, new = await services_repo.node_history(conn, node_id)
    assert new.trains == old.trains - 1
    assert new.trains == len(await services_repo.calls_at_node(conn, node_id, REFERENCE))
    # y en un tramo por el que no pasaba, los mismos
    other = "convencional-madrid-alcazar-cordoba:andujar:villa-del-rio"
    assert removed.id not in {
        d.service.id for d in await services_repo.passes_on_segment(conn, other, REFERENCE)
    }
    old, new = await services_repo.segment_history(conn, other)
    assert old.trains == new.trains > 0 and old.products == new.products
    assert new.change is not None and new.change.trains_before == new.change.trains_after > 0


@requires_db
@in_db
async def test_each_dataset_is_counted_on_its_own_reference_day(
    conn: asyncpg.Connection, two_datasets: dict[str, Any]
) -> None:
    """Si el día de referencia de un fichero es otro, su punto lleva ese día y sus trenes."""
    from oniel.repo import datasets_repo, services_repo

    segment_id = two_datasets["segment_id"]
    later = dt.date(2026, 11, 20)
    transaction = conn.transaction()
    await transaction.start()
    try:
        # el fichero nuevo, como los que publica Renfe cada noche, ya no trae los días pasados
        await conn.execute(
            "DELETE FROM service_dates WHERE dataset_id = $1 AND service_date < $2", NEWER_ID, later
        )
        refs = await datasets_repo.reference_dates(conn)
        assert refs[FEED_DATASET_ID] == REFERENCE and refs[NEWER_ID] >= later
        old, new = await services_repo.segment_history(conn, segment_id)
        assert (old.date, new.date) == (REFERENCE, refs[NEWER_ID])
        assert old.trains == two_datasets["before"][segment_id]
        assert new.trains == len(
            await services_repo.passes_on_segment(conn, segment_id, refs[NEWER_ID])
        )
        # la comparación en los mismos días no depende del día de referencia: sigue contando las
        # cuatro semanas desde que valen los dos ficheros, y al nuevo le faltan los días borrados
        assert new.change is not None
        assert (new.change.date_from, new.change.date_to) == (
            dt.date(2026, 11, 7),
            dt.date(2026, 12, 4),
        )
        assert 0 < new.change.trains_after < new.change.trains_before
        # los días ya calculados se pueden pasar, como hace la exportación
        assert await services_repo.segment_history(conn, segment_id, refs) == [old, new]
    finally:
        await transaction.rollback()


@requires_db
@in_db
async def test_counts_are_split_by_operator_and_the_reference_day_is_common_to_all(
    conn: asyncpg.Connection, two_datasets: dict[str, Any]
) -> None:
    """Un segundo operador, con su propia fuente y una validez distinta, suma sus pasos aparte."""
    from oniel.repo import datasets_repo, services_repo

    segment_id = two_datasets["segment_id"]
    renfe = await services_repo.daily_counts(conn, REFERENCE)
    assert await services_repo.daily_counts_by_operator(conn, REFERENCE) == {
        segment: {FEED_OPERATOR_ID: n} for segment, n in renfe.items()
    }
    other, dataset_id = "otro-operador", "otra-fuente-2026-07-02"
    transaction = conn.transaction()
    await transaction.start()
    try:
        await conn.execute(
            "INSERT INTO operators (id, name, role) VALUES ($1, 'Otro operador', 'operador')", other
        )
        # su fichero empieza a valer en junio y termina en diciembre, antes que el de Renfe
        await conn.execute(
            """
            INSERT INTO datasets (id, source_id, operator_id, file, sha256, retrieved_on, valid_from, valid_to)
            VALUES ($1, 'adif-mapa-red', $2, 'raw/otro/horarios_2026-07-02.zip', 'sha-de-prueba',
                    '2026-07-02', '2026-06-26', '2026-12-12')
            """,
            dataset_id,
            other,
        )
        await conn.execute(
            """
            INSERT INTO services (dataset_id, id, operator_id, train_number, product, valid_from, valid_to, resolution)
            VALUES ($1, 'viaje-1', $2, '06510', 'Otro', '2026-06-26', '2026-12-12', 'completa')
            """,
            dataset_id,
            other,
        )
        days = [dt.date(2026, 6, 26), dt.date(2026, 6, 29), REFERENCE, dt.date(2026, 12, 12)]
        await conn.executemany(
            "INSERT INTO service_dates (dataset_id, service_id, service_date) VALUES ($1, 'viaje-1', $2)",
            [(dataset_id, day) for day in days],
        )
        await conn.execute(
            """
            INSERT INTO service_segment_passes (dataset_id, service_id, segment_id, kind, enter_s, exit_s,
                                                enter_margin_s, exit_margin_s, km_increasing, basis)
            VALUES ($1, 'viaje-1', $2, 'estimado', 36000, 36600, 60, 60, true, 'de prueba')
            """,
            dataset_id,
            segment_id,
        )
        # el día de referencia sale de los días que cubren los dos ficheros a la vez
        assert await datasets_repo.feed_bounds(conn) == (
            dt.date(2026, 11, 7),
            dt.date(2026, 12, 12),
            REFERENCE,
        )
        split = await services_repo.daily_counts_by_operator(conn, REFERENCE)
        assert split[segment_id] == {FEED_OPERATOR_ID: renfe[segment_id], other: 1}
        totals = await services_repo.daily_counts(conn, REFERENCE)
        assert totals[segment_id] == renfe[segment_id] + 1
        assert {s: sum(by.values()) for s, by in split.items()} == totals
        on_segment = await services_repo.passes_on_segment(conn, segment_id, REFERENCE)
        assert [d.service.train_number for d in on_segment if d.service.operator_id == other] == [
            "06510"
        ]
        # un día que solo cubre el segundo fichero cuenta solo a su operador
        assert await services_repo.daily_counts_by_operator(conn, dt.date(2026, 6, 29)) == {
            segment_id: {other: 1}
        }
    finally:
        await transaction.rollback()
    assert (await datasets_repo.feed_bounds(conn))[2] == REFERENCE


@requires_db
@in_db
async def test_the_active_dataset_is_the_newest_one_valid_that_day(
    conn: asyncpg.Connection, two_datasets: dict[str, Any]
) -> None:
    from oniel.repo import datasets_repo, services_repo

    later = dt.date(2026, 12, 2)
    async with conn.transaction():
        # si el fichero nuevo empezara a valer el 1 de diciembre, hasta entonces manda el anterior
        await conn.execute("UPDATE datasets SET valid_from = '2026-12-01' WHERE id = $1", NEWER_ID)
        assert [d.id for d in await datasets_repo.fetch_active_datasets(conn, REFERENCE)] == [
            FEED_DATASET_ID
        ]
        assert await services_repo.daily_counts(conn, REFERENCE) == two_datasets["before"]
        assert [d.id for d in await datasets_repo.fetch_active_datasets(conn, later)] == [NEWER_ID]
        assert await services_repo.daily_counts(conn, later) == await services_repo.daily_counts(
            conn, later, NEWER_ID
        )
        # y fuera de la validez de todos no hay nada que mostrar
        assert await datasets_repo.fetch_active_datasets(conn, dt.date(2025, 1, 1)) == []
        assert await services_repo.daily_counts(conn, dt.date(2025, 1, 1)) == {}
        await conn.execute("UPDATE datasets SET valid_from = '2026-11-07' WHERE id = $1", NEWER_ID)


@requires_db
@in_db
async def test_importing_the_same_file_again_duplicates_nothing(
    conn: asyncpg.Connection, two_datasets: dict[str, Any]
) -> None:
    from oniel.gtfs.importer import import_gtfs

    again = await import_gtfs(
        conn,
        two_datasets["newer"],
        SPECS,
        source_id=FEED_SOURCE_ID,
        operator_id=FEED_OPERATOR_ID,
    )
    assert again["dataset"]["id"] == NEWER_ID and again["dataset"]["reused"] is True
    assert await conn.fetchval("SELECT count(*) FROM datasets") == 2
    assert await _count(conn, "services", NEWER_ID) == 813
    assert await conn.fetchval("SELECT count(*) FROM services") == 814 + 813


@requires_db
@in_db
async def test_import_all_takes_several_files_and_drops_undeclared_datasets(
    conn: asyncpg.Connection, two_datasets: dict[str, Any], tmp_path: Path
) -> None:
    from oniel.importing import run_import_all

    def feed(path: Path, day: dt.date) -> FeedSpec:
        return FeedSpec(
            file=str(path),
            source_id=FEED_SOURCE_ID,
            operator_id=FEED_OPERATOR_ID,
            retrieved_on=day,
        )

    async def run(feeds: list[FeedSpec], snapshot_dir: Path | None) -> dict[str, Any]:
        return await run_import_all(
            conn,
            specs=SPECS,
            sources=SOURCES,
            feeds=feeds,
            data_dir=DATA_DIR,
            snapshot_dir=snapshot_dir,
        )

    both = [feed(FEED, dt.date(2026, 11, 8)), feed(two_datasets["newer"], dt.date(2026, 11, 20))]
    result = await run(both, tmp_path)
    assert [g["dataset"]["id"] for g in result["gtfs"]] == [FEED_DATASET_ID, NEWER_ID]
    assert [g["trips_imported"] for g in result["gtfs"]] == [814, 813]
    assert result["datasets_removed"] == []
    # la instantánea lleva el estado actual (el conjunto activo) y un recuento compacto por conjunto
    coverage = json.loads((tmp_path / "coverage.json").read_text(encoding="utf-8"))
    assert [d["id"] for d in coverage["datasets"]] == [NEWER_ID]
    # el estado actual va repartido en un fichero por línea
    lines = [json.loads(p.read_text(encoding="utf-8")) for p in (tmp_path / "lines").glob("*.json")]
    assert {d["date"] for d in lines} == {REFERENCE.isoformat()}
    current = {
        "date": REFERENCE.isoformat(),
        "counts": {k: v for d in lines for k, v in d["counts"].items()},
    }
    history = {
        p.parent.name: json.loads(p.read_text(encoding="utf-8"))
        for p in (tmp_path / "historico").glob("*/segment-counts.json")
    }
    assert set(history) == {FEED_DATASET_ID, NEWER_ID}
    assert history[FEED_DATASET_ID]["counts"] == two_datasets["before"]
    assert history[NEWER_ID]["counts"] == current["counts"]
    assert history[NEWER_ID]["date"] == current["date"] == REFERENCE.isoformat()
    # y, por tramo y por nodo, los trenes de cada conjunto: lo que compara la ficha
    by_segment = json.loads(
        (
            tmp_path
            / "historico"
            / "segments"
            / f"{two_datasets['segment_id']}.json".replace(":", "--")
        ).read_text(encoding="utf-8")
    )
    assert by_segment["id"] == two_datasets["segment_id"]
    assert [(p["dataset_id"], p["date"]) for p in by_segment["points"]] == [
        (FEED_DATASET_ID, REFERENCE.isoformat()),
        (NEWER_ID, REFERENCE.isoformat()),
    ]
    first, second = (p["trains"] for p in by_segment["points"])
    assert second == first - 1
    # un conjunto que deja de estar declarado se retira, también de la instantánea
    result = await run(both[:1], tmp_path)
    assert result["datasets_removed"] == [NEWER_ID]
    assert await conn.fetchval("SELECT count(*) FROM services") == 814
    assert sorted(p.name for p in (tmp_path / "historico").iterdir()) == sorted(
        [FEED_DATASET_ID, "nodes", "segments"]
    )
    by_segment = json.loads(
        (
            tmp_path
            / "historico"
            / "segments"
            / f"{two_datasets['segment_id']}.json".replace(":", "--")
        ).read_text(encoding="utf-8")
    )
    assert [p["dataset_id"] for p in by_segment["points"]] == [FEED_DATASET_ID]
