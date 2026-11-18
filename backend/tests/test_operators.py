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
    # Iryo no publica sus horarios: sus trenes se cargan de una compilación no oficial, con su
    # fichero declarado y su propia fuente
    assert timetables["iryo"] == "no_oficial"
    assert "iryo" in {f["operator_id"] for f in report["feeds"]}
    sources = {op["id"]: op["source_id"] for op in report["operators"]}
    assert sources["iryo"] == "iryo-gtfs-no-oficial"
    # el día de referencia sale de los días que cubren todos los ficheros vigentes
    start, end = report["common_validity"]
    assert all(f["valid"][0] <= start <= end <= f["valid"][1] for f in report["feeds"])


def test_only_the_lines_iryo_runs_on_declare_it() -> None:
    """Iryo va de Madrid a Sevilla, a Málaga, a Barcelona, a Valencia y a Alicante: no circula por las convencionales ni
    llega a Granada."""
    by_line = {
        load_network_spec(path).line.id: {
            op.id for op in load_network_spec(path).operators if op.role == "operador"
        }
        for path in SPECS
    }
    assert by_line[load_network_spec(SPEC).line.id] >= {"renfe", "iryo"}
    with_iryo = {
        "lav-madrid-sevilla",
        "lav-cordoba-malaga",
        "lav-madrid-barcelona",
        "lav-madrid-valencia",
        "lav-albacete-alicante",
    }
    # los dos baipases de la línea de Barcelona declaran los mismos operadores que ella
    with_iryo |= {"baipas-zaragoza", "baipas-lleida"}
    assert {line for line, ops in by_line.items() if "iryo" in ops} == with_iryo
    assert by_line["lav-cordoba-malaga"] == {"renfe", "ouigo", "iryo"}
    assert by_line["lav-antequera-granada"] == {"renfe"}
    assert by_line["lav-madrid-barcelona"] == {"renfe", "ouigo", "iryo"}


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
    # un operador declarado sin horarios publicados no puede tener fichero
    specs = []
    for path in SPECS:
        copy = tmp_path / path.name
        copy.write_text(
            path.read_text(encoding="utf-8").replace('"no_oficial"', '"no_publicado"'),
            encoding="utf-8",
        )
        specs.append(copy)
    unpublished = validate_operators(specs, SOURCES, DATA_DIR)
    assert any("declarado sin horarios publicados" in p for p in unpublished["problems"])


def test_an_operator_loaded_from_an_unofficial_feed_needs_it_declared(tmp_path: Path) -> None:
    """Un operador «no_oficial» tiene trenes cargados: sin su fichero, la validación lo dice."""
    sources = _sources_with_feeds(
        tmp_path, lambda feeds: [f for f in feeds if f["operator_id"] != "iryo"]
    )
    report = validate_operators(SPECS, sources, DATA_DIR)
    assert "el operador iryo no tiene ningún fichero de horarios declarado" in report["problems"]


def test_the_unofficial_feed_says_where_its_timetables_come_from() -> None:
    """La fuente del fichero de Iryo dice que no es oficial, quién lo compila y de dónde sale."""
    from oniel.network.spec import load_feeds, load_sources

    source = {s.id: s for s in load_sources(SOURCES)}["iryo-gtfs-no-oficial"]
    assert "no oficial" in source.name
    assert "sin vínculo con Iryo" in source.publisher
    assert "CC BY 4.0" in str(source.license) and "© Iryo" in str(source.license)
    assert "iryo.eu" in str(source.notes) and "deryclem.github.io" in str(source.notes)
    assert source.file is not None and (DATA_DIR / source.file).exists()
    feed = next(f for f in load_feeds(SOURCES) if f.operator_id == "iryo")
    # usa los códigos de Adif con sus propios nombres: no renombra las paradas asignadas
    assert feed.names_stops is False and feed.product == "Iryo"
