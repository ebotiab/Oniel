"""Conexiones a PostgreSQL con asyncpg."""

from __future__ import annotations

import json
from collections.abc import AsyncIterator
from contextlib import asynccontextmanager
from typing import Any
from urllib.parse import parse_qsl, urlencode, urlsplit, urlunsplit

import asyncpg

#: Parámetros que traen las cadenas de conexión de algunos proveedores y que asyncpg no entiende:
#: los mandaría al servidor como ajustes de sesión y la conexión fallaría.
_PARAMETROS_AJENOS = frozenset({"channel_binding"})

#: Segundos que una conexión puede pasar sin uso antes de cerrarse. Una base que se suspende sola
#: a los cinco minutos sin actividad (Neon) cortaría por su lado las que el pool guardara más tiempo.
_VIDA_SIN_USO_S = 120.0


def normalize_dsn(dsn: str) -> str:
    """Quita de la cadena de conexión los parámetros que asyncpg no admite; el resto no cambia."""
    partes = urlsplit(dsn)
    if not partes.query:
        return dsn
    pares = parse_qsl(partes.query, keep_blank_values=True)
    limpios = [(clave, valor) for clave, valor in pares if clave not in _PARAMETROS_AJENOS]
    if len(limpios) == len(pares):
        return dsn
    return urlunsplit(partes._replace(query=urlencode(limpios)))


async def _init_connection(conn: asyncpg.Connection) -> None:
    for typename in ("json", "jsonb"):
        await conn.set_type_codec(
            typename, encoder=json.dumps, decoder=json.loads, schema="pg_catalog"
        )


async def create_pool(dsn: str, *, min_size: int = 1, max_size: int = 8) -> asyncpg.Pool:
    return await asyncpg.create_pool(
        normalize_dsn(dsn),
        min_size=min_size,
        max_size=max_size,
        init=_init_connection,
        command_timeout=60,
        max_inactive_connection_lifetime=_VIDA_SIN_USO_S,
    )


async def fetch_int(conn: asyncpg.Connection, query: str, *args: Any) -> int:
    """``fetchval`` para consultas que siempre devuelven un entero (``count(*)``, ``RETURNING id``)."""
    value = await conn.fetchval(query, *args)
    if value is None:
        raise RuntimeError(f"la consulta no devolvió ningún valor: {query}")
    return int(value)


@asynccontextmanager
async def connect(dsn: str) -> AsyncIterator[asyncpg.Connection]:
    conn = await asyncpg.connect(normalize_dsn(dsn))
    try:
        await _init_connection(conn)
        yield conn
    finally:
        await conn.close()
