"""Qué envía Oniel a Logfire y qué no: salud, SQL del importador, pruebas y excepciones."""

from __future__ import annotations

import tomllib
from pathlib import Path

import httpx
import logfire
import pytest
from fastapi import FastAPI
from logfire.testing import CaptureLogfire

from oniel import observability
from oniel.observability import instrument_api, send_to_logfire

BACKEND = Path(__file__).resolve().parents[1]


def test_tests_never_send_even_with_a_token() -> None:
    assert send_to_logfire({"PYTEST_VERSION": "9", "LOGFIRE_TOKEN": "un-token"}) is False
    assert send_to_logfire({"LOGFIRE_TOKEN": "un-token"}) == "if-token-present"
    # esta misma ejecución es una prueba: lo que configure la aplicación no sale de aquí
    assert send_to_logfire() is False


def test_pytest_plugin_is_off_also_in_ci() -> None:
    config = tomllib.loads((BACKEND / "pyproject.toml").read_text(encoding="utf-8"))
    assert "--no-logfire" in config["tool"]["pytest"]["ini_options"]["addopts"]


def test_only_the_api_traces_sql(monkeypatch: pytest.MonkeyPatch) -> None:
    calls: list[str] = []
    monkeypatch.setattr(observability, "_configured", set())
    monkeypatch.setattr(logfire, "configure", lambda **kw: calls.append("configure"))
    monkeypatch.setattr(logfire, "instrument_asyncpg", lambda: calls.append("sql"))
    monkeypatch.setattr(
        logfire,
        "instrument_system_metrics",
        lambda config, base: calls.append(f"metrics:{len(config)}:{base}"),
    )
    from oniel.settings import Settings

    observability.configure_logfire("oniel-data", Settings())
    assert calls == ["configure", "metrics:4:None"]
    observability.configure_logfire("oniel-api", Settings(), sql=True)
    assert calls[2:] == ["configure", "sql", "metrics:4:None"]
    # una segunda llamada para el mismo servicio no repite nada
    observability.configure_logfire("oniel-api", Settings(), sql=True)
    assert len(calls) == 5


async def test_health_checks_are_not_traced_and_errors_are_exceptions(
    capfire: CaptureLogfire,
) -> None:
    app = FastAPI()
    instrument_api(app)

    @app.get("/healthz")
    async def healthz() -> dict[str, str]:
        return {"status": "ok"}

    @app.get("/api/falla")
    async def falla() -> None:
        raise RuntimeError("fallo de prueba")

    transport = httpx.ASGITransport(app=app, raise_app_exceptions=False)
    async with httpx.AsyncClient(transport=transport, base_url="http://test") as client:
        assert (await client.get("/healthz")).status_code == 200
        assert (await client.get("/api/falla")).status_code == 500

    spans = capfire.exporter.exported_spans_as_dict()
    assert not [s for s in spans if "healthz" in s["name"]]
    failed = [s for s in spans if s["name"] == "GET /api/falla"]
    assert len(failed) == 1
    # la excepción va como evento del tramo: es lo que Logfire agrupa en «Error tracking»
    events = failed[0].get("events", [])
    assert [e["name"] for e in events] == ["exception"]
    assert events[0]["attributes"]["exception.type"] == "RuntimeError"
    assert failed[0]["attributes"]["logfire.level_num"] >= 17
