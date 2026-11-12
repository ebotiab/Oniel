"""Pruebas con PostgreSQL: importación repetible y API. Requieren ONIEL_TEST_DATABASE_URL."""

from __future__ import annotations

import datetime as dt
import json
from collections.abc import AsyncIterator, Iterator
from pathlib import Path
from typing import Any

import asyncpg
import httpx
import pytest
import pytest_asyncio
from asgi_lifespan import LifespanManager
from conftest import (
    DATA_DIR,
    FEED,
    OUIGO_DATASET_ID,
    OUIGO_FEED,
    OUIGO_OPERATOR_ID,
    OUIGO_PRODUCT,
    OUIGO_SOURCE_ID,
    OUIGO_STOP_ID_PREFIX,
    SOURCES,
    SPECS,
    database_url_for_tests,
    requires_db,
)

LAV, CONV, MZCR = (
    "lav-madrid-sevilla",
    "convencional-madrid-alcazar-cordoba",
    "manzanares-ciudad-real",
)
RULES = {
    "atocha-cercanias-ciudad-real-por-manzanares": 20,
    "atocha-cercanias-cordoba-por-manzanares": 4,
}
ANNOTATIONS = DATA_DIR / "curated" / "anotaciones.json"
LAV_CUT = "lav-madrid-andalucia-2026-10-28"
WORKS_CUT = "convencional-obras-autopista-ferroviaria-2026-09-06"
TUNNELS_PROJECT = "proyecto-galibo-tuneles-venta-de-cardenas-montoro"
#: Día en que se comprobaron las dos interrupciones iniciales: ambas estaban vigentes. Las pruebas
#: que dependen de la fecha usan este día, que no cambia aunque después se registre su final.
CHECKED = "2026-11-10"

pytestmark = [requires_db, pytest.mark.asyncio(loop_scope="module")]


@pytest.fixture(scope="module")
def dsn() -> str:
    url = database_url_for_tests()
    assert url is not None
    return url


@pytest_asyncio.fixture(loop_scope="module", scope="module")
async def imported(dsn: str) -> dict[str, Any]:
    from oniel.db.migrate import drop_everything, migrate
    from oniel.db.pool import connect
    from oniel.gtfs.importer import import_gtfs
    from oniel.network.annotations import import_annotations
    from oniel.network.importer import import_network

    async with connect(dsn) as conn:
        await drop_everything(conn)
        await migrate(conn)
        net1 = [await import_network(conn, s, SOURCES, DATA_DIR) for s in SPECS]
        cuts1 = await import_annotations(conn, ANNOTATIONS, SOURCES, DATA_DIR)
        gtfs1 = await import_gtfs(
            conn,
            FEED,
            SPECS,
            source_id="renfe-gtfs-av-ld-md",
            operator_id="renfe",
            data_dir=DATA_DIR,
        )
        ouigo1 = await import_gtfs(
            conn,
            OUIGO_FEED,
            SPECS,
            source_id=OUIGO_SOURCE_ID,
            operator_id=OUIGO_OPERATOR_ID,
            data_dir=DATA_DIR,
            product=OUIGO_PRODUCT,
            stop_id_prefix=OUIGO_STOP_ID_PREFIX,
        )
        # repetir la importación debe dejar exactamente el mismo estado
        net2 = [await import_network(conn, s, SOURCES, DATA_DIR) for s in SPECS]
        cuts2 = await import_annotations(conn, ANNOTATIONS, SOURCES, DATA_DIR)
        gtfs2 = await import_gtfs(
            conn,
            FEED,
            SPECS,
            source_id="renfe-gtfs-av-ld-md",
            operator_id="renfe",
            data_dir=DATA_DIR,
        )
        ouigo2 = await import_gtfs(
            conn,
            OUIGO_FEED,
            SPECS,
            source_id=OUIGO_SOURCE_ID,
            operator_id=OUIGO_OPERATOR_ID,
            data_dir=DATA_DIR,
            product=OUIGO_PRODUCT,
            stop_id_prefix=OUIGO_STOP_ID_PREFIX,
        )
        counts = {
            t: await conn.fetchval(f"SELECT count(*) FROM {t}")
            for t in (
                "lines",
                "nodes",
                "segments",
                "services",
                "service_dates",
                "service_stops",
                "service_segment_passes",
                "import_runs",
                "annotations",
                "datasets",
            )
        }
    return {
        "net": (net1, net2),
        "gtfs": (gtfs1, gtfs2),
        "ouigo": (ouigo1, ouigo2),
        "interruptions": (cuts1, cuts2),
        "counts": counts,
    }


async def test_import_is_repeatable(imported: dict[str, Any]) -> None:
    net1, net2 = imported["net"]
    gtfs1, gtfs2 = imported["gtfs"]
    assert net1 == net2
    # 335 viajes en la LAV, 503 en la convencional y 154 en la de Manzanares a Ciudad Real. Los
    # 24 Intercity/Alvia Madrid-Atocha Cercanías cuentan en las tres (convencional hasta
    # Manzanares, la tercera entera, LAV desde Ciudad Real) y los 130 MD y Regional Exprés de la
    # tercera ya estaban en la convencional: cada viaje se guarda una sola vez.
    assert gtfs1["trips_imported"] == gtfs2["trips_imported"] == 335 + 503 - 24
    assert gtfs1["lines"][LAV]["trips"] == 335
    assert gtfs1["lines"][CONV]["trips"] == 503
    assert gtfs1["lines"][MZCR]["trips"] == 130 + 24
    for line_id in (LAV, CONV, MZCR):
        assert gtfs1["lines"][line_id]["route_overrides"] == RULES
    assert gtfs1["lines"][MZCR]["passes"] == {"publicado": 130 * 3, "estimado": 24 * 3}
    assert "indeterminado" not in gtfs1["passes"] and gtfs1["unmapped_stops"] == {}
    # Ouigo: 25 viajes Madrid–Córdoba–Sevilla o Málaga (4 de ellos vienen de Barcelona o siguen
    # hasta allí), todos por la LAV y ninguno por las líneas convencionales. Solo paran en Madrid,
    # Córdoba y Sevilla, así que el paso por cada tramo es estimado: 245 pasos.
    ouigo1, ouigo2 = imported["ouigo"]
    assert ouigo1["trips_imported"] == ouigo2["trips_imported"] == 25
    assert ouigo1["train_numbers"] == 20
    assert ouigo1["lines"][LAV]["trips"] == 25
    assert ouigo1["lines"][CONV]["trips"] == ouigo1["lines"][MZCR]["trips"] == 0
    assert ouigo1["passes"] == {"estimado": 245} and ouigo1["unmapped_stops"] == {}
    assert ouigo1["resolution"] == {"completa": 25}
    assert ouigo1["dataset"]["id"] == ouigo2["dataset"]["id"] == OUIGO_DATASET_ID
    assert (ouigo1["feed_start"], ouigo1["feed_end"]) == ("2026-06-26", "2026-12-12")
    c = imported["counts"]
    assert c["lines"] == 3 and c["segments"] == 11 + 25 + 3 and c["services"] == 814 + 25
    assert c["service_segment_passes"] == (3126 + 115) + (2469 + 683) + (72 + 390) + 245
    assert c["import_runs"] == 4
    # el mismo fichero dos veces es un solo conjunto de datos, reconocido por su SHA-256
    assert c["datasets"] == 2
    assert gtfs1["dataset"]["id"] == gtfs2["dataset"]["id"] == "renfe-gtfs-av-ld-md-2026-11-08"
    assert (gtfs1["dataset"]["reused"], gtfs2["dataset"]["reused"]) == (False, True)


