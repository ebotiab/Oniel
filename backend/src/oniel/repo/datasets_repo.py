"""Conjuntos de datos: cada fichero de horarios importado, con su fuente, su fecha y su validez.

Dos reglas deciden qué conjunto se usa:

- El **vigente** de una fuente es el descargado más recientemente. Con los vigentes se calculan el
  día de referencia y las cifras de la cobertura.
- El **activo** de una fuente en un día es el más reciente cuya validez incluye ese día. Las
  consultas con fecha (pasos por un tramo, paradas en una estación, recuentos) leen solo los
  conjuntos activos ese día, de modo que un fichero nuevo sustituye al anterior sin borrarlo.

Se decide por fuente y no por operador porque un operador puede publicar varios ficheros que no se
sustituyen entre sí (alta velocidad y cercanías, por ejemplo).
"""

from __future__ import annotations

import datetime as dt

import asyncpg

from oniel.domain.schemas import DatasetOut

#: Ids de los conjuntos vigentes: el más reciente de cada fuente.
CURRENT_IDS_SQL = """
    (SELECT DISTINCT ON (source_id) id FROM datasets
     ORDER BY source_id, retrieved_on DESC, valid_to DESC, id DESC)
"""


def active_ids_sql(param: str) -> str:
    """Subconsulta con los ids de los conjuntos activos el día del parámetro (``$1``, ``$2``…)."""
    return f"""
        (SELECT DISTINCT ON (source_id) id FROM datasets
         WHERE {param}::date BETWEEN valid_from AND valid_to
         ORDER BY source_id, retrieved_on DESC, valid_to DESC, id DESC)
    """


def _dataset(r: asyncpg.Record) -> DatasetOut:
    return DatasetOut(
        id=r["id"],
        source_id=r["source_id"],
        operator_id=r["operator_id"],
        file=r["file"],
        sha256=r["sha256"],
        retrieved_on=r["retrieved_on"],
        valid_from=r["valid_from"],
        valid_to=r["valid_to"],
    )


async def fetch_datasets(conn: asyncpg.Connection) -> list[DatasetOut]:
    """Todos los conjuntos guardados, del más antiguo al más reciente."""
    rows = await conn.fetch("SELECT * FROM datasets ORDER BY retrieved_on, id")
    return [_dataset(r) for r in rows]


async def fetch_active_datasets(conn: asyncpg.Connection, date: dt.date) -> list[DatasetOut]:
    rows = await conn.fetch(
        f"SELECT * FROM datasets WHERE id IN {active_ids_sql('$1')} ORDER BY source_id", date
    )
    return [_dataset(r) for r in rows]


async def feed_bounds(
    conn: asyncpg.Connection, dataset_id: str | None = None
) -> tuple[dt.date | None, dt.date | None, dt.date | None]:
    """Primer y último día con servicio y día de referencia, de un conjunto o de los vigentes.

    Con varios conjuntos vigentes (uno por fuente: cada operador publica el suyo) los días son los
    que cubren todos a la vez, del comienzo más tardío al final más temprano, para que el día de
    referencia tenga los trenes de todos los operadores. Si no coinciden en ningún día, se devuelve
    el periodo que cubren entre todos. El día de referencia es el laborable con más servicios de
    los primeros treinta días.
    """
    scope = "dataset_id = $1" if dataset_id else f"dataset_id IN {CURRENT_IDS_SQL}"
    args = [dataset_id] if dataset_id else []
    r = await conn.fetchrow(
        f"""
        SELECT max(a) AS a, min(b) AS b, min(a) AS first, max(b) AS last
        FROM (SELECT min(service_date) AS a, max(service_date) AS b
              FROM service_dates WHERE {scope} GROUP BY dataset_id) per_dataset
        """,
        *args,
    )
    if r is None or r["a"] is None:
        return None, None, None
    start, end = (r["a"], r["b"]) if r["a"] <= r["b"] else (r["first"], r["last"])
    n = len(args) + 1
    ref = await conn.fetchrow(
        f"""
        SELECT service_date FROM service_dates
        WHERE {scope} AND service_date BETWEEN ${n} AND least(${n} + 30, ${n + 1})
          AND extract(isodow FROM service_date) <= 5
        GROUP BY service_date ORDER BY count(*) DESC, service_date LIMIT 1
        """,
        *args,
        start,
        end,
    )
    return start, end, ref["service_date"] if ref else start


async def reference_dates(conn: asyncpg.Connection) -> dict[str, dt.date]:
    """Día de referencia propio de cada conjunto guardado; sin los que no tienen ningún servicio."""
    out: dict[str, dt.date] = {}
    for dataset in await fetch_datasets(conn):
        _, _, ref = await feed_bounds(conn, dataset.id)
        if ref is not None:
            out[dataset.id] = ref
    return out
