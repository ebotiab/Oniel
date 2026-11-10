"""Pruebas con PostgreSQL: importación repetible y API. Requieren ONIEL_TEST_DATABASE_URL."""

from __future__ import annotations

import json
from collections.abc import AsyncIterator, Iterator
from pathlib import Path
from typing import Any

import httpx
import pytest
import pytest_asyncio
from asgi_lifespan import LifespanManager
from conftest import DATA_DIR, FEED, SOURCES, SPEC, database_url_for_tests, requires_db

CONV_SPEC = DATA_DIR / "curated" / "convencional-madrid-alcazar-cordoba.json"
SPECS = [SPEC, CONV_SPEC]
INTERRUPTIONS = DATA_DIR / "curated" / "interrupciones.json"
LAV_CUT = "lav-madrid-andalucia-2026-10-28"
WORKS_CUT = "convencional-obras-autopista-ferroviaria-2026-09-06"
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
    from oniel.network.importer import import_network
    from oniel.network.interruptions import import_interruptions

    async with connect(dsn) as conn:
        await drop_everything(conn)
        await migrate(conn)
        net1 = [await import_network(conn, s, SOURCES, DATA_DIR) for s in SPECS]
        cuts1 = await import_interruptions(conn, INTERRUPTIONS, SOURCES, DATA_DIR)
        gtfs1 = await import_gtfs(
            conn, FEED, SPECS, source_id="renfe-gtfs-av-ld-md", operator_id="renfe"
        )
        # repetir la importación debe dejar exactamente el mismo estado
        net2 = [await import_network(conn, s, SOURCES, DATA_DIR) for s in SPECS]
        cuts2 = await import_interruptions(conn, INTERRUPTIONS, SOURCES, DATA_DIR)
        gtfs2 = await import_gtfs(
            conn, FEED, SPECS, source_id="renfe-gtfs-av-ld-md", operator_id="renfe"
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
                "interruptions",
            )
        }
    return {
        "net": (net1, net2),
        "gtfs": (gtfs1, gtfs2),
        "interruptions": (cuts1, cuts2),
        "counts": counts,
    }


async def test_import_is_repeatable(imported: dict[str, Any]) -> None:
    net1, net2 = imported["net"]
    gtfs1, gtfs2 = imported["gtfs"]
    assert net1 == net2
    # 335 viajes en la LAV y 503 en la convencional; 24 Intercity/Alvia Madrid-Atocha Cercanías
    # cuentan en las dos (convencional hasta Manzanares, LAV desde Ciudad Real) y se guardan una vez
    assert gtfs1["trips_imported"] == gtfs2["trips_imported"] == 335 + 503 - 24
    assert gtfs1["lines"]["lav-madrid-sevilla"]["trips"] == 335
    assert gtfs1["lines"]["convencional-madrid-alcazar-cordoba"]["trips"] == 503
    assert gtfs1["lines"]["lav-madrid-sevilla"]["route_overrides"] == {
        "atocha-cercanias-ciudad-real-por-manzanares": 20,
        "atocha-cercanias-cordoba-por-manzanares": 4,
    }
    c = imported["counts"]
    assert c["lines"] == 2 and c["segments"] == 11 + 25 and c["services"] == 814
    assert c["service_segment_passes"] == (3126 + 115) + (2469 + 683)
    assert c["import_runs"] == 2


async def test_interruptions_import_is_repeatable_and_survives_a_network_reimport(
    imported: dict[str, Any],
) -> None:
    from oniel.network.spec import load_interruptions

    cuts1, cuts2 = imported["interruptions"]
    assert cuts1 == cuts2
    # la segunda importación de la red (que borra y recrea nodos de línea y tramos) no las pierde
    assert imported["counts"]["interruptions"] == len(load_interruptions(INTERRUPTIONS))
    assert {LAV_CUT, WORKS_CUT} <= set(cuts1["ids"])