async def test_interruptions_import_is_repeatable_and_survives_a_network_reimport(
    imported: dict[str, Any],
) -> None:
    from oniel.network.spec import load_annotations

    cuts1, cuts2 = imported["interruptions"]
    assert cuts1 == cuts2
    # la segunda importación de la red (que borra y recrea nodos de línea y tramos) no las pierde
    assert imported["counts"]["annotations"] == len(load_annotations(ANNOTATIONS))
    assert {LAV_CUT, WORKS_CUT} <= set(cuts1["ids"])


async def test_interruptions_that_do_not_fit_the_network_are_not_imported(
    dsn: str, imported: dict[str, Any], tmp_path: Path
) -> None:
    from oniel.db.pool import connect
    from oniel.network.annotations import import_annotations

    bad = tmp_path / "anotaciones.json"
    entry = {
        "id": "corte-imposible",
        "kind": "interrupcion",
        "status": "vigente",
        "line_id": "lav-madrid-sevilla",
        "from_node": "cordoba",
        "to_node": "ciudad-real",
        "start_date": "2026-03-01",
        "reason": "Obras en la vía.",
        "source_ids": ["adif-estado-de-la-red"],
        "checked_on": "2026-03-10",
    }
    bad.write_text(json.dumps({"annotations": [entry]}), encoding="utf-8")
    async with connect(dsn) as conn:
        with pytest.raises(ValueError, match="cordoba está después de ciudad-real"):
            await import_annotations(conn, bad, SOURCES, DATA_DIR)
        # la importación fallida no toca lo que había
        assert (
            await conn.fetchval("SELECT count(*) FROM annotations")
            == (imported["counts"]["annotations"])
        )


@pytest_asyncio.fixture(loop_scope="module", scope="module")
async def client(
    dsn: str, imported: dict[str, Any], monkeypatch_module: pytest.MonkeyPatch
) -> AsyncIterator[httpx.AsyncClient]:
    monkeypatch_module.setenv("ONIEL_DATABASE_URL", dsn)
    from oniel.settings import get_settings

    get_settings.cache_clear()
    from oniel.api.main import create_app

    app = create_app()
    async with (
        LifespanManager(app),
        httpx.AsyncClient(transport=httpx.ASGITransport(app=app), base_url="http://test") as c,
    ):
        yield c
    get_settings.cache_clear()


@pytest.fixture(scope="module")
def monkeypatch_module() -> Iterator[pytest.MonkeyPatch]:
    mp = pytest.MonkeyPatch()
    yield mp
    mp.undo()


async def test_network_endpoint(client: httpx.AsyncClient) -> None:
    r = await client.get("/api/network")
    assert r.status_code == 200
    data = r.json()
    assert [n["id"] for n in data["nodes"]][:3] == [
        "madrid-puerta-de-atocha",
        "bif-torrejon-de-velasco",
        "bif-la-sagra",
    ]
    assert len(data["segment_features"]["features"]) == 11 + 25 + 3
    assert data["connection_features"]["features"]
    # la conexión a trazos Manzanares–Ciudad Real desaparece: ahora es una línea cargada, y de
    # Ciudad Real sale a trazos la convencional hacia Badajoz
    connections = {c["id"]: c["node_id"] for c in data["connections"]}
    assert "conv-manzanares-ciudad-real" not in connections
    assert connections["conv-ciudad-real-badajoz"] == "ciudad-real"
    # Córdoba y Atocha están en las dos líneas: una fila por línea, un solo punto en el mapa
    cordoba = [n for n in data["nodes"] if n["id"] == "cordoba"]
    assert sorted(n["line_id"] for n in cordoba) == [
        "convencional-madrid-alcazar-cordoba",
        "lav-madrid-sevilla",
    ]
    assert sum(1 for f in data["node_features"]["features"] if f["id"] == "cordoba") == 1
    single = [s for s in data["segments"] if s["tracks"] == 1]
    assert {s["line_id"] for s in single} == {CONV, MZCR}
    assert sum(1 for s in data["segments"] if s["line_id"] == MZCR and s["tracks"] == 1) == 3
    assert [line["id"] for line in data["lines"]] == [LAV, CONV, MZCR]
    # la tercera línea une las otras dos: Manzanares es de la convencional y Ciudad Real, de la LAV
    memberships = {
        node_id: sorted(n["line_id"] for n in data["nodes"] if n["id"] == node_id)
        for node_id in ("manzanares", "ciudad-real", "daimiel")
    }
    assert memberships == {
        "manzanares": [CONV, MZCR],
        "ciudad-real": [LAV, MZCR],
        "daimiel": [MZCR],
    }
    for node_id in ("manzanares", "ciudad-real"):
        assert sum(1 for f in data["node_features"]["features"] if f["id"] == node_id) == 1
    # los nodos compartidos conservan la descripción de la línea que los define
    ciudad_real = next(
        n for n in data["nodes"] if n["id"] == "ciudad-real" and n["line_id"] == MZCR
    )
    assert (
        ciudad_real["km"] > 64
        and "Primera estación con parada comercial" in (ciudad_real["description"])
    )


async def test_interruptions_endpoint(client: httpx.AsyncClient) -> None:
    r = await client.get("/api/interruptions")
    assert r.status_code == 200
    by_id = {i["id"]: i for i in r.json()}
    works = by_id[WORKS_CUT]
    assert works["from_name"] == "Almuradiel-Viso del Marqués"
    assert works["to_name"] == "Alcolea de Córdoba"
    # los tramos afectados salen del orden de los dos nodos en la línea
    prefix = "convencional-madrid-alcazar-cordoba:"
    assert works["segment_ids"] == [
        prefix + "almuradiel-viso-del-marques:venta-de-cardenas",
        prefix + "venta-de-cardenas:vilches",
        prefix + "vilches:vadollano",
        prefix + "vadollano:linares-baeza",
        prefix + "linares-baeza:espeluy",
        prefix + "espeluy:andujar",
        prefix + "andujar:villa-del-rio",
        prefix + "villa-del-rio:montoro",
        prefix + "montoro:alcolea-de-cordoba",
    ]
    assert works["start_date"] == "2026-09-06" and works["expected_end_text"] == "otoño de 2027"
    assert works["checked_on"] >= CHECKED
    # la fuente principal va primera, con quién la publica y dónde
    assert works["sources"][0]["publisher"] == "Adif"
    assert works["sources"][0]["url"].startswith("https://www.adif.es/")
    assert len(works["sources"]) >= 2
    assert works["schedule_note"].startswith(
        "Horario publicado; sin circulación real desde el 6 de septiembre de 2026"
    )
    lav = by_id[LAV_CUT]
    assert lav["segment_ids"][0] == "lav-madrid-sevilla:bif-la-sagra:urda"
    assert lav["segment_ids"][-1] == "lav-madrid-sevilla:adamuz:cordoba"
    assert len(lav["segment_ids"]) == 6 and lav["km_from"] < lav["km_to"]


