from __future__ import annotations

from collections.abc import AsyncIterator
from typing import Annotated, cast

import asyncpg
from fastapi import Depends, Request


async def get_connection(request: Request) -> AsyncIterator[asyncpg.Connection]:
    pool: asyncpg.Pool = request.app.state.pool
    async with pool.acquire() as conn:
        # El pool entrega un proxy con la misma interfaz que Connection; asyncpg no lo declara así.
        yield cast(asyncpg.Connection, conn)


ConnectionDep = Annotated[asyncpg.Connection, Depends(get_connection)]
