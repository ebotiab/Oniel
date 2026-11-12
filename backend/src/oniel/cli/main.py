"""oniel-data: importación, validación y exportación de datos. Separada de la API."""

from __future__ import annotations

import asyncio
import datetime as dt
import json
from collections.abc import Callable, Coroutine
from pathlib import Path
from typing import TYPE_CHECKING, Annotated, Any

import logfire
import typer

from oniel.db.pool import connect
from oniel.observability import configure_logfire
from oniel.settings import get_settings

if TYPE_CHECKING:
    from oniel.network.spec import FeedSpec

app = typer.Typer(
    help="Datos de Oniel: base de datos, importaciones, validación y exportación.",
    no_args_is_help=True,
)
db_app = typer.Typer(help="Esquema de la base de datos.", no_args_is_help=True)
import_app = typer.Typer(help="Importaciones repetibles.", no_args_is_help=True)
export_app = typer.Typer(help="Exportaciones.", no_args_is_help=True)
refresh_app = typer.Typer(help="Refresco de los ficheros de horarios.", no_args_is_help=True)
app.add_typer(db_app, name="db")
app.add_typer(import_app, name="import")
app.add_typer(export_app, name="export")
app.add_typer(refresh_app, name="refresh")

settings = get_settings()
CURATED = settings.data_dir / "curated"
#: Líneas cargadas, en el orden en que se importan (la primera define los nodos compartidos).
SPECS_DEFAULT = [CURATED / f"{line_id}.json" for line_id in settings.line_ids]
SOURCES_DEFAULT = CURATED / "sources.json"
ANNOTATIONS_DEFAULT = CURATED / "anotaciones.json"
SNAPSHOT_DEFAULT = settings.data_dir.parent.parent / "frontend" / "public" / "data"
DOCS_DEFAULT = settings.data_dir.parent.parent / "docs" / "datos.md"
#: Fuente de horarios que `refresh gtfs` sabe descargar sin sesión iniciada.
REFRESH_SOURCE_DEFAULT = "renfe-gtfs-av-ld-md"

SpecsOption = Annotated[
    list[Path] | None,
    typer.Option(
        "--spec", help="Especificación curada de una línea (repetible); por defecto, todas"
    ),
]


def _run[T](fn: Callable[..., Coroutine[Any, Any, T]], *args: Any, **kwargs: Any) -> T:
    configure_logfire("oniel-data", settings)
    return asyncio.run(fn(*args, **kwargs))


def _echo_json(payload: Any) -> None:
    typer.echo(json.dumps(payload, ensure_ascii=False, indent=2, default=str))


def _specs(spec: list[Path] | None) -> list[Path]:
    return spec or SPECS_DEFAULT


def _declared_feeds(sources: Path = SOURCES_DEFAULT) -> list[FeedSpec]:
    """Ficheros de horarios declarados en sources.json (clave ``feeds``), del más antiguo al más reciente."""
    from oniel.network.spec import load_feeds

    return load_feeds(sources)


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
    spec: SpecsOption = None,
    sources: Annotated[Path, typer.Option(help="Registro de fuentes")] = SOURCES_DEFAULT,
) -> None:
    """Importa (o reimporta) la red de una o varias líneas."""
    from oniel.network.importer import import_network

    async def go() -> list[dict[str, Any]]:
        async with connect(settings.database_url) as conn:
            return [
                await import_network(conn, path, sources, settings.data_dir)
                for path in _specs(spec)
            ]

    _echo_json(_run(go))


@import_app.command("annotations")
def import_annotations_cmd(
    file: Annotated[
        Path, typer.Option(help="Fichero curado de anotaciones de red")
    ] = ANNOTATIONS_DEFAULT,
    sources: Annotated[Path, typer.Option(help="Registro de fuentes")] = SOURCES_DEFAULT,
) -> None:
    """Importa (o reimporta) las anotaciones de red (interrupciones del servicio); la red tiene que estar cargada."""
    from oniel.network.annotations import import_annotations

    async def go() -> dict[str, Any]:
        async with connect(settings.database_url) as conn:
            return await import_annotations(conn, file, sources, settings.data_dir)

    _echo_json(_run(go))