async def test_annotations_endpoint_filters_by_kind_and_day(client: httpx.AsyncClient) -> None:
    r = await client.get("/api/annotations")
    assert r.status_code == 200
    everything = r.json()
    by_id = {a["id"]: a for a in everything}
    works = by_id[WORKS_CUT]
    assert (works["kind"], works["status"]) == ("interrupcion", "vigente")
    # el alcance es de nodo a nodo: ni nodo suelto ni geometría propia
    assert works["line_id"] == CONV and works["node_id"] is None and works["geometry"] is None
    assert len(works["segment_ids"]) == 9
    # las interrupciones son el alias filtrado por tipo: las mismas entradas, campo por campo
    cuts = (await client.get("/api/annotations", params={"kind": "interrupcion"})).json()
    assert cuts == (await client.get("/api/interruptions")).json()
    assert cuts == [a for a in everything if a["kind"] == "interrupcion"]
    on = (await client.get("/api/annotations", params={"on": "2026-09-06"})).json()
    assert {a["id"] for a in on} & {LAV_CUT, WORKS_CUT} == {WORKS_CUT}
    assert [a for a in on if a["kind"] == "interrupcion"] == (
        await client.get("/api/interruptions", params={"date": "2026-09-06"})
    ).json()
    unknown = await client.get("/api/annotations", params={"kind": "no-declarado"})
    assert unknown.status_code == 422 and "interrupcion" in unknown.json()["detail"]


async def test_index_and_lines_carry_annotations_with_interruptions_as_an_alias(
    client: httpx.AsyncClient,
) -> None:
    index = (await client.get("/api/lines")).json()
    assert {LAV_CUT, WORKS_CUT} <= {a["id"] for a in index["annotations"]}
    assert index["interruptions"] == [
        a for a in index["annotations"] if a["kind"] == "interrupcion"
    ]
    line = (await client.get(f"/api/lines/{CONV}")).json()
    # la línea lleva sus anotaciones de cualquier tipo; el alias, solo las interrupciones
    assert {a["id"] for a in line["annotations"]} == {WORKS_CUT, TUNNELS_PROJECT}
    assert [a["id"] for a in line["interruptions"]] == [WORKS_CUT]
    assert (await client.get(f"/api/lines/{MZCR}")).json()["annotations"] == []


async def test_projects_are_served_with_their_status_milestones_and_sketch(
    client: httpx.AsyncClient,
) -> None:
    projects = (await client.get("/api/annotations", params={"kind": "proyecto"})).json()
    by_id = {p["id"]: p for p in projects}
    assert len(by_id) == 5
    mora = by_id["proyecto-lav-mora-alcazar"]
    assert mora["status"] == "sin_ejecutar" and mora["start_date"] is None
    # un esbozo propio, sin tramos de la red, que arranca en la alta velocidad y acaba en Alcázar
    assert mora["geometry"]["type"] == "LineString" and mora["segment_ids"] == []
    assert mora["geometry"]["coordinates"][-1] == [-3.205285, 39.395729]
    assert [m["date"] for m in mora["milestones"]] == sorted(m["date"] for m in mora["milestones"])
    for p in projects:
        assert p["title"] and p["reason"] and p["milestones"], p["id"]
        # cada hito cita una de las fuentes del proyecto, y un proyecto no corta la circulación
        assert {m["source_id"] for m in p["milestones"]} <= {s["id"] for s in p["sources"]}
        assert p["schedule_note"] is None
    tunnels = by_id[TUNNELS_PROJECT]
    assert (tunnels["status"], tunnels["line_id"]) == ("en_obras", CONV)
    assert (tunnels["from_name"], tunnels["to_name"]) == ("Venta de Cárdenas", "Alcolea de Córdoba")
    assert len(tunnels["segment_ids"]) == 8 and tunnels["geometry"] is None
    # los proyectos no son interrupciones: ni en el alias ni en los pasos ni en los recorridos
    cuts = {a["id"] for a in (await client.get("/api/interruptions")).json()}
    assert not cuts & set(by_id)
    segment = tunnels["segment_ids"][0]
    services = (
        await client.get(f"/api/segments/{segment}/services", params={"date": CHECKED})
    ).json()
    assert [i["id"] for i in services["interruptions"]] == [WORKS_CUT]
    # un proyecto sin fecha de inicio consta desde siempre; el de las obras, desde que empezaron
    before = (await client.get("/api/annotations", params={"on": "2026-09-05"})).json()
    assert {a["id"] for a in before} == set(by_id) - {TUNNELS_PROJECT}


async def test_annotations_of_every_scope_are_stored_and_read_back(
    dsn: str, imported: dict[str, Any], monkeypatch: pytest.MonkeyPatch
) -> None:
    """Un tipo recién declarado se guarda y se lee por el mismo camino, con sus tres alcances."""
    from oniel.db.pool import connect
    from oniel.domain.annotations import ANNOTATION_KINDS, AnnotationKind
    from oniel.repo.network_repo import fetch_annotations, fetch_interruptions

    monkeypatch.setitem(
        ANNOTATION_KINDS,
        "juguete",
        AnnotationKind(
            id="juguete",
            label="el juguete",
            statuses=("en estudio",),
            ended_statuses=frozenset(),
            scopes=("tramo", "nodo", "geometria"),
        ),
    )
    line = {"type": "LineString", "coordinates": [[-3.7, 40.4], [-4.0, 39.9]]}
    common: dict[str, Any] = {
        "kind": "juguete",
        "status": "en estudio",
        "source_ids": ["adif-estado-de-la-red"],
        "checked_on": "2026-03-10",
    }
    entries: list[dict[str, Any]] = [
        {**common, "id": "j-geometria", "title": "Variante de prueba", "geometry": line},
        {**common, "id": "j-nodo", "title": "Estación de prueba", "node_id": "manzanares"},
        {
            **common,
            "id": "j-tramo",
            "reason": "Tramo de prueba.",
            "line_id": MZCR,
            "from_node": "manzanares",
            "to_node": "daimiel",
            "start_date": "2026-03-01",
        },
    ]
    async with connect(dsn) as conn:
        tr = conn.transaction()
        await tr.start()
        try:
            for e in entries:
                await conn.execute(
                    """
                    INSERT INTO annotations (id, kind, status, line_id, from_node_id, to_node_id,
                        node_id, geometry, start_date, title, reason, source_ids, checked_on)
                    VALUES ($1,$2,$3,$4,$5,$6,$7,$8,$9,$10,$11,$12,$13)
                    """,
                    e["id"],
                    e["kind"],
                    e["status"],
                    e.get("line_id"),
                    e.get("from_node"),
                    e.get("to_node"),
                    e.get("node_id"),
                    e.get("geometry"),
                    dt.date.fromisoformat(e["start_date"]) if "start_date" in e else None,
                    e.get("title"),
                    e.get("reason"),
                    e["source_ids"],
                    dt.date.fromisoformat(e["checked_on"]),
                )
            toys = {a.id: a for a in await fetch_annotations(conn, kind="juguete")}
            assert toys["j-geometria"].geometry == line and toys["j-geometria"].segment_ids == []
            assert toys["j-nodo"].node_name == "Manzanares"
            assert toys["j-tramo"].segment_ids and toys["j-tramo"].from_name == "Manzanares"
            # un tipo que no corta la circulación no lleva nota de horario ni cuenta como interrupción
            assert all(a.schedule_note is None for a in toys.values())
            assert not {a.id for a in await fetch_interruptions(conn)} & set(toys)
            # por línea salen las de sus tramos y las de sus nodos; las de geometría propia, no
            in_line = {a.id for a in await fetch_annotations(conn, line_id=MZCR)}
            assert in_line == {"j-nodo", "j-tramo"}
            # el alcance es uno solo: la base rechaza una entrada con dos
            with pytest.raises(asyncpg.CheckViolationError):
                async with conn.transaction():
                    await conn.execute(
                        "UPDATE annotations SET node_id = 'daimiel' WHERE id = 'j-geometria'"
                    )
        finally:
            await tr.rollback()


