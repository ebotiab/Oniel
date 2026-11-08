"""Pruebas con PostgreSQL: importación repetible y API. Requieren ONIEL_TEST_DATABASE_URL."""

from __future__ import annotations

import httpx
import pytest
import pytest_asyncio
from asgi_lifespan import LifespanManager
from conftest import DATA_DIR, FEED, SOURCES, SPEC, database_url_for_tests, requires_db

pytestmark = [requires_db, pytest.mark.asyncio(loop_scope="module")]


@pytest.fixture(scope="module")
def dsn() -> str:
    url = database_url_for_tests()
    assert url is not None
    return url


@pytest_asyncio.fixture(loop_scope="module", scope="module")
async def imported(dsn):
    from oniel.db.migrate import drop_everything, migrate
    from oniel.db.pool import connect
    from oniel.gtfs.importer import import_gtfs
    from oniel.network.importer import import_network

    async with connect(dsn) as conn:
        await drop_everything(conn)
        await migrate(conn)
        net1 = await import_network(conn, SPEC, SOURCES, DATA_DIR)
        gtfs1 = await import_gtfs(
            conn, FEED, SPEC, source_id="renfe-gtfs-av-ld-md", operator_id="renfe"
        )
        # repetir la importación debe dejar exactamente el mismo estado
        net2 = await import_network(conn, SPEC, SOURCES, DATA_DIR)
        gtfs2 = await import_gtfs(
            conn, FEED, SPEC, source_id="renfe-gtfs-av-ld-md", operator_id="renfe"
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


async def test_import_is_repeatable(imported):
    net1, net2 = imported["net"]
    gtfs1, gtfs2 = imported["gtfs"]
    assert net1 == net2
    assert gtfs1["trips_imported"] == gtfs2["trips_imported"] == 335
    c = imported["counts"]
    assert c["lines"] == 1 and c["segments"] == 11 and c["services"] == 335
    assert c["service_segment_passes"] == 3222 + 115
    assert c["import_runs"] == 2


@pytest_asyncio.fixture(loop_scope="module", scope="module")
async def client(dsn, imported, monkeypatch_module):
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
def monkeypatch_module():
    mp = pytest.MonkeyPatch()
    yield mp
    mp.undo()


async def test_network_endpoint(client):
    r = await client.get("/api/network")
    assert r.status_code == 200
    data = r.json()
    assert [n["id"] for n in data["nodes"]][:3] == [
        "madrid-puerta-de-atocha",
        "bif-torrejon-de-velasco",
        "bif-la-sagra",
    ]
    assert len(data["segment_features"]["features"]) == 11
    assert data["connection_features"]["features"]


async def test_coverage_and_sources(client):
    r = await client.get("/api/coverage")
    assert r.status_code == 200
    cov = r.json()
    assert cov["station_count"] == 6 and cov["service_count"] == 99
    assert {s["id"] for s in cov["sources"]} >= {
        "renfe-gtfs-av-ld-md",
        "osm-relation-1254828",
        "adif-mapa-red",
    }
    assert cov["reference_date"] is not None


async def test_segment_services_on_a_weekday(client):
    r = await client.get(
        "/api/segments/lav-madrid-sevilla:ciudad-real:puertollano/services",
        params={"date": "2026-11-13"},
    )
    assert r.status_code == 200
    body = r.json()
    numbers = {p["service"]["train_number"]: p for p in body["passes"]}
    assert numbers["02070"]["kind"] == "publicado"
    assert numbers["02070"]["enter"] == "07:55" and numbers["02070"]["exit"] == "08:09"


async def test_closure_hand_case(client):
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


async def test_unknown_segment_is_404(client):
    r = await client.post(
        "/api/simulations/closure",
        json={"segment_id": "nada", "date": "2026-11-13", "start": "08:00", "end": "09:00"},
    )
    assert r.status_code == 404
