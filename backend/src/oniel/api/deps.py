from __future__ import annotations

from collections.abc import AsyncIterator
from typing import Annotated, cast

import asyncpg
from fastapi import Depends, Request

from oniel.repo import cache


async def get_connection(request: Request) -> AsyncIterator[asyncpg.Connection]:
    pool: asyncpg.Pool = request.app.state.pool
    async with pool.acquire() as conn:
        # El pool entrega un proxy con la misma interfaz que Connection; asyncpg no lo declara así.
        connection = cast(asyncpg.Connection, conn)
        # La versión de los datos, una vez por petición: con ella el repositorio reutiliza lo que
        # ya leyó de la red y de los horarios mientras nadie los haya cambiado (`oniel.repo.cache`).
        cache.begin(await cache.data_version(connection))
        yield connection


ConnectionDep = Annotated[asyncpg.Connection, Depends(get_connection)]