async def test_interruptions_endpoint_filters_by_date(client: httpx.AsyncClient) -> None:
    async def active(day: str) -> set[str]:
        r = await client.get("/api/interruptions", params={"date": day})
        assert r.status_code == 200
        return {i["id"] for i in r.json()} & {LAV_CUT, WORKS_CUT}

    assert await active("2026-09-05") == set()
    assert await active("2026-09-06") == {WORKS_CUT}
    assert await active("2026-10-27") == {WORKS_CUT}
    assert await active(CHECKED) == {LAV_CUT, WORKS_CUT}


async def test_network_carries_the_interruptions(client: httpx.AsyncClient) -> None:
    data = (await client.get("/api/network")).json()
    assert {LAV_CUT, WORKS_CUT} <= {i["id"] for i in data["interruptions"]}
    segment_ids = {s["id"] for s in data["segments"]}
    for i in data["interruptions"]:
        assert i["segment_ids"] and set(i["segment_ids"]) <= segment_ids


async def test_segment_services_carry_a_note_when_the_segment_is_interrupted(
    client: httpx.AsyncClient,
) -> None:
    cut = "convencional-madrid-alcazar-cordoba:venta-de-cardenas:vilches"
    body = (await client.get(f"/api/segments/{cut}/services", params={"date": CHECKED})).json()
    # el horario publicado sigue trayendo trenes; la nota dice que no circulan
    assert body["passes"]
    assert [i["id"] for i in body["interruptions"]] == [WORKS_CUT]
    assert body["interruptions"][0]["schedule_note"] == (
        "Horario publicado; sin circulación real desde el 6 de septiembre de 2026 (Adif)."
    )
    # antes de las obras, el mismo tramo no lleva nota
    earlier = await client.get(f"/api/segments/{cut}/services", params={"date": "2026-09-05"})
    assert earlier.json()["interruptions"] == []
    # un tramo de la misma línea fuera del corte tampoco
    open_segment = "convencional-madrid-alcazar-cordoba:valdepenas:santa-cruz-de-mudela"
    r = await client.get(f"/api/segments/{open_segment}/services", params={"date": CHECKED})
    assert r.json()["passes"] and r.json()["interruptions"] == []


async def test_closure_of_an_interrupted_segment_says_so(client: httpx.AsyncClient) -> None:
    """Cerrar Villanueva–Adamuz el día de la comprobación: ya estaba interrumpido, y la alternativa también."""
    r = await client.post(
        "/api/simulations/closure",
        json={
            "segment_id": "lav-madrid-sevilla:villanueva-de-cordoba:adamuz",
            "date": CHECKED,
            "start": "08:00",
            "end": "09:00",
        },
    )
    assert r.status_code == 200
    res = r.json()
    assert [i["id"] for i in res["interruptions"]] == [LAV_CUT]
    assert any("interrupción real" in c for c in res["caveats"])
    # la simulación sigue calculándose sobre el horario publicado
    assert res["items"] and sum(res["counts"].values()) == len(res["items"])
    # la alternativa por Despeñaperros cruza el corte por obras, y el rodeo por Manzanares también
    by_manzanares, alt = res["alternatives"]
    assert alt["line_ids"] == ["convencional-madrid-alcazar-cordoba"]
    assert by_manzanares["line_ids"] == [MZCR, CONV]
    assert [i["id"] for i in by_manzanares["interruptions"]] == [WORKS_CUT]
    assert [i["id"] for i in alt["interruptions"]] == [WORKS_CUT]
    assert (
        "no hay circulación entre Almuradiel-Viso del Marqués y Alcolea de Córdoba desde el"
        " 6 de septiembre de 2026 (Adif)" in alt["note"]
    )


async def test_closure_before_the_interruptions_has_no_notes(client: httpx.AsyncClient) -> None:
    r = await client.post(
        "/api/simulations/closure",
        json={
            "segment_id": "lav-madrid-sevilla:villanueva-de-cordoba:adamuz",
            "date": "2026-09-05",
            "start": "08:00",
            "end": "09:00",
        },
    )
    res = r.json()
    assert res["interruptions"] == []
    assert not any("interrupción real" in c for c in res["caveats"])
    assert len(res["alternatives"]) == 2
    for alt in res["alternatives"]:
        assert alt["interruptions"] == [] and "no está disponible" not in alt["note"]


async def test_closure_of_an_open_segment_warns_when_the_alternative_is_interrupted(
    client: httpx.AsyncClient,
) -> None:
    r = await client.post(
        "/api/simulations/closure",
        json={
            "segment_id": "convencional-madrid-alcazar-cordoba:aranjuez:castillejo-anover",
            "date": CHECKED,
            "start": "07:00",
            "end": "10:00",
        },
    )
    res = r.json()
    assert res["interruptions"] == []
    # Madrid – Manzanares por la alta velocidad y la línea de Ciudad Real, o Madrid – Córdoba
    by_ciudad_real, alt = res["alternatives"]
    assert alt["line_ids"] == ["lav-madrid-sevilla"]
    assert [i["id"] for i in alt["interruptions"]] == [LAV_CUT]
    assert by_ciudad_real["line_ids"] == [LAV, MZCR]
    assert (by_ciudad_real["from_node_id"], by_ciudad_real["to_node_id"]) == (
        "madrid-puerta-de-atocha",
        "manzanares",
    )
    # la interrupción de la alta velocidad incluye Madrid – Ciudad Real desde La Sagra
    assert [i["id"] for i in by_ciudad_real["interruptions"]] == [LAV_CUT]


