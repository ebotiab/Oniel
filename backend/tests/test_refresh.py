"""Refresco de un fichero de horarios: qué se declara cuando el publicado cambia y qué no se toca."""

from __future__ import annotations

import datetime as dt
import json
import shutil
import zipfile
from pathlib import Path

import pytest
from conftest import (
    DATA_DIR,
    FEED,
    FEED_DATASET_ID,
    FEED_SOURCE_ID,
    OUIGO_DATASET_ID,
    OUIGO_FEED,
    OUIGO_SOURCE_ID,
    SOURCES,
    SPECS,
)

from oniel.gtfs.reader import GtfsFeed
from oniel.gtfs.refresh import (
    RefreshResult,
    ckan_package_api,
    content_sha256,
    expiring_feeds,
    gtfs_resource_url,
    pr_body,
    refresh_source,
    spanish_range,
    update_docs,
)
from oniel.gtfs.trips import select_trips_for_spec
from oniel.network.spec import NetworkSpec, load_feeds, load_sources

DOCS = DATA_DIR.parents[1] / "docs" / "datos.md"
TODAY = dt.date(2026, 11, 20)


@pytest.fixture
def data_dir(tmp_path: Path) -> Path:
    """Copia de ``data/`` con el registro de fuentes y los dos ficheros fijos de las pruebas."""
    raw = json.loads(SOURCES.read_text(encoding="utf-8"))
    fixed = {FEED.relative_to(DATA_DIR).as_posix(), OUIGO_FEED.relative_to(DATA_DIR).as_posix()}
    raw["feeds"] = [f for f in raw["feeds"] if f["file"] in fixed]
    for source in raw["sources"]:
        if source["id"] == FEED_SOURCE_ID:
            source["file"] = FEED.relative_to(DATA_DIR).as_posix()
    (tmp_path / "curated").mkdir()
    (tmp_path / "curated" / "sources.json").write_text(
        json.dumps(raw, ensure_ascii=False, indent=2) + "\n", encoding="utf-8"
    )
    for feed in (FEED, OUIGO_FEED):
        target = tmp_path / feed.relative_to(DATA_DIR)
        target.parent.mkdir(parents=True)
        shutil.copyfile(feed, target)
    return tmp_path


def republished(
    source: Path,
    target: Path,
    *,
    drop_last_trip: bool = False,
    drop_trip_id: str | None = None,
    extra_file: bool = False,
) -> Path:
    """Un GTFS vuelto a empaquetar: otros bytes y, si se le quita un viaje, otro horario."""
    with zipfile.ZipFile(source) as src, zipfile.ZipFile(target, "w", zipfile.ZIP_DEFLATED) as out:
        for info in src.infolist():
            data = src.read(info.filename)
            if info.filename == "trips.txt":
                rows = data.splitlines(keepends=True)
                if drop_last_trip:
                    rows = rows[:-1]
                if drop_trip_id is not None:
                    kept = [r for r in rows if drop_trip_id.encode() not in r]
                    assert len(kept) == len(rows) - 1
                    rows = kept
                data = b"".join(rows)
            out.writestr(info.filename, data)
        if extra_file:
            out.writestr("feed_info.txt", "feed_publisher_name\nRenfe\n")
        out.comment = b"publicado otra vez"
    return target


def another_timetable(source: Path, target: Path) -> Path:
    return republished(source, target, drop_last_trip=True)


def test_dates_read_like_the_registry() -> None:
    assert spanish_range(dt.date(2026, 11, 7), dt.date(2027, 9, 29)) == (
        "del 7 de noviembre de 2026 al 29 de septiembre de 2027"
    )
    assert spanish_range(dt.date(2026, 6, 26), dt.date(2026, 12, 12)) == (
        "del 26 de junio al 12 de diciembre de 2026"
    )


def test_the_registered_page_leads_to_the_published_file() -> None:
    renfe = next(s for s in load_sources(SOURCES) if s.id == FEED_SOURCE_ID)
    assert renfe.url is not None
    assert ckan_package_api(renfe.url) == (
        "https://data.renfe.com/api/3/action/package_show"
        "?id=horarios-de-alta-velocidad-larga-distancia-y-media-distancia"
    )
    # el Punto de Acceso Nacional no es un portal CKAN y exige sesión: se descarga a mano
    ouigo = next(s for s in load_sources(SOURCES) if s.id == OUIGO_SOURCE_ID)
    assert ouigo.url is not None
    assert ckan_package_api(ouigo.url) is None
    package = {"result": {"resources": [{"format": "GTFS", "url": "https://example.org/g.zip"}]}}
    assert gtfs_resource_url(package) == "https://example.org/g.zip"
    with pytest.raises(ValueError, match="hay 0"):
        gtfs_resource_url({"result": {"resources": [{"format": "PDF", "url": "x.pdf"}]}})


