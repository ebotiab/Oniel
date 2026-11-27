"""Las costuras entre líneas: una conexión a trazos se declara en sus dos extremos, los nombres
de las conexiones siguen un solo criterio, el texto de un nodo de varias líneas no habla de «esta
línea» y un tren que va por una vía paralela sin cargar no cuenta en la que sí lo está."""

from __future__ import annotations

import json
from pathlib import Path

import pytest
from conftest import DATA_DIR, SPECS
from pydantic import ValidationError

from oniel.gtfs.reader import GtfsStopTime, GtfsTrip
from oniel.gtfs.trips import takes_parallel_track
from oniel.network.spec import ConnectionSpec, SlowRun, load_network_spec
from oniel.validate import CONNECTION_END_M, connection_name_problem, validate_connections

CURATED = DATA_DIR / "curated"
ALBACETE = CURATED / "alcazar-albacete.json"
MURCIA = CURATED / "lav-monforte-murcia.json"
SEVILLA = CURATED / "lav-madrid-sevilla.json"


def _changed(path: Path, tmp_path: Path, change: dict[str, object], connection: str) -> Path:
    """Copia de una especificación con una conexión cambiada; ``None`` quita la clave."""
    raw = json.loads(path.read_text(encoding="utf-8"))
    (target,) = [c for c in raw["connections"] if c["id"] == connection]
    for key, value in change.items():
        if value is None:
            target.pop(key, None)
        else:
            target[key] = value
    out = tmp_path / path.name
    out.write_text(json.dumps(raw, ensure_ascii=False), encoding="utf-8")
    return out


def _others(path: Path) -> list[Path]:
    return [p for p in SPECS if p != path]


def test_the_loaded_network_has_no_loose_seams() -> None:
    """Ninguna conexión llega a un nodo cargado sin declararlo, y todas se nombran igual."""
    report = validate_connections(SPECS, DATA_DIR)
    assert report["problems"] == []
    total = sum(len(load_network_spec(p).connections) for p in SPECS)
    assert report["connections"]["total"] == total
    assert 0 < report["connections"]["both_ends"] < total


def test_a_connection_between_two_loaded_nodes_says_where_it_leads_from_each() -> None:
    """La convencional de Chinchilla a Murcia y Cartagena llega a otro nodo cargado."""
    (link,) = load_network_spec(ALBACETE).connections
    assert (link.node_id, link.to_node_id) == ("bif-chinchilla", "murcia-del-carmen")
    assert "Cartagena" in link.towards and "Chinchilla" in (link.towards_back or "")
    assert link.to_node_id in {n.id for n in load_network_spec(MURCIA).nodes}


def test_lines_drawn_from_both_ends_are_one_connection_now() -> None:
    """Las líneas que salían a trazos de cada extremo como dos cabos son una conexión sola."""
    connections = {c.id: c for p in SPECS for c in load_network_spec(p).connections}
    for gone in ("conv-albacete-levante", "conv-los-naranjos-cordoba", "merida-ciudad-real"):
        assert gone not in connections
    ends = {
        "conv-chinchilla-murcia-cartagena": ("bif-chinchilla", "murcia-del-carmen"),
        "conv-cordoba-sevilla": ("cordoba", "bif-los-naranjos"),
        "conv-ciudad-real-badajoz": ("ciudad-real", "merida"),
        # la convencional de Valladolid a Burgos: por ella llegan a Burgos los regionales
        "conv-valladolid-venta-de-banos": ("valladolid-campo-grande", "burgos-rosa-manzano"),
    }
    for connection, pair in ends.items():
        assert (connections[connection].node_id, connections[connection].to_node_id) == pair


def test_validate_asks_for_the_other_end(tmp_path: Path) -> None:
    undeclared = _changed(
        ALBACETE,
        tmp_path,
        {"to_node_id": None, "towards_back": None},
        "conv-chinchilla-murcia-cartagena",
    )
    report = validate_connections([undeclared, *_others(ALBACETE)], DATA_DIR)
    (problem,) = report["problems"]
    assert "conv-chinchilla-murcia-cartagena" in problem and "murcia-del-carmen" in problem
    assert "falta to_node_id" in problem


def test_validate_checks_that_the_sketch_reaches_the_declared_node(tmp_path: Path) -> None:
    short = _changed(
        ALBACETE, tmp_path, {"sketch": [[-1.7005, 38.9000]]}, "conv-chinchilla-murcia-cartagena"
    )
    (problem,) = validate_connections([short, *_others(ALBACETE)], DATA_DIR)["problems"]
    assert "el croquis acaba a" in problem and "murcia-del-carmen" in problem
    assert CONNECTION_END_M == 300
    ausente = _changed(
        ALBACETE, tmp_path, {"to_node_id": "estacion-ausente"}, "conv-chinchilla-murcia-cartagena"
    )
    (missing,) = validate_connections([ausente, *_others(ALBACETE)], DATA_DIR)["problems"]
    assert "estacion-ausente" in missing and "no está cargado" in missing


