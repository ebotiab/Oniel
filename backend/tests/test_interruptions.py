"""Interrupciones del servicio: esquema del fichero curado y validación contra la red y las fuentes."""

from __future__ import annotations

import datetime as dt
import json
from pathlib import Path
from typing import Any

import pytest
from conftest import DATA_DIR, SOURCES, SPEC
from pydantic import ValidationError
from typer.testing import CliRunner

from oniel.domain.interruptions import schedule_note, source_label, spanish_date
from oniel.network.interruptions import check_interruptions
from oniel.network.spec import InterruptionSpec, load_interruptions, load_sources
from oniel.validate import validate_interruptions

INTERRUPTIONS = DATA_DIR / "curated" / "interrupciones.json"
CONV_SPEC = DATA_DIR / "curated" / "convencional-madrid-alcazar-cordoba.json"
SPECS = [SPEC, CONV_SPEC]

#: Una línea de juguete, con sus nodos en el orden del kilometraje.
LINE_NODES = {"linea": ["a", "b", "c", "d"]}
SOURCE_URLS: dict[str, str | None] = {"aviso": "https://example.org/aviso", "sin-url": None}


def entry(**changes: Any) -> dict[str, Any]:
    base: dict[str, Any] = {
        "id": "corte",
        "line_id": "linea",
        "from_node": "b",
        "to_node": "d",
        "start_date": "2026-03-01",
        "reason": "Obras en la vía.",
        "source_ids": ["aviso"],
        "checked_on": "2026-03-10",
    }
    return {**base, **changes}


def spec(**changes: Any) -> InterruptionSpec:
    return InterruptionSpec.model_validate(entry(**changes))


def test_the_curated_file_loads_and_every_entry_has_source_and_check_date() -> None:
    interruptions = load_interruptions(INTERRUPTIONS)
    assert {i.id for i in interruptions} >= {
        "lav-madrid-andalucia-2026-10-28",
        "convencional-obras-autopista-ferroviaria-2026-09-06",
    }
    sources = {s.id: s for s in load_sources(SOURCES)}
    for i in interruptions:
        assert i.source_ids and i.checked_on >= i.start_date
        for source_id in i.source_ids:
            # cada fuente está registrada con URL, licencia y fecha de consulta
            source = sources[source_id]
            assert source.url and source.license and source.retrieved_on


def test_the_curated_file_fits_the_loaded_lines() -> None:
    report = validate_interruptions(INTERRUPTIONS, SOURCES, SPECS, DATA_DIR)
    assert report["problems"] == []
    assert len(report["entries"]) == len(load_interruptions(INTERRUPTIONS))


@pytest.mark.parametrize(
    ("changes", "message"),
    [
        ({"expected_end_date": "2026-02-01"}, "prevé terminar antes de empezar"),
        ({"ended_on": "2026-02-01"}, "termina antes de empezar"),
        ({"ended_on": "2026-03-20"}, "termina después de la fecha de consulta"),
        ({"to_node": "b"}, "empieza y termina en el mismo nodo"),
        ({"source_ids": []}, "source_ids"),
        ({"source_ids": ["aviso", "aviso"]}, "repite fuentes"),
        ({"reason": ""}, "reason"),
        ({"start_date": "primavera"}, "start_date"),
        ({"motivo": "campo que no existe"}, "motivo"),
    ],
)
def test_an_entry_with_inconsistent_fields_is_rejected(
    changes: dict[str, Any], message: str
) -> None:
    with pytest.raises(ValidationError, match=message):
        spec(**changes)


@pytest.mark.parametrize("missing", ["checked_on", "source_ids", "start_date", "reason"])
def test_an_entry_without_a_required_field_is_rejected(missing: str) -> None:
    raw = entry()
    del raw[missing]
    with pytest.raises(ValidationError, match=missing):
        InterruptionSpec.model_validate(raw)


def test_an_interruption_is_active_from_its_start_until_the_day_service_resumes() -> None:
    open_ended = spec()
    assert not open_ended.active_on(dt.date(2026, 2, 28))
    assert open_ended.active_on(dt.date(2026, 3, 1))
    assert open_ended.active_on(dt.date(2030, 1, 1))
    ended = spec(ended_on="2026-03-08")
    assert ended.active_on(dt.date(2026, 3, 7))
    # ended_on es el día en que vuelve a haber trenes
    assert not ended.active_on(dt.date(2026, 3, 8))