def test_the_same_timetable_changes_nothing(data_dir: Path, tmp_path: Path) -> None:
    sources = data_dir / "curated" / "sources.json"
    before = sources.read_text(encoding="utf-8")
    # Renfe sirve el mismo horario en zips distintos según el servidor que responda: lo que
    # cuenta es el contenido, no los bytes del zip
    same = republished(OUIGO_FEED, tmp_path / "descarga.zip")
    assert same.read_bytes() != OUIGO_FEED.read_bytes()
    assert content_sha256(same) == content_sha256(OUIGO_FEED)
    result = refresh_source(
        same, source_id=OUIGO_SOURCE_ID, sources_path=sources, data_dir=data_dir, today=TODAY
    )
    assert not result.changed
    assert result.previous_dataset_id == OUIGO_DATASET_ID
    assert sources.read_text(encoding="utf-8") == before
    assert sorted(p.name for p in (data_dir / "raw" / "ouigo").iterdir()) == [OUIGO_FEED.name]


def test_a_new_file_is_saved_and_declared_after_the_previous_one(
    data_dir: Path, tmp_path: Path
) -> None:
    sources = data_dir / "curated" / "sources.json"
    new = another_timetable(OUIGO_FEED, tmp_path / "descarga.zip")
    result = refresh_source(
        new, source_id=OUIGO_SOURCE_ID, sources_path=sources, data_dir=data_dir, today=TODAY
    )
    assert result.changed
    assert result.file == "raw/ouigo/gtfs_ouigo_2026-11-20.zip"
    assert result.dataset_id == "ouigo-gtfs-nap-2026-11-20"
    assert (result.valid_from, result.valid_to) == ("2026-06-26", "2026-12-12")
    assert (data_dir / result.file).read_bytes() == new.read_bytes()
    # el anterior sigue declarado y el nuevo va detrás, con las mismas opciones de lectura
    ouigo = [f for f in load_feeds(sources) if f.source_id == OUIGO_SOURCE_ID]
    assert [f.file for f in ouigo] == ["raw/ouigo/gtfs_ouigo_2026-11-12.zip", result.file]
    assert (ouigo[-1].product, ouigo[-1].stop_id_prefix) == (ouigo[0].product, "0071")
    source = next(s for s in load_sources(sources) if s.id == OUIGO_SOURCE_ID)
    assert (source.file, source.retrieved_on) == (result.file, "2026-11-20")
    assert "Validez del fichero del 26 de junio al 12 de diciembre de 2026." in (
        source.coverage or ""
    )
    # sus notas no dicen «Fichero … publicado el …»: no se tocan y se avisa a quien revise
    assert any("`notes`" in item for item in result.pending)
    # las demás fuentes y ficheros quedan como estaban
    renfe = [f for f in load_feeds(sources) if f.source_id == FEED_SOURCE_ID]
    assert [f.file for f in renfe] == [FEED.relative_to(DATA_DIR).as_posix()]
    # y descargarlo otra vez ya no cambia nada
    again = refresh_source(
        new,
        source_id=OUIGO_SOURCE_ID,
        sources_path=sources,
        data_dir=data_dir,
        today=TODAY + dt.timedelta(days=7),
    )
    assert not again.changed


def test_the_source_says_when_the_new_file_is_from_and_what_it_covers(
    data_dir: Path, tmp_path: Path
) -> None:
    sources = data_dir / "curated" / "sources.json"
    result = refresh_source(
        another_timetable(FEED, tmp_path / "descarga.zip"),
        source_id=FEED_SOURCE_ID,
        sources_path=sources,
        data_dir=data_dir,
        today=TODAY,
        published_on=dt.date(2026, 11, 19),
    )
    assert result.changed and result.pending == []
    assert result.file == "raw/renfe/google_transit_av_ld_md_2026-11-20.zip"
    source = next(s for s in load_sources(sources) if s.id == FEED_SOURCE_ID)
    assert "Validez del fichero del 7 de noviembre de 2026 al 29 de septiembre de 2027." in (
        source.coverage or ""
    )
    assert (source.notes or "").startswith(
        "Fichero google_transit.zip publicado el 19 de noviembre de 2026. Son horarios planificados"
    )


