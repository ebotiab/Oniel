"""Estado de producción desde Logfire: token, consultas e informe, con respuestas simuladas y sin red."""

from __future__ import annotations

import datetime as dt
import json
from collections.abc import Callable
from pathlib import Path
from typing import Any

import httpx
import pytest
from typer.testing import CliRunner

from oniel import obs
from oniel.cli.main import app
from oniel.observability import deployed_commit, service_version

COMMIT = "7ba26940c0ffee00000000000000000000000abc"
NOW = dt.datetime(2026, 11, 12, 17, 0, tzinfo=dt.UTC)


def _payload(rows: list[dict[str, Any]]) -> dict[str, Any]:
    """Respuesta de `POST /v2/query`: el esquema y las filas."""
    names = list(rows[0]) if rows else []
    return {"schema": {"fields": [{"name": n} for n in names]}, "data": rows}


def _body(request: httpx.Request) -> dict[str, Any]:
    body: dict[str, Any] = json.loads(request.content)
    return body


def _import_row(outcome: str = "completed", **extra: Any) -> dict[str, Any]:
    return {
        "kind": "span",
        "start_timestamp": "2026-11-12T16:02:00Z",
        "duration": 82.4,
        "service_version": COMMIT,
        "level": 9,
        "is_exception": False,
        "exception_type": None,
        "exception_message": None,
        "attributes": json.dumps(
            {"outcome": outcome, "lines": 3, "trips_imported": 1650, "code.filepath": "x.py"}
        ),
    } | extra


def _answers(**overrides: list[dict[str, Any]]) -> dict[str, list[dict[str, Any]]]:
    """Respuesta de cada consulta del informe, identificada por un trozo de su SQL."""
    answers: dict[str, list[dict[str, Any]]] = {
        "GROUP BY service_name, service_version": [
            {
                "service_name": "oniel-api",
                "service_version": COMMIT,
                "first_seen": "2026-11-12T16:04:00Z",
                "last_seen": "2026-11-12T16:58:00Z",
                "records": 120,
            },
            {
                "service_name": "oniel-data",
                "service_version": COMMIT,
                "first_seen": "2026-11-12T16:02:00Z",
                "last_seen": "2026-11-12T16:03:30Z",
                "records": 9000,
            },
            {
                "service_name": "oniel-api",
                "service_version": "0.1.0",
                "first_seen": "2026-11-08T15:59:00Z",
                "last_seen": "2026-11-12T16:03:50Z",
                "records": 17000,
            },
        ],
        "'api started'": [{"started": "2026-11-12T16:04:00Z"}],
        "'import all started'": [_import_row()],
        "is_exception": [
            {
                "service_name": "oniel-api",
                "span_name": "GET /api/lines",
                "exception_type": "KeyError",
                "detail": "'tracks'",
                "level": 17,
                "n": 3,
                "last_seen": "2026-11-12T16:40:00Z",
                "trace_id": "0af7651916cd43dd8448eb211c80319c",
            },
            {
                "service_name": "oniel-api",
                "span_name": "GET /api/annotations",
                "exception_type": "fastapi.exceptions.HTTPException",
                "detail": "422: Tipo de anotación sin declarar",
                "level": 13,
                "n": 7,
                "last_seen": "2026-11-12T16:30:00Z",
                "trace_id": "01a1d05c1fbea5f66a836a47c84c8af6",
            },
        ],
        "http_response_status_code >= 400": [
            {
                "route": "/api/annotations",
                "status": 422,
                "n": 7,
                "last_seen": "2026-11-12T16:30:00Z",
            }
        ],
        "approx_percentile_cont": [
            {"route": "/api/lines", "n": 40, "mean_ms": 480.0, "p95_ms": 1494.0, "max_ms": 2486.0},
            {"route": "/api/coverage", "n": 10, "mean_ms": 374.0, "p95_ms": 996.0, "max_ms": 999.0},
        ],
    }
    return answers | overrides


def _reader(
    answers: dict[str, list[dict[str, Any]]], seen: list[httpx.Request] | None = None
) -> obs.LogfireReader:
    def handler(request: httpx.Request) -> httpx.Response:
        if seen is not None:
            seen.append(request)
        assert request.method == "POST" and request.url.path == "/v2/query"
        sql = _body(request)["sql"]
        for marker, rows in answers.items():
            if marker in sql:
                return httpx.Response(200, json=_payload(rows))
        raise AssertionError(f"consulta inesperada: {sql}")

    return obs.LogfireReader("token-de-prueba", transport=httpx.MockTransport(handler))


