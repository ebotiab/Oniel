"""Lo leído de la base, guardado en memoria mientras los datos no cambien.

La red y los horarios solo cambian al importar. Aun así cada petición volvía a leerlos enteros:
abrir una línea eran diez consultas, dos de ellas sobre los horarios de toda la red. Aquí se
guardan esas lecturas con la versión de los datos con la que se hicieron.

La versión es un número que la base sube en cada transacción que escribe en una tabla de la red o
de los horarios (migración ``0014_version_de_datos``). La API la lee una vez al empezar cada
petición (:func:`session`, desde ``oniel.api.deps``): si es la misma, lo guardado vale; si ha
cambiado, se tira todo y se vuelve a leer. No se supone que los datos no cambian mientras el
proceso vive: se comprueba en cada petición, con una consulta en lugar de diez.

Fuera de una petición (la importación, la exportación de la instantánea, las pruebas que llaman al
repositorio directamente) no hay versión leída y :func:`remember` no guarda nada: lee siempre.

Lo guardado se comparte entre peticiones: quien lo recibe no lo modifica.
"""

from __future__ import annotations

from collections import OrderedDict
from collections.abc import Awaitable, Callable, Hashable, Iterator
from contextlib import contextmanager
from contextvars import ContextVar
from typing import Any, cast

import asyncpg

from oniel.db.pool import fetch_int

#: Entradas que se guardan como mucho. Las que no dependen de un día son una docena; el resto del
#: sitio es para las que sí (los recuentos de cada día pedido), y sale primero la que lleva más
#: tiempo sin usarse. Así pedir muchos días distintos no hace crecer la memoria sin fin.
MAX_ENTRIES = 128

#: Versión de los datos leída para la petición en curso; ``None`` fuera de una petición.
_current: ContextVar[int | None] = ContextVar("oniel_data_version", default=None)


class _Store:
    def __init__(self) -> None:
        self.version: int | None = None
        self.entries: OrderedDict[Hashable, Any] = OrderedDict()

    def at(self, version: int) -> OrderedDict[Hashable, Any]:
        """Las entradas de esa versión; las de cualquier otra se tiran."""
        if self.version != version:
            self.entries.clear()
            self.version = version
        return self.entries


_store = _Store()


async def data_version(conn: asyncpg.Connection) -> int | None:
    """La versión actual de los datos en la base; ``None`` si la base aún no la lleva.

    Una base sin la migración aplicada (la API arrancada antes de importar) no tiene la tabla: se
    sirve igual, leyendo siempre.
    """
    try:
        return await fetch_int(conn, "SELECT version FROM data_version")
    except asyncpg.UndefinedTableError:
        return None


@contextmanager
def session(version: int) -> Iterator[None]:
    """Dentro de este bloque, :func:`remember` guarda y reutiliza lo leído con esa versión."""
    token = _current.set(version)
    try:
        yield
    finally:
        _current.reset(token)


def begin(version: int | None) -> None:
    """Como :func:`session`, para quien no puede envolver su trabajo en un bloque ``with``.

    Una dependencia de FastAPI se cierra a veces en un contexto distinto del que la abrió, y allí
    no se puede deshacer el cambio. No hace falta: cada petición tiene su propio contexto.
    """
    _current.set(version)


def active() -> bool:
    """Si hay una versión leída, es decir, si :func:`remember` va a guardar lo que lea."""
    return _current.get() is not None


async def remember[T](key: Hashable, load: Callable[[], Awaitable[T]]) -> T:
    """Lo guardado con esa clave para la versión en curso o, si no está, lo que devuelva ``load``."""
    version = _current.get()
    if version is None:
        return await load()
    entries = _store.at(version)
    if key in entries:
        entries.move_to_end(key)
        return cast(T, entries[key])
    value = await load()
    # Mientras se leía, otra petición puede haber visto una versión nueva y vaciado lo guardado:
    # lo de esta ya no se guarda.
    if _store.version == version:
        entries[key] = value
        entries.move_to_end(key)
        while len(entries) > MAX_ENTRIES:
            entries.popitem(last=False)
    return value


def clear() -> None:
    """Olvida todo lo guardado (para las pruebas)."""
    _store.version = None
    _store.entries.clear()