def test_another_file_with_the_same_trains_waits_until_the_loaded_one_is_old(
    data_dir: Path, tmp_path: Path
) -> None:
    sources = data_dir / "curated" / "sources.json"
    before = sources.read_text(encoding="utf-8")
    # otro contenido (un fichero más en el zip), los mismos trenes en las líneas cargadas
    other = republished(FEED, tmp_path / "descarga.zip", extra_file=True)
    assert content_sha256(other) != content_sha256(FEED)

    def refresh(today: dt.date) -> RefreshResult:
        return refresh_source(
            other,
            source_id=FEED_SOURCE_ID,
            sources_path=sources,
            data_dir=data_dir,
            today=today,
            spec_paths=SPECS,
        )

    young = refresh(dt.date(2026, 12, 5))
    assert (young.changed, young.reason) == (False, "mismos_trenes")
    assert (young.train_days_changed, young.previous_age_days) == (0, 27)
    assert sources.read_text(encoding="utf-8") == before
    assert sorted(p.name for p in (data_dir / "raw" / "renfe").iterdir()) == [FEED.name]
    # a los 28 días se releva aunque no cambie ningún tren: el día de referencia no se queda atrás
    old = refresh(dt.date(2026, 12, 6))
    assert (old.changed, old.reason, old.train_days_changed) == (True, "antiguedad", 0)
    assert old.file == "raw/renfe/google_transit_av_ld_md_2026-12-06.zip"


def test_a_train_that_changes_in_the_coming_weeks_opens_the_refresh(
    data_dir: Path, tmp_path: Path, feed: GtfsFeed, spec: NetworkSpec
) -> None:
    def runs_on(trip_service: str, start: dt.date, days: int) -> int:
        end = start + dt.timedelta(days=days)
        return sum(start <= d < end for d in feed.service_dates[trip_service])

    # un tren de la alta velocidad que circula un solo día de las cuatro semanas que se comparan
    trip = next(
        t for t in select_trips_for_spec(feed, spec) if runs_on(t.service_id, TODAY, 28) == 1
    )
    result = refresh_source(
        republished(FEED, tmp_path / "descarga.zip", drop_trip_id=trip.trip_id),
        source_id=FEED_SOURCE_ID,
        sources_path=data_dir / "curated" / "sources.json",
        data_dir=data_dir,
        today=TODAY,
        spec_paths=SPECS,
    )
    assert (result.changed, result.reason, result.train_days_changed) == (True, "trenes", 1)
    assert (result.window_days, result.previous_age_days) == (28, 12)


def test_one_file_per_source_and_day(data_dir: Path, tmp_path: Path) -> None:
    with pytest.raises(ValueError, match="un fichero por fuente y día"):
        refresh_source(
            another_timetable(OUIGO_FEED, tmp_path / "descarga.zip"),
            source_id=OUIGO_SOURCE_ID,
            sources_path=data_dir / "curated" / "sources.json",
            data_dir=data_dir,
            today=dt.date(2026, 11, 12),
        )


def test_a_file_that_is_not_a_timetable_is_not_declared(data_dir: Path, tmp_path: Path) -> None:
    sources = data_dir / "curated" / "sources.json"
    before = sources.read_text(encoding="utf-8")
    broken = tmp_path / "descarga.zip"
    broken.write_bytes(b"<html>Servicio no disponible</html>")
    with pytest.raises(zipfile.BadZipFile):
        refresh_source(
            broken, source_id=OUIGO_SOURCE_ID, sources_path=sources, data_dir=data_dir, today=TODAY
        )
    assert sources.read_text(encoding="utf-8") == before
    assert sorted(p.name for p in (data_dir / "raw" / "ouigo").iterdir()) == [OUIGO_FEED.name]