def test_nodes_in_line_order_and_registered_sources_give_no_problems() -> None:
    assert check_interruptions([spec()], LINE_NODES, SOURCE_URLS) == []
    # dos nodos consecutivos (un solo tramo) o separados: basta con que estén en orden
    assert check_interruptions([spec(from_node="a", to_node="b")], LINE_NODES, SOURCE_URLS) == []


@pytest.mark.parametrize(
    ("changes", "message"),
    [
        ({"line_id": "otra"}, "apunta a la línea otra, que no está cargada"),
        ({"to_node": "z"}, "el nodo z no pertenece a la línea linea"),
        ({"from_node": "d", "to_node": "b"}, "d está después de b"),
        ({"source_ids": ["desconocida"]}, "cita la fuente desconocida"),
        ({"source_ids": ["sin-url", "aviso"]}, "su fuente principal, sin-url, no tiene URL"),
    ],
)
def test_an_entry_that_does_not_fit_the_network_or_the_sources_is_a_problem(
    changes: dict[str, Any], message: str
) -> None:
    problems = check_interruptions([spec(**changes)], LINE_NODES, SOURCE_URLS)
    assert len(problems) == 1 and message in problems[0]


def _write(tmp_path: Path, *entries: dict[str, Any]) -> Path:
    path = tmp_path / "interrupciones.json"
    path.write_text(json.dumps({"interruptions": list(entries)}), encoding="utf-8")
    return path


def test_validate_reports_a_node_that_is_not_in_the_line(tmp_path: Path) -> None:
    path = _write(
        tmp_path,
        entry(
            line_id="lav-madrid-sevilla",
            from_node="ciudad-real",
            to_node="linares-baeza",  # es de la línea convencional
            source_ids=["adif-estado-de-la-red"],
        ),
    )
    report = validate_interruptions(path, SOURCES, SPECS, DATA_DIR)
    assert report["problems"] == [
        "la interrupción corte: el nodo linares-baeza no pertenece a la línea lav-madrid-sevilla"
    ]


def test_validate_reports_nodes_against_the_direction_of_the_line(tmp_path: Path) -> None:
    path = _write(
        tmp_path,
        entry(
            line_id="lav-madrid-sevilla",
            from_node="cordoba",
            to_node="ciudad-real",
            source_ids=["adif-estado-de-la-red"],
        ),
    )
    (problem,) = validate_interruptions(path, SOURCES, SPECS, DATA_DIR)["problems"]
    assert "cordoba está después de ciudad-real" in problem


def test_validate_reports_a_file_that_breaks_the_schema(tmp_path: Path) -> None:
    path = _write(tmp_path, entry(ended_on="2026-01-01"), entry())
    (problem,) = validate_interruptions(path, SOURCES, SPECS, DATA_DIR)["problems"]
    assert "termina antes de empezar" in problem
    repeated = _write(tmp_path, entry(), entry())
    (problem,) = validate_interruptions(repeated, SOURCES, SPECS, DATA_DIR)["problems"]
    assert "ids de interrupción repetidos" in problem


def test_the_validate_command_fails_when_the_interruptions_do_not_fit(tmp_path: Path) -> None:
    from oniel.cli.main import app

    path = _write(tmp_path, entry(line_id="lav-madrid-sevilla", from_node="nada", to_node="urda"))
    result = CliRunner().invoke(app, ["validate", "--interruptions", str(path)])
    assert result.exit_code == 1
    assert "el nodo nada no pertenece a la línea lav-madrid-sevilla" in result.output


def test_dates_and_notes_read_as_plain_spanish() -> None:
    assert spanish_date(dt.date(2026, 10, 28)) == "28 de octubre de 2026"
    assert source_label("Adif; Europa Press / Demócrata") == "Adif"
    assert (
        schedule_note(dt.date(2026, 10, 28), None, "Adif")
        == "Horario publicado; sin circulación real desde el 28 de octubre de 2026 (Adif)."
    )
    assert schedule_note(dt.date(2026, 1, 18), dt.date(2026, 2, 17), "Adif") == (
        "Horario publicado; sin circulación real desde el 18 de enero de 2026 hasta la"
        " reanudación del 17 de febrero de 2026 (Adif)."
    )