@import_app.command("gtfs")
def import_gtfs_cmd(
    feed: Annotated[
        Path | None,
        typer.Option(help="Fichero GTFS (zip); por defecto, todos los declarados en sources.json"),
    ] = None,
    spec: SpecsOption = None,
    source_id: Annotated[
        str, typer.Option(help="Id de la fuente en sources.json (con --feed)")
    ] = "renfe-gtfs-av-ld-md",
    operator_id: Annotated[str, typer.Option(help="Id del operador (con --feed)")] = "renfe",
    retrieved_on: Annotated[
        str | None,
        typer.Option(
            help="Día de descarga, AAAA-MM-DD (con --feed); por defecto, el del nombre del fichero"
        ),
    ] = None,
) -> None:
    """Importa ficheros GTFS como conjuntos de datos: cada uno se crea o, si ya está, se rehace.

    El conjunto se reconoce por el SHA-256 del fichero, así que repetir la orden no duplica nada e
    importar un fichero nuevo conserva los anteriores.
    """
    from oniel.gtfs.importer import import_gtfs

    async def go() -> list[dict[str, Any]]:
        async with connect(settings.database_url) as conn:
            if feed is not None:
                return [
                    await import_gtfs(
                        conn,
                        feed,
                        _specs(spec),
                        source_id=source_id,
                        operator_id=operator_id,
                        retrieved_on=dt.date.fromisoformat(retrieved_on) if retrieved_on else None,
                        data_dir=settings.data_dir,
                    )
                ]
            return [
                await import_gtfs(
                    conn,
                    settings.data_dir / f.file,
                    _specs(spec),
                    source_id=f.source_id,
                    operator_id=f.operator_id,
                    retrieved_on=f.retrieved_on,
                    data_dir=settings.data_dir,
                    product=f.product,
                    stop_id_prefix=f.stop_id_prefix,
                )
                for f in _declared_feeds()
            ]

    _echo_json(_run(go))


@import_app.command("all")
def import_all_cmd(
    if_changed: Annotated[
        bool,
        typer.Option(
            "--if-changed",
            help="Saltar la importación si los datos y el código no han cambiado desde la última",
        ),
    ] = False,
) -> None:
    """Migra, importa la red, las anotaciones y cada fichero de horarios declarado y exporta la instantánea."""
    from oniel.importing import run_import_all

    async def go() -> dict[str, Any]:
        async with connect(settings.database_url) as conn:
            return await run_import_all(
                conn,
                specs=SPECS_DEFAULT,
                sources=SOURCES_DEFAULT,
                feeds=_declared_feeds(),
                data_dir=settings.data_dir,
                snapshot_dir=SNAPSHOT_DEFAULT,
                annotations=ANNOTATIONS_DEFAULT,
                if_changed=if_changed,
            )

    _echo_json(_run(go))


@app.command("validate")
def validate_cmd(
    spec: SpecsOption = None,
    feed: Annotated[
        Path | None,
        typer.Option(help="Fichero GTFS (zip); por defecto, todos los declarados en sources.json"),
    ] = None,
    annotations: Annotated[
        Path, typer.Option(help="Fichero curado de anotaciones de red")
    ] = ANNOTATIONS_DEFAULT,
    sources: Annotated[Path, typer.Option(help="Registro de fuentes")] = SOURCES_DEFAULT,
) -> None:
    """Comprueba la red, la resolución de los horarios y las anotaciones sin tocar la base de datos."""
    from oniel.validate import (
        unused_route_overrides,
        validate_all,
        validate_annotations,
        validate_attributes,
        validate_operators,
    )

    # Las demás líneas configuradas se cargan como contexto aunque solo se valide una: una
    # parada puede ser salida hacia otra línea y medir la distancia por ella.
    context = list(dict.fromkeys([*SPECS_DEFAULT, *_specs(spec)]))
    feeds: list[tuple[Path, str | None]] = (
        [(feed, None)]
        if feed
        else [(settings.data_dir / f.file, f.stop_id_prefix) for f in _declared_feeds(sources)]
    )
    # Los atributos de tramo van primero: si una línea no se puede construir por ellos, se dice
    # como problema y no se sigue con los horarios.
    attributes = validate_attributes(context, sources, settings.data_dir)
    if attributes["problems"]:
        _echo_json([attributes])
        raise typer.Exit(code=1)
    reports = [
        validate_all(
            path,
            feed_path,
            settings.data_dir,
            [p for p in context if p != path],
            stop_id_prefix=prefix,
            require_rules=False,
        )
        for feed_path, prefix in feeds
        for path in _specs(spec)
    ]
    # Cada regla de recorrido tiene que encajar con algún viaje de alguno de los ficheros.
    reports.append(
        {"route_overrides": "todos los ficheros", "problems": unused_route_overrides(reports)}
    )
    # Las anotaciones se contrastan con todas las líneas configuradas, se valide una o todas.
    reports.append(validate_annotations(annotations, sources, context, settings.data_dir))
    # Los operadores y sus ficheros de horarios también se contrastan con todas las líneas.
    reports.append(validate_operators(context, sources, settings.data_dir))
    reports.append(attributes)
    _echo_json(reports)
    if any(r["problems"] for r in reports):
        raise typer.Exit(code=1)


