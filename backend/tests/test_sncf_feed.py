"""Los TGV oficiales: extracto reproducible, calendarios, límites y ausencia de duplicados."""

from __future__ import annotations

import datetime as dt
import hashlib
import zipfile
from collections import Counter
from pathlib import Path

import pytest
from conftest import DATA_DIR, SOURCES, SPECS, database_url_for_tests, requires_db

from oniel.gtfs.reader import GtfsFeed, read_feed
from oniel.gtfs.sncf_extract import extract, rows
from oniel.gtfs.trips import select_trips_for_spec
from oniel.network.spec import FeedSpec, load_feeds, load_network_spec

SNAPSHOT = DATA_DIR / "raw/sncf/gtfs_sncf_paris_espagne_2026-11-26.zip"
DAY = dt.date(2026, 11, 26)
NUMBERS = {"9706", "9708", "9713", "9715"}


@pytest.fixture(scope="module")
def declared() -> FeedSpec:
    return next(f for f in load_feeds(SOURCES) if f.file == str(SNAPSHOT.relative_to(DATA_DIR)))


@pytest.fixture(scope="module")
def sncf(declared: FeedSpec) -> GtfsFeed:
    return read_feed(
        SNAPSHOT,
        stop_id_prefix=declared.stop_id_prefix,
        stop_id_aliases=declared.stop_id_aliases,
        train_number_field=declared.train_number_field,
    )


def test_calendarios_numeros_y_restricciones_del_original(
    sncf: GtfsFeed, declared: FeedSpec
) -> None:
    """Las 63 variantes representan cuatro trenes el 26/11, sin inventar servicio nacional."""
    assert sncf.agency_name == "SNCF VOYAGEURS"
    assert (sncf.feed_start, sncf.feed_end) == (dt.date(2026, 11, 25), dt.date(2027, 4, 30))
    assert len(sncf.trips) == 63 and sncf.merged_train_numbers == 0
    assert declared.product == "TGV" and not declared.names_stops
    assert declared.train_number_field == "trip_headsign"
    days = Counter(
        (t.train_number, d) for t in sncf.trips.values() for d in sncf.service_dates[t.service_id]
    )
    assert len(days) == 614 and set(days.values()) == {1}
    current = [t for t in sncf.trips.values() if DAY in sncf.service_dates[t.service_id]]
    assert {t.train_number for t in current} == NUMBERS
    for trip in current:
        spanish = [s for s in trip.stop_times if s.stop_id in {"71801", "79300", "04307"}]
        assert len(spanish) == 3
        towards_france = trip.stop_times[0].stop_id == "71801"
        assert {(s.pickup_type, s.drop_off_type) for s in spanish} == (
            {(0, 1)} if towards_france else {(1, 0)}
        )
    # No se adivina el número comercial a partir de cualquier destino de otro proveedor.
    plain = read_feed(SNAPSHOT)
    assert all(t.train_number == t.trip_id for t in plain.trips.values())


def test_solo_entran_en_la_alta_velocidad_hasta_el_limite(sncf: GtfsFeed) -> None:
    """Ningún TGV se suma a la línea convencional ni crea líneas o estaciones francesas."""
    selected = {}
    for path in SPECS:
        spec = load_network_spec(path)
        trips = select_trips_for_spec(sncf, spec)
        if not trips:
            continue
        selected[spec.line.id] = len(trips)
        for trip in trips:
            for stop in trip.stop_times:
                mapping = spec.stop_mappings[stop.stop_id]
                if stop.stop_id.startswith("87"):
                    assert mapping.node is None and mapping.exits == [
                        "limite-seccion-internacional"
                    ]
                    assert not mapping.via
    assert selected == {"lav-barcelona-figueres": 63}


