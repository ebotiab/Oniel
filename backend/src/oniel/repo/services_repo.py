"""Servicios y pasos por tramo."""

from __future__ import annotations

import datetime as dt
from collections import Counter
from collections.abc import Iterable
from dataclasses import dataclass, field
from typing import Any

import asyncpg

from oniel.analysis.criticality import ServicePath
from oniel.domain.schemas import (
    DatasetOut,
    DestinationOperatorOut,
    DestinationOut,
    HistoryChangeOut,
    HistoryPointOut,
    HistoryProductOut,
    ServiceOut,
    StopOut,
)
from oniel.repo import datasets_repo
from oniel.repo.datasets_repo import active_ids_sql
from oniel.sim.passes import SegmentPass


@dataclass(frozen=True)
class DatedPass:
    service: ServiceOut
    segment_pass: SegmentPass
    from_previous_day: bool


def _service(r: asyncpg.Record) -> ServiceOut:
    return ServiceOut(
        id=r["id"],
        operator_id=r["operator_id"],
        train_number=r["train_number"],
        product=r["product"],
        origin_name=r["origin_name"],
        destination_name=r["destination_name"],
        resolution=r["resolution"],
        valid_from=r["valid_from"],
        valid_to=r["valid_to"],
    )


def _pass(r: asyncpg.Record) -> SegmentPass:
    return SegmentPass(
        segment_id=r["segment_id"],
        kind=r["kind"],
        enter_s=float(r["enter_s"]) if r["enter_s"] is not None else None,
        exit_s=float(r["exit_s"]) if r["exit_s"] is not None else None,
        enter_margin_s=float(r["enter_margin_s"] or 0),
        exit_margin_s=float(r["exit_margin_s"] or 0),
        km_increasing=r["km_increasing"],
        basis=r["basis"],
    )


#: Pasos por un tramo ($1) un día ($2), leídos de los conjuntos de datos activos ese día.
PASS_SQL = f"""
    SELECT p.*, s.id, s.operator_id, s.train_number, s.product, s.origin_name, s.destination_name,
           s.resolution, s.valid_from, s.valid_to
    FROM service_segment_passes p
    JOIN services s ON s.dataset_id = p.dataset_id AND s.id = p.service_id
    JOIN service_dates d
      ON d.dataset_id = s.dataset_id AND d.service_id = s.id AND d.service_date = $2
    WHERE p.segment_id = $1 AND p.dataset_id IN {active_ids_sql("$2")}
"""


async def passes_on_segment(
    conn: asyncpg.Connection, segment_id: str, date: dt.date
) -> list[DatedPass]:
    """Pasos del día pedido más los del día anterior que terminan después de medianoche."""
    today = await conn.fetch(PASS_SQL, segment_id, date)
    yesterday = await conn.fetch(
        PASS_SQL + " AND p.exit_s IS NOT NULL AND p.exit_s + p.exit_margin_s >= 86400",
        segment_id,
        date - dt.timedelta(days=1),
    )
    out = [DatedPass(_service(r), _pass(r), False) for r in today]
    out += [DatedPass(_service(r), _pass(r), True) for r in yesterday]
    out.sort(
        key=lambda d: (
            (d.segment_pass.enter_s if d.segment_pass.enter_s is not None else 1e9)
            - (86400 if d.from_previous_day else 0),
            d.service.train_number,
            d.service.id,
        )
    )
    return out


async def daily_counts(
    conn: asyncpg.Connection, date: dt.date, dataset_id: str | None = None
) -> dict[str, int]:
    """Pasos por tramo un día: de los conjuntos activos ese día o, si se da, de un conjunto concreto."""
    scope = "p.dataset_id = $2" if dataset_id else f"p.dataset_id IN {active_ids_sql('$1')}"
    rows = await conn.fetch(
        f"""
        SELECT p.segment_id, count(*) AS n
        FROM service_segment_passes p
        JOIN service_dates d ON d.dataset_id = p.dataset_id AND d.service_id = p.service_id
        WHERE d.service_date = $1 AND {scope} GROUP BY p.segment_id ORDER BY p.segment_id
        """,
        date,
        *([dataset_id] if dataset_id else []),
    )
    return {r["segment_id"]: r["n"] for r in rows}


