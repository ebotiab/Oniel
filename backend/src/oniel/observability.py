"""Instrumentación con Logfire.

Sin token (LOGFIRE_TOKEN o backend/.logfire/) Logfire no envía nada y la aplicación
funciona igual: la configuración usa ``send_to_logfire="if-token-present"``.

La versión del servicio es el commit desplegado, para poder preguntar a las trazas qué commit
corre en producción y comparar errores antes y después de un despliegue (`oniel-data obs estado`).
"""

from __future__ import annotations

import os
from collections.abc import Mapping

import logfire

from oniel import __version__
from oniel.settings import Settings

_configured: set[str] = set()


def deployed_commit(env: Mapping[str, str] | None = None) -> str | None:
    """Commit desplegado: Render lo da en ``RENDER_GIT_COMMIT``. Fuera de Render no hay."""
    environ = os.environ if env is None else env
    return environ.get("RENDER_GIT_COMMIT", "").strip() or None


def service_version(env: Mapping[str, str] | None = None) -> str:
    """Lo que las trazas llevan como versión: el commit desplegado o, en local, la del paquete."""
    return deployed_commit(env) or __version__


def configure_logfire(service_name: str, settings: Settings) -> None:
    if service_name in _configured:
        return
    logfire.configure(
        service_name=service_name,
        service_version=service_version(),
        environment=settings.environment,
        send_to_logfire="if-token-present",
        console=False,
        code_source=logfire.CodeSource(
            repository="https://github.com/ebotiab/Oniel",
            revision=deployed_commit() or "main",
            root_path="backend",
        ),
    )
    logfire.instrument_asyncpg()
    _configured.add(service_name)