async def test_coverage_and_sources(client: httpx.AsyncClient) -> None:
    r = await client.get("/api/coverage")
    assert r.status_code == 200
    cov = r.json()
    # Daimiel y Almagro son las dos estaciones nuevas; sus trenes ya contaban en la convencional
    assert cov["station_count"] == 6 + 22 + 2 and cov["service_count"] == 99 + 99 + 20
    assert {s["id"] for s in cov["sources"]} >= {
        "renfe-gtfs-av-ld-md",
        "osm-relation-1254828",
        "osm-relation-18368327",
        "osm-relation-11351144",
        "osm-relation-6759901",
        "wikipedia-linea-522",
        "fcmaf-linea-522",
        "adif-mapa-red",
        "adif-estado-de-la-red",
        "adif-aviso-obras-autopista-ferroviaria",
    }
    assert "línea convencional" in cov["notice"]
    assert "y la línea convencional Manzanares – Ciudad Real" in cov["notice"]
    assert [line["id"] for line in cov["lines"]] == [LAV, CONV, MZCR]
    # la cobertura dice de qué conjunto de datos salen las cifras y el día de referencia
    # un conjunto por fuente de horarios: el de Ouigo y el de Renfe
    ouigo, dataset = cov["datasets"]
    assert dataset["id"] == "renfe-gtfs-av-ld-md-2026-11-08"
    assert dataset["source_id"] == "renfe-gtfs-av-ld-md" and dataset["operator_id"] == "renfe"
    assert dataset["file"] == "raw/renfe/google_transit_av_ld_md_2026-11-08.zip"
    assert dataset["retrieved_on"] == "2026-11-08"
    assert (ouigo["id"], ouigo["operator_id"]) == (OUIGO_DATASET_ID, OUIGO_OPERATOR_ID)
    assert (ouigo["valid_from"], ouigo["valid_to"]) == ("2026-06-26", "2026-12-12")
    # los horarios «válidos» son los días que cubren los dos ficheros a la vez: empiezan con el
    # de Renfe y terminan con el de Ouigo, y el día de referencia cae dentro de los dos
    assert (cov["feed_start"], cov["feed_end"]) == (dataset["valid_from"], ouigo["valid_to"])
    assert cov["reference_date"] == "2026-11-13"
    for d in cov["datasets"]:
        assert d["valid_from"] <= cov["reference_date"] <= d["valid_to"]
    # los operadores de trenes, con su fuente y si sus horarios están cargados
    operators = {o["id"]: o for o in cov["operators"] if o["role"] == "operador"}
    assert {k: (o["timetable"], o["source_id"]) for k, o in operators.items()} == {
        "renfe": ("cargado", "renfe-gtfs-av-ld-md"),
        "ouigo": ("cargado", OUIGO_SOURCE_ID),
        "iryo": ("no_publicado", "iryo-web"),
    }
    assert {line["id"]: line["operator_ids"] for line in cov["lines"]} == {
        LAV: ["iryo", "ouigo", "renfe"],
        CONV: ["renfe"],
        MZCR: ["renfe"],
    }
    assert "con los servicios de Ouigo España y Renfe Viajeros que las recorren" in cov["notice"]
    assert "No están los trenes de Iryo, que no publica sus horarios" in cov["notice"]
    assert "interrupciones" in cov["notice"]
    assert cov["reference_date"] is not None


async def test_segment_counts_are_split_by_operator(client: httpx.AsyncClient) -> None:
    """El 13/11/2026: 12 trenes de Ouigo entre Madrid y la bifurcación de Málaga y 6 hasta Sevilla;
    en las líneas convencionales, solo Renfe."""
    body = (await client.get("/api/segment-counts", params={"date": "2026-11-13"})).json()
    split, totals = body["by_operator"], body["counts"]
    assert {s: sum(by.values()) for s, by in split.items()} == totals
    assert split[f"{LAV}:madrid-puerta-de-atocha:bif-torrejon-de-velasco"] == {
        "renfe": 72,
        "ouigo": 12,
    }
    assert split[f"{LAV}:ciudad-real:puertollano"] == {"renfe": 96, "ouigo": 12}
    assert split[f"{LAV}:cordoba:bif-malaga"] == {"renfe": 96, "ouigo": 12}
    assert split[f"{LAV}:bif-malaga:majarabique"] == {"renfe": 49, "ouigo": 6}
    assert split[f"{LAV}:majarabique:sevilla-santa-justa"] == {"renfe": 47, "ouigo": 6}
    lav = [by for s, by in split.items() if s.startswith(f"{LAV}:")]
    assert len(lav) == 11 and all(set(by) == {"renfe", "ouigo"} for by in lav)
    assert all(set(by) == {"renfe"} for s, by in split.items() if not s.startswith(f"{LAV}:"))
    # las listas de trenes del tramo y de la estación llevan el operador de cada servicio
    r = await client.get(
        f"/api/segments/{LAV}:ciudad-real:puertollano/services", params={"date": "2026-11-13"}
    )
    passes = r.json()["passes"]
    ouigo = [p for p in passes if p["service"]["operator_id"] == "ouigo"]
    assert len(passes) == 108 and len(ouigo) == 12
    assert {p["service"]["product"] for p in ouigo} == {"Ouigo"}
    assert {p["kind"] for p in ouigo} == {"estimado"}
    first = ouigo[0]["service"]
    assert (first["train_number"], first["origin_name"], first["destination_name"]) == (
        "6476",
        "Madrid-Puerta de Atocha",
        "Sevilla-Santa Justa",
    )
    calls = (await client.get("/api/nodes/cordoba/services", params={"date": "2026-11-13"})).json()[
        "calls"
    ]
    assert len([c for c in calls if c["operator_id"] == "ouigo"]) == 12
    assert {c["operator_id"] for c in calls} == {"renfe", "ouigo"}
    conv = (
        await client.get("/api/nodes/alcazar-de-san-juan/services", params={"date": "2026-11-13"})
    ).json()["calls"]
    assert {c["operator_id"] for c in conv} == {"renfe"}


def _direct_trains(origin: list[dict[str, Any]], dest: list[dict[str, Any]]) -> int:
    """Trenes directos como los cuenta el comparador del visor (``trenesDirectos``)."""
    arrivals = {c["service_id"]: c for c in dest}
    n = 0
    for c in origin:
        to = arrivals.get(c["service_id"])
        if to is None or not c["boards"] or not to["alights"]:
            continue
        departure: str | None = c["departure"] or c["arrival"]
        arrival: str | None = to["arrival"] or to["departure"]
        if not departure or not arrival:
            continue
        n += _minutes(arrival) > _minutes(departure)
    return n


def _minutes(hhmm: str) -> int:
    return int(hhmm[:2]) * 60 + int(hhmm[3:5]) + (1440 if hhmm.endswith("(+1)") else 0)


async def test_direct_destinations_from_ciudad_real(client: httpx.AsyncClient) -> None:
    """El 13/11/2026, con el GTFS real: a dónde se llega desde Ciudad Real sin cambiar de tren."""
    body = (
        await client.get("/api/nodes/ciudad-real/services", params={"date": "2026-11-13"})
    ).json()
    dest = body["destinations"]
    by_node = {d["node_id"]: d for d in dest if d["node_id"]}
    assert {
        "madrid-puerta-de-atocha",
        "sevilla-santa-justa",
        "cordoba",
        "puertollano",
        "alcazar-de-san-juan",
    } <= set(by_node)
    assert "ciudad-real" not in by_node
    # del más frecuente al menos
    assert [d["trains"] for d in dest] == sorted((d["trains"] for d in dest), reverse=True)
    assert (dest[0]["node_id"], dest[0]["name"], dest[0]["trains"]) == ("cordoba", "Córdoba", 20)
    assert dest[0]["products"] == ["Intercity", "AVLO", "AVE", "ALVIA"]
    assert dest[0]["operators"] == [{"operator_id": "renfe", "trains": 20}]
    assert (dest[0]["first_departure"], dest[0]["last_departure"]) == ("07:55", "22:01")
    # Por Ciudad Real pasan 23 trenes hacia Madrid, pero 11 solo dejan viajeros allí (los
    # Intercity y un Alvia que vienen de Andalucía): a Madrid se puede ir en 12
    assert by_node["madrid-puerta-de-atocha"]["trains"] == 12
    assert by_node["alcazar-de-san-juan"]["products"] == ["MD"]
    # fuera de la red cargada, el destino lleva el nombre de la parada del fichero
    outside = {d["name"]: d["trains"] for d in dest if d["node_id"] is None}
    assert outside["Málaga María Zambrano"] == 8 and outside["Badajoz"] == 1
    assert len(dest) == 49 and len(by_node) == 14


