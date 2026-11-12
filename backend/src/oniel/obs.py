"""Estado de producción leído de las trazas de Logfire.

`oniel-data obs estado` responde a lo que se pregunta tras fusionar en `main`: qué commit está
desplegado y desde cuándo, cómo terminó la última importación y qué errores hay desde entonces.
Solo lee: usa un token de lectura del proyecto, que vive fuera del repositorio (la variable
``LOGFIRE_READ_TOKEN`` o el fichero ``~/.config/oniel/logfire-read-token``), contra la API de
consultas SQL de Logfire. Nada de este módulo envía trazas.
"""

from __future__ import annotations

import csv
import datetime as dt
import io
import json
import os
import re
import time
from collections.abc import Callable, Mapping
from dataclasses import asdict, dataclass, field
from pathlib import Path
from typing import Any

import httpx

#: El proyecto `oniel` está en la región US de Logfire.
BASE_URL = "https://logfire-us.pydantic.dev"
BASE_URL_ENV = "LOGFIRE_BASE_URL"
TOKEN_ENV = "LOGFIRE_READ_TOKEN"
TOKEN_FILE = Path.home() / ".config" / "oniel" / "logfire-read-token"
SERVICES = ("oniel-api", "oniel-data")
#: A partir de este nivel una traza es un error; por debajo, una excepción controlada (un 4xx).
ERROR_LEVEL = 17
#: Entornos que envían trazas (`deployment_environment`): Render y quien desarrolla con credenciales.
ENVIRONMENTS = ("production", "local")
#: Valor de `--entorno` que no filtra por entorno.
ALL_ENVIRONMENTS = "todos"

NO_TOKEN_MESSAGE = (
    "Sin token de lectura de Logfire: no se puede consultar el estado de producción.\n"
    f"Se busca en la variable {TOKEN_ENV} y en {TOKEN_FILE} (docs/despliegue.md, «Logfire»)."
)

_COMMIT = re.compile(r"[0-9a-f]{7,40}")
_ENVIRONMENT = re.compile(r"[A-Za-z0-9_.-]+")

Row = dict[str, Any]


class LogfireError(Exception):
    """La API de consultas no respondió o rechazó la consulta."""


def read_token(env: Mapping[str, str] | None = None, token_file: Path = TOKEN_FILE) -> str | None:
    """Token de lectura: primero la variable de entorno, después el fichero local."""
    environ = os.environ if env is None else env
    token = environ.get(TOKEN_ENV, "").strip()
    if token:
        return token
    try:
        return token_file.read_text(encoding="utf-8").strip() or None
    except OSError:
        return None


def _utc(moment: dt.datetime) -> str:
    return moment.astimezone(dt.UTC).strftime("%Y-%m-%dT%H:%M:%S.%fZ")


def _parse(value: Any) -> dt.datetime | None:
    if not value:
        return None
    parsed = dt.datetime.fromisoformat(str(value))
    return parsed if parsed.tzinfo else parsed.replace(tzinfo=dt.UTC)


class LogfireReader:
    """Cliente mínimo de la API de consultas de Logfire (`POST /v2/query`)."""

    def __init__(
        self,
        token: str,
        *,
        base_url: str | None = None,
        transport: httpx.BaseTransport | None = None,
        timeout: float = 60.0,
    ) -> None:
        self._client = httpx.Client(
            base_url=base_url or os.environ.get(BASE_URL_ENV) or BASE_URL,
            headers={"Authorization": f"Bearer {token}", "Accept": "application/json"},
            transport=transport,
            timeout=timeout,
        )

    def close(self) -> None:
        self._client.close()

    def query(
        self,
        sql: str,
        *,
        since: dt.datetime,
        limit: int | None = None,
        environment: str | None = None,
    ) -> list[Row]:
        """Ejecuta una consulta y devuelve las filas como diccionarios.

        ``environment`` deja solo los registros de ese entorno (`deployment_environment`), sin
        tener que escribirlo en el SQL; vale para `records` y para `metrics`.
        """
        body: dict[str, Any] = {"sql": sql, "min_timestamp": _utc(since)}
        if limit is not None:
            body["limit"] = limit
        if environment is not None:
            body["deployment_environment"] = [environment]
        try:
            response = self._client.post("/v2/query", json=body)
        except httpx.HTTPError as exc:
            raise LogfireError(
                f"No se pudo conectar con Logfire ({type(exc).__name__}: {exc}). "
                "Dentro del sandbox del shell la conexión TLS se corta: hay que ejecutarlo fuera."
            ) from exc
        if response.status_code in (401, 403):
            raise LogfireError(
                f"Logfire rechazó el token de lectura ({response.status_code}); "
                "docs/despliegue.md, «Logfire», dice cómo se renueva."
            )
        if response.status_code == 429:
            raise LogfireError(
                "Logfire ha limitado las consultas con token de lectura (429); "
                f"reintentar en {response.headers.get('Retry-After', '?')} s."
            )
        if response.status_code >= 400:
            raise LogfireError(
                f"Logfire respondió {response.status_code}: {response.text.strip()[:400]}"
            )
        return rows_from_payload(response.json())