async def daily_counts_by_operator(
    conn: asyncpg.Connection, date: dt.date
) -> dict[str, dict[str, int]]:
    """Pasos por tramo un día, separados por operador; solo de los conjuntos activos ese día.

    Por cada tramo, la suma de sus operadores es el recuento de :func:`daily_counts`.
    """
    rows = await conn.fetch(
        f"""
        SELECT p.segment_id, s.operator_id, count(*) AS n
        FROM service_segment_passes p
        JOIN services s ON s.dataset_id = p.dataset_id AND s.id = p.service_id
        JOIN service_dates d ON d.dataset_id = p.dataset_id AND d.service_id = p.service_id
        WHERE d.service_date = $1 AND p.dataset_id IN {active_ids_sql("$1")}
        GROUP BY p.segment_id, s.operator_id ORDER BY p.segment_id, s.operator_id
        """,
        date,
    )
    out: dict[str, dict[str, int]] = {}
    for r in rows:
        out.setdefault(r["segment_id"], {})[r["operator_id"]] = r["n"]
    return out


async def service_paths(conn: asyncpg.Connection, date: dt.date) -> list[ServicePath]:
    """Los trenes de un día con los tramos que recorre cada uno; de los conjuntos activos ese día.

    Cuenta los mismos pasos que :func:`daily_counts`: un tren por cada tramo que recorre.
    """
    rows = await conn.fetch(
        f"""
        SELECT p.service_id, s.operator_id, array_agg(p.segment_id ORDER BY p.segment_id) AS ids
        FROM service_segment_passes p
        JOIN services s ON s.dataset_id = p.dataset_id AND s.id = p.service_id
        JOIN service_dates d ON d.dataset_id = p.dataset_id AND d.service_id = p.service_id
        WHERE d.service_date = $1 AND p.dataset_id IN {active_ids_sql("$1")}
        GROUP BY p.dataset_id, p.service_id, s.operator_id ORDER BY p.service_id
        """,
        date,
    )
    return [ServicePath(r["service_id"], r["operator_id"], frozenset(r["ids"])) for r in rows]


async def fetch_service(
    conn: asyncpg.Connection, service_id: str
) -> tuple[ServiceOut, list[StopOut]] | None:
    # El mismo viaje puede estar en varios conjuntos de datos: se sirve el del más reciente.
    r = await conn.fetchrow(
        """
        SELECT s.* FROM services s JOIN datasets ds ON ds.id = s.dataset_id
        WHERE s.id = $1 ORDER BY ds.retrieved_on DESC, ds.valid_to DESC, ds.id DESC LIMIT 1
        """,
        service_id,
    )
    if r is None:
        return None
    stops = await conn.fetch(
        """
        SELECT ss.*, m.node_id FROM service_stops ss LEFT JOIN stop_mappings m ON m.stop_id = ss.stop_id
        WHERE ss.dataset_id = $1 AND ss.service_id = $2 ORDER BY ss.seq
        """,
        r["dataset_id"],
        service_id,
    )
    return _service(r), [
        StopOut(
            seq=s["seq"],
            stop_id=s["stop_id"],
            stop_name=s["stop_name"],
            arrival=fmt_time(s["arrival_s"]),
            departure=fmt_time(s["departure_s"]),
            node_id=s["node_id"],
        )
        for s in stops
    ]


async def calls_at_node(
    conn: asyncpg.Connection, node_id: str, date: dt.date
) -> list[dict[str, Any]]:
    rows = await conn.fetch(
        f"""
        SELECT s.id, s.operator_id, s.train_number, s.product, s.origin_name, s.destination_name, ss.arrival_s, ss.departure_s, ss.seq,
               ss.pickup_type, ss.drop_off_type,
               (SELECT max(seq) FROM service_stops x
                WHERE x.dataset_id = s.dataset_id AND x.service_id = s.id) AS last_seq
        FROM service_stops ss
        JOIN stop_mappings m ON m.stop_id = ss.stop_id AND m.node_id = $1
        JOIN services s ON s.dataset_id = ss.dataset_id AND s.id = ss.service_id
        JOIN service_dates d
          ON d.dataset_id = s.dataset_id AND d.service_id = s.id AND d.service_date = $2
        WHERE ss.dataset_id IN {active_ids_sql("$2")}
        ORDER BY ss.departure_s, s.train_number, s.id
        """,
        node_id,
        date,
    )
    return [
        {
            "service_id": r["id"],
            "operator_id": r["operator_id"],
            "train_number": r["train_number"],
            "product": r["product"],
            "origin_name": r["origin_name"],
            "destination_name": r["destination_name"],
            "arrival": None if r["seq"] == 1 else fmt_time(r["arrival_s"]),
            "departure": None if r["seq"] == r["last_seq"] else fmt_time(r["departure_s"]),
            # El fichero marca las paradas en las que un tren solo deja o solo recoge viajeros.
            "boards": r["pickup_type"] != 1 and r["seq"] != r["last_seq"],
            "alights": r["drop_off_type"] != 1 and r["seq"] != 1,
        }
        for r in rows
    ]


