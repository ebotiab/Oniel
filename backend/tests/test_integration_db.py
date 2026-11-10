"""Pruebas con PostgreSQL: importación repetible y API. Requieren ONIEL_TEST_DATABASE_URL."""

from __future__ import annotations

from collections.abc import AsyncIterator, Iterator
from typing import Any

import httpx
import pytest
import pytest_asyncio
from asgi_lifespan import LifespanManager
from conftest import DATA_DIR, FEED, SOURCES, SPECS, database_url_for_tests, requires_db

LAV, CONV, MZCR = (
    "lav-madrid-sevilla",
    "convencional-madrid-alcazar-cordoba",
    "manzanares-ciudad-real",
)
RULES = {
    "atocha-cercanias-ciudad-real-por-manzanares": 20,
    "atocha-cercanias-cordoba-por-manzanares": 4,
}

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

    async with connect(dsn) as conn:
        await drop_everything(conn)
        await migrate(conn)
        net1 = [await import_network(conn, s, SOURCES, DATA_DIR) for s in SPECS]
        gtfs1 = await import_gtfs(
            conn, FEED, SPECS, source_id="renfe-gtfs-av-ld-md", operator_id="renfe"
        )
        # repetir la importación debe dejar exactamente el mismo estado
        net2 = [await import_network(conn, s, SOURCES, DATA_DIR) for s in SPECS]
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
            )
        }
    return {"net": (net1, net2), "gtfs": (gtfs1, gtfs2), "counts": counts}


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
    c = imported["counts"]
    assert c["lines"] == 3 and c["segments"] == 11 + 25 + 3 and c["services"] == 814
    assert c["service_segment_passes"] == (3126 + 115) + (2469 + 683) + (72 + 390)
    assert c["import_runs"] == 2


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


async def test_coverage_and_sources(client: httpx.AsyncClient) -> None:
    r = await client.get("/api/coverage")
    assert r.status_code == 200
    cov = r.json()
    # Daimiel y Almagro son las dos estaciones nuevas; sus trenes ya contaban en la convencional
    assert cov["station_count"] == 6 + 22 + 2 and cov["service_count"] == 99 + 99
    assert {s["id"] for s in cov["sources"]} >= {
        "renfe-gtfs-av-ld-md",
        "osm-relation-1254828",
        "osm-relation-18368327",
        "osm-relation-11351144",
        "osm-relation-6759901",
        "wikipedia-linea-522",
        "fcmaf-linea-522",
        "adif-mapa-red",
    }
    assert "línea convencional" in cov["notice"]
    assert "y la línea convencional Manzanares – Ciudad Real" in cov["notice"]
    assert [line["id"] for line in cov["lines"]] == [LAV, CONV, MZCR]
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
    # ninguna línea sola une los dos lados del tramo: sin alternativa cargada
    assert res["alternatives"] == []


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
    assert [a["line_id"] for a in res["alternatives"]] == [LAV]
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
