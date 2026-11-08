"""Conexiones a PostgreSQL con asyncpg."""

from __future__ import annotations

import json
from collections.abc import AsyncIterator
from contextlib import asynccontextmanager
from typing import Any

import asyncpg


async def _init_connection(conn: asyncpg.Connection) -> None:
    for typename in ("json", "jsonb"):
        await conn.set_type_codec(
            typename, encoder=json.dumps, decoder=json.loads, schema="pg_catalog"
        )


async def create_pool(dsn: str, *, min_size: int = 1, max_size: int = 8) -> asyncpg.Pool:
    return await asyncpg.create_pool(
        dsn, min_size=min_size, max_size=max_size, init=_init_connection, command_timeout=60
    )


async def fetch_int(conn: asyncpg.Connection, query: str, *args: Any) -> int:
    """``fetchval`` para consultas que siempre devuelven un entero (``count(*)``, ``RETURNING id``)."""
    value = await conn.fetchval(query, *args)
    if value is None:
        raise RuntimeError(f"la consulta no devolvió ningún valor: {query}")
    return int(value)


@asynccontextmanager
async def connect(dsn: str) -> AsyncIterator[asyncpg.Connection]:
    conn = await asyncpg.connect(dsn)
    try:
        await _init_connection(conn)
        yield conn
    finally:
        await conn.close()
