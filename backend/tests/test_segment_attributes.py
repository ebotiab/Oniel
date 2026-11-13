"""Atributos de tramo por secciones: declaración, reparto a los tramos, cobertura y validación."""

from __future__ import annotations

import datetime as dt
import json
from pathlib import Path
from typing import Any

import pytest
from conftest import CONV_SPEC, DATA_DIR, JAEN_SPEC, MZCR_SPEC, SOURCES, SPEC, SPECS
from pydantic import ValidationError

from oniel.domain.attributes import (
    ATTRIBUTE_RULES,
    BLOQUEO,
    MANDO,
    PROTECCION_TREN,
    SIN_DATO_PUBLICADO,
    AttributeValue,
)
from oniel.network.build import BuiltNetwork, build_network, distribute_attributes
from oniel.network.spec import AttributeSection, NetworkSpec, load_network_spec
from oniel.validate import validate_attributes

SIGNALLING = (PROTECCION_TREN, BLOQUEO, MANDO)
DR = "adif-declaracion-red-2026-mapas"


def _with(spec: NetworkSpec, sections: list[AttributeSection], **line: Any) -> NetworkSpec:
    """La misma línea con otras secciones de atributo y, si se dan, otros campos de línea.

    La señalización de la línea se conserva: es obligatoria y estas pruebas no tratan de ella.
    """
    declared = {s.attribute for s in sections}
    kept = [
        s
        for s in spec.attribute_sections
        if s.attribute in SIGNALLING and s.attribute not in declared
    ]
    return spec.model_copy(
        update={"attribute_sections": [*sections, *kept], "line": spec.line.model_copy(update=line)}
    )


def _section(
    attribute: str, from_node: str, to_node: str, value: Any, **more: Any
) -> AttributeSection:
    return AttributeSection(
        attribute=attribute, from_node=from_node, to_node=to_node, value=value, **more
    )


def _ids(built: BuiltNetwork) -> list[str]:
    return [s.id.split(":", 1)[1] for s in built.segments]


def test_a_section_gives_its_value_to_the_segments_between_its_nodes(
    spec: NetworkSpec, built: BuiltNetwork
) -> None:
    section = _section(
        "senalizacion",
        "ciudad-real",
        "cordoba",
        "lzb",
        source_id="adif-declaracion-red",
        checked_on=dt.date(2026, 11, 12),
    )
    attributes = distribute_attributes(_with(spec, [section]), built.nodes)
    assert len(attributes) == len(built.segments)
    inside = [
        i
        for i, s in enumerate(built.segments)
        if built.node("ciudad-real").km <= s.km_from and s.km_to <= built.node("cordoba").km
    ]
    assert inside and len(inside) < len(built.segments)
    for i, values in enumerate(attributes):
        if i in inside:
            assert values["senalizacion"] == AttributeValue(
                "lzb", "adif-declaracion-red", dt.date(2026, 11, 12)
            )
        else:
            assert "senalizacion" not in values


def test_a_section_reads_the_same_in_either_direction(
    spec: NetworkSpec, built: BuiltNetwork
) -> None:
    forwards = distribute_attributes(
        _with(spec, [_section("catenaria", "ciudad-real", "cordoba", "bca")]), built.nodes
    )
    backwards = distribute_attributes(
        _with(spec, [_section("catenaria", "cordoba", "ciudad-real", "bca")]), built.nodes
    )
    assert forwards == backwards


def test_the_line_value_fills_what_no_section_declares(
    spec: NetworkSpec, built: BuiltNetwork
) -> None:
    section = _section("tracks", "ciudad-real", "puertollano", 1, source_id="una-fuente")
    attributes = distribute_attributes(_with(spec, [section], tracks=2), built.nodes)
    values = {
        segment_id: a["tracks"] for segment_id, a in zip(_ids(built), attributes, strict=True)
    }
    assert values["ciudad-real:puertollano"] == AttributeValue(1, "una-fuente")
    # el valor de la línea no tiene fuente propia
    assert values["madrid-puerta-de-atocha:bif-los-gavilanes"] == AttributeValue(2)
    assert sum(1 for v in values.values() if v.value == 1) == 1


def test_a_required_attribute_must_cover_every_segment(
    spec: NetworkSpec, built: BuiltNetwork
) -> None:
    partial = _with(spec, [_section("tracks", "ciudad-real", "cordoba", 2)], tracks=None)
    with pytest.raises(ValueError, match="«tracks» no cubre el tramo") as error:
        distribute_attributes(partial, built.nodes)
    assert "madrid-puerta-de-atocha" in str(error.value)
    assert "ciudad-real–" not in str(error.value)
    # con secciones que cubren la línea entera no hace falta el valor de la línea
    first, last = built.nodes[0].spec.id, built.nodes[-1].spec.id
    whole = _with(spec, [_section("tracks", first, last, 2)], tracks=None)
    assert all(a["tracks"].value == 2 for a in distribute_attributes(whole, built.nodes))