@dataclass(frozen=True)
class DirectStop:
    """Una parada posterior de un tren que para en el nodo de salida."""

    service_id: str
    operator_id: str
    product: str
    #: Salida del tren del nodo de salida, en segundos desde la medianoche del día de servicio.
    departure_s: float
    #: Nodo de la red en el que está la parada, si está en ella.
    node_id: str | None
    stop_id: str
    name: str


@dataclass
class _Destination:
    node_id: str | None
    stop_id: str
    name: str
    departures: dict[str, float] = field(default_factory=dict)
    products: Counter[str] = field(default_factory=Counter)
    operators: Counter[str] = field(default_factory=Counter)


def group_destinations(stops: Iterable[DirectStop]) -> list[DestinationOut]:
    """Agrupa las paradas posteriores de cada tren en destinos, del más frecuente al menos.

    Un destino es un nodo de la red o, fuera de ella, una parada del fichero de horarios. Cada tren
    cuenta una vez por destino aunque pare en dos paradas del mismo nodo.
    """
    found: dict[str, _Destination] = {}
    for stop in stops:
        dest = found.setdefault(
            stop.node_id or stop.stop_id, _Destination(stop.node_id, stop.stop_id, stop.name)
        )
        if stop.service_id in dest.departures:
            continue
        dest.departures[stop.service_id] = stop.departure_s
        dest.products[stop.product] += 1
        dest.operators[stop.operator_id] += 1
    out = [
        DestinationOut(
            node_id=d.node_id,
            stop_id=d.stop_id,
            name=d.name,
            trains=len(d.departures),
            products=[p for p, _ in sorted(d.products.items(), key=lambda kv: (-kv[1], kv[0]))],
            operators=[
                DestinationOperatorOut(operator_id=o, trains=n)
                for o, n in sorted(d.operators.items(), key=lambda kv: (-kv[1], kv[0]))
            ],
            first_departure=fmt_time(min(d.departures.values())),
            last_departure=fmt_time(max(d.departures.values())),
        )
        for d in found.values()
    ]
    return sorted(out, key=lambda d: (-d.trains, d.name))


async def destinations_from_node(
    conn: asyncpg.Connection, node_id: str, date: dt.date
) -> list[DestinationOut]:
    """Estaciones a las que se llega sin cambiar de tren desde un nodo, un día.

    De cada tren que para en el nodo ese día (conjuntos de datos activos) y admite viajeros allí,
    las paradas posteriores en las que se puede bajar: el fichero de horarios marca las paradas en
    las que un tren solo deja o solo recoge viajeros (``pickup_type`` y ``drop_off_type``). Las que
    están en la red llevan el nombre del nodo; las demás, el de la parada en el fichero. Es el
    mismo criterio con el que el comparador de recorridos cuenta los trenes directos.
    """
    rows = await conn.fetch(
        f"""
        WITH origin AS (
            SELECT ss.dataset_id, ss.service_id, min(ss.seq) AS seq
            FROM service_stops ss
            JOIN stop_mappings m ON m.stop_id = ss.stop_id AND m.node_id = $1
            JOIN service_dates d ON d.dataset_id = ss.dataset_id
             AND d.service_id = ss.service_id AND d.service_date = $2
            WHERE ss.dataset_id IN {active_ids_sql("$2")} AND ss.pickup_type IS DISTINCT FROM 1
            GROUP BY ss.dataset_id, ss.service_id
        )
        SELECT s.id, s.operator_id, s.product, o_stop.departure_s, m.node_id, ss.stop_id,
               coalesce(n.name, ss.stop_name) AS name
        FROM origin o
        JOIN service_stops o_stop ON o_stop.dataset_id = o.dataset_id
         AND o_stop.service_id = o.service_id AND o_stop.seq = o.seq
        JOIN services s ON s.dataset_id = o.dataset_id AND s.id = o.service_id
        JOIN service_stops ss ON ss.dataset_id = o.dataset_id
         AND ss.service_id = o.service_id AND ss.seq > o.seq
        LEFT JOIN stop_mappings m ON m.stop_id = ss.stop_id
        LEFT JOIN (SELECT DISTINCT id, name FROM nodes) n ON n.id = m.node_id
        WHERE m.node_id IS DISTINCT FROM $1 AND ss.drop_off_type IS DISTINCT FROM 1
        ORDER BY s.id, ss.seq
        """,
        node_id,
        date,
    )
    return group_destinations(
        DirectStop(
            service_id=r["id"],
            operator_id=r["operator_id"],
            product=r["product"],
            departure_s=r["departure_s"],
            node_id=r["node_id"],
            stop_id=r["stop_id"],
            name=r["name"],
        )
        for r in rows
    )


