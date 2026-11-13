"""Zonas: la clasificación con la que el visor agrupa las líneas."""

from __future__ import annotations

import json
import shutil
from pathlib import Path

import pytest
from conftest import DATA_DIR, SPECS

from oniel.network.importer import ZONES_FILE
from oniel.network.spec import load_network_spec, load_zones
from oniel.validate import validate_zones


def test_every_line_declares_a_zone_of_the_registry() -> None:
    report = validate_zones(SPECS, DATA_DIR)
    assert report["problems"] == []
    assert len(report["zones"]) == len(SPECS)
    # la zona es la del extremo más alejado de Madrid; si la línea no pasa por Madrid, donde está
    assert report["zones"]["lav-madrid-sevilla"] == "Andalucía"
    assert report["zones"]["lav-madrid-barcelona"] == "Cataluña"
    assert report["zones"]["manzanares-ciudad-real"] == "Madrid y Castilla-La Mancha"


def test_the_registry_goes_from_north_to_south_without_repeats() -> None:
    zones = load_zones(DATA_DIR / ZONES_FILE)
    assert [z.sort_order for z in zones] == sorted({z.sort_order for z in zones})
    assert zones[0].id == "galicia"
    assert zones[-1].id == "andalucia"
    assert all(z.cities for z in zones)


def test_a_repeated_zone_is_rejected(tmp_path: Path) -> None:
    raw = json.loads((DATA_DIR / ZONES_FILE).read_text(encoding="utf-8"))
    raw["zones"].append(raw["zones"][0])
    path = tmp_path / "zonas.json"
    path.write_text(json.dumps(raw), encoding="utf-8")
    with pytest.raises(ValueError, match="repite"):
        load_zones(path)


def test_a_line_with_a_zone_out_of_the_registry_is_a_problem(tmp_path: Path) -> None:
    curated = tmp_path / "curated"
    curated.mkdir()
    shutil.copy(DATA_DIR / ZONES_FILE, curated / "zonas.json")
    raw = json.loads(SPECS[0].read_text(encoding="utf-8"))
    raw["line"]["zone"] = "atlantida"
    spec = curated / SPECS[0].name
    spec.write_text(json.dumps(raw), encoding="utf-8")
    assert load_network_spec(spec).line.zone == "atlantida"
    report = validate_zones([spec], tmp_path)
    assert report["problems"] == [
        f"{raw['line']['id']} declara la zona atlantida, que no está en zonas.json"
    ]