def test_an_optional_attribute_may_cover_only_part_of_the_line(
    spec: NetworkSpec, built: BuiltNetwork
) -> None:
    attributes = distribute_attributes(
        _with(spec, [_section("radio", "ciudad-real", "cordoba", "ctc")]), built.nodes
    )
    assert 0 < sum(1 for a in attributes if "radio" in a) < len(attributes)


def test_two_sections_of_the_same_attribute_cannot_overlap(
    spec: NetworkSpec, built: BuiltNetwork
) -> None:
    overlapping = _with(
        spec,
        [
            _section("radio", "ciudad-real", "cordoba", "ctc"),
            _section("radio", "puertollano", "sevilla-santa-justa", "local"),
        ],
    )
    with pytest.raises(ValueError, match="dos secciones de «radio» se pisan"):
        distribute_attributes(overlapping, built.nodes)
    # dos atributos distintos sí pueden cubrir los mismos tramos, y dos secciones, tocarse
    touching = _with(
        spec,
        [
            _section("radio", "ciudad-real", "cordoba", "ctc"),
            _section("radio", "cordoba", "sevilla-santa-justa", "local"),
            _section("catenaria", "puertollano", "sevilla-santa-justa", "bca"),
        ],
    )
    attributes = distribute_attributes(touching, built.nodes)
    assert {a["radio"].value for a in attributes if "radio" in a} == {"ctc", "local"}


def _raw(path: Path = CONV_SPEC) -> dict[str, Any]:
    return json.loads(path.read_text(encoding="utf-8"))  # type: ignore[no-any-return]


def test_sections_are_checked_when_the_spec_is_read() -> None:
    raw = _raw()
    raw["attribute_sections"][0]["to_node"] = "no-existe"
    with pytest.raises(ValidationError, match="nodo desconocido no-existe"):
        NetworkSpec.model_validate(raw)
    raw = _raw()
    raw["attribute_sections"][0]["value"] = "una"
    with pytest.raises(ValidationError, match="el atributo es de tipo int"):
        NetworkSpec.model_validate(raw)
    raw = _raw()
    raw["attribute_sections"][0]["to_node"] = raw["attribute_sections"][0]["from_node"]
    with pytest.raises(ValidationError, match="empieza y termina en el mismo nodo"):
        NetworkSpec.model_validate(raw)
    raw = _raw()
    raw["attribute_sections"][0]["tracks"] = 1
    with pytest.raises(ValidationError):
        NetworkSpec.model_validate(raw)


def test_the_old_track_sections_are_rejected_instead_of_ignored() -> None:
    raw = _raw()
    raw["track_sections"] = [
        {"from_node": s["from_node"], "to_node": s["to_node"], "tracks": s["value"]}
        for s in raw.pop("attribute_sections")
    ]
    with pytest.raises(ValidationError, match="track_sections ya no existe"):
        NetworkSpec.model_validate(raw)


def test_every_loaded_line_declares_its_tracks_with_a_source_where_they_change() -> None:
    for path in SPECS:
        loaded = load_network_spec(path)
        net = build_network(loaded, DATA_DIR)
        assert all(isinstance(s.attributes["tracks"].value, int) for s in net.segments)
        for segment in net.segments:
            value = segment.attributes["tracks"]
            if value.value != loaded.line.tracks or path == MZCR_SPEC:
                assert value.source_id and value.checked_on
    # la alta velocidad es de vía doble entera, por el valor de la línea
    lav = build_network(load_network_spec(SPEC), DATA_DIR)
    assert {s.tracks for s in lav.segments} == {2}


def test_validate_reports_coverage_and_unregistered_sources(tmp_path: Path) -> None:
    report = validate_attributes(SPECS, SOURCES, DATA_DIR)
    assert report["problems"] == []
    by_line = {line["line"]: line for line in report["attributes"]}
    granada = by_line["lav-antequera-granada"]
    for line in by_line.values():
        covered = dict(line["covered_segments"])
        # el ancho solo se declara donde no es el de la línea: el mixto del paso por Loja, de la
        # entrada a Granada y de la entrada a Murcia desde El Reguerón y, en la línea de Valencia
        # a Camp de Tarragona, el mixto hasta Castelló (18 tramos) y el estándar del último, que
        # además va a otra tensión
        coast = line["line"] == "valencia-castello-tarragona"
        other = {
            "lav-antequera-granada": 3,
            "lav-monforte-murcia": 1,
            "valencia-castello-tarragona": 19,
        }
        assert covered.pop("gauge", None) == other.get(line["line"])
        assert covered.pop("electrification", None) == (1 if coast else None)
        # la velocidad declarada es opcional: tres tramos de la alta velocidad de Barcelona
        barcelona = line["line"] == "lav-madrid-barcelona"
        assert covered.pop("max_speed_kmh", None) == (3 if barcelona else None)
        assert covered == dict.fromkeys(
            ["bloqueo", "mando", "proteccion_tren", "tracks"], line["segments"]
        )
    assert granada["sections"] == 4 + 3
    # dos de vía única, seis de bloqueo, una de protección del tren y una de mando
    assert by_line["convencional-madrid-alcazar-cordoba"]["sections"] == 10

    # sin el valor de la línea, las dos secciones de vía única no cubren la convencional
    raw = _raw()
    del raw["line"]["tracks"]
    raw["attribute_sections"][0]["source_id"] = "fuente-que-no-existe"
    broken = tmp_path / "convencional.json"
    broken.write_text(json.dumps(raw), encoding="utf-8")
    problems = validate_attributes([broken], SOURCES, DATA_DIR)["problems"]
    assert any("fuente no registrada (fuente-que-no-existe)" in p for p in problems)
    assert any("«tracks» no cubre el tramo" in p for p in problems)


