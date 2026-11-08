"""Instrumentación con Logfire.

Sin token (LOGFIRE_TOKEN o backend/.logfire/) Logfire no envía nada y la aplicación
funciona igual: la configuración usa ``send_to_logfire="if-token-present"``.
"""

from __future__ import annotations

import logfire

from oniel.settings import Settings

_configured: set[str] = set()


def configure_logfire(service_name: str, settings: Settings) -> None:
    if service_name in _configured:
        return
    logfire.configure(
        service_name=service_name,
        service_version=__import__("oniel").__version__,
        environment=settings.environment,
        send_to_logfire="if-token-present",
        console=False,
        code_source=logfire.CodeSource(
            repository="https://github.com/ebotiab/Oniel", revision="main", root_path="backend"
        ),
    )
    logfire.instrument_asyncpg()
    _configured.add(service_name)
