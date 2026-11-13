"""Anotaciones de red: esquema del fichero curado, tipos declarados y validación contra la red y las fuentes."""

from __future__ import annotations

import datetime as dt
import json
from pathlib import Path
from typing import Any

import pytest
from conftest import DATA_DIR, LAV_GRANADA_SPEC, LAV_MALAGA_SPEC, SOURCES, SPEC
from pydantic import ValidationError
from typer.testing import CliRunner

from oniel.domain.annotations import (
    ANNOTATION_KINDS,
    AnnotationKind,
    schedule_note,
    source_label,
    spanish_date,
)
from oniel.network.annotations import check_annotations
from oniel.network.spec import AnnotationSpec, load_annotations, load_sources
from oniel.validate import validate_annotations

ANNOTATIONS = DATA_DIR / "curated" / "anotaciones.json"
CONV_SPEC = DATA_DIR / "curated" / "convencional-madrid-alcazar-cordoba.json"
JAEN_SPEC = DATA_DIR / "curated" / "espeluy-jaen.json"
#: Las líneas de las que cuelgan las anotaciones registradas.
SPECS = [SPEC, CONV_SPEC, JAEN_SPEC, LAV_MALAGA_SPEC, LAV_GRANADA_SPEC]

#: Una línea de juguete, con sus nodos en el orden del kilometraje.
LINE_NODES = {"linea": ["a", "b", "c", "d"]}
SOURCE_URLS: dict[str, str | None] = {"aviso": "https://example.org/aviso", "sin-url": None}


def entry(**changes: Any) -> dict[str, Any]:
    base: dict[str, Any] = {
        "id": "corte",
        "kind": "interrupcion",
        "status": "vigente",
        "line_id": "linea",
        "from_node": "b",
        "to_node": "d",
        "start_date": "2026-03-01",
        "reason": "Obras en la vía.",
        "source_ids": ["aviso"],
        "checked_on": "2026-03-10",
    }
    return {**base, **changes}


def spec(**changes: Any) -> AnnotationSpec:
    return AnnotationSpec.model_validate(entry(**changes))


def test_the_curated_file_loads_and_every_entry_has_source_and_check_date() -> None:
    interruptions = [a for a in load_annotations(ANNOTATIONS) if a.kind == "interrupcion"]
    assert {i.id for i in interruptions} >= {
        "lav-madrid-andalucia-2026-10-28",
        "convencional-obras-autopista-ferroviaria-2026-09-06",
    }
    sources = {s.id: s for s in load_sources(SOURCES)}
    for i in interruptions:
        assert i.source_ids and i.start_date is not None and i.checked_on >= i.start_date
        for source_id in i.source_ids:
            # cada fuente está registrada con URL, licencia y fecha de consulta
            source = sources[source_id]
            assert source.url and source.license and source.retrieved_on


def test_the_curated_file_keeps_an_ended_interruption_as_a_record() -> None:
    ended = [a for a in load_annotations(ANNOTATIONS) if a.ended_on is not None]
    assert [a.id for a in ended] == [
        "lav-madrid-andalucia-2026-01-19",
        "lav-cordoba-malaga-desprendimiento-alora-2026-02-04",
    ]
    adamuz, alora = ended
    # la de Álora: sin trenes entre Antequera-Santa Ana y Málaga hasta la reapertura del 30 de abril
    assert (alora.line_id, alora.status) == ("lav-cordoba-malaga", "terminada")
    assert (alora.from_node, alora.to_node) == ("antequera-santa-ana", "malaga-maria-zambrano")
    assert not alora.active_on(dt.date(2026, 2, 3)) and alora.active_on(dt.date(2026, 2, 4))
    assert alora.active_on(dt.date(2026, 4, 29)) and not alora.active_on(dt.date(2026, 4, 30))
    assert (adamuz.from_node, adamuz.to_node) == ("villanueva-de-cordoba", "cordoba")
    assert adamuz.status == "terminada"
    # vigente desde el primer día completo sin trenes hasta la víspera de la reapertura
    assert not adamuz.active_on(dt.date(2026, 1, 18))
    assert adamuz.active_on(dt.date(2026, 1, 19))
    assert adamuz.active_on(dt.date(2026, 2, 16))
    assert not adamuz.active_on(dt.date(2026, 2, 17))


