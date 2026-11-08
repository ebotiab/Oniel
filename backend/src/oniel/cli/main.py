"""oniel-data: importación, validación y exportación de datos. Separada de la API."""

from __future__ import annotations

import asyncio
import datetime as dt
import json
from collections.abc import Awaitable, Callable
from pathlib import Path
from typing import Annotated, Any

import logfire
import typer

from oniel.db.pool import connect
from oniel.observability import configure_logfire
from oniel.settings import get_settings

app = typer.Typer(
    help="Datos de Oniel: base de datos, importaciones, validación y exportación.",
    no_args_is_help=True,
)
db_app = typer.Typer(help="Esquema de la base de datos.", no_args_is_help=True)
import_app = typer.Typer(help="Importaciones repetibles.", no_args_is_help=True)
export_app = typer.Typer(help="Exportaciones.", no_args_is_help=True)
app.add_typer(db_app, name="db")
app.add_typer(import_app, name="import")
app.add_typer(export_app, name="export")

settings = get_settings()
SPEC_DEFAULT = settings.data_dir / "curated" / "lav-madrid-sevilla.json"
SOURCES_DEFAULT = settings.data_dir / "curated" / "sources.json"
FEED_DEFAULT = settings.data_dir / "raw" / "renfe" / "google_transit_av_ld_md_2026-11-08.zip"


def _run(fn: Callable[..., Awaitable[Any]], *args: Any, **kwargs: Any) -> Any:
    configure_logfire("oniel-data", settings)
    return asyncio.run(fn(*args, **kwargs))


def _echo_json(payload: Any) -> None:
    typer.echo(json.dumps(payload, ensure_ascii=False, indent=2, default=str))


@db_app.command("migrate")
def db_migrate() -> None:
    """Aplica las migraciones pendientes."""
    from oniel.db.migrate import migrate

    async def go() -> list[str]:
        async with connect(settings.database_url) as conn:
            return await migrate(conn)

    applied = _run(go)
    typer.echo(f"Migraciones aplicadas: {applied or 'ninguna (al día)'}")


@db_app.command("reset")
def db_reset(
    yes: Annotated[bool, typer.Option("--yes", help="No pedir confirmación")] = False,
) -> None:
    """Borra todo el esquema y vuelve a migrar (solo desarrollo)."""
    from oniel.db.migrate import drop_everything, migrate

    if not yes:
        typer.confirm(
            f"Esto borra todas las tablas de {settings.database_url}. ¿Seguir?", abort=True
        )

    async def go() -> list[str]:
        async with connect(settings.database_url) as conn:
            await drop_everything(conn)
            return await migrate(conn)

    typer.echo(f"Esquema recreado; migraciones: {_run(go)}")


@import_app.command("network")
def import_network_cmd(
    spec: Annotated[Path, typer.Option(help="Especificación curada de la línea")] = SPEC_DEFAULT,
    sources: Annotated[Path, typer.Option(help="Registro de fuentes")] = SOURCES_DEFAULT,
) -> None:
    """Importa (o reimporta) la red de una línea."""
    from oniel.network.importer import import_network

    async def go() -> dict[str, Any]:
        async with connect(settings.database_url) as conn:
            return await import_network(conn, spec, sources, settings.data_dir)

    _echo_json(_run(go))


@import_app.command("gtfs")
def import_gtfs_cmd(
    feed: Annotated[Path, typer.Option(help="Fichero GTFS (zip)")] = FEED_DEFAULT,
    spec: Annotated[Path, typer.Option(help="Especificación curada de la línea")] = SPEC_DEFAULT,
    source_id: Annotated[
        str, typer.Option(help="Id de la fuente en sources.json")
    ] = "renfe-gtfs-av-ld-md",
    operator_id: Annotated[str, typer.Option(help="Id del operador")] = "renfe",
) -> None:
    """Importa (o reimporta) los servicios que recorren la línea."""
    from oniel.gtfs.importer import import_gtfs

    async def go() -> dict[str, Any]:
        async with connect(settings.database_url) as conn:
            return await import_gtfs(conn, feed, spec, source_id=source_id, operator_id=operator_id)

    _echo_json(_run(go))


@import_app.command("all")
def import_all_cmd() -> None:
    """Migra, importa la red y los horarios y exporta la instantánea estática."""
    from oniel.db.migrate import migrate
    from oniel.export.snapshot import export_snapshot
    from oniel.gtfs.importer import import_gtfs
    from oniel.network.importer import import_network

    async def go() -> dict[str, Any]:
        async with connect(settings.database_url) as conn:
            migrations = await migrate(conn)
            net = await import_network(conn, SPEC_DEFAULT, SOURCES_DEFAULT, settings.data_dir)
            gtfs = await import_gtfs(
                conn,
                FEED_DEFAULT,
                SPEC_DEFAULT,
                source_id="renfe-gtfs-av-ld-md",
                operator_id="renfe",
            )
            snap = await export_snapshot(
                conn, settings.data_dir.parent.parent / "frontend" / "public" / "data"
            )
            return {"migrations": migrations, "network": net, "gtfs": gtfs, "snapshot": snap}

    _echo_json(_run(go))


@app.command("validate")
def validate_cmd(
    spec: Annotated[Path, typer.Option()] = SPEC_DEFAULT,
    feed: Annotated[Path, typer.Option()] = FEED_DEFAULT,
) -> None:
    """Comprueba la red construida y la resolución de los horarios sin tocar la base de datos."""
    from oniel.validate import validate_all

    report = validate_all(spec, feed, settings.data_dir)
    _echo_json(report)
    if report["problems"]:
        raise typer.Exit(code=1)


@export_app.command("snapshot")
def export_snapshot_cmd(
    out: Annotated[Path, typer.Option(help="Carpeta de salida")] = settings.data_dir.parent.parent
    / "frontend"
    / "public"
    / "data",
    date: Annotated[str | None, typer.Option(help="Día de servicio (AAAA-MM-DD)")] = None,
) -> None:
    """Exporta red y servicios a JSON estático para el visor."""
    from oniel.export.snapshot import export_snapshot

    async def go() -> dict[str, Any]:
        async with connect(settings.database_url) as conn:
            return await export_snapshot(conn, out, dt.date.fromisoformat(date) if date else None)

    _echo_json(_run(go))


@app.command("sources")
def sources_cmd() -> None:
    """Lista las fuentes registradas con licencia y fecha."""
    from oniel.network.spec import load_sources

    for s in load_sources(SOURCES_DEFAULT):
        typer.echo(
            f"- {s.id}: {s.name}\n    {s.publisher} · {s.license} · {s.retrieved_on}\n    {s.url}"
        )


@app.command("logfire-test")
def logfire_test_cmd() -> None:
    """Envía una traza de prueba a Logfire (si hay token)."""
    configure_logfire("oniel-data", settings)
    with logfire.span("oniel logfire test"):
        logfire.info("Traza de prueba desde oniel-data", environment=settings.environment)
    logfire.force_flush()
    typer.echo("Traza enviada (si había token configurado).")


if __name__ == "__main__":
    app()