def test_every_segment_of_every_loaded_line_has_its_signalling_with_source_and_date() -> None:
    for path in SPECS:
        net = build_network(load_network_spec(path), DATA_DIR)
        for segment in net.segments:
            for attribute in SIGNALLING:
                value = segment.attributes[attribute]
                assert value.value in (ATTRIBUTE_RULES[attribute].values or ())
                # la prolongación a Málaga se leyó en el mapa un día después que el resto
                assert value.source_id == DR
                assert value.checked_on in (dt.date(2026, 11, 12), dt.date(2026, 11, 13))


def test_the_signalling_is_what_the_network_statement_map_says() -> None:
    def values(path: Path, attribute: str) -> dict[str, Any]:
        net = build_network(load_network_spec(path), DATA_DIR)
        return {s.id.split(":", 1)[1]: s.attributes[attribute].value for s in net.segments}

    # la alta velocidad: LZB y ASFA con bloqueo de control automático; el mapa no dice su mando
    assert set(values(SPEC, PROTECCION_TREN).values()) == {"lzb_asfa"}
    assert set(values(SPEC, BLOQUEO).values()) == {"bca"}
    assert set(values(SPEC, MANDO).values()) == {SIN_DATO_PUBLICADO}
    # la convencional: ASFA y CTC enteras; el bloqueo cambia con la vía
    assert set(values(CONV_SPEC, PROTECCION_TREN).values()) == {"asfa"}
    assert set(values(CONV_SPEC, MANDO).values()) == {"ctc"}
    bloqueo = values(CONV_SPEC, BLOQUEO)
    assert bloqueo["alcazar-de-san-juan:cinco-casas"] == "bab"
    # entre Cinco Casas y Manzanares cambia en Herrera de la Mancha, que no es un nodo
    assert bloqueo["cinco-casas:manzanares"] == "bab_bad"
    assert bloqueo["manzanares:valdepenas"] == "bab"
    assert bloqueo["santa-cruz-de-mudela:almuradiel-viso-del-marques"] == "bau"
    assert bloqueo["vadollano:linares-baeza"] == "bab"
    assert bloqueo["linares-baeza:espeluy"] == "bau"
    # el bloqueo de vía única solo está donde la vía es única
    tracks = values(CONV_SPEC, "tracks")
    assert {k for k, v in bloqueo.items() if v == "bau"} == {k for k, v in tracks.items() if v == 1}
    assert set(values(MZCR_SPEC, BLOQUEO).values()) == {"bau"}
    assert set(values(MZCR_SPEC, MANDO).values()) == {"ctc"}
    # el ramal de Jaén: ASFA y CTC, con bloqueo de liberación automática en vía única
    assert set(values(JAEN_SPEC, PROTECCION_TREN).values()) == {"asfa"}
    assert set(values(JAEN_SPEC, BLOQUEO).values()) == {"blau"}
    assert set(values(JAEN_SPEC, MANDO).values()) == {"ctc"}


def test_a_signalling_section_needs_a_known_value_a_source_and_a_date() -> None:
    ok = {"source_id": DR, "checked_on": dt.date(2026, 11, 12)}
    _section(BLOQUEO, "a", "b", "bau", **ok)
    # el hueco se declara: es un valor más, con la fuente en la que se buscó
    _section(MANDO, "a", "b", SIN_DATO_PUBLICADO, **ok)
    with pytest.raises(ValidationError, match="solo admite"):
        _section(BLOQUEO, "a", "b", "automatico", **ok)
    with pytest.raises(ValidationError, match="no dice su fuente"):
        _section(PROTECCION_TREN, "a", "b", "asfa", source_id=DR)
    with pytest.raises(ValidationError, match="no dice su fuente"):
        _section(MANDO, "a", "b", "ctc", checked_on=dt.date(2026, 11, 12))


def test_validate_fails_when_a_segment_lacks_its_signalling(tmp_path: Path) -> None:
    for attribute in SIGNALLING:
        raw = _raw()
        sections = raw["attribute_sections"]
        # sin la sección de Linares-Baeza a Córdoba (o sin la única que tiene) el atributo no llega
        last = [s for s in sections if s["attribute"] == attribute][-1]
        if last["from_node"] == "madrid-puerta-de-atocha":
            last["to_node"] = "linares-baeza"
        else:
            sections.remove(last)
        broken = tmp_path / f"sin-{attribute}.json"
        broken.write_text(json.dumps(raw), encoding="utf-8")
        problems = validate_attributes([broken], SOURCES, DATA_DIR)["problems"]
        assert any(f"«{attribute}» no cubre el tramo linares-baeza–espeluy" in p for p in problems)
