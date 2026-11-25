"""Regresiones de #265: lo que se publica debe ser coherente y tener procedencia."""

from __future__ import annotations

import json
from dataclasses import replace
from pathlib import Path

import pytest
from conftest import DATA_DIR, SOURCES, SPEC
from typer.testing import CliRunner

from oniel.cli.main import app
from oniel.validate import ValidationLine, validate_attributes


@pytest.mark.parametrize("speed", [299, 301, None])
def test_validate_rechaza_una_maxima_de_linea_distinta_de_sus_tramos(
    tmp_path: Path, speed: int | None
) -> None:
    data = json.loads(SPEC.read_text())
    data["line"]["max_speed_kmh"] = speed
    path = tmp_path / "linea.json"
    path.write_text(json.dumps(data))
    result = CliRunner().invoke(app, ["validate", "--spec", str(path)])
    assert result.exit_code == 1, result.output
    assert "la máxima documentada de sus tramos es 300" in result.output


@pytest.mark.parametrize("value", ["25kv_ca", "25 kV", "desconocida"])
def test_validate_rechaza_otra_escritura_de_electrificacion(tmp_path: Path, value: str) -> None:
    data = json.loads(SPEC.read_text())
    data["attribute_sections"].append(
        {
            "attribute": "electrification",
            "from_node": "madrid-puerta-de-atocha",
            "to_node": "sevilla-santa-justa",
            "value": value,
            "source_id": "adif-declaracion-red-2026-mapas",
            "checked_on": "2026-11-25",
        }
    )
    path = tmp_path / "linea.json"
    path.write_text(json.dumps(data))
    result = CliRunner().invoke(app, ["validate", "--spec", str(path)])
    assert result.exit_code == 1, result.output
    assert "el atributo solo admite" in result.output


def test_validate_acepta_la_linea_coherente() -> None:
    result = CliRunner().invoke(app, ["validate", "--spec", str(SPEC)])
    assert result.exit_code == 0, result.output
    assert all(not report["problems"] for report in json.loads(result.output))


def test_sin_velocidad_ni_electrificacion_no_se_inventa_un_valor() -> None:
    line = ValidationLine(SPEC, DATA_DIR)
    net = line.network
    # Una fuente sin velocidades: no convertir la ausencia en cero ni en la máxima de otra línea.
    line.__dict__["spec"] = net.spec.model_copy(
        update={
            "line": net.spec.line.model_copy(
                update={"max_speed_kmh": None, "electrification": None}
            )
        }
    )
    line.__dict__["network"] = replace(
        net,
        spec=line.spec,
        segments=[replace(s, max_speed_kmh=None, typical_speed_kmh=None) for s in net.segments],
    )
    assert validate_attributes([line], SOURCES, DATA_DIR)["problems"] == []
    assert line.spec.line.electrification is None
    # Si solo falta en un tramo, se compara con las máximas documentadas de los demás.
    line.__dict__["spec"] = net.spec
    line.__dict__["network"] = replace(
        net, segments=[replace(net.segments[0], max_speed_kmh=None), *net.segments[1:]]
    )
    assert validate_attributes([line], SOURCES, DATA_DIR)["problems"] == []


def test_validate_rechaza_vias_heredadas_sin_procedencia(tmp_path: Path) -> None:
    data = json.loads(SPEC.read_text())
    data["attribute_sections"] = [
        s for s in data["attribute_sections"] if s["attribute"] != "tracks"
    ]
    path = tmp_path / "linea.json"
    path.write_text(json.dumps(data))
    result = CliRunner().invoke(app, ["validate", "--spec", str(path)])
    assert result.exit_code == 1
    assert "número de vías sin fuente registrada y fecha" in result.output


@pytest.mark.parametrize(
    "line_id,maximum,typical",
    [
        ("lav-madrid-barcelona", 300, 300),
        ("burgos-miranda-vitoria", 160, 155),
    ],
)
def test_los_dos_casos_conservan_la_maxima_oficial_y_la_predominante(
    line_id: str, maximum: int, typical: int
) -> None:
    net = ValidationLine(DATA_DIR / "curated" / f"{line_id}.json", DATA_DIR).network
    segment = next(
        s
        for s in net.segments
        if "max_speed_kmh" in s.attributes
        and s.attributes["max_speed_kmh"].source_id == "adif-declaracion-red-2026-mapas"
    )
    assert net.spec.line.max_speed_kmh == max(s.max_speed_kmh or 0 for s in net.segments) == maximum
    assert segment.max_speed_kmh == maximum
    assert segment.typical_speed_kmh == typical


@pytest.mark.parametrize(
    "line_id,expected",
    [
        ("lav-madrid-sevilla", 470.269),
        ("lav-venta-de-banos-burgos", 86.272),
    ],
)
def test_la_longitud_de_cabecera_acaba_en_el_ultimo_nodo(line_id: str, expected: float) -> None:
    net = ValidationLine(DATA_DIR / "curated" / f"{line_id}.json", DATA_DIR).network
    assert net.length_km == pytest.approx(expected, abs=0.001)
    assert net.length_km == pytest.approx(net.nodes[-1].km - net.nodes[0].km)
    assert net.length_km < net.line.polyline.length_km