def test_the_tables_of_the_documentation_follow(tmp_path: Path) -> None:
    docs = tmp_path / "datos.md"
    shutil.copyfile(DOCS, docs)
    pending = update_docs(
        docs,
        source_id=FEED_SOURCE_ID,
        dataset_id="renfe-gtfs-av-ld-md-2026-11-20",
        previous_dataset_id=FEED_DATASET_ID,
        retrieved_on=TODAY,
        valid=(dt.date(2026, 11, 19), dt.date(2027, 9, 29)),
    )
    assert pending == []
    lines = docs.read_text(encoding="utf-8").split("\n")
    source_row = next(x for x in lines if x.startswith(f"| `{FEED_SOURCE_ID}` |"))
    assert source_row.endswith("| CC BY 4.0 | 2026-11-20 |")
    previous = next(i for i, x in enumerate(lines) if x.startswith(f"| `{FEED_DATASET_ID}` |"))
    assert lines[previous + 1] == (
        "| `renfe-gtfs-av-ld-md-2026-11-20` | `renfe-gtfs-av-ld-md` | Renfe | 2026-11-20"
        " | del 19 de noviembre de 2026 al 29 de septiembre de 2027 |"
    )
    assert len(lines) == len(DOCS.read_text(encoding="utf-8").split("\n")) + 1
    # una fila que falta no rompe nada: queda anotada para quien revise
    assert (
        len(
            update_docs(
                docs,
                source_id="otra-fuente",
                dataset_id="otra-fuente-2026-11-20",
                previous_dataset_id="otra-fuente-2026-11-01",
                retrieved_on=TODAY,
                valid=(TODAY, TODAY),
            )
        )
        == 2
    )


def test_manual_sources_are_remembered_before_they_expire(data_dir: Path) -> None:
    sources = data_dir / "curated" / "sources.json"
    automatic = frozenset({FEED_SOURCE_ID})

    def expiring(today: dt.date) -> list[str]:
        found = expiring_feeds(sources, data_dir, today=today, days=21, exclude=automatic)
        return [f"{f['source_id']}:{f['days_left']}" for f in found]

    # el fichero de Ouigo vale hasta el 12 de diciembre de 2026
    assert expiring(dt.date(2026, 11, 20)) == []
    assert expiring(dt.date(2026, 11, 21)) == ["ouigo-gtfs-nap:21"]
    assert expiring(dt.date(2026, 12, 20)) == ["ouigo-gtfs-nap:-8"]


def test_the_pull_request_says_what_changed(tmp_path: Path) -> None:
    def gtfs(dataset: str, trips: int, lav: int) -> dict[str, object]:
        return {
            "dataset": {"id": dataset, "sha256": f"zip-de-{dataset}"},
            "trips_in_feed": 6000,
            "trips_imported": trips,
            "unmapped_stops": {},
            "lines": {"lav-madrid-sevilla": {"trips": lav}},
        }

    new_id = "renfe-gtfs-av-ld-md-2026-11-20"
    for dataset, count in ((FEED_DATASET_ID, 96), (new_id, 94)):
        folder = tmp_path / "historico" / dataset
        folder.mkdir(parents=True)
        (folder / "segment-counts.json").write_text(
            json.dumps({"date": "2026-11-13", "counts": {"lav:a:b": count, "lav:b:c": 40}}),
            encoding="utf-8",
        )
    body = pr_body(
        {
            "source_id": FEED_SOURCE_ID,
            "sha256": f"zip-de-{new_id}",
            "content_sha256": "d22a9f9df253b6ca80d5",
            "file": "raw/renfe/google_transit_av_ld_md_2026-11-20.zip",
            "dataset_id": new_id,
            "previous_dataset_id": FEED_DATASET_ID,
            "retrieved_on": "2026-11-20",
            "published_on": "2026-11-19",
            "valid_from": "2026-11-19",
            "valid_to": "2027-09-29",
            "pending": ["`notes` de la fuente"],
            "reason": "trenes",
            "train_days_changed": 54,
            "window_days": 28,
        },
        {"gtfs": [gtfs(FEED_DATASET_ID, 814, 331), gtfs(new_id, 799, 328)]},
        tmp_path,
    )
    assert "descargado el 20 de noviembre de 2026, publicado el 19 de noviembre de 2026" in body
    assert "Validez: del 19 de noviembre de 2026 al 29 de septiembre de 2027." in body
    assert "| `lav-madrid-sevilla` | 331 | 328 |" in body
    assert "| `lav:a:b` | 96 | 94 |" in body
    assert "lav:b:c" not in body
    assert "Sin actualizar, a mano: `notes` de la fuente." in body
    assert "en los próximos 28 días hay 54 trenes-día" in body
    assert "El flujo no fusiona nada." in body
