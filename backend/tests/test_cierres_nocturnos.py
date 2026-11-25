"""Pasos de los días contiguos y límites de la franja de cierre."""

import datetime as dt
from typing import Any
from unittest.mock import AsyncMock

import pytest

from oniel.domain.schemas import ClosureRequest, SegmentOut
from oniel.sim import service

DAY = dt.date(2026, 11, 19)
SEGMENT = SegmentOut(
    id="lav-madrid-sevilla:ciudad-real:puertollano",
    line_id="lav-madrid-sevilla",
    seq=1,
    from_node_id="ciudad-real",
    from_name="Ciudad Real",
    to_node_id="puertollano",
    to_name="Puertollano",
    km_from=170.0,
    km_to=209.0,
    length_km=39.0,
    status="disponible",
)


def row(number: str, hour: int, minute: int, *, margin: int = 0) -> dict[str, Any]:
    enter = (hour * 60 + minute) * 60
    return {
        "id": number,
        "operator_id": "renfe",
        "train_number": number,
        "product": "AVE",
        "origin_name": "Madrid",
        "destination_name": "Sevilla",
        "resolution": "completa",
        "valid_from": DAY,
        "valid_to": DAY + dt.timedelta(days=1),
        "segment_id": SEGMENT.id,
        "kind": "estimado" if margin else "publicado",
        "enter_s": enter,
        "exit_s": enter + 12 * 60,
        "enter_margin_s": margin,
        "exit_margin_s": margin,
        "km_increasing": True,
        "basis": "Horario de prueba.",
    }


@pytest.fixture
def connection(monkeypatch: pytest.MonkeyPatch) -> AsyncMock:
    monkeypatch.setattr(service, "fetch_interruptions", AsyncMock(return_value=[]))
    monkeypatch.setattr(service, "fetch_graph", AsyncMock())
    monkeypatch.setattr(service, "alternatives", lambda *_: ([], 0))
    return AsyncMock()


def request(start: int, end: int, day: dt.date = DAY) -> ClosureRequest:
    return ClosureRequest(segment_id=SEGMENT.id, date=day, start=dt.time(start), end=dt.time(end))


@pytest.mark.parametrize("start", [23, 8], ids=["cruza la medianoche", "dura 24 horas"])
async def test_el_02061_del_dia_siguiente_entra_una_vez_y_se_respetan_los_limites(
    connection: AsyncMock, start: int
) -> None:
    today = [row("02061", 7, 31), row("nocturno", 24, 15)]
    tomorrow = [row("02061", 7, 31), row("límite", 8, 0), row("margen", 8, 2, margin=300)]
    connection.fetch.side_effect = [today, [], tomorrow]
    result = await service.simulate_closure(connection, SEGMENT, request(start, 8))

    assert [call.args[1:] for call in connection.fetch.await_args_list] == [
        (SEGMENT.id, DAY),
        (SEGMENT.id, DAY - dt.timedelta(days=1)),
        (SEGMENT.id, DAY + dt.timedelta(days=1), 8 * 3600),
    ]
    assert [(i.service.train_number, i.status, i.from_next_day) for i in result.items] == [
        ("nocturno", "afectado_publicado", False),
        ("02061", "afectado_publicado", True),
        ("margen", "indeterminado", True),
        ("02061", "no_afectado", False),
    ]
    assert sum(result.counts.values()) == 4
    next_train = next(i for i in result.items if i.from_next_day and i.service.id == "02061")
    assert (next_train.enter, next_train.exit) == ("07:31", "07:43")


@pytest.mark.parametrize(
    ("start", "end", "previous_affected"),
    [(23, 0, False), (0, 8, True)],
    ids=["termina a medianoche", "empieza a medianoche"],
)
async def test_el_cierre_que_no_entra_en_la_manana_siguiente_solo_consulta_hoy_y_ayer(
    connection: AsyncMock, start: int, end: int, previous_affected: bool
) -> None:
    connection.fetch.side_effect = [[row("02061", 7, 31)], [row("nocturno", 24, 15)]]
    result = await service.simulate_closure(connection, SEGMENT, request(start, end))
    assert connection.fetch.await_count == 2
    assert [i.service.id for i in result.items if i.from_previous_day] == (
        ["nocturno"] if previous_affected else []
    )
    assert not any(i.from_next_day for i in result.items)