def rows_from_payload(payload: Any) -> list[Row]:
    """La API responde `{"schema": …, "data": [fila, …]}`; aquí interesan las filas."""
    data = payload.get("data", []) if isinstance(payload, dict) else []
    return [dict(row) for row in data]


def rows_to_csv(rows: list[Row]) -> str:
    if not rows:
        return ""
    out = io.StringIO()
    writer = csv.DictWriter(out, fieldnames=list(rows[0]), lineterminator="\n")
    writer.writeheader()
    writer.writerows(rows)
    return out.getvalue()


def short_version(version: str | None) -> str:
    """Un commit completo se enseña con sus siete primeros caracteres; lo demás, tal cual."""
    if version and len(version) == 40 and _COMMIT.fullmatch(version):
        return version[:7]
    return version or "desconocida"


def is_commit(version: str | None, commit: str) -> bool:
    """¿Es ``version`` el commit pedido? Admite el hash abreviado (siete caracteres o más)."""
    wanted = commit.strip().lower()
    return bool(version) and bool(_COMMIT.fullmatch(wanted)) and str(version).startswith(wanted)


@dataclass
class VersionSeen:
    service: str
    version: str
    first_seen: dt.datetime | None
    last_seen: dt.datetime | None
    records: int


@dataclass
class ImportRun:
    started: dt.datetime | None
    duration_s: float | None
    version: str | None
    outcome: str  # completed | skipped | failed | running
    detail: dict[str, Any] = field(default_factory=dict)
    error: str | None = None


@dataclass
class Status:
    environment: str
    checked_at: dt.datetime
    window_start: dt.datetime
    #: Versiones vistas en la ventana, de la más reciente a la más antigua, por servicio.
    versions: list[VersionSeen]
    api_started: dt.datetime | None
    last_import: ImportRun | None
    since: dt.datetime
    errors: list[Row]
    handled: list[Row]
    http_errors: list[Row]
    routes: list[Row]

    def current(self, service: str = "oniel-api") -> VersionSeen | None:
        return next((v for v in self.versions if v.service == service), None)

    def to_json(self) -> str:
        return json.dumps(asdict(self), ensure_ascii=False, indent=2, default=str)


def _import_run(rows: list[Row]) -> ImportRun | None:
    """La importación más reciente: su tramo si terminó, o el aviso de inicio si sigue en curso."""
    if not rows:
        return None
    latest = rows[0]
    if latest.get("kind") == "log":
        return ImportRun(
            started=_parse(latest.get("start_timestamp")),
            duration_s=None,
            version=latest.get("service_version"),
            outcome="running",
        )
    raw = latest.get("attributes") or {}
    attributes: dict[str, Any] = json.loads(raw) if isinstance(raw, str) else dict(raw)
    failed = bool(latest.get("is_exception")) or int(latest.get("level") or 0) >= ERROR_LEVEL
    error = None
    if failed:
        error = ": ".join(
            str(part)
            for part in (latest.get("exception_type"), latest.get("exception_message"))
            if part
        )
    detail = {
        key: value
        for key, value in attributes.items()
        if not key.startswith(("code.", "logfire.")) and key != "outcome"
    }
    return ImportRun(
        started=_parse(latest.get("start_timestamp")),
        duration_s=latest.get("duration"),
        version=latest.get("service_version"),
        outcome="failed" if failed else str(attributes.get("outcome") or "completed"),
        detail=detail,
        error=error or None,
    )


