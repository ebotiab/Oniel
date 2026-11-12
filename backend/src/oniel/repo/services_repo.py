"""Servicios y pasos por tramo."""

from __future__ import annotations

import datetime as dt
from dataclasses import dataclass
from typing import Any

import asyncpg

from oniel.domain.schemas import ServiceOut, StopOut
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
        }
        for r in rows
    ]


def fmt_time(seconds: float) -> str:
    """Segundos desde la medianoche del día de servicio → ``HH:MM``, con ``(+1)`` pasada la medianoche."""
    s = round(seconds)
    h, rem = divmod(s, 3600)
    suffix = " (+1)" if h >= 24 else ""
    return f"{h % 24:02d}:{rem // 60:02d}{suffix}"
