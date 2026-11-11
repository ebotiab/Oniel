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
            conn,
            FEED,
            SPECS,
            source_id="renfe-gtfs-av-ld-md",
            operator_id="renfe",
            data_dir=DATA_DIR,
        )
        # repetir la importación debe dejar exactamente el mismo estado
        net2 = [await import_network(conn, s, SOURCES, DATA_DIR) for s in SPECS]
        cuts2 = await import_interruptions(conn, INTERRUPTIONS, SOURCES, DATA_DIR)
        gtfs2 = await import_gtfs(
            conn,
            FEED,
            SPECS,
            source_id="renfe-gtfs-av-ld-md",
            operator_id="renfe",
            data_dir=DATA_DIR,
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
                "datasets",
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
    # el mismo fichero dos veces es un solo conjunto de datos, reconocido por su SHA-256
    assert c["datasets"] == 1
    assert gtfs1["dataset"]["id"] == gtfs2["dataset"]["id"] == "renfe-gtfs-av-ld-md-2026-11-08"
    assert (gtfs1["dataset"]["reused"], gtfs2["dataset"]["reused"]) == (False, True)


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
        "adif-estado-de-la-red",
        "adif-aviso-obras-autopista-ferroviaria",
    }
    assert "línea convencional" in cov["notice"]
    assert "y la línea convencional Manzanares – Ciudad Real" in cov["notice"]
    assert [line["id"] for line in cov["lines"]] == [LAV, CONV, MZCR]
    # la cobertura dice de qué conjunto de datos salen las cifras y el día de referencia
    (dataset,) = cov["datasets"]
    assert dataset["id"] == "renfe-gtfs-av-ld-md-2026-11-08"
    assert dataset["source_id"] == "renfe-gtfs-av-ld-md" and dataset["operator_id"] == "renfe"
    assert dataset["file"] == "raw/renfe/google_transit_av_ld_md_2026-11-08.zip"
    assert dataset["retrieved_on"] == "2026-11-08"
    assert (dataset["valid_from"], dataset["valid_to"]) == (cov["feed_start"], cov["feed_end"])
    assert dataset["valid_from"] <= cov["reference_date"] <= dataset["valid_to"]
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