def test_token_prefers_the_variable_then_the_file(tmp_path: Path) -> None:
    token_file = tmp_path / "logfire-read-token"
    assert obs.read_token({}, token_file) is None
    token_file.write_text("del-fichero\n", encoding="utf-8")
    assert obs.read_token({}, token_file) == "del-fichero"
    assert (
        obs.read_token({"LOGFIRE_READ_TOKEN": " de-la-variable "}, token_file) == "de-la-variable"
    )
    assert obs.read_token({"LOGFIRE_READ_TOKEN": ""}, token_file) == "del-fichero"


def test_version_is_the_deployed_commit_on_render() -> None:
    assert deployed_commit({}) is None
    assert service_version({}) == "0.1.0"
    assert service_version({"RENDER_GIT_COMMIT": COMMIT}) == COMMIT


def test_rows_from_payload_and_csv() -> None:
    rows = obs.rows_from_payload(_payload([{"a": 1, "b": "x"}, {"a": 2, "b": "y, z"}]))
    assert rows == [{"a": 1, "b": "x"}, {"a": 2, "b": "y, z"}]
    assert obs.rows_to_csv(rows) == 'a,b\n1,x\n2,"y, z"\n'
    assert obs.rows_from_payload({"data": []}) == [] and obs.rows_to_csv([]) == ""


def test_query_sends_the_environment_only_when_asked() -> None:
    seen: list[httpx.Request] = []
    reader = _reader({"select 1": [{"n": 1}]}, seen)
    since = NOW - dt.timedelta(hours=1)
    assert reader.query("select 1", since=since, limit=5, environment="local") == [{"n": 1}]
    reader.query("select 1", since=since)
    assert _body(seen[0])["deployment_environment"] == ["local"] and _body(seen[0])["limit"] == 5
    assert "deployment_environment" not in _body(seen[1]) and "limit" not in _body(seen[1])


