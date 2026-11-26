"""Extracto reproducible de Paris–España del GTFS oficial SNCF; no cambia sus filas.

Se ejecuta a mano antes de declarar un feed. Rechaza tablas desconocidas para que una
renovación no pierda referencias nuevas sin revisión. No forma parte de la importación.
"""

from __future__ import annotations

import argparse
import csv
import hashlib
import io
import json
import zipfile
from collections.abc import Callable, Iterator
from pathlib import Path
from typing import Any

ROUTE_NAME = "Paris - Espagne TGV"
REQUIRED = {"agency.txt", "routes.txt", "trips.txt", "stops.txt", "stop_times.txt"}
SUPPORTED = REQUIRED | {
    "calendar.txt",
    "calendar_dates.txt",
    "transfers.txt",
    "feed_info.txt",
    "shapes.txt",
    "frequencies.txt",
}


def rows(archive: zipfile.ZipFile, name: str) -> Iterator[dict[str, str]]:
    """Lee por filas: stop_times nacional no se retiene en memoria."""
    with archive.open(name) as raw:
        yield from csv.DictReader(io.TextIOWrapper(raw, encoding="utf-8-sig"))


def extract(original: Path, output: Path, provenance: dict[str, Any]) -> dict[str, Any]:
    """Conserva ruta, viajes completos, calendarios, paradas y referencias de las tablas."""
    original_hash = hashlib.sha256(original.read_bytes()).hexdigest()
    if provenance["sha256"] != original_hash:
        raise ValueError("La huella del original no coincide con la procedencia")
    with zipfile.ZipFile(original) as source:
        names = set(source.namelist())
        if names - SUPPORTED or REQUIRED - names:
            raise ValueError(
                f"Tablas que requieren revisión: nuevas {sorted(names - SUPPORTED)}, faltantes {sorted(REQUIRED - names)}"
            )
        if not names & {"calendar.txt", "calendar_dates.txt"}:
            raise ValueError("El original no contiene calendarios")
        routes = [r for r in rows(source, "routes.txt") if r["route_long_name"] == ROUTE_NAME]
        if len(routes) != 1:
            raise ValueError(f"Se esperaba una ruta {ROUTE_NAME!r}; hay {len(routes)}")
        route_ids = {r["route_id"] for r in routes}
        agencies = {r["agency_id"] for r in routes}
        trips = [r for r in rows(source, "trips.txt") if r["route_id"] in route_ids]
        if not trips or any(not r.get("trip_headsign", "").isdigit() for r in trips):
            raise ValueError("La ruta no tiene viajes o ha cambiado el campo del número de tren")
        trip_ids = {r["trip_id"] for r in trips}
        services = {r["service_id"] for r in trips}
        shapes = {r["shape_id"] for r in trips if r.get("shape_id")}
        times = [r for r in rows(source, "stop_times.txt") if r["trip_id"] in trip_ids]
        if {r["trip_id"] for r in times} != trip_ids:
            raise ValueError("Hay viajes sin paradas")
        stop_ids = {r["stop_id"] for r in times}
        all_stops = {r["stop_id"]: r for r in rows(source, "stops.txt")}
        # Las estaciones padre también son parte del extracto; no se asignan al grafo.
        while True:
            if stop_ids - all_stops.keys():
                raise ValueError("Hay referencias a paradas ausentes")
            parents = {
                all_stops[s]["parent_station"]
                for s in stop_ids
                if all_stops[s].get("parent_station")
            }
            if parents <= stop_ids:
                break
            stop_ids |= parents
        if shapes and "shapes.txt" not in names:
            raise ValueError("Hay geometrías referenciadas sin shapes.txt")

        selected: dict[str, list[dict[str, str]]] = {
            "routes.txt": routes,
            "trips.txt": trips,
            "stop_times.txt": times,
            "stops.txt": [r for r in all_stops.values() if r["stop_id"] in stop_ids],
        }
        filters: dict[str, Callable[[dict[str, str]], bool]] = {
            "agency.txt": lambda r: r["agency_id"] in agencies,
            "calendar.txt": lambda r: r["service_id"] in services,
            "calendar_dates.txt": lambda r: r["service_id"] in services,
            "shapes.txt": lambda r: r["shape_id"] in shapes,
            "frequencies.txt": lambda r: r["trip_id"] in trip_ids,
            "feed_info.txt": lambda r: True,
            "transfers.txt": lambda r: all(
                not r.get(field) or r[field] in ids
                for field, ids in (
                    ("from_stop_id", stop_ids),
                    ("to_stop_id", stop_ids),
                    ("from_route_id", route_ids),
                    ("to_route_id", route_ids),
                    ("from_trip_id", trip_ids),
                    ("to_trip_id", trip_ids),
                )
            ),
        }
        for name, predicate in filters.items():
            if name in names:
                selected[name] = [r for r in rows(source, name) if predicate(r)]
        calendar_services = {
            r["service_id"]
            for n in ("calendar.txt", "calendar_dates.txt")
            for r in selected.get(n, [])
        }
        if services - calendar_services:
            raise ValueError("Hay viajes sin calendario")
        if agencies != {r["agency_id"] for r in selected["agency.txt"]}:
            raise ValueError("Hay rutas sin agencia")
        if shapes != {r["shape_id"] for r in selected.get("shapes.txt", [])}:
            raise ValueError("Hay geometrías ausentes")

        # Cabeceras originales y orden estable; misma entrada produce exactamente el mismo ZIP.
        content = io.BytesIO()
        with zipfile.ZipFile(content, "w", compression=zipfile.ZIP_DEFLATED) as target:
            for name in sorted(names):
                with source.open(name) as raw:
                    fields = next(csv.reader(io.TextIOWrapper(raw, encoding="utf-8-sig")))
                text = io.StringIO(newline="")
                writer = csv.DictWriter(text, fieldnames=fields, lineterminator="\n")
                writer.writeheader()
                writer.writerows(selected[name])
                info = zipfile.ZipInfo(name, date_time=(1980, 1, 1, 0, 0, 0))
                info.compress_type = zipfile.ZIP_DEFLATED
                target.writestr(info, text.getvalue().encode("utf-8"))
        data = content.getvalue()
        output.parent.mkdir(parents=True, exist_ok=True)
        output.write_bytes(data)
        manifest = {
            "source_id": "sncf-horarios-abiertos",
            "catalogue_url": "https://transport.data.gouv.fr/datasets/horaires-sncf",
            "license": "ODbL 1.0",
            "license_url": "https://opendatacommons.org/licenses/odbl/1.0/",
            "original": provenance
            | {"uncompressed_bytes": sum(i.file_size for i in source.infolist())},
            "criterion": {
                "route_long_name": ROUTE_NAME,
                "route_ids": sorted(route_ids),
                "complete_trips": True,
                "parent_stations": True,
            },
            "script": "src/oniel/gtfs/sncf_extract.py",
            "extract": {
                "file": output.name,
                "sha256": hashlib.sha256(data).hexdigest(),
                "size_bytes": len(data),
                "rows": {n: len(r) for n, r in sorted(selected.items())},
            },
        }
        output.with_suffix(".json").write_text(
            json.dumps(manifest, ensure_ascii=False, indent=2) + "\n", encoding="utf-8"
        )
        return manifest


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--original", required=True, type=Path, help="ZIP oficial sin modificar")
    parser.add_argument(
        "--provenance", required=True, type=Path, help="JSON de descarga, fecha y SHA-256"
    )
    parser.add_argument("--output", required=True, type=Path, help="ZIP del extracto con fecha")
    args = parser.parse_args()
    manifest = extract(
        args.original, args.output, json.loads(args.provenance.read_text(encoding="utf-8"))
    )
    print(json.dumps(manifest, ensure_ascii=False, indent=2))


if __name__ == "__main__":
    main()