async def test_interruptions_that_do_not_fit_the_network_are_not_imported(
    dsn: str, imported: dict[str, Any], tmp_path: Path
) -> None:
    from oniel.db.pool import connect
    from oniel.network.interruptions import import_interruptions

    bad = tmp_path / "interrupciones.json"
    entry = {
        "id": "corte-imposible",
        "line_id": "lav-madrid-sevilla",
        "from_node": "cordoba",
        "to_node": "ciudad-real",
        "start_date": "2026-03-01",
        "reason": "Obras en la vía.",
        "source_ids": ["adif-estado-de-la-red"],
        "checked_on": "2026-03-10",
    }
    bad.write_text(json.dumps({"interruptions": [entry]}), encoding="utf-8")
    async with connect(dsn) as conn:
        with pytest.raises(ValueError, match="cordoba está después de ciudad-real"):
            await import_interruptions(conn, bad, SOURCES, DATA_DIR)
        # la importación fallida no toca lo que había
        assert (
            await conn.fetchval("SELECT count(*) FROM interruptions")
            == (imported["counts"]["interruptions"])
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
    assert len(data["segment_features"]["features"]) == 11 + 25
    assert data["connection_features"]["features"]
    # Córdoba y Atocha están en las dos líneas: una fila por línea, un solo punto en el mapa
    cordoba = [n for n in data["nodes"] if n["id"] == "cordoba"]
    assert sorted(n["line_id"] for n in cordoba) == [
        "convencional-madrid-alcazar-cordoba",
        "lav-madrid-sevilla",
    ]
    assert sum(1 for f in data["node_features"]["features"] if f["id"] == "cordoba") == 1
    single = [s for s in data["segments"] if s["tracks"] == 1]
    assert single and all(s["line_id"] == "convencional-madrid-alcazar-cordoba" for s in single)
    assert [line["id"] for line in data["lines"]] == [
        "lav-madrid-sevilla",
        "convencional-madrid-alcazar-cordoba",
    ]


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
    # la alternativa por Despeñaperros cruza el corte por obras
    (alt,) = res["alternatives"]
    assert alt["line_id"] == "convencional-madrid-alcazar-cordoba"
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
    (alt,) = res["alternatives"]
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
    (alt,) = res["alternatives"]
    assert alt["line_id"] == "lav-madrid-sevilla"
    assert [i["id"] for i in alt["interruptions"]] == [LAV_CUT]


async def test_coverage_and_sources(client: httpx.AsyncClient) -> None:
    r = await client.get("/api/coverage")
    assert r.status_code == 200
    cov = r.json()
    assert cov["station_count"] == 6 + 22 and cov["service_count"] == 99 + 99
    assert {s["id"] for s in cov["sources"]} >= {
        "renfe-gtfs-av-ld-md",
        "osm-relation-1254828",
        "osm-relation-18368327",
        "osm-relation-11351144",
        "adif-mapa-red",
        "adif-estado-de-la-red",
        "adif-aviso-obras-autopista-ferroviaria",
    }
    assert "línea convencional" in cov["notice"]
    assert "interrupciones" in cov["notice"]
    assert cov["reference_date"] is not None


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
    alt = res["alternatives"]
    assert [a["line_id"] for a in alt] == ["convencional-madrid-alcazar-cordoba"]
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
            "segment_id": "convencional-madrid-alcazar-cordoba:venta-de-cardenas:vilches",
            "date": "2026-11-13",
            "start": "07:00",
            "end": "10:00",
        },
    )
    assert r.status_code == 200
    res = r.json()
    assert res["segment"]["tracks"] == 1
    assert {i["service"]["product"] for i in res["items"]} <= {"MD", "ALVIA", "REG.EXP."}
    assert [a["line_id"] for a in res["alternatives"]] == ["lav-madrid-sevilla"]
    assert res["alternatives"][0]["length_km"] < res["alternatives"][0]["closed_line_length_km"]


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


async def test_unknown_segment_is_404(client: httpx.AsyncClient) -> None:
    r = await client.post(
        "/api/simulations/closure",
        json={"segment_id": "nada", "date": "2026-11-13", "start": "08:00", "end": "09:00"},
    )
    assert r.status_code == 404