@pytest.mark.parametrize(
    ("name", "fault"),
    [
        ("Línea convencional Córdoba–Sevilla", "raya sin espacios"),
        ("Enlace Málaga–Granada", "raya sin espacios"),
        ("Línea Casetas – Bilbao", "sin decir si es convencional"),
        ("Línea de Sagunt a Teruel y Zaragoza", "sin decir si es convencional"),
    ],
)
def test_names_that_break_the_rule(name: str, fault: str) -> None:
    assert fault in (connection_name_problem(name) or "")


@pytest.mark.parametrize(
    "name",
    [
        "Línea convencional Miranda de Ebro – Logroño",
        "Línea antigua por el puerto de Pajares",
        "Enlace de Perales del Río",
        "Vía de ancho ibérico por Grisén",
        "Ramal de Tortosa",
        "Sección internacional Figueres – Perpiñán",
        "Línea convencional Maçanet-Massanes – Mataró – Barcelona",
    ],
)
def test_names_that_follow_the_rule(name: str) -> None:
    assert connection_name_problem(name) is None


def test_a_shared_node_does_not_speak_from_one_line(tmp_path: Path) -> None:
    """Sevilla-Santa Justa es de tres líneas: «Final de la línea» se leería igual desde las tres."""
    raw = json.loads(SEVILLA.read_text(encoding="utf-8"))
    (station,) = [n for n in raw["nodes"] if n["id"] == "sevilla-santa-justa"]
    assert "final de la línea" not in station["description"].lower()
    station["description"] = "Final de la línea. Estación pasante."
    stale = tmp_path / SEVILLA.name
    stale.write_text(json.dumps(raw, ensure_ascii=False), encoding="utf-8")
    (problem,) = validate_connections([stale, *_others(SEVILLA)], DATA_DIR)["problems"]
    assert "sevilla-santa-justa es de 3 líneas" in problem and "«final de la línea»" in problem


def test_a_connection_declares_both_things_of_the_other_end_or_none() -> None:
    base = {"id": "x", "node_id": "a", "name": "Enlace de X", "towards": "B"}
    assert ConnectionSpec.model_validate(base).to_node_id is None
    with pytest.raises(ValidationError, match="a la vez o ninguno"):
        ConnectionSpec.model_validate({**base, "to_node_id": "b"})
    with pytest.raises(ValidationError, match="a la vez o ninguno"):
        ConnectionSpec.model_validate({**base, "towards_back": "A"})
    with pytest.raises(ValidationError, match="mismo nodo"):
        ConnectionSpec.model_validate({**base, "to_node_id": "a", "towards_back": "A"})


def _trip(*stops: tuple[str, int, int]) -> GtfsTrip:
    return GtfsTrip(
        trip_id="t",
        route_id="r",
        service_id="s",
        train_number="1",
        product="Regional",
        stop_times=[
            GtfsStopTime(i, stop, arrival * 60, departure * 60, None, None)
            for i, (stop, arrival, departure) in enumerate(stops, start=1)
        ],
    )


def test_a_train_that_takes_too_long_goes_by_the_parallel_track() -> None:
    """De A a B sin paradas, una hora o más es la vía paralela; en cualquiera de los sentidos y
    contando de la salida de una a la llegada a la otra."""
    runs = [SlowRun(stop_ids=("A", "B"), min_minutes=60)]
    assert takes_parallel_track(runs, _trip(("A", 0, 0), ("B", 67, 70), ("C", 100, 100)))
    assert takes_parallel_track(runs, _trip(("C", 0, 0), ("B", 30, 32), ("A", 104, 104)))
    assert takes_parallel_track(runs, _trip(("A", 0, 0), ("B", 60, 60)))
    assert not takes_parallel_track(runs, _trip(("A", 0, 0), ("B", 47, 50)))
    # la espera en la primera no cuenta, y con una parada entre las dos no son seguidas
    assert not takes_parallel_track(runs, _trip(("A", 0, 30), ("B", 77, 80)))
    assert not takes_parallel_track(runs, _trip(("A", 0, 0), ("X", 30, 31), ("B", 80, 80)))
    assert not takes_parallel_track([], _trip(("A", 0, 0), ("B", 600, 600)))