def production_status(
    reader: LogfireReader,
    *,
    now: dt.datetime | None = None,
    window_days: int = 7,
    since: dt.datetime | None = None,
    environment: str = "production",
) -> Status:
    """Consulta las trazas y resume el estado. ``since`` acota errores y respuestas; por defecto, el despliegue vigente."""
    if not _ENVIRONMENT.fullmatch(environment):
        raise LogfireError(f"Entorno no válido: {environment!r}")
    now = now or dt.datetime.now(dt.UTC)
    window_start = now - dt.timedelta(days=window_days)
    env = f"deployment_environment = '{environment}'"

    seen = reader.query(
        f"""
        SELECT service_name, service_version, min(start_timestamp) AS first_seen,
               max(start_timestamp) AS last_seen, count(*) AS records
        FROM records
        WHERE {env} AND service_name IN ('oniel-api', 'oniel-data')
        GROUP BY service_name, service_version
        ORDER BY last_seen DESC
        """,
        since=window_start,
    )
    versions = [
        VersionSeen(
            service=str(row["service_name"]),
            version=str(row["service_version"]),
            first_seen=_parse(row["first_seen"]),
            last_seen=_parse(row["last_seen"]),
            records=int(row["records"]),
        )
        for row in seen
    ]
    api = next((v for v in versions if v.service == "oniel-api"), None)
    if since is None:
        since = api.first_seen if api and api.first_seen else window_start
    since_sql = f"start_timestamp >= '{_utc(since)}'"

    started = reader.query(
        f"""
        SELECT max(start_timestamp) AS started FROM records
        WHERE {env} AND service_name = 'oniel-api' AND span_name = 'api started'
        """,
        since=window_start,
    )
    imports = reader.query(
        f"""
        SELECT kind, start_timestamp, duration, service_version, level, is_exception,
               exception_type, exception_message, attributes
        FROM records
        WHERE {env} AND service_name = 'oniel-data'
          AND span_name IN ('import all', 'import all started')
        ORDER BY start_timestamp DESC, kind DESC
        LIMIT 1
        """,
        since=window_start,
    )
    problems = reader.query(
        f"""
        SELECT service_name, span_name, coalesce(exception_type, '') AS exception_type,
               left(coalesce(exception_message, message), 200) AS detail, max(level) AS level,
               count(*) AS n, max(start_timestamp) AS last_seen, max(trace_id) AS trace_id
        FROM records
        WHERE {env} AND (level >= {ERROR_LEVEL} OR is_exception) AND {since_sql}
        GROUP BY 1, 2, 3, 4
        ORDER BY last_seen DESC
        LIMIT 30
        """,
        since=since,
    )
    http_errors = reader.query(
        f"""
        SELECT coalesce(http_route, url_path) AS route, http_response_status_code AS status,
               count(*) AS n, max(start_timestamp) AS last_seen
        FROM records
        WHERE {env} AND service_name = 'oniel-api' AND http_response_status_code >= 400
          AND {since_sql}
        GROUP BY 1, 2
        ORDER BY n DESC
        LIMIT 30
        """,
        since=since,
    )
    routes = reader.query(
        f"""
        SELECT http_route AS route, count(*) AS n, round(avg(duration) * 1000) AS mean_ms,
               round(approx_percentile_cont(duration, 0.95) * 1000) AS p95_ms,
               round(max(duration) * 1000) AS max_ms
        FROM records
        WHERE {env} AND service_name = 'oniel-api' AND http_route IS NOT NULL
          AND parent_span_id IS NULL AND {since_sql}
        GROUP BY 1
        ORDER BY p95_ms DESC
        """,
        since=since,
    )
    return Status(
        environment=environment,
        checked_at=now,
        window_start=window_start,
        versions=versions,
        api_started=_parse(started[0].get("started")) if started else None,
        last_import=_import_run(imports),
        since=since,
        errors=[row for row in problems if int(row.get("level") or 0) >= ERROR_LEVEL],
        handled=[row for row in problems if int(row.get("level") or 0) < ERROR_LEVEL],
        http_errors=http_errors,
        routes=routes,
    )


def commit_deployed(status: Status, commit: str) -> bool:
    """El commit está desplegado cuando es la versión de la API y su importación no falló ni sigue en curso."""
    api = status.current()
    if api is None or not is_commit(api.version, commit):
        return False
    run = status.last_import
    return not (run and is_commit(run.version, commit) and run.outcome in ("running", "failed"))


def wait_for_commit(
    fetch: Callable[[], Status],
    commit: str,
    *,
    timeout_s: float,
    interval_s: float = 30.0,
    sleep: Callable[[float], None] = time.sleep,
    clock: Callable[[], float] = time.monotonic,
) -> Status:
    """Repite la consulta hasta que el commit sea el desplegado o se agote el tiempo."""
    deadline = clock() + timeout_s
    while True:
        status = fetch()
        if commit_deployed(status, commit) or clock() + interval_s > deadline:
            return status
        sleep(interval_s)


def _when(moment: dt.datetime | None) -> str:
    return (
        moment.astimezone(dt.UTC).strftime("%Y-%m-%d %H:%M UTC") if moment else "fecha desconocida"
    )


