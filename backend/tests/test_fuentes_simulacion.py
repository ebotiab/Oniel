"""Atribución de los horarios que aportan trenes a un cierre."""

from types import SimpleNamespace
from unittest.mock import AsyncMock

import pytest
from conftest import SOURCES

from oniel.network.spec import NetworkSpec, load_feeds, load_sources
from oniel.sim import service


@pytest.fixture
def catalog(spec: NetworkSpec, monkeypatch: pytest.MonkeyPatch) -> dict[str, str]:
    feeds = load_feeds(SOURCES)
    datasets = [SimpleNamespace(id=f.file, source_id=f.source_id) for f in feeds]
    renfe = next(f for f in feeds if f.operator_id == "renfe")
    datasets.append(SimpleNamespace(id="edición anterior", source_id=renfe.source_id))
    monkeypatch.setattr(service, "fetch_datasets", AsyncMock(return_value=datasets))
    monkeypatch.setattr(service, "fetch_sources", AsyncMock(return_value=load_sources(SOURCES)))
    monkeypatch.setattr(service, "fetch_operators", AsyncMock(return_value=spec.operators))
    return {f.operator_id: f.file for f in feeds}


async def test_el_cierre_cita_las_tres_fuentes_y_distingue_la_compilacion_de_iryo(
    catalog: dict[str, str],
) -> None:
    used = {(op, catalog[op]) for op in ("renfe", "ouigo", "iryo")}
    credits = await service.timetable_credits(AsyncMock(), used)
    assert len(credits) == 3
    assert any("Renfe Viajeros" in c and "larga distancia" in c for c in credits)
    assert any("Ouigo España" in c and "Horarios de alta velocidad" in c for c in credits)
    assert any("Iryo" in c and "compilación no oficial" in c for c in credits)


async def test_un_tramo_con_un_solo_operador_cita_una_vez_la_fuente_aunque_haya_dos_versiones(
    catalog: dict[str, str],
) -> None:
    used = {("renfe", catalog["renfe"]), ("renfe", "edición anterior")}
    credits = await service.timetable_credits(AsyncMock(), used)
    assert len(credits) == 1
    assert "Renfe Viajeros" in credits[0]
    assert all(name not in credits[0] for name in ("Ouigo", "Iryo"))


async def test_sin_trenes_no_se_atribuyen_horarios_a_ningun_operador() -> None:
    conn = AsyncMock()
    assert await service.timetable_credits(conn, set()) == [
        "No hay servicios en los horarios consultados para este tramo y esta fecha."
    ]
    conn.fetch.assert_not_awaited()