async def test_direct_destinations_carry_each_operator(client: httpx.AsyncClient) -> None:
    body = (
        await client.get(
            "/api/nodes/madrid-puerta-de-atocha/services", params={"date": "2026-11-13"}
        )
    ).json()
    cordoba = body["destinations"][0]
    assert (cordoba["node_id"], cordoba["trains"]) == ("cordoba", 55)
    assert cordoba["operators"] == [
        {"operator_id": "renfe", "trains": 49},
        {"operator_id": "ouigo", "trains": 6},
    ]
    assert all(
        sum(o["trains"] for o in d["operators"]) == d["trains"] for d in body["destinations"]
    )
    # un nodo que no es estación no tiene paradas ni destinos
    urda = (await client.get("/api/nodes/urda/services", params={"date": "2026-11-13"})).json()
    assert urda["calls"] == [] and urda["destinations"] == []


async def test_direct_destinations_match_the_route_comparator(client: httpx.AsyncClient) -> None:
    """El comparador cuenta los trenes directos con las paradas de los dos nodos; la ficha de la
    estación, con una consulta. Tienen que dar el mismo número para cada par de la red."""
    nodes = {n["id"] for n in (await client.get("/api/network")).json()["nodes"]}
    services = {
        n: (await client.get(f"/api/nodes/{n}/services", params={"date": "2026-11-13"})).json()
        for n in sorted(nodes)
    }
    pairs = 0
    for origin, body in services.items():
        expected = {d["node_id"]: d["trains"] for d in body["destinations"] if d["node_id"]}
        counted = {
            to: _direct_trains(body["calls"], services[to]["calls"]) for to in nodes - {origin}
        }
        assert {to: n for to, n in counted.items() if n} == expected, origin
        pairs += len(expected)
    assert pairs > 300


async def test_segment_services_on_a_weekday(client: httpx.AsyncClient) -> None:
    r = await client.get(
        "/api/segments/lav-madrid-sevilla:ciudad-real:puertollano/services",
        params={"date": "2026-11-13"},
    )
    assert r.status_code == 200
    body = r.json()
    numbers = {p["service"]["train_number"]: p for p in body["passes"]}
    assert numbers["02070"]["kind"] == "publicado"
    assert numbers["02070"]["enter"] == "07:55" and numbers["02070"]["exit"] == "08:09"


async def test_diverted_trains_run_along_manzanares_ciudad_real(client: httpx.AsyncClient) -> None:
    """«Trenes que lo recorren» de un tramo nuevo: los MD con paso publicado y los Intercity y
    Alvia desviados con paso estimado, explicado con kilómetros por las líneas."""
    r = await client.get(
        f"/api/segments/{MZCR}:daimiel:almagro/services", params={"date": "2026-11-13"}
    )
    assert r.status_code == 200
    body = r.json()
    assert body["segment"]["tracks"] == 1
    passes = {p["service"]["train_number"]: p for p in body["passes"]}
    products = {p["service"]["product"] for p in body["passes"]}
    assert products == {"MD", "Intercity", "ALVIA"}
    assert body["counts"]["indeterminado"] == 0 and body["counts"]["publicado"] > 0
    intercity = passes["10270"]
    assert intercity["kind"] == "estimado"
    assert intercity["enter"] == "08:09" and intercity["exit"] == "08:22"
    assert "entra en esta línea por Manzanares" in intercity["basis"]
    assert "196 km por esa línea hasta Madrid-Atocha Cercanías" in intercity["basis"]
    assert not any("línea recta" in p["basis"] for p in body["passes"])
    alvia = passes["09366"]
    assert alvia["kind"] == "estimado" and "sin parar en ella" in alvia["basis"]
    # y siguen en la convencional hasta Manzanares, ya sin línea recta
    r = await client.get(
        f"/api/segments/{CONV}:cinco-casas:manzanares/services", params={"date": "2026-11-13"}
    )
    conv = {p["service"]["train_number"]: p for p in r.json()["passes"]}
    assert "64 km por esa línea hasta Ciudad Real" in conv["10270"]["basis"]
    assert "línea recta" not in conv["10270"]["basis"]


async def test_closure_between_manzanares_and_ciudad_real_affects_the_diverted_trains(
    client: httpx.AsyncClient,
) -> None:
    """El Intercity 10270 pasa por Almagro – Ciudad Real de 8:22 (estimado) a 8:35 (publicado):
    un cierre de 8:00 a 9:00 lo afecta, junto con los MD de esa hora."""
    r = await client.post(
        "/api/simulations/closure",
        json={
            "segment_id": f"{MZCR}:almagro:ciudad-real",
            "date": "2026-11-13",
            "start": "08:00",
            "end": "09:00",
        },
    )
    assert r.status_code == 200
    res = r.json()
    items = {i["service"]["train_number"]: i for i in res["items"]}
    assert items["10270"]["status"] == "afectado_estimado"
    assert items["10270"]["enter"] == "08:22" and items["10270"]["exit"] == "08:35"
    affected = [i for i in res["items"] if i["status"].startswith("afectado")]
    assert {"Intercity", "MD"} <= {i["service"]["product"] for i in affected}
    assert any(i["status"] == "afectado_publicado" for i in affected)
    assert sum(res["counts"].values()) == len(res["items"])
    # ninguna línea sola une los dos lados del tramo; el grafo encuentra el rodeo por dos:
    # la convencional hasta Madrid (o hasta Córdoba) y la alta velocidad hasta Ciudad Real
    by_madrid, by_cordoba = res["alternatives"]
    assert by_madrid["line_ids"] == by_cordoba["line_ids"] == [CONV, LAV]
    assert (by_madrid["from_node_id"], by_madrid["to_node_id"]) == ("manzanares", "ciudad-real")
    assert (by_madrid["length_km"], by_madrid["closed_line_length_km"]) == (366.9, 64.4)
    assert [leg["to_name"] for leg in by_madrid["legs"]] == [
        "Madrid-Puerta de Atocha",
        "Ciudad Real",
    ]
    assert by_cordoba["length_km"] == 417.4