def test_cli_query_filters_production_unless_told_otherwise(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    seen: list[httpx.Request] = []
    reader = _reader({"select 1": []}, seen)
    monkeypatch.setattr(reader, "close", lambda: None)  # se reutiliza en las tres llamadas
    monkeypatch.setattr(obs, "read_token", lambda: "token-de-prueba")
    monkeypatch.setattr(obs, "LogfireReader", lambda token: reader)
    for args in ([], ["--entorno", "local"], ["--entorno", "todos"]):
        assert CliRunner().invoke(app, ["obs", "consulta", "select 1", *args]).exit_code == 0
    assert [_body(r).get("deployment_environment") for r in seen] == [
        ["production"],
        ["local"],
        None,
    ]


def test_commit_matching_accepts_short_hashes_only() -> None:
    assert obs.is_commit(COMMIT, "7ba2694") and obs.is_commit(COMMIT, COMMIT.upper())
    assert not obs.is_commit(COMMIT, "7ba") and not obs.is_commit("0.1.0", "0.1.0")
    assert obs.short_version(COMMIT) == "7ba2694" and obs.short_version("0.1.0") == "0.1.0"


def test_status_reports_version_import_errors_and_routes() -> None:
    seen: list[httpx.Request] = []
    status = obs.production_status(_reader(_answers(), seen), now=NOW)

    api = status.current()
    assert api is not None and api.version == COMMIT
    # errores y respuestas se cuentan desde que entró la versión vigente
    assert status.since == dt.datetime(2026, 11, 12, 16, 4, tzinfo=dt.UTC)
    assert _body(seen[0])["min_timestamp"] == "2026-11-05T17:00:00.000000Z"
    assert _body(seen[-1])["min_timestamp"] == "2026-11-12T16:04:00.000000Z"
    assert seen[0].headers["authorization"] == "Bearer token-de-prueba"
    assert [e["exception_type"] for e in status.errors] == ["KeyError"]
    assert [e["span_name"] for e in status.handled] == ["GET /api/annotations"]
    assert status.last_import is not None and status.last_import.outcome == "completed"
    assert status.last_import.detail == {"lines": 3, "trips_imported": 1650}
    assert obs.commit_deployed(status, "7ba2694") and not obs.commit_deployed(status, "abcdef0")

    text = obs.format_status(status, commit="7ba2694")
    assert "oniel-api: 7ba2694 desde el 2026-11-12 16:04 UTC; última traza hace 2 min" in text
    assert "antes: 0.1.0, hasta el 2026-11-12 16:03 UTC" in text
    assert "El commit 7ba2694 ES el desplegado." in text
    assert "completada el 2026-11-12 16:02 UTC en 82 s (versión 7ba2694)" in text
    assert "3× oniel-api · GET /api/lines · KeyError: 'tracks'" in text
    assert "traza 0af7651916cd43dd8448eb211c80319c" in text
    assert "422 /api/annotations: 7" in text
    assert "Rutas más lentas (de 50 peticiones)" in text
    assert "/api/lines: p95 1494 ms, media 480 ms" in text
    assert json.loads(status.to_json())["last_import"]["outcome"] == "completed"


@pytest.mark.parametrize(
    ("row", "expected", "deployed"),
    [
        (_import_row("skipped"), "omitida el 2026-11-12 16:02 UTC", True),
        (
            _import_row(
                level=17,
                is_exception=True,
                exception_type="RuntimeError",
                exception_message="fichero de horarios ilegible",
                attributes=json.dumps({"outcome": "failed"}),
            ),
            "FALLIDA el 2026-11-12 16:02 UTC en 82 s (versión 7ba2694)\n    RuntimeError: fichero de horarios ilegible",
            False,
        ),
        (
            {**_import_row(), "kind": "log", "duration": None, "attributes": "{}"},
            "en curso desde 2026-11-12 16:02 UTC",
            False,
        ),
    ],
)
def test_import_outcomes(row: dict[str, Any], expected: str, deployed: bool) -> None:
    status = obs.production_status(_reader(_answers(**{"'import all started'": [row]})), now=NOW)
    text = obs.format_status(status, commit="7ba2694")
    assert expected in text
    assert obs.commit_deployed(status, "7ba2694") is deployed
    if not deployed:
        assert "su importación no ha terminado bien" in text


def test_status_without_traces_says_so() -> None:
    empty: dict[str, list[dict[str, Any]]] = {marker: [] for marker in _answers()}
    status = obs.production_status(_reader(empty), now=NOW)
    text = obs.format_status(status, commit="7ba2694")
    assert "la API no ha enviado trazas en los últimos 7 días" in text
    assert "ninguna de la versión 7ba2694 registrada en los últimos 7 días" in text
    assert "El commit 7ba2694 NO es el desplegado todavía." in text
    assert "ninguna registrada en los últimos 7 días" in obs.format_status(status)
    assert text.count("  ninguno") == 1 and "sin peticiones en ese periodo" in text


def test_data_version_ahead_of_the_api_is_flagged() -> None:
    versions = _answers()["GROUP BY service_name, service_version"]
    versions[0]["service_version"] = "0.1.0"
    del versions[2]
    status = obs.production_status(
        _reader(_answers(**{"GROUP BY service_name, service_version": versions})), now=NOW
    )
    text = obs.format_status(status, commit="7ba2694")
    assert "oniel-data: 7ba2694" in text and "No coincide con la API" in text
    assert "NO es el desplegado todavía" in text


OLD = "6dc0573c0ffee000000000000000000000000def"


def _overlapping_deploy() -> dict[str, list[dict[str, Any]]]:
    """El despliegue del 12 de noviembre de 2026 tras la PR 119 (#120): la importación de la versión
    nueva empieza medio segundo antes que la de la anterior, que se la salta y acaba mucho antes."""
    versions = _answers()["GROUP BY service_name, service_version"]
    versions[2]["service_version"] = OLD
    return _answers(
        **{
            "GROUP BY service_name, service_version": versions,
            "'import all started'": [
                _import_row(
                    "skipped",
                    start_timestamp="2026-11-12T16:02:00.501Z",
                    duration=1.1,
                    service_version=OLD,
                    attributes=json.dumps({"outcome": "skipped", "if_changed": True}),
                ),
                {
                    **_import_row(),
                    "kind": "log",
                    "start_timestamp": "2026-11-12T16:02:00.500Z",
                    "service_version": OLD,
                    "duration": None,
                    "attributes": "{}",
                },
                _import_row(start_timestamp="2026-11-12T16:02:00.001Z"),
                {
                    **_import_row(),
                    "kind": "log",
                    "start_timestamp": "2026-11-12T16:02:00Z",
                    "duration": None,
                    "attributes": "{}",
                },
            ],
        }
    )


def test_overlapping_imports_report_the_deployed_version() -> None:
    status = obs.production_status(_reader(_overlapping_deploy()), now=NOW)
    assert [(run.version, run.outcome) for run in status.imports] == [
        (OLD, "skipped"),
        (COMMIT, "completed"),
    ]
    assert status.last_import is not None and status.last_import.version == COMMIT
    assert status.last_import.detail == {"lines": 3, "trips_imported": 1650}
    assert obs.commit_deployed(status, "7ba2694")

    for commit in ("7ba2694", None):
        text = obs.format_status(status, commit=commit)
        imports = text.split("Última importación\n")[1].split("\n\n")[0].splitlines()
        assert imports == [
            "  completada el 2026-11-12 16:02 UTC en 82 s (versión 7ba2694)",
            "    lines=3, trips_imported=1650",
            "  La más reciente es de otra versión; no cuenta para la desplegada:",
            "    omitida el 2026-11-12 16:02 UTC en 1 s (versión 6dc0573): los datos y el código "
            "no han cambiado (--if-changed)",
        ]

    # Con --commit de la versión anterior se ve la suya, y la API dice que no es la desplegada.
    text = obs.format_status(status, commit="6dc0573")
    assert "El commit 6dc0573 NO es el desplegado todavía." in text
    assert "Última importación\n  omitida el 2026-11-12 16:02 UTC" in text
    assert "La más reciente es de otra versión" not in text


def test_import_of_the_commit_still_running_is_not_deployed() -> None:
    answers = _overlapping_deploy()
    answers["'import all started'"] = answers["'import all started'"][:2] + [
        answers["'import all started'"][3]
    ]  # sin el tramo de la versión nueva: su importación sigue en curso
    status = obs.production_status(_reader(answers), now=NOW)
    run = status.import_for("7ba2694")
    assert run is not None and run.outcome == "running"
    assert status.last_import is run
    assert not obs.commit_deployed(status, "7ba2694")
    text = obs.format_status(status, commit="7ba2694")
    assert "en curso desde 2026-11-12 16:02 UTC (versión 7ba2694)" in text
    assert "su importación no ha terminado bien" in text


def test_reader_explains_failures() -> None:
    def handler(status: int) -> Callable[[httpx.Request], httpx.Response]:
        return lambda request: httpx.Response(status, json={"detail": "Invalid token"})

    since = NOW - dt.timedelta(hours=1)
    with pytest.raises(obs.LogfireError, match="rechazó el token"):
        obs.LogfireReader("x", transport=httpx.MockTransport(handler(401))).query(
            "select 1", since=since
        )
    with pytest.raises(obs.LogfireError, match="limitado las consultas"):
        obs.LogfireReader("x", transport=httpx.MockTransport(handler(429))).query(
            "select 1", since=since
        )
    with pytest.raises(obs.LogfireError, match="respondió 400"):
        obs.LogfireReader("x", transport=httpx.MockTransport(handler(400))).query(
            "select 1", since=since
        )

    def refuse(request: httpx.Request) -> httpx.Response:
        raise httpx.ConnectError("TLS cortado")

    with pytest.raises(obs.LogfireError, match="No se pudo conectar"):
        obs.LogfireReader("x", transport=httpx.MockTransport(refuse)).query("select 1", since=since)
    with pytest.raises(obs.LogfireError, match="Entorno no válido"):
        obs.production_status(_reader(_answers()), environment="x' or '1'='1")


def test_wait_for_commit_polls_until_it_is_deployed() -> None:
    old = obs.production_status(_reader(dict.fromkeys(_answers(), [])), now=NOW)
    new = obs.production_status(_reader(_answers()), now=NOW)
    pending = [old, old, new]
    slept: list[float] = []
    clock = iter(range(0, 10_000, 30))
    status = obs.wait_for_commit(
        lambda: pending.pop(0),
        "7ba2694",
        timeout_s=600,
        sleep=slept.append,
        clock=lambda: next(clock),
    )
    assert status is new and slept == [30.0, 30.0]

    # si no entra, devuelve lo último visto al agotarse el tiempo
    calls: list[int] = []
    clock = iter(range(0, 10_000, 30))

    def never() -> obs.Status:
        calls.append(1)
        return old

    assert (
        obs.wait_for_commit(
            never, "7ba2694", timeout_s=90, sleep=slept.append, clock=lambda: next(clock)
        )
        is old
    )
    assert len(calls) <= 3


def test_wait_for_commit_waits_for_its_import_and_stops_if_it_fails() -> None:
    answers = _overlapping_deploy()
    rows = answers["'import all started'"]
    running = obs.production_status(
        _reader(answers | {"'import all started'": [*rows[:2], rows[3]]}), now=NOW
    )
    done = obs.production_status(_reader(answers), now=NOW)
    pending = [running, running, done]
    slept: list[float] = []
    clock = iter(range(0, 10_000, 30))
    status = obs.wait_for_commit(
        lambda: pending.pop(0),
        "7ba2694",
        timeout_s=600,
        sleep=slept.append,
        clock=lambda: next(clock),
    )
    assert status is done and slept == [30.0, 30.0]

    failed_row = _import_row(level=17, is_exception=True, exception_type="RuntimeError")
    failed = obs.production_status(
        _reader(answers | {"'import all started'": [*rows[:2], failed_row]}), now=NOW
    )
    assert obs.import_failed(failed, "7ba2694") and not obs.commit_deployed(failed, "7ba2694")
    slept.clear()
    assert (
        obs.wait_for_commit(
            lambda: failed, "7ba2694", timeout_s=600, sleep=slept.append, clock=lambda: 0.0
        )
        is failed
    )
    assert slept == []


def test_wait_for_commit_waits_out_the_rate_limit() -> None:
    """Con el token compartido entre sesiones, Logfire responde 429 a menudo tras un despliegue."""
    done = obs.production_status(_reader(_answers()), now=NOW)
    limited = obs.LogfireRateLimited("429", retry_after_s=67.0)
    replies: list[obs.Status | Exception] = [limited, limited, done]
    slept: list[float] = []
    now = [0.0]

    def fetch() -> obs.Status:
        reply = replies.pop(0)
        if isinstance(reply, Exception):
            raise reply
        return reply

    def sleep(seconds: float) -> None:
        slept.append(seconds)
        now[0] += seconds

    status = obs.wait_for_commit(fetch, "7ba2694", timeout_s=900, sleep=sleep, clock=lambda: now[0])
    assert status is done and slept == [68.0, 68.0]

    # sin nada visto y sin tiempo para esperar, el límite sale como error
    def always_limited() -> obs.Status:
        raise obs.LogfireRateLimited("429", retry_after_s=120.0)

    with pytest.raises(obs.LogfireRateLimited):
        obs.wait_for_commit(always_limited, "7ba2694", timeout_s=60, sleep=sleep, clock=lambda: 0.0)


def test_rate_limit_carries_retry_after() -> None:
    def limited(request: httpx.Request) -> httpx.Response:
        return httpx.Response(429, headers={"Retry-After": "94"}, json={})

    reader = obs.LogfireReader("x", transport=httpx.MockTransport(limited))
    with pytest.raises(obs.LogfireRateLimited, match="reintentar en 94 s") as caught:
        reader.query("select 1", since=NOW)
    assert caught.value.retry_after_s == 94.0


def test_cli_without_token_says_so_and_does_not_fail(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setattr(obs, "read_token", lambda: None)
    for args in (["obs", "estado"], ["obs", "consulta", "select 1"]):
        result = CliRunner().invoke(app, args)
        assert result.exit_code == 0
        assert "Sin token de lectura de Logfire" in result.output


def test_cli_estado_and_consulta(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setattr(obs, "read_token", lambda: "token-de-prueba")
    reader = _reader(_answers())
    monkeypatch.setattr(reader, "close", lambda: None)  # las órdenes lo cierran; aquí se reutiliza
    monkeypatch.setattr(obs, "LogfireReader", lambda token: reader)

    ok = CliRunner().invoke(app, ["obs", "estado", "--commit", "7ba2694"])
    assert ok.exit_code == 0 and "ES el desplegado" in ok.output
    missing = CliRunner().invoke(app, ["obs", "estado", "--commit", "abcdef0"])
    assert missing.exit_code == 1 and "NO es el desplegado" in missing.output
    as_json = CliRunner().invoke(app, ["obs", "estado", "--json"])
    assert json.loads(as_json.output)["versions"][0]["version"] == COMMIT
    bad_date = CliRunner().invoke(app, ["obs", "estado", "--desde", "ayer"])
    assert bad_date.exit_code == 2

    rows = CliRunner().invoke(app, ["obs", "consulta", "select 'api started'"])
    assert rows.exit_code == 0 and rows.output == "started\n2026-11-12T16:04:00Z\n"


# El modo estricto ejecuta su SQL sobre SQLite en memoria: se comprueban los filtros reales
# de versión, servicio, fechas y nivel, además de la salida del comando, sin acceder a la red.
def _verification_reader(
    extra: list[dict[str, Any]] | None = None,
    *,
    imports: list[dict[str, Any]] | None = None,
    api: bool = True,
    seen: list[httpx.Request] | None = None,
) -> obs.LogfireReader:
    import sqlite3

    conn = sqlite3.connect(":memory:")
    conn.row_factory = sqlite3.Row
    conn.execute("""CREATE TABLE source_records (
        service_name TEXT, service_version TEXT, deployment_environment TEXT,
        kind TEXT, span_name TEXT, start_timestamp TEXT, duration REAL,
        level INTEGER, is_exception BOOLEAN, exception_type TEXT, exception_message TEXT,
        attributes TEXT, trace_id TEXT, http_response_status_code INTEGER
    )""")
    now = dt.datetime.now(dt.UTC)
    base: dict[str, Any] = {
        "service_name": "oniel-api",
        "service_version": COMMIT,
        "deployment_environment": "production",
        "kind": "span",
        "span_name": "GET /api/lines",
        "start_timestamp": obs._utc(now - dt.timedelta(minutes=1)),
        "duration": 0.5,
        "level": 9,
        "is_exception": False,
        "attributes": "{}",
        "trace_id": "traza-de-prueba",
        "http_response_status_code": 200,
    }
    default_import = _import_row() | {
        "service_name": "oniel-data",
        "span_name": "import all",
        "start_timestamp": obs._utc(now - dt.timedelta(minutes=3)),
    }
    records = (
        ([base] if api else []) + ([default_import] if imports is None else imports) + (extra or [])
    )
    for record in records:
        row = base | record
        conn.execute(
            f"INSERT INTO source_records ({','.join(row)}) VALUES ({','.join('?' for _ in row)})",
            list(row.values()),
        )

    def handler(request: httpx.Request) -> httpx.Response:
        if seen is not None:
            seen.append(request)
        body = _body(request)
        cursor = conn.execute(
            """WITH records AS (SELECT * FROM source_records WHERE start_timestamp >= ?
                AND start_timestamp <= ? AND deployment_environment = ?) """
            + body["sql"],
            (body["min_timestamp"], body["max_timestamp"], body["deployment_environment"][0]),
        )
        rows = [dict(row) for row in cursor.fetchall()]
        for row in rows:
            if "is_exception" in row:
                row["is_exception"] = bool(row["is_exception"])
        return httpx.Response(200, json=_payload(rows))

    return obs.LogfireReader("token-de-prueba", transport=httpx.MockTransport(handler))


def _verificar_cli(monkeypatch: pytest.MonkeyPatch, reader: obs.LogfireReader, *args: str) -> Any:
    monkeypatch.setattr(obs, "read_token", lambda: "token-de-prueba")
    monkeypatch.setattr(obs, "LogfireReader", lambda token: reader)
    return CliRunner().invoke(
        app, ["obs", "estado", "--verificar", "--commit", COMMIT, "--json", *args]
    )


@pytest.mark.parametrize("outcome", ["completed", "skipped"])
def test_verificacion_exige_api_importacion_y_ausencia_de_errores(
    monkeypatch: pytest.MonkeyPatch,
    outcome: str,
) -> None:
    row = _import_row(outcome) | {
        "service_name": "oniel-data",
        "span_name": "import all",
        "start_timestamp": obs._utc(dt.datetime.now(dt.UTC) - dt.timedelta(minutes=3)),
    }
    seen: list[httpx.Request] = []
    result = _verificar_cli(monkeypatch, _verification_reader(imports=[row], seen=seen))
    assert result.exit_code == 0, result.output
    data = json.loads(result.output)
    assert data["outcome"] == "success" and data["exit_code"] == 0
    assert data["last_import"]["outcome"] == outcome and data["server_errors"] == 0
    assert data["api"]["version"] == COMMIT
    assert len({_body(r)["max_timestamp"] for r in seen}) == 1
    assert len({_body(r)["min_timestamp"] for r in seen}) == 1


@pytest.mark.parametrize(
    ("extra", "code"),
    [
        ({"level": 17}, 1),
        ({"http_response_status_code": 500}, 1),
        ({"http_response_status_code": 503}, 1),
        ({"http_response_status_code": 422, "level": 13, "is_exception": True}, 0),
        ({"http_response_status_code": 404, "level": 9}, 0),
        ({"service_version": OLD, "level": 17, "http_response_status_code": 500}, 0),
        ({"service_name": "otro-servicio", "level": 17}, 0),
        ({"deployment_environment": "local", "level": 17}, 0),
        ({"level": 17, "start_timestamp": "2000-01-01T00:00:00.000000Z"}, 0),
    ],
)
def test_verificacion_atribuye_errores_por_version_servicio_entorno_y_ventana(
    monkeypatch: pytest.MonkeyPatch,
    extra: dict[str, Any],
    code: int,
) -> None:
    record = {
        "start_timestamp": obs._utc(dt.datetime.now(dt.UTC) - dt.timedelta(minutes=2))
    } | extra
    result = _verificar_cli(monkeypatch, _verification_reader([record]))
    assert result.exit_code == code, result.output
    data = json.loads(result.output)
    assert data["outcome"] == ("failure" if code else "success")
    if code:
        assert data["reason"] == "server_errors" and data["server_errors"] == 1
        assert data["error_trace_id"] == "traza-de-prueba"


def test_verificacion_cuenta_errores_aunque_haya_muchos_4xx(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    rows = [{"http_response_status_code": 400 + n} for n in range(40)]
    rows.append({"http_response_status_code": 503})
    result = _verificar_cli(monkeypatch, _verification_reader(rows))
    assert result.exit_code == 1
    assert json.loads(result.output)["server_errors"] == 1


@pytest.mark.parametrize(
    ("api", "imports", "code", "reason"),
    [
        (False, [], 2, "no_evidence"),
        (False, None, 2, "commit_not_current"),
        (True, [], 2, "import_pending"),
        (True, [{"kind": "log", "attributes": "{}"}], 2, "import_pending"),
        (True, [{"attributes": '{"outcome":"failed"}'}], 1, "import_failed"),
        (False, [{"attributes": '{"outcome":"failed"}'}], 1, "import_failed"),
        (True, [{"attributes": "{}"}], 2, "unusable_response"),
        (True, [{"attributes": "roto"}], 2, "unusable_response"),
        (True, [{"start_timestamp": "fecha rota"}], 2, "import_pending"),
    ],
)
def test_verificacion_no_certifica_evidencia_ausente_o_importacion_invalida(
    monkeypatch: pytest.MonkeyPatch,
    api: bool,
    imports: list[dict[str, Any]] | None,
    code: int,
    reason: str,
) -> None:
    if imports is not None:
        imports = [
            _import_row()
            | {
                "service_name": "oniel-data",
                "span_name": "import all",
                "start_timestamp": obs._utc(dt.datetime.now(dt.UTC) - dt.timedelta(minutes=3)),
            }
            | row
            for row in imports
        ]
    result = _verificar_cli(monkeypatch, _verification_reader(api=api, imports=imports))
    assert result.exit_code == code, result.output
    assert json.loads(result.output)["reason"] == reason


@pytest.mark.parametrize(
    "response",
    [
        httpx.Response(401),
        httpx.Response(403),
        httpx.Response(500),
        httpx.Response(200, text="no es JSON"),
        httpx.Response(200, json={}),
        httpx.Response(200, json={"data": None}),
        httpx.Response(200, json={"data": [1]}),
        httpx.Response(200, json={"data": [{}]}),
    ],
)
def test_verificacion_entrega_json_si_la_consulta_falla(
    monkeypatch: pytest.MonkeyPatch,
    response: httpx.Response,
) -> None:
    reader = obs.LogfireReader("x", transport=httpx.MockTransport(lambda request: response))
    result = _verificar_cli(monkeypatch, reader)
    assert result.exit_code == 2
    assert json.loads(result.output)["outcome"] == "unverifiable"


def test_verificacion_sin_token_falla_y_el_informe_conserva_su_comportamiento(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    monkeypatch.setattr(obs, "read_token", lambda: None)
    args = ["obs", "estado", "--commit", COMMIT]
    assert CliRunner().invoke(app, args).exit_code == 0
    for output in ([], ["--json"]):
        result = CliRunner().invoke(app, [*args, "--verificar", *output])
        assert result.exit_code == 2
        if output:
            assert json.loads(result.output)["reason"] == "missing_token"
        else:
            assert "VERIFICACIÓN IMPOSIBLE" in result.output


def test_verificacion_respeta_retry_after_y_el_plazo(monkeypatch: pytest.MonkeyPatch) -> None:
    reader = _verification_reader()
    original = reader.query
    elapsed = [0.0]
    pauses: list[float] = []
    attempts = [0]

    def query(sql: str, **kwargs: Any) -> list[obs.Row]:
        attempts[0] += 1
        if attempts[0] <= 2:
            raise obs.LogfireRateLimited("429", retry_after_s=67)
        return original(sql, **kwargs)

    def sleep(seconds: float) -> None:
        pauses.append(seconds)
        elapsed[0] += seconds

    monkeypatch.setattr(reader, "query", query)
    result = obs.verify_deployment(
        reader, COMMIT, timeout_s=900, clock=lambda: elapsed[0], sleep=sleep
    )
    assert result.exit_code == 0 and pauses == [68, 68]
    attempts[0] = 0
    pauses.clear()
    result = obs.verify_deployment(
        reader, COMMIT, timeout_s=60, clock=lambda: elapsed[0], sleep=sleep
    )
    assert result.exit_code == 2 and result.reason == "timeout" and not pauses


def test_verificacion_no_acepta_una_respuesta_que_llega_fuera_de_plazo(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    reader = _verification_reader()
    original = reader.query
    elapsed = [0.0]

    def query(sql: str, **kwargs: Any) -> list[obs.Row]:
        result = original(sql, **kwargs)
        elapsed[0] += 21
        return result

    monkeypatch.setattr(reader, "query", query)
    result = obs.verify_deployment(reader, COMMIT, timeout_s=60, clock=lambda: elapsed[0])
    assert result.exit_code == 2 and result.reason == "timeout"


def test_verificacion_agota_espera_sin_evidencia_y_no_duerme_tras_un_fallo() -> None:
    elapsed = [0.0]
    pauses: list[float] = []

    def sleep(seconds: float) -> None:
        pauses.append(seconds)
        elapsed[0] += seconds

    result = obs.verify_deployment(
        _verification_reader(api=False, imports=[]),
        COMMIT,
        timeout_s=65,
        clock=lambda: elapsed[0],
        sleep=sleep,
    )
    assert result.exit_code == 2 and result.reason == "timeout" and pauses == [30, 30]
    pauses.clear()
    result = obs.verify_deployment(
        _verification_reader([{"level": 17}]),
        COMMIT,
        timeout_s=900,
        clock=lambda: elapsed[0],
        sleep=sleep,
    )
    assert result.exit_code == 1 and not pauses


@pytest.mark.parametrize("rows", [[], [{}], [{"n": None}], [{"n": -1}], [{"n": "0"}]])
def test_verificacion_no_interpreta_un_recuento_invalido_como_cero(
    monkeypatch: pytest.MonkeyPatch,
    rows: list[dict[str, Any]],
) -> None:
    reader = _verification_reader()
    original = reader.query

    def query(sql: str, **kwargs: Any) -> list[obs.Row]:
        return rows if "max(trace_id)" in sql else original(sql, **kwargs)

    monkeypatch.setattr(reader, "query", query)
    result = _verificar_cli(monkeypatch, reader)
    assert result.exit_code == 2 and json.loads(result.output)["reason"] == "unusable_response"


def test_verificacion_ignora_importacion_omitida_de_otra_version() -> None:
    old_import = _import_row("skipped") | {
        "service_name": "oniel-data",
        "span_name": "import all",
        "service_version": OLD,
        "start_timestamp": obs._utc(dt.datetime.now(dt.UTC) - dt.timedelta(seconds=30)),
    }
    result = obs.verify_deployment(_verification_reader([old_import]), COMMIT[:7])
    assert result.exit_code == 0 and result.last_import is not None
    assert result.last_import.version == COMMIT and result.last_import.outcome == "completed"


def test_verificacion_no_confunde_un_prefijo_ambiguo_ni_una_version_con_sufijo() -> None:
    for version, reason in [
        (COMMIT[:-1] + "d", "ambiguous_commit"),
        (COMMIT + "-otro", "ambiguous_commit"),
    ]:
        result = obs.verify_deployment(
            _verification_reader([{"service_version": version}]), COMMIT[:7]
        )
        assert result.exit_code == 2 and result.reason == reason
    reader = _verification_reader(
        imports=[], api=False, extra=[{"service_version": COMMIT + "-otro"}]
    )
    assert obs.verify_deployment(reader, COMMIT).reason == "unusable_response"


@pytest.mark.parametrize(
    "args",
    [
        ["--desde", "2026-11-01"],
        ["--commit", "xyz"],
        ["--dias", "0"],
        ["--esperar", "-1"],
        ["--entorno", "x' or '1'='1"],
    ],
)
def test_verificacion_rechaza_argumentos_invalidos_con_json(
    monkeypatch: pytest.MonkeyPatch,
    args: list[str],
) -> None:
    result = _verificar_cli(monkeypatch, _verification_reader(), *args)
    assert result.exit_code == 2 and json.loads(result.output)["reason"] == "invalid_arguments"


def test_verificacion_puede_esperar_hasta_que_aparezca_la_evidencia(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    reader = _verification_reader()
    original = reader.query
    elapsed = [0.0]
    bounds: list[dt.datetime] = []

    def query(sql: str, **kwargs: Any) -> list[obs.Row]:
        bounds.append(kwargs["since"])
        return [] if elapsed[0] == 0 else original(sql, **kwargs)

    monkeypatch.setattr(reader, "query", query)
    result = obs.verify_deployment(
        reader,
        COMMIT,
        timeout_s=120,
        clock=lambda: elapsed[0],
        sleep=lambda seconds: elapsed.__setitem__(0, elapsed[0] + seconds),
    )
    assert result.exit_code == 0 and elapsed == [30] and len(set(bounds)) == 1