#: Conjuntos ($2) con el día de referencia de cada uno ($3), para contar cada uno en el suyo.
_REFS_SQL = "SELECT * FROM unnest($2::text[], $3::date[]) AS r(dataset_id, day)"

#: Trenes que paran en un nodo ($1), por conjunto y tipo de servicio: las mismas filas que
#: :func:`calls_at_node`, sin limitarse a los conjuntos activos.
NODE_HISTORY_SQL = f"""
    WITH refs AS ({_REFS_SQL})
    SELECT r.dataset_id, s.product, count(*) AS n
    FROM refs r
    JOIN service_stops ss ON ss.dataset_id = r.dataset_id
    JOIN stop_mappings m ON m.stop_id = ss.stop_id AND m.node_id = $1
    JOIN services s ON s.dataset_id = ss.dataset_id AND s.id = ss.service_id
    JOIN service_dates d
      ON d.dataset_id = s.dataset_id AND d.service_id = s.id AND d.service_date = r.day
    GROUP BY r.dataset_id, s.product
"""

#: Trenes que recorren un tramo ($1), por conjunto y tipo de servicio: los pasos del día y los del
#: día anterior que terminan pasada la medianoche, como :func:`passes_on_segment`.
SEGMENT_HISTORY_SQL = f"""
    WITH refs AS ({_REFS_SQL})
    SELECT r.dataset_id, s.product, count(*) AS n
    FROM refs r
    JOIN service_segment_passes p ON p.dataset_id = r.dataset_id AND p.segment_id = $1
    JOIN services s ON s.dataset_id = p.dataset_id AND s.id = p.service_id
    JOIN service_dates d ON d.dataset_id = s.dataset_id AND d.service_id = s.id
     AND (d.service_date = r.day
          OR (d.service_date = r.day - 1
              AND p.exit_s IS NOT NULL AND p.exit_s + p.exit_margin_s >= 86400))
    GROUP BY r.dataset_id, s.product
"""


#: Días que se comparan entre un conjunto y el anterior: las cuatro semanas con las que el refresco
#: de horarios decide si un fichero trae cambios (``oniel.gtfs.refresh``).
CHANGE_WINDOW_DAYS = 28

#: Ventanas ($2 conjunto, $3 primer día, $4 último día, $5 número de la ventana).
_WINDOWS_SQL = """
    SELECT * FROM unnest($2::text[], $3::date[], $4::date[], $5::int[])
        AS w(dataset_id, d_from, d_to, k)
"""

#: Trenes que paran en un nodo ($1) en cada ventana de días, uno por tren y día.
NODE_WINDOW_SQL = f"""
    WITH windows AS ({_WINDOWS_SQL})
    SELECT w.k, count(*) AS n
    FROM windows w
    JOIN service_stops ss ON ss.dataset_id = w.dataset_id
    JOIN stop_mappings m ON m.stop_id = ss.stop_id AND m.node_id = $1
    JOIN service_dates d ON d.dataset_id = ss.dataset_id AND d.service_id = ss.service_id
     AND d.service_date BETWEEN w.d_from AND w.d_to
    GROUP BY w.k
"""

#: Trenes que recorren un tramo ($1) en cada ventana de días, por su día de servicio.
SEGMENT_WINDOW_SQL = f"""
    WITH windows AS ({_WINDOWS_SQL})
    SELECT w.k, count(*) AS n
    FROM windows w
    JOIN service_segment_passes p ON p.dataset_id = w.dataset_id AND p.segment_id = $1
    JOIN service_dates d ON d.dataset_id = p.dataset_id AND d.service_id = p.service_id
     AND d.service_date BETWEEN w.d_from AND w.d_to
    GROUP BY w.k
"""