async def test_closure_hand_case(client: httpx.AsyncClient) -> None:
    """AVE 02070 el 13/11/2026 en Villanueva–Adamuz con cierre de 8:00 a 9:00: afectado (estimado)."""
    r = await client.post(
        "/api/simulations/closure",
        json={
            "segment_id": "lav-madrid-sevilla:villanueva-de-cordoba:adamuz",
            "date": "2026-11-13",
            "start": "08:00",
            "end": "09:00",
        },
    )
    assert r.status_code == 200
    res = r.json()
    item = next(i for i in res["items"] if i["service"]["train_number"] == "02070")
    assert item["status"] == "afectado_estimado"
    assert item["enter"] == "08:34" and item["exit"] == "08:44"
    assert res["counts"]["afectado_publicado"] + res["counts"]["afectado_estimado"] >= 1
    assert sum(res["counts"].values()) == len(res["items"])
    # la línea convencional une Madrid y Córdoba a ambos lados del tramo cerrado
    # y, más ceñido al tramo, el rodeo de Ciudad Real a Córdoba por Manzanares (dos líneas)
    alt = [a for a in res["alternatives"] if len(a["legs"]) == 1]
    assert [a["line_ids"] for a in res["alternatives"]] == [[MZCR, CONV], [CONV]]
    assert [a["line_id"] for a in alt] == [CONV]
    assert alt[0]["from_node_id"] == "madrid-puerta-de-atocha" and alt[0]["to_node_id"] == "cordoba"
    assert alt[0]["length_km"] > alt[0]["closed_line_length_km"]
    assert alt[0]["single_track_km"] > 100
    assert "Alcázar de San Juan" in alt[0]["via"]
    assert any("alternativo" in c for c in res["caveats"])


async def test_closure_on_the_conventional_line_points_back_to_high_speed(
    client: httpx.AsyncClient,
) -> None:
    r = await client.post(
        "/api/simulations/closure",
        json={
            "segment_id": f"{CONV}:venta-de-cardenas:vilches",
            "date": "2026-11-13",
            "start": "07:00",
            "end": "10:00",
        },
    )
    assert r.status_code == 200
    res = r.json()
    assert res["segment"]["tracks"] == 1
    assert {i["service"]["product"] for i in res["items"]} <= {"MD", "ALVIA", "REG.EXP."}
    # de Manzanares a Córdoba por Ciudad Real (237,2 km frente a 244,6) y Madrid – Córdoba
    assert [a["line_ids"] for a in res["alternatives"]] == [[MZCR, LAV], [LAV]]
    for a in res["alternatives"]:
        assert a["length_km"] < a["closed_line_length_km"]
    assert res["alternatives"][0]["length_km"] == 237.2


async def test_closure_beyond_the_shared_nodes_has_no_alternative(
    client: httpx.AsyncClient,
) -> None:
    r = await client.post(
        "/api/simulations/closure",
        json={
            "segment_id": "lav-madrid-sevilla:bif-malaga:majarabique",
            "date": "2026-11-13",
            "start": "08:00",
            "end": "09:00",
        },
    )
    assert r.status_code == 200
    assert r.json()["alternatives"] == []


async def test_closure_between_urda_and_ciudad_real_finds_the_detour_through_manzanares(
    client: httpx.AsyncClient,
) -> None:
    """El desvío de los Intercity y Alvia tras Urda: 260,5 km por dos líneas frente a 170,8 km."""
    r = await client.post(
        "/api/simulations/closure",
        json={
            "segment_id": f"{LAV}:urda:ciudad-real",
            "date": "2026-11-13",
            "start": "08:00",
            "end": "09:00",
        },
    )
    assert r.status_code == 200
    detour, whole_line = r.json()["alternatives"]
    assert detour["line_ids"] == [CONV, MZCR]
    assert (detour["from_node_id"], detour["to_node_id"]) == (
        "madrid-puerta-de-atocha",
        "ciudad-real",
    )
    assert (detour["length_km"], detour["closed_line_length_km"]) == (260.5, 170.8)
    assert detour["single_track_km"] == 64.4 and detour["time_min"] == 107
    assert "hasta Manzanares y por la línea convencional Manzanares – Ciudad Real" in detour["note"]
    # ese rodeo queda al norte del corte por obras de la convencional: sin interrupciones
    assert detour["interruptions"] == []
    assert whole_line["line_ids"] == [CONV] and whole_line["to_node_id"] == "cordoba"
    assert [i["id"] for i in whole_line["interruptions"]] == [WORKS_CUT]


async def test_closure_with_a_scenario_adds_its_other_changes(client: httpx.AsyncClient) -> None:
    """Con Daimiel – Almagro cerrado además, el rodeo por Manzanares desaparece."""
    body = {
        "segment_id": f"{LAV}:urda:ciudad-real",
        "date": "2026-11-13",
        "start": "08:00",
        "end": "09:00",
        "scenario": f"c~{MZCR}:daimiel:almagro",
    }
    r = await client.post("/api/simulations/closure", json=body)
    assert r.status_code == 200
    assert [a["line_ids"] for a in r.json()["alternatives"]] == [[CONV]]
    r = await client.post("/api/simulations/closure", json={**body, "scenario": "c~no:existe"})
    assert r.status_code == 422 and "Escenario no válido" in r.json()["detail"]


async def test_routes_between_madrid_and_ciudad_real(client: httpx.AsyncClient) -> None:
    r = await client.get(
        "/api/routes", params={"from": "madrid-puerta-de-atocha", "to": "ciudad-real"}
    )
    assert r.status_code == 200
    body = r.json()
    assert body["scenario_code"] == ""
    assert (body["max_changes"], body["max_ratio"]) == (5, 2)
    # la vuelta por Córdoba (613,5 km) pasa del doble del más corto y no se devuelve
    assert [route["line_ids"] for route in body["routes"]] == [[LAV], [CONV, MZCR]]
    assert [route["length_km"] for route in body["routes"]] == [170.8, 260.5]
    # con el recorrido por Manzanares comparte Madrid – Manzanares, y desde allí recorre 417,4 km
    # para lo que el otro hace en 64,4 km: 6,5 veces. Con un tope de 4 sigue fuera; con 7, entra.
    wide = {"from": "madrid-puerta-de-atocha", "to": "ciudad-real"}
    r = await client.get("/api/routes", params={**wide, "max_ratio": "4"})
    assert [route["length_km"] for route in r.json()["routes"]] == [170.8, 260.5]
    r = await client.get("/api/routes", params={**wide, "max_ratio": "7"})
    assert [route["length_km"] for route in r.json()["routes"]] == [170.8, 260.5, 613.5]
    assert body["routes"][0]["time_min"] == 40
    assert "velocidad habitual" in body["method"]
    assert all(route["interruptions"] == [] for route in body["routes"])


async def test_routes_with_a_scenario_and_the_interruptions_of_a_day(
    client: httpx.AsyncClient,
) -> None:
    params = {
        "from": "madrid-puerta-de-atocha",
        "to": "cordoba",
        "scenario": f"c~{LAV}:urda:ciudad-real",
        "date": CHECKED,
        "max_changes": "2",
    }
    r = await client.get("/api/routes", params=params)
    assert r.status_code == 200
    body = r.json()
    assert body["scenario"]["closures"] == [f"{LAV}:urda:ciudad-real"]
    assert body["scenario_code"] == f"c~{LAV}:urda:ciudad-real"
    # sin Urda – Ciudad Real quedan el desvío por Manzanares y la convencional entera
    assert [route["line_ids"] for route in body["routes"]] == [[CONV, MZCR, LAV], [CONV]]
    assert [[i["id"] for i in route["interruptions"]] for route in body["routes"]] == [
        [LAV_CUT],
        [WORKS_CUT],
    ]
    # las interrupciones vigentes como cierres del escenario: ese día no queda ningún recorrido
    r = await client.get("/api/routes", params={**params, "avoid_interruptions": "true"})
    assert r.json()["routes"] == []
    assert len(r.json()["scenario"]["closures"]) > 1
    # el mismo escenario como JSON
    as_json = json.dumps({"closures": [f"{LAV}:urda:ciudad-real"]})
    r = await client.get("/api/routes", params={**params, "scenario": as_json})
    assert [route["line_ids"] for route in r.json()["routes"]] == [[CONV, MZCR, LAV], [CONV]]


