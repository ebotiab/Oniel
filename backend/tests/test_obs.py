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
    assert "ninguna registrada en los últimos 7 días" in text
    assert "El commit 7ba2694 NO es el desplegado todavía." in text
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
