"""Lo leído de la base se guarda en memoria solo dentro de una petición y solo mientras los datos no cambien."""

from __future__ import annotations

from collections.abc import Iterator
from typing import Any, cast

import asyncpg
import pytest

from oniel.repo import cache


@pytest.fixture(autouse=True)
def _empty_cache() -> Iterator[None]:
    cache.clear()
    yield
    cache.clear()


class _Loader:
    """Una lectura que cuenta las veces que se hace."""

    def __init__(self) -> None:
        self.calls = 0

    async def __call__(self) -> list[int]:
        self.calls += 1
        return [self.calls]


async def test_outside_a_request_nothing_is_kept() -> None:
    load = _Loader()
    assert not cache.active()
    assert await cache.remember("clave", load) == [1]
    assert await cache.remember("clave", load) == [2]


async def test_inside_a_request_a_reading_is_made_once() -> None:
    load = _Loader()
    with cache.session(7):
        assert cache.active()
        first = await cache.remember("clave", load)
        assert await cache.remember("clave", load) is first
        # otra clave es otra lectura
        assert await cache.remember("otra", load) == [2]
    # y otra petición con la misma versión de los datos la reutiliza
    with cache.session(7):
        assert await cache.remember("clave", load) is first
    assert load.calls == 2
    assert not cache.active()


async def test_a_new_data_version_discards_everything_kept() -> None:
    load = _Loader()
    with cache.session(7):
        await cache.remember("clave", load)
        await cache.remember("otra", load)
    with cache.session(8):
        assert await cache.remember("clave", load) == [3]
        assert await cache.remember("otra", load) == [4]
    # tampoco vuelve lo de la versión anterior si alguien la pide de nuevo
    with cache.session(7):
        assert await cache.remember("clave", load) == [5]


async def test_a_reading_made_with_a_stale_version_is_not_kept() -> None:
    load = _Loader()

    async def slow() -> list[int]:
        # mientras esta petición lee, otra ve una versión nueva de los datos
        with cache.session(8):
            await cache.remember("clave", load)
        return [0]

    with cache.session(7):
        assert await cache.remember("clave", slow) == [0]
    with cache.session(8):
        assert await cache.remember("clave", load) == [1]
    assert load.calls == 1


async def test_only_the_most_recently_used_entries_are_kept(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    monkeypatch.setattr(cache, "MAX_ENTRIES", 3)
    load = _Loader()
    with cache.session(1):
        for day in ("lunes", "martes", "miércoles"):
            await cache.remember(day, load)
        await cache.remember("lunes", load)  # el lunes se acaba de usar
        await cache.remember("jueves", load)  # y el martes, el más antiguo, deja su sitio
        assert load.calls == 4
        await cache.remember("lunes", load)
        await cache.remember("miércoles", load)
        await cache.remember("jueves", load)
        assert load.calls == 4
        await cache.remember("martes", load)
        assert load.calls == 5


async def test_a_database_without_the_migration_is_served_without_keeping_anything() -> None:
    class _NoTable:
        async def fetchval(self, *args: Any, **kwargs: Any) -> Any:
            raise asyncpg.UndefinedTableError('relation "data_version" does not exist')

    version = await cache.data_version(cast(asyncpg.Connection, _NoTable()))
    assert version is None
    cache.begin(version)
    assert not cache.active()