async def test_routes_reject_unknown_nodes_and_unreadable_scenarios(
    client: httpx.AsyncClient,
) -> None:
    r = await client.get("/api/routes", params={"from": "atlantida", "to": "cordoba"})
    assert r.status_code == 404
    ok = {"from": "madrid-puerta-de-atocha", "to": "cordoba"}
    for scenario in ("x~nada", "c~no:existe:aqui", '{"closures": 3}'):
        r = await client.get("/api/routes", params={**ok, "scenario": scenario})
        assert r.status_code == 422 and "Escenario no válido" in r.json()["detail"]


async def test_unknown_segment_is_404(client: httpx.AsyncClient) -> None:
    r = await client.post(
        "/api/simulations/closure",
        json={"segment_id": "nada", "date": "2026-11-13", "start": "08:00", "end": "09:00"},
    )
    assert r.status_code == 404


async def test_lines_endpoints_serve_the_network_in_parts(client: httpx.AsyncClient) -> None:
    network = (await client.get("/api/network")).json()
    index = (await client.get("/api/lines")).json()
    assert index["lines"] == network["lines"]
    assert index["connections"] == network["connections"]
    assert index["connection_features"] == network["connection_features"]
    assert index["interruptions"] == network["interruptions"]
    # los nodos del índice son los de la red sin sus textos
    assert index["nodes"] == [
        {k: v for k, v in n.items() if k not in ("description", "details")}
        for n in network["nodes"]
    ]
    # los tramos son los mismos, con sus datos, y la geometría simplificada no mueve los extremos
    full = {f["id"]: f for f in network["segment_features"]["features"]}
    assert [f["id"] for f in index["segment_features"]["features"]] == list(full)
    points = 0
    for f in index["segment_features"]["features"]:
        assert f["properties"] == full[f["id"]]["properties"]
        coords, original = f["geometry"]["coordinates"], full[f["id"]]["geometry"]["coordinates"]
        assert coords[0] == original[0] and coords[-1] == original[-1]
        assert set(map(tuple, coords)) <= set(map(tuple, original))
        points += len(coords)
    assert points < sum(len(f["geometry"]["coordinates"]) for f in full.values()) / 10

    counts = (await client.get("/api/segment-counts")).json()
    nodes: list[Any] = []
    segments: list[Any] = []
    features: list[Any] = []
    merged: dict[str, int] = {}
    for line in index["lines"]:
        detail = (await client.get(f"/api/lines/{line['id']}")).json()
        assert detail["line"] == line
        assert detail["date"] == counts["date"]
        assert detail["network_max_count"] == max(counts["counts"].values())
        node_ids = {n["id"] for n in detail["nodes"]}
        assert detail["connections"] == [
            c for c in network["connections"] if c["node_id"] in node_ids
        ]
        assert detail["interruptions"] == [
            i for i in network["interruptions"] if i["line_id"] == line["id"]
        ]
        nodes += detail["nodes"]
        segments += detail["segments"]
        features += detail["segment_features"]["features"]
        merged |= detail["counts"]
        # el reparto por operador de cada tramo suma su recuento, y hoy todo es de Renfe
        assert detail["counts_by_operator"] == {
            s: counts["by_operator"][s] for s in detail["counts"]
        }
    assert {s: sum(by.values()) for s, by in counts["by_operator"].items()} == counts["counts"]
    # las líneas, juntas, suman lo mismo que la red entera
    assert nodes == network["nodes"]
    assert segments == network["segments"]
    assert features == network["segment_features"]["features"]
    assert merged == counts["counts"]

    other_day = (await client.get(f"/api/lines/{MZCR}", params={"date": "2026-11-14"})).json()
    assert other_day["date"] == "2026-11-14"
    assert (await client.get("/api/lines/no-existe")).status_code == 404


async def test_snapshot_parts_add_up_to_the_whole_network(
    imported: dict[str, Any], dsn: str, tmp_path: Path
) -> None:
    from oniel.db.pool import connect
    from oniel.export.snapshot import export_snapshot
    from oniel.repo import network_repo, services_repo

    async with connect(dsn) as conn:
        result = await export_snapshot(conn, tmp_path)
        whole = await network_repo.fetch_network(conn)
        day = result["date"]
        counts = {
            "date": day,
            "counts": await services_repo.daily_counts(conn, dt.date.fromisoformat(day)),
            "by_operator": await services_repo.daily_counts_by_operator(
                conn, dt.date.fromisoformat(day)
            ),
        }
    network = whole.model_dump(mode="json")

    def read(name: str) -> Any:
        return json.loads((tmp_path / name).read_text(encoding="utf-8"))

    index = read("index.json")
    # la red entera ya no se exporta en un solo fichero: el visor no lo descargaba
    assert not (tmp_path / "network.json").exists()
    assert not (tmp_path / "segment-counts.json").exists()
    assert result["lines"] == [LAV, CONV, MZCR]
    assert sorted(p.name for p in (tmp_path / "lines").iterdir()) == sorted(
        f"{line}.json" for line in result["lines"]
    )
    assert index["lines"] == network["lines"]
    assert [n["id"] for n in index["nodes"]] == [n["id"] for n in network["nodes"]]
    details = [read(f"lines/{line}.json") for line in result["lines"]]
    assert [n for d in details for n in d["nodes"]] == network["nodes"]
    assert [s for d in details for s in d["segments"]] == network["segments"]
    assert [f for d in details for f in d["segment_features"]["features"]] == network[
        "segment_features"
    ]["features"]
    merged: dict[str, int] = {}
    by_operator: dict[str, dict[str, int]] = {}
    for d in details:
        assert d["date"] == counts["date"]
        merged |= d["counts"]
        by_operator |= d["counts_by_operator"]
    assert merged == counts["counts"]
    assert by_operator == counts["by_operator"]
    assert {s: sum(by.values()) for s, by in by_operator.items()} == counts["counts"]
    # el índice pesa una fracción de la red entera: es lo que el visor descarga al arrancar. Las
    # anotaciones van enteras en los dos y no dependen de la geometría, así que se miden aparte
    notes = {"annotations", "interruptions"}

    def size(payload: dict[str, Any], keys: set[str]) -> int:
        part = {k: v for k, v in payload.items() if k in keys}
        return len(json.dumps(part, ensure_ascii=False).encode())

    assert size(index, set(index) - notes) < size(network, set(network) - notes) / 5
    # y tienen su propio tope: cuando no quepan, su detalle tendrá que pedirse aparte
    assert size(index, notes) < 40_000
    # una línea que deja de estar cargada no deja su fichero en la instantánea
    (tmp_path / "lines" / "retirada.json").write_text("{}", encoding="utf-8")
    async with connect(dsn) as conn:
        await export_snapshot(conn, tmp_path)
    assert not (tmp_path / "lines" / "retirada.json").exists()