def test_the_curated_file_fits_the_loaded_lines() -> None:
    report = validate_annotations(ANNOTATIONS, SOURCES, SPECS, DATA_DIR)
    assert report["problems"] == []
    assert len(report["entries"]) == len(load_annotations(ANNOTATIONS))


@pytest.mark.parametrize(
    ("changes", "message"),
    [
        ({"expected_end_date": "2026-02-01"}, "prevé terminar antes de empezar"),
        ({"ended_on": "2026-02-01", "status": "terminada"}, "termina antes de empezar"),
        (
            {"ended_on": "2026-03-20", "status": "terminada"},
            "termina después de la fecha de consulta",
        ),
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


@pytest.mark.parametrize(
    "missing", ["kind", "status", "checked_on", "source_ids", "start_date", "reason"]
)
def test_an_entry_without_a_required_field_is_rejected(missing: str) -> None:
    raw = entry()
    del raw[missing]
    with pytest.raises(ValidationError, match=missing):
        AnnotationSpec.model_validate(raw)


def test_an_interruption_is_active_from_its_start_until_the_day_service_resumes() -> None:
    open_ended = spec()
    assert not open_ended.active_on(dt.date(2026, 2, 28))
    assert open_ended.active_on(dt.date(2026, 3, 1))
    assert open_ended.active_on(dt.date(2030, 1, 1))
    ended = spec(ended_on="2026-03-08", status="terminada")
    assert ended.active_on(dt.date(2026, 3, 7))
    # ended_on es el día en que vuelve a haber trenes
    assert not ended.active_on(dt.date(2026, 3, 8))


def test_nodes_in_line_order_and_registered_sources_give_no_problems() -> None:
    assert check_annotations([spec()], LINE_NODES, SOURCE_URLS) == []
    # dos nodos consecutivos (un solo tramo) o separados: basta con que estén en orden
    assert check_annotations([spec(from_node="a", to_node="b")], LINE_NODES, SOURCE_URLS) == []


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
    problems = check_annotations([spec(**changes)], LINE_NODES, SOURCE_URLS)
    assert len(problems) == 1 and message in problems[0]


def _write(tmp_path: Path, *entries: dict[str, Any]) -> Path:
    path = tmp_path / "anotaciones.json"
    path.write_text(json.dumps({"annotations": list(entries)}), encoding="utf-8")
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
    report = validate_annotations(path, SOURCES, SPECS, DATA_DIR)
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
    (problem,) = validate_annotations(path, SOURCES, SPECS, DATA_DIR)["problems"]
    assert "cordoba está después de ciudad-real" in problem


def test_validate_reports_a_file_that_breaks_the_schema(tmp_path: Path) -> None:
    path = _write(tmp_path, entry(ended_on="2026-01-01", status="terminada"), entry())
    (problem,) = validate_annotations(path, SOURCES, SPECS, DATA_DIR)["problems"]
    assert "termina antes de empezar" in problem
    repeated = _write(tmp_path, entry(), entry())
    (problem,) = validate_annotations(repeated, SOURCES, SPECS, DATA_DIR)["problems"]
    assert "ids de anotación repetidos" in problem


def test_the_validate_command_fails_when_the_interruptions_do_not_fit(tmp_path: Path) -> None:
    from oniel.cli.main import app

    path = _write(tmp_path, entry(line_id="lav-madrid-sevilla", from_node="nada", to_node="urda"))
    result = CliRunner().invoke(app, ["validate", "--annotations", str(path)])
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


#: Un tipo de juguete que admite los tres alcances y no exige fecha de inicio, como un proyecto.
TOY = AnnotationKind(
    id="juguete",
    label="el juguete",
    statuses=("en estudio", "en obras", "en servicio"),
    ended_statuses=frozenset({"en servicio"}),
    scopes=("tramo", "nodo", "geometria"),
    required=("title",),
)
LINE = {"type": "LineString", "coordinates": [[-3.7, 40.4], [-4.0, 39.9]]}


@pytest.fixture
def toy_kind(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setitem(ANNOTATION_KINDS, TOY.id, TOY)


def toy(**changes: Any) -> AnnotationSpec:
    base: dict[str, Any] = {
        "id": "variante",
        "kind": "juguete",
        "status": "en estudio",
        "geometry": LINE,
        "title": "Variante de prueba",
        "source_ids": ["aviso"],
        "checked_on": "2026-03-10",
    }
    return AnnotationSpec.model_validate({**base, **changes})


def test_the_interruption_kind_declares_its_statuses_and_its_scope() -> None:
    kind = ANNOTATION_KINDS["interrupcion"]
    assert kind.statuses == ("vigente", "terminada") and kind.scopes == ("tramo",)
    assert kind.cuts_service


@pytest.mark.parametrize(
    ("changes", "message"),
    [
        ({"kind": "obra"}, "es de un tipo sin declarar, obra"),
        ({"status": "en obras"}, "tiene un estado que su tipo no admite, en obras"),
        ({"status": "terminada"}, "el estado terminada no encaja con ended_on"),
        ({"ended_on": "2026-03-08"}, "el estado vigente no encaja con ended_on"),
        ({"node_id": "b"}, "necesita un único alcance"),
        ({"geometry": LINE}, "necesita un único alcance"),
        ({"to_node": None}, "necesita line_id, from_node y to_node"),
    ],
)
def test_kind_status_and_scope_are_checked_against_the_declared_kind(
    changes: dict[str, Any], message: str
) -> None:
    with pytest.raises(ValidationError, match=message):
        spec(**changes)


def test_an_interruption_cannot_hang_from_a_node_or_from_its_own_geometry() -> None:
    stretch = {"line_id": None, "from_node": None, "to_node": None}
    with pytest.raises(ValidationError, match="un alcance que su tipo no admite, nodo"):
        spec(**stretch, node_id="b")
    with pytest.raises(ValidationError, match="un alcance que su tipo no admite, geometria"):
        spec(**stretch, geometry=LINE)
    with pytest.raises(ValidationError, match="necesita un único alcance"):
        spec(**stretch)


@pytest.mark.usefixtures("toy_kind")
def test_a_new_kind_only_needs_its_declaration() -> None:
    """Declarado el tipo, el mismo modelo lo valida con sus estados, sus alcances y sus campos."""
    own = toy()
    assert own.scope == "geometria" and own.label == "el juguete variante"
    # sin fecha de inicio está vigente hasta que termina
    assert own.active_on(dt.date(2020, 1, 1))
    at_node = toy(geometry=None, node_id="b")
    stretch = toy(geometry=None, line_id="linea", from_node="a", to_node="c", status="en obras")
    assert (at_node.scope, stretch.scope) == ("nodo", "tramo")
    assert check_annotations([own, at_node, stretch], LINE_NODES, SOURCE_URLS) == []
    done = toy(status="en servicio", ended_on="2026-03-01")
    assert not done.active_on(dt.date(2026, 3, 1))
    with pytest.raises(ValidationError, match="no tiene title, que su tipo exige"):
        toy(title=None, reason="Sin nombre propio.")
    with pytest.raises(ValidationError, match="los válidos son: en estudio, en obras, en servicio"):
        toy(status="vigente")
    with pytest.raises(ValidationError, match="geometría GeoJSON con coordenadas"):
        toy(geometry={"type": "Feature", "coordinates": []})


@pytest.mark.usefixtures("toy_kind")
def test_a_node_annotation_must_point_to_a_loaded_node() -> None:
    (problem,) = check_annotations([toy(geometry=None, node_id="z")], LINE_NODES, SOURCE_URLS)
    assert problem == "el juguete variante apunta al nodo z, que no está en ninguna línea cargada"


def project(**changes: Any) -> AnnotationSpec:
    base: dict[str, Any] = {
        "id": "enlace",
        "kind": "proyecto",
        "status": "en_estudio",
        "geometry": LINE,
        "title": "Enlace de prueba",
        "reason": "Une dos líneas de prueba.",
        "milestones": [
            {"date": "2022", "text": "Se licita el estudio.", "source_id": "aviso"},
            {"date": "2025-03", "text": "Se anuncia.", "source_id": "aviso"},
            {"date": "2026-01-08", "text": "Empieza el estudio.", "source_id": "aviso"},
        ],
        "source_ids": ["aviso"],
        "checked_on": "2026-03-10",
    }
    return AnnotationSpec.model_validate({**base, **changes})


def test_the_project_kind_declares_its_statuses_and_admits_every_scope() -> None:
    kind = ANNOTATION_KINDS["proyecto"]
    assert kind.statuses == (
        "en_estudio",
        "en_proyecto",
        "licitado",
        "en_obras",
        "parado",
        "sin_ejecutar",
        "en_servicio",
    )
    assert set(kind.scopes) == {"tramo", "nodo", "geometria"} and not kind.cuts_service
    sketch = project()
    assert sketch.scope == "geometria" and sketch.label == "el proyecto enlace"
    # sin fecha de inicio, un proyecto consta desde siempre y hasta que entra en servicio
    assert sketch.active_on(dt.date(2000, 1, 1))
    on_line = project(geometry=None, line_id="linea", from_node="a", to_node="c", status="en_obras")
    assert check_annotations([sketch, on_line], LINE_NODES, SOURCE_URLS) == []
    opened = project(status="en_servicio", ended_on="2026-03-01")
    assert not opened.active_on(dt.date(2026, 3, 1))


@pytest.mark.parametrize(
    ("changes", "message"),
    [
        ({"status": "vigente"}, "un estado que su tipo no admite, vigente"),
        ({"title": None}, "no tiene title, que su tipo exige"),
        ({"reason": None}, "no tiene reason, que su tipo exige"),
        ({"status": "en_servicio"}, "el estado en_servicio no encaja con ended_on"),
        (
            {"geometry": {"type": "LineString", "coordinates": [[40.4, -3.7], [39.9, -4.0]]}},
            "puntos fuera de la península",
        ),
        ({"geometry": {"type": "LineString", "coordinates": [["a", "b"]]}}, "mal formadas"),
    ],
)
def test_a_project_with_inconsistent_fields_is_rejected(
    changes: dict[str, Any], message: str
) -> None:
    with pytest.raises(ValidationError, match=message):
        project(**changes)


@pytest.mark.parametrize(
    ("milestones", "message"),
    [
        ([{"date": "primavera de 2010", "text": "x", "source_id": "aviso"}], "date"),
        ([{"date": "2010-13", "text": "x", "source_id": "aviso"}], "date"),
        ([{"date": "2010", "text": "", "source_id": "aviso"}], "text"),
        ([{"date": "2010", "text": "x", "source_id": "otra"}], "cita la fuente otra"),
        ([{"date": "2026-04", "text": "x", "source_id": "aviso"}], "posterior a la comprobación"),
        (
            [
                {"date": "2025-03", "text": "x", "source_id": "aviso"},
                {"date": "2022", "text": "y", "source_id": "aviso"},
            ],
            "del más antiguo al más reciente",
        ),
    ],
)
def test_milestones_need_a_known_date_a_text_and_one_of_the_sources(
    milestones: list[dict[str, str]], message: str
) -> None:
    with pytest.raises(ValidationError, match=message):
        project(milestones=milestones)


def test_every_project_in_the_curated_file_has_dated_milestones_and_registered_sources() -> None:
    projects = [a for a in load_annotations(ANNOTATIONS) if a.kind == "proyecto"]
    assert len(projects) >= 4
    sources = {s.id: s for s in load_sources(SOURCES)}
    for p in projects:
        assert p.title and p.reason and p.milestones, p.id
        for source_id in p.source_ids:
            source = sources[source_id]
            assert source.url and source.license and source.retrieved_on, source_id