def test_extracto_conserva_referencias_y_es_reproducible(tmp_path: Path) -> None:
    """Filtra otra ruta sin perder padres, excepciones ni metadatos de la que permanece."""
    original = tmp_path / "original.zip"
    with zipfile.ZipFile(SNAPSHOT) as source, zipfile.ZipFile(original, "w") as target:
        for name in source.namelist():
            data = source.read(name)
            if name == "routes.txt":
                data += b"otra,1187,,Otra ruta,,2,,,\n"
            target.writestr(name, data)
    provenance = {"sha256": hashlib.sha256(original.read_bytes()).hexdigest()}
    out = tmp_path / "extracto.zip"
    manifest = extract(original, out, provenance)
    assert out.read_bytes() == SNAPSHOT.read_bytes()
    assert manifest["extract"]["size_bytes"] < 10_000
    with zipfile.ZipFile(out) as archive:
        tables = {n: list(rows(archive, n)) for n in archive.namelist()}
    stops = {s["stop_id"] for s in tables["stops.txt"]}
    assert len(stops) == 28
    assert all(not s["parent_station"] or s["parent_station"] in stops for s in tables["stops.txt"])
    assert all(s["stop_id"] in stops for s in tables["stop_times.txt"])
    services = {s["service_id"] for s in tables["calendar_dates.txt"]}
    assert all(t["service_id"] in services for t in tables["trips.txt"])
    assert "calendar.txt" not in tables
    assert tables["transfers.txt"] == [] and len(tables["feed_info.txt"]) == 1
    # Un cambio de esquema del productor necesita revisión, no una pérdida silenciosa.
    with zipfile.ZipFile(original, "a") as archive:
        archive.writestr("fare_rules.txt", "fare_id,route_id\nnueva,otra\n")
    provenance["sha256"] = hashlib.sha256(original.read_bytes()).hexdigest()
    with pytest.raises(ValueError, match="Tablas que requieren revisión"):
        extract(original, out, provenance)
    with pytest.raises(ValueError, match="huella"):
        extract(original, out, {"sha256": "incorrecta"})


@requires_db
async def test_importacion_repetida_fichas_y_destinos(declared: FeedSpec) -> None:
    """La misma fuente se importa dos veces y conserva cuatro trenes en cada estación y tramo."""
    from oniel.db.migrate import drop_everything, migrate
    from oniel.db.pool import connect
    from oniel.gtfs.importer import import_gtfs
    from oniel.network.importer import import_network
    from oniel.repo.services_repo import calls_at_node, destinations_from_node, passes_on_segment

    dsn = database_url_for_tests()
    assert dsn is not None
    async with connect(dsn) as conn:
        await drop_everything(conn)
        await migrate(conn)
        for spec in SPECS:
            await import_network(conn, spec, SOURCES, DATA_DIR)
        for _ in range(2):
            result = await import_gtfs(
                conn,
                SNAPSHOT,
                SPECS,
                source_id=declared.source_id,
                operator_id=declared.operator_id,
                retrieved_on=declared.retrieved_on,
                data_dir=DATA_DIR,
                product=declared.product,
                stop_id_prefix=declared.stop_id_prefix,
                stop_id_aliases=declared.stop_id_aliases,
                names_stops=declared.names_stops,
                train_number_field=declared.train_number_field,
            )
            assert result["trips_imported"] == 63
        assert await conn.fetchval("SELECT count(*) FROM datasets") == 1
        assert await conn.fetchval("SELECT count(*) FROM services") == 63
        assert await conn.fetchval("SELECT count(*) FROM service_dates") == 614
        for node in ("barcelona-sants", "girona", "figueres-vilafant"):
            calls = await calls_at_node(conn, node, DAY)
            assert len(calls) == 4
            assert {c["train_number"] for c in calls} == NUMBERS
            assert all(c["operator_id"] == "sncf" and c["product"] == "TGV" for c in calls)
            destinations = await destinations_from_node(conn, node, DAY)
            assert destinations
            # Restricción comercial del GTFS: los TGV no venden trayectos entre estas estaciones.
            assert all(
                d.node_id not in {"barcelona-sants", "girona", "figueres-vilafant"}
                for d in destinations
            )
        segments = await conn.fetch(
            "SELECT id FROM segments WHERE line_id = 'lav-barcelona-figueres'"
        )
        assert len(segments) == 7
        for segment in segments:
            passes = await passes_on_segment(conn, segment["id"], DAY)
            assert len(passes) == 4
            assert {p.service.train_number for p in passes} == NUMBERS
        assert (
            await conn.fetchval(
                "SELECT count(*) FROM service_segment_passes p JOIN segments s ON s.id=p.segment_id WHERE s.line_id <> 'lav-barcelona-figueres'"
            )
            == 0
        )