async def _changes(
    conn: asyncpg.Connection, sql: str, entity_id: str, datasets: list[DatasetOut]
) -> dict[str, HistoryChangeOut]:
    """Cada conjunto frente al anterior de su fuente, contados los dos en los mismos días.

    El día de referencia de dos ficheros seguidos suele ser el mismo o caer en semanas distintas,
    así que no dice qué cambió de uno a otro. Lo dice contar los dos en los mismos días: las
    primeras cuatro semanas del fichero nuevo, hasta donde lleguen los dos.
    """
    pairs: list[tuple[DatasetOut, DatasetOut, dt.date, dt.date]] = []
    last: dict[str, DatasetOut] = {}
    for d in datasets:
        previous = last.get(d.source_id)
        last[d.source_id] = d
        if previous is None:
            continue
        start = max(previous.valid_from, d.valid_from)
        end = min(start + dt.timedelta(days=CHANGE_WINDOW_DAYS - 1), previous.valid_to, d.valid_to)
        if start <= end:
            pairs.append((previous, d, start, end))
    if not pairs:
        return {}
    # dos ventanas por pareja: la del conjunto anterior (par) y la del nuevo (impar)
    rows = await conn.fetch(
        sql,
        entity_id,
        [d.id for previous, new, _, _ in pairs for d in (previous, new)],
        [start for _, _, start, _ in pairs for _ in range(2)],
        [end for _, _, _, end in pairs for _ in range(2)],
        list(range(2 * len(pairs))),
    )
    counts = {r["k"]: r["n"] for r in rows}
    return {
        new.id: HistoryChangeOut(
            previous_dataset_id=previous.id,
            previous_retrieved_on=previous.retrieved_on,
            date_from=start,
            date_to=end,
            trains_before=counts.get(2 * i, 0),
            trains_after=counts.get(2 * i + 1, 0),
        )
        for i, (previous, new, start, end) in enumerate(pairs)
    }


async def _history(
    conn: asyncpg.Connection,
    sql: str,
    window_sql: str,
    entity_id: str,
    refs: dict[str, dt.date] | None,
) -> list[HistoryPointOut]:
    """Un punto por conjunto de datos, del descargado antes al más reciente.

    Cada conjunto se cuenta en su propio día de referencia y sin mirar cuál está activo: es lo que
    decía ese fichero de horarios cuando se descargó. Un conjunto sin trenes aquí da un punto con
    cero, que también es un dato (el de otro operador, o una estación que se queda sin servicio).
    """
    if refs is None:
        refs = await datasets_repo.reference_dates(conn)
    datasets = [d for d in await datasets_repo.fetch_datasets(conn) if d.id in refs]
    rows = await conn.fetch(
        sql, entity_id, [d.id for d in datasets], [refs[d.id] for d in datasets]
    )
    by_dataset: dict[str, Counter[str]] = {}
    for r in rows:
        by_dataset.setdefault(r["dataset_id"], Counter())[r["product"]] = r["n"]
    changes = await _changes(conn, window_sql, entity_id, datasets)
    points = []
    for d in datasets:
        products = by_dataset.get(d.id, Counter())
        points.append(
            HistoryPointOut(
                dataset_id=d.id,
                source_id=d.source_id,
                operator_id=d.operator_id,
                retrieved_on=d.retrieved_on,
                date=refs[d.id],
                trains=sum(products.values()),
                products=[
                    HistoryProductOut(product=p, trains=n)
                    for p, n in sorted(products.items(), key=lambda kv: (-kv[1], kv[0]))
                ],
                change=changes.get(d.id),
            )
        )
    return points


async def node_history(
    conn: asyncpg.Connection, node_id: str, refs: dict[str, dt.date] | None = None
) -> list[HistoryPointOut]:
    """Trenes que paran en un nodo según cada conjunto de datos, en el día de referencia de cada uno.

    ``refs`` son los días de referencia ya calculados (:func:`datasets_repo.reference_dates`), para
    no repetirlos al exportar todos los nodos.
    """
    return await _history(conn, NODE_HISTORY_SQL, NODE_WINDOW_SQL, node_id, refs)


async def segment_history(
    conn: asyncpg.Connection, segment_id: str, refs: dict[str, dt.date] | None = None
) -> list[HistoryPointOut]:
    """Trenes que recorren un tramo según cada conjunto de datos, en su día de referencia."""
    return await _history(conn, SEGMENT_HISTORY_SQL, SEGMENT_WINDOW_SQL, segment_id, refs)


def fmt_time(seconds: float) -> str:
    """Segundos desde la medianoche del día de servicio → ``HH:MM``, con ``(+1)`` pasada la medianoche."""
    s = round(seconds)
    h, rem = divmod(s, 3600)
    suffix = " (+1)" if h >= 24 else ""
    return f"{h % 24:02d}:{rem // 60:02d}{suffix}"
