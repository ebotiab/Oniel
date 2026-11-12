"""Operadores de trenes: cuáles circulan por cada línea y de cuáles hay horarios cargados."""

from __future__ import annotations

import json
from pathlib import Path
from typing import Any

from conftest import DATA_DIR, FEED_OPERATOR_ID, SOURCES, SPEC, SPECS

from oniel.network.spec import load_network_spec
from oniel.validate import validate_operators


def _sources_with_feeds(tmp_path: Path, change: Any) -> Path:
    raw = json.loads(SOURCES.read_text(encoding="utf-8"))
    raw["feeds"] = change(raw["feeds"])
    path = tmp_path / "sources.json"
    path.write_text(json.dumps(raw), encoding="utf-8")
    return path


def test_declared_operators_and_feeds_hold_together() -> None:
    report = validate_operators(SPECS, SOURCES, DATA_DIR)
    assert report["problems"] == []
    timetables = {op["id"]: op["timetable"] for op in report["operators"]}
    assert timetables[FEED_OPERATOR_ID] == "cargado"
    # Iryo circula por la alta velocidad y no publica sus horarios: se declara, sin fichero
    assert timetables["iryo"] == "no_publicado"
    assert "iryo" not in {f["operator_id"] for f in report["feeds"]}
    # el día de referencia sale de los días que cubren todos los ficheros vigentes
    start, end = report["common_validity"]
    assert all(f["valid"][0] <= start <= end <= f["valid"][1] for f in report["feeds"])


def test_only_the_high_speed_line_declares_iryo() -> None:
    by_line = {
        load_network_spec(path).line.id: {
            op.id for op in load_network_spec(path).operators if op.role == "operador"
        }
        for path in SPECS
    }
    assert by_line[load_network_spec(SPEC).line.id] >= {"renfe", "iryo"}
    assert all("iryo" not in ops for line, ops in by_line.items() if line != "lav-madrid-sevilla")


def test_an_operator_with_loaded_timetables_needs_a_feed(tmp_path: Path) -> None:
    sources = _sources_with_feeds(
        tmp_path, lambda feeds: [f for f in feeds if f["operator_id"] != FEED_OPERATOR_ID]
    )
    report = validate_operators(SPECS, sources, DATA_DIR)
    assert (
        f"el operador {FEED_OPERATOR_ID} no tiene ningún fichero de horarios declarado"
        in (report["problems"])
    )


def test_a_feed_needs_an_operator_declared_with_timetables(tmp_path: Path) -> None:
    def to(operator_id: str) -> Any:
        return lambda feeds: [*feeds[:-1], {**feeds[-1], "operator_id": operator_id}]

    unknown = validate_operators(SPECS, _sources_with_feeds(tmp_path, to("otro")), DATA_DIR)
    assert any("que no está en ninguna línea" in p for p in unknown["problems"])
    unpublished = validate_operators(SPECS, _sources_with_feeds(tmp_path, to("iryo")), DATA_DIR)
    assert any("declarado sin horarios publicados" in p for p in unpublished["problems"])