@export_app.command("snapshot")
def export_snapshot_cmd(
    out: Annotated[Path, typer.Option(help="Carpeta de salida")] = SNAPSHOT_DEFAULT,
    date: Annotated[str | None, typer.Option(help="Día de servicio (AAAA-MM-DD)")] = None,
) -> None:
    """Exporta red y servicios a JSON estático para el visor."""
    from oniel.export.snapshot import export_snapshot

    async def go() -> dict[str, Any]:
        async with connect(settings.database_url) as conn:
            return await export_snapshot(conn, out, dt.date.fromisoformat(date) if date else None)

    _echo_json(_run(go))


@refresh_app.command("gtfs")
def refresh_gtfs_cmd(
    source: Annotated[
        str, typer.Option(help="Fuente de sources.json que se refresca")
    ] = REFRESH_SOURCE_DEFAULT,
    file: Annotated[
        Path | None,
        typer.Option(help="Fichero ya descargado (zip); por defecto se descarga el publicado"),
    ] = None,
    date: Annotated[
        str | None, typer.Option(help="Día de descarga (AAAA-MM-DD); por defecto, hoy")
    ] = None,
    window_days: Annotated[
        int, typer.Option(help="Días, desde hoy, en los que se comparan los trenes")
    ] = 28,
    max_age_days: Annotated[
        int,
        typer.Option(
            help="Días a partir de los cuales el fichero cargado se releva aunque no cambie"
        ),
    ] = 28,
    any_change: Annotated[
        bool,
        typer.Option(
            "--any-change", help="Declararlo con que el contenido sea otro, sin comparar trenes"
        ),
    ] = False,
) -> None:
    """Descarga el fichero publicado de una fuente y, si cambian los trenes de las líneas cargadas, lo declara.

    También lo declara si los trenes son los mismos pero el fichero cargado ya es viejo.

    No toca la base de datos. Imprime qué ha hecho; si `changed` es verdadero, faltan `validate`
    e `import all`.
    """
    import tempfile

    from oniel.gtfs.refresh import download_feed, refresh_source
    from oniel.network.spec import load_sources

    today = dt.date.fromisoformat(date) if date else dt.datetime.now(dt.UTC).date()
    with tempfile.TemporaryDirectory() as tmp:
        published: dt.date | None = None
        downloaded = file
        if downloaded is None:
            url = next((s.url for s in load_sources(SOURCES_DEFAULT) if s.id == source), None)
            if url is None:
                raise typer.BadParameter(f"la fuente {source} no está registrada o no tiene URL")
            downloaded = Path(tmp) / "descarga.zip"
            published = download_feed(url, downloaded)
        result = refresh_source(
            downloaded,
            source_id=source,
            sources_path=SOURCES_DEFAULT,
            data_dir=settings.data_dir,
            today=today,
            published_on=published,
            docs_path=DOCS_DEFAULT if DOCS_DEFAULT.exists() else None,
            spec_paths=[] if any_change else SPECS_DEFAULT,
            window_days=window_days,
            max_age_days=max_age_days,
        )
    _echo_json(result.as_json())


@refresh_app.command("expiring")
def refresh_expiring_cmd(
    days: Annotated[int, typer.Option(help="Días de margen antes del fin de la validez")] = 21,
    exclude: Annotated[
        list[str] | None,
        typer.Option(help="Fuente que se refresca sola y no hay que recordar (repetible)"),
    ] = None,
    date: Annotated[str | None, typer.Option(help="Día de referencia; por defecto, hoy")] = None,
) -> None:
    """Lista los ficheros vigentes cuya validez termina pronto: los que hay que descargar a mano."""
    from oniel.gtfs.refresh import expiring_feeds

    today = dt.date.fromisoformat(date) if date else dt.datetime.now(dt.UTC).date()
    _echo_json(
        expiring_feeds(
            SOURCES_DEFAULT,
            settings.data_dir,
            today=today,
            days=days,
            exclude=frozenset(exclude or [REFRESH_SOURCE_DEFAULT]),
        )
    )


@refresh_app.command("summary")
def refresh_summary_cmd(
    result: Annotated[Path, typer.Option(help="Salida de `refresh gtfs` (JSON)")],
    report: Annotated[Path, typer.Option(help="Salida de `import all` (JSON)")],
    snapshot: Annotated[Path, typer.Option(help="Instantánea exportada")] = SNAPSHOT_DEFAULT,
) -> None:
    """Escribe la descripción de la PR de un refresco: validez, viajes por línea y pasos por tramo."""
    from oniel.gtfs.refresh import pr_body

    typer.echo(
        pr_body(
            json.loads(result.read_text(encoding="utf-8")),
            json.loads(report.read_text(encoding="utf-8")),
            snapshot,
        ),
        nl=False,
    )


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