def _ago(moment: dt.datetime | None, now: dt.datetime) -> str:
    if moment is None:
        return "nunca"
    minutes = int((now - moment).total_seconds() // 60)
    if minutes < 1:
        return "hace menos de un minuto"
    if minutes < 120:
        return f"hace {minutes} min"
    if minutes < 48 * 60:
        return f"hace {minutes // 60} h"
    return f"hace {minutes // (60 * 24)} días"


def _import_lines(run: ImportRun | None, window_days: int) -> list[str]:
    if run is None:
        return [f"  ninguna registrada en los últimos {window_days} días"]
    version = short_version(run.version)
    if run.outcome == "running":
        return [f"  en curso desde {_when(run.started)} (versión {version}); aún no ha terminado"]
    took = f" en {run.duration_s:.0f} s" if run.duration_s is not None else ""
    head = f"{_when(run.started)}{took} (versión {version})"
    if run.outcome == "failed":
        return [f"  FALLIDA el {head}", f"    {run.error or 'sin detalle de la excepción'}"]
    if run.outcome == "skipped":
        return [f"  omitida el {head}: los datos y el código no han cambiado (--if-changed)"]
    detail = ", ".join(f"{key}={value}" for key, value in sorted(run.detail.items()))
    return [f"  completada el {head}"] + ([f"    {detail}"] if detail else [])


def _problem_lines(rows: list[Row]) -> list[str]:
    lines = []
    for row in rows:
        what = ": ".join(
            str(part) for part in (row.get("exception_type"), row.get("detail")) if part
        )
        lines.append(
            f"  {row['n']}× {row['service_name']} · {row['span_name']} · {what} "
            f"(último {_when(_parse(row.get('last_seen')))}, traza {row.get('trace_id')})"
        )
    return lines


def format_status(status: Status, *, commit: str | None = None, window_days: int = 7) -> str:
    """El informe en texto, en el orden en que se pregunta tras un despliegue."""
    now = status.checked_at
    out = [
        f"Oniel en «{status.environment}» según las trazas de Logfire ({_when(now)})",
        "",
        "Versión desplegada",
    ]
    api = status.current()
    if api is None:
        out.append(f"  la API no ha enviado trazas en los últimos {window_days} días")
    else:
        since = (
            f"desde antes del {_when(status.window_start)}"
            if api.first_seen and api.first_seen - status.window_start < dt.timedelta(hours=1)
            else f"desde el {_when(api.first_seen)}"
        )
        out.append(
            f"  oniel-api: {short_version(api.version)} {since}; "
            f"última traza {_ago(api.last_seen, now)}"
        )
        if api.version != short_version(api.version):
            out.append(f"    commit {api.version}")
        if status.api_started:
            out.append(f"    último arranque: {_when(status.api_started)}")
        previous = [v for v in status.versions if v.service == "oniel-api"][1:3]
        for old in previous:
            out.append(f"    antes: {short_version(old.version)}, hasta el {_when(old.last_seen)}")
    data = status.current("oniel-data")
    if data and (api is None or data.version != api.version):
        out.append(
            f"  oniel-data: {short_version(data.version)}, última traza {_ago(data.last_seen, now)}. "
            "No coincide con la API: puede haber un despliegue en curso, o la API no ha arrancado."
        )
    if commit:
        if commit_deployed(status, commit):
            out.append(f"  El commit {commit} ES el desplegado.")
        elif api is not None and is_commit(api.version, commit):
            out.append(
                f"  El commit {commit} es el de la API, pero su importación no ha terminado bien."
            )
        else:
            out.append(f"  El commit {commit} NO es el desplegado todavía.")
    out += ["", "Última importación", *_import_lines(status.last_import, window_days)]
    out += ["", f"Errores desde el {_when(status.since)}"]
    out += _problem_lines(status.errors) or ["  ninguno"]
    if status.handled:
        out += ["", "Excepciones controladas (no son errores del servidor)"]
        out += _problem_lines(status.handled)
    out += ["", "Respuestas 4xx y 5xx por ruta"]
    out += [
        f"  {row['status']} {row['route']}: {row['n']} (última {_when(_parse(row.get('last_seen')))})"
        for row in status.http_errors
    ] or ["  ninguna"]
    total = sum(int(row["n"]) for row in status.routes)
    out += ["", f"Rutas más lentas (de {total} peticiones)"]
    out += [
        f"  {row['route']}: p95 {row['p95_ms']:.0f} ms, media {row['mean_ms']:.0f} ms, "
        f"máximo {row['max_ms']:.0f} ms, {row['n']} peticiones"
        for row in status.routes[:5]
    ] or ["  sin peticiones en ese periodo"]
    return "\n".join(out) + "\n"
