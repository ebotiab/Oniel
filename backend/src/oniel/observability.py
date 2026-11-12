"""Instrumentación con Logfire.

Sin token (LOGFIRE_TOKEN o backend/.logfire/) Logfire no envía nada y la aplicación
funciona igual: la configuración usa ``send_to_logfire="if-token-present"``.

La versión del servicio es el commit desplegado, para poder preguntar a las trazas qué commit
corre en producción y comparar errores antes y después de un despliegue (`oniel-data obs estado`).

Lo que se envía cuenta contra la cuota mensual del proyecto (cada tramo, aviso y punto de métrica
es un registro), así que aquí se decide también lo que no se envía: las comprobaciones de salud de
Render, las sentencias SQL del importador y cualquier cosa que salga de una ejecución de pytest.
`docs/despliegue.md`, «Logfire», tiene las cifras y los entornos.
"""

from __future__ import annotations

import os
from collections.abc import Mapping
from typing import Literal

import logfire
from fastapi import FastAPI

from oniel import __version__
from oniel.settings import Settings

_configured: set[str] = set()

#: Rutas que la instrumentación de FastAPI no traza ni mide. Render llama a `/healthz` cada pocos
#: segundos mientras la API está despierta: eran miles de tramos al día sin información.
EXCLUDED_URLS = r"/healthz$"

#: Métricas del sistema, una lectura por minuto de cada una. Las dos del proceso dicen cuánto
#: procesador y cuánta memoria usa Oniel (la memoria residente es la que cuenta contra el límite
#: de la instancia de Render); las dos de la máquina, cuánto queda alrededor.
SYSTEM_METRICS: dict[str, list[str] | None] = {
    "process.cpu.utilization": None,
    "process.memory.usage": None,
    "system.cpu.simple_utilization": None,
    "system.memory.utilization": ["available"],
}


def deployed_commit(env: Mapping[str, str] | None = None) -> str | None:
    """Commit desplegado: Render lo da en ``RENDER_GIT_COMMIT``. Fuera de Render no hay."""
    environ = os.environ if env is None else env
    return environ.get("RENDER_GIT_COMMIT", "").strip() or None


def service_version(env: Mapping[str, str] | None = None) -> str:
    """Lo que las trazas llevan como versión: el commit desplegado o, en local, la del paquete."""
    return deployed_commit(env) or __version__


def running_under_pytest(env: Mapping[str, str] | None = None) -> bool:
    """pytest define ``PYTEST_VERSION`` mientras corre; es la señal que usa también el SDK."""
    environ = os.environ if env is None else env
    return "PYTEST_VERSION" in environ


def send_to_logfire(env: Mapping[str, str] | None = None) -> bool | Literal["if-token-present"]:
    """Las pruebas no envían nunca, haya o no un token en el entorno; lo demás, solo con token."""
    return False if running_under_pytest(env) else "if-token-present"


def configure_logfire(service_name: str, settings: Settings, *, sql: bool = False) -> None:
    """Configura Logfire para un servicio; con ``sql`` cada consulta a la base es un tramo.

    La API lo activa: una petición hace pocas consultas y verlas es lo que explica una ruta lenta.
    El importador no: una importación completa son miles de sentencias, y lo que interesa de ella
    lo llevan sus propios tramos (`import all`, uno por línea, uno por fichero de horarios, las
    anotaciones y la exportación), con sus recuentos.
    """
    if service_name in _configured:
        return
    logfire.configure(
        service_name=service_name,
        service_version=service_version(),
        environment=settings.environment,
        send_to_logfire=send_to_logfire(),
        console=False,
        # Servicio público: no se continúa la traza de quien llama aunque mande `traceparent`.
        distributed_tracing=False,
        code_source=logfire.CodeSource(
            repository="https://github.com/ebotiab/Oniel",
            revision=deployed_commit() or "main",
            root_path="backend",
        ),
    )
    if sql:
        logfire.instrument_asyncpg()
    logfire.instrument_system_metrics(SYSTEM_METRICS, base=None)  # type: ignore[arg-type]
    _configured.add(service_name)


def instrument_api(app: FastAPI) -> None:
    """Un tramo por petición, sin cabeceras y sin las comprobaciones de salud."""
    logfire.instrument_fastapi(app, capture_headers=False, excluded_urls=EXCLUDED_URLS)
