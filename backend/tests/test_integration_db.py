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

LAV, CONV, MZCR, JAEN, LBMG, ALBACETE = (
    "lav-madrid-sevilla",
    "convencional-madrid-alcazar-cordoba",
    "manzanares-ciudad-real",
    "espeluy-jaen",
    "linares-baeza-moreda-granada",
    "alcazar-albacete",
)
LAV_MALAGA, LAV_GRANADA = "lav-cordoba-malaga", "lav-antequera-granada"
BCN = "lav-madrid-barcelona"
RULES = {
    "atocha-cercanias-ciudad-real-por-manzanares": 20,
    "atocha-cercanias-cordoba-por-manzanares": 2,
}
#: La convencional tiene además la regla de los trenes de Jaén que solo paran una vez en ella.
JAEN_RULES = {"cordoba-jaen-sin-paradas": 42}
#: La alta velocidad Madrid – Sevilla tiene además las de los AVE que no paran en Madrid: los de
#: Barcelona entran por la bifurcación Los Gavilanes y los de Valencia, por la de Yeles.
AWAY_RULES = {
    "barcelona-cordoba-sin-parar-en-madrid": 8,
    "barcelona-ciudad-real-sin-parar-en-madrid": 8,
    "valencia-ciudad-real-sin-parar-en-madrid": 4,
}
#: Reglas de la alta velocidad de Barcelona que encajan con el fichero de Renfe; la de los Ouigo
#: que siguen a Andalucía parando en Madrid solo encaja con el de Ouigo (4 viajes).
BCN_RULES = {
    "calatayud-tudela-por-plasencia-de-jalon": 24,
    "calatayud-pamplona-por-plasencia-de-jalon": 3,
    "madrid-tudela-por-plasencia-de-jalon": 53,
    "zaragoza-huesca": 11,
    "barcelona-cordoba-por-valencia": 14,
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
    # Los viajes son ya uno por número de tren y día: el fichero trae 6.841 y 237 números de tren
    # repetidos algún día, que al leerlo se juntan (``oniel.gtfs.variants``).
    # 317 viajes en la LAV, 432 en la convencional, 146 en la de Manzanares a Ciudad Real y 123
    # en la de Jaén. Los 22 Intercity/Alvia Madrid-Atocha Cercanías cuentan en las tres primeras
    # (convencional hasta Manzanares, la tercera entera, LAV desde Ciudad Real), y los 124 MD y
    # Regional Exprés de la tercera y los 123 MD de la de Jaén también están en la convencional:
    # cada viaje se guarda una sola vez. De los 432 de la convencional, 42 entran por la regla
    # de los trenes Córdoba – Jaén sin paradas, que solo paran una vez en ella.
    # De los 38 de la línea de Linares-Baeza a Granada, 12 son Alvia Madrid – Granada –
    # Almería que ya estaban en la LAV y 26, Media Distancia que no pasan por ninguna otra línea.
    # De los 142 de la línea de Alcázar de San Juan a Albacete, 127 ya estaban en la convencional
    # y 15 solo paran en ella una vez (Regional Exprés entre Alcázar de San Juan y Valencia).
    # La alta velocidad de Barcelona añade 571 viajes, de los que 16 ya estaban: los Alvia
    # Barcelona – València – Alcázar de San Juan – Córdoba, que recorren también la convencional,
    # y los AVE de Barcelona a Andalucía de las líneas de Málaga y Granada.
    # y 8 más que solo recorren la alta velocidad Madrid – Sevilla sin parar en Madrid: 4 Avant de
    # Sevilla a Córdoba y 4 AVE de Valencia a Sevilla
    assert gtfs1["trips_in_feed"] == 6841 and gtfs1["merged_train_numbers"] == 237
    trips = 317 + 432 - 22 + 26 + 15 + 37 + 571 - 16 + 8
    assert gtfs1["trips_imported"] == gtfs2["trips_imported"] == trips
    assert gtfs1["lines"][BCN]["trips"] == 571
    assert gtfs1["lines"][BCN]["route_overrides"] == BCN_RULES
    # ningún tramo de esa línea va de una estación a la siguiente (entre dos estaciones siempre
    # hay un PAET o una bifurcación), así que todos sus pasos son estimados
    assert gtfs1["lines"][BCN]["passes"] == {"estimado": 7590}
    # Las dos líneas de alta velocidad de Córdoba a Granada traen 181 y 63 viajes. De ellos, 37 no
    # estaban: los Avant de Sevilla a Málaga y a Granada, los de Málaga a Granada y los AVE
    # de Barcelona a Málaga y a Granada, que no paran en Madrid.
    assert gtfs1["lines"][LAV_MALAGA]["trips"] == 181
    assert gtfs1["lines"][LAV_GRANADA]["trips"] == 63
    assert gtfs1["lines"][LAV_MALAGA]["passes"] == {"estimado": 656, "publicado": 68}
    assert gtfs1["lines"][LAV_GRANADA]["passes"] == {"estimado": 498}
    # En la alta velocidad Madrid – Sevilla, 317 paran en Córdoba y en Madrid y 47 la recorren sin
    # parar en Madrid: 27 Avant de Sevilla y 20 AVE de Barcelona y de Valencia. De esos 47, 31 ya
    # se importaban por las líneas de Málaga y de Granada y 16 son nuevos (4 Avant Sevilla – Córdoba,
    # 8 AVE Barcelona – Sevilla y 4 AVE Valencia – Sevilla).
    assert gtfs1["lines"][LAV]["trips"] == 317 + 47
    assert gtfs1["lines"][CONV]["trips"] == 390 + 42
    assert gtfs1["lines"][MZCR]["trips"] == 124 + 22
    assert gtfs1["lines"][JAEN]["trips"] == 123
    assert gtfs1["lines"][LAV]["route_overrides"] == RULES | AWAY_RULES
    assert gtfs1["lines"][MZCR]["route_overrides"] == RULES
    assert gtfs1["lines"][CONV]["route_overrides"] == RULES | JAEN_RULES
    assert gtfs1["lines"][JAEN]["route_overrides"] == {}
    # en la de Jaén solo los 20 trenes que paran en Mengíbar-Artichuela y en Jaén tienen pasos
    # publicados; los demás entran o salen por Espelúy sin parar en la estación
    assert gtfs1["lines"][JAEN]["passes"] == {"publicado": 20, "estimado": 226}
    assert gtfs1["lines"][MZCR]["passes"] == {"publicado": 124 * 3, "estimado": 22 * 3}
    assert gtfs1["lines"][LBMG]["trips"] == 26 + 12
    assert gtfs1["lines"][ALBACETE]["trips"] == 127 + 15
    assert gtfs1["lines"][ALBACETE]["route_overrides"] == {}
    assert gtfs1["lines"][ALBACETE]["passes"] == {"publicado": 516, "estimado": 478}
    assert gtfs1["lines"][LBMG]["route_overrides"] == {"linares-baeza-almeria-por-moreda": 4}
    assert gtfs1["lines"][LBMG]["passes"] == {"publicado": 18, "estimado": 62}
    assert "indeterminado" not in gtfs1["passes"] and gtfs1["unmapped_stops"] == {}
    # Ouigo: 25 viajes Madrid–Córdoba–Sevilla o Málaga (4 de ellos vienen de Barcelona o siguen
    # hasta allí), todos por la LAV y ninguno por las líneas convencionales. Solo paran en Madrid,
    # Córdoba y Sevilla, así que el paso por cada tramo es estimado: 295 pasos.
    ouigo1, ouigo2 = imported["ouigo"]
    # Y otros 25 por la alta velocidad de Barcelona; los 4 que enlazan con Andalucía cuentan en
    # las dos líneas, así que son 46 viajes distintos y 500 pasos más, también estimados.
    assert ouigo1["trips_imported"] == ouigo2["trips_imported"] == 25 + 25 - 4
    assert ouigo1["train_numbers"] == 30
    assert ouigo1["lines"][BCN]["trips"] == 25
    assert ouigo1["lines"][BCN]["route_overrides"] == {
        "barcelona-andalucia-con-parada-en-madrid": 4
    }
    assert ouigo1["lines"][LAV]["trips"] == 25
    assert ouigo1["lines"][CONV]["trips"] == ouigo1["lines"][MZCR]["trips"] == 0
    assert ouigo1["lines"][JAEN]["trips"] == 0
    assert ouigo1["lines"][LBMG]["trips"] == 0
    assert ouigo1["lines"][ALBACETE]["trips"] == 0
    # los 15 de Málaga siguen por la línea de Córdoba a Málaga sin parar hasta Málaga: 4 tramos
    assert ouigo1["lines"][LAV_MALAGA]["trips"] == 15 and ouigo1["lines"][LAV_GRANADA]["trips"] == 0
    assert ouigo1["lines"][LAV_MALAGA]["passes"] == {"estimado": 15 * 4}
    assert ouigo1["passes"] == {"estimado": 295 + 60 + 500} and ouigo1["unmapped_stops"] == {}
    assert ouigo1["resolution"] == {"completa": 46}
    assert ouigo1["dataset"]["id"] == ouigo2["dataset"]["id"] == OUIGO_DATASET_ID
    assert (ouigo1["feed_start"], ouigo1["feed_end"]) == ("2026-06-26", "2026-12-12")
    c = imported["counts"]
    assert c["lines"] == 9 and c["segments"] == 13 + 25 + 3 + 2 + 6 + 7 + 4 + 8 + 20
    assert c["services"] == trips + 46
    renfe_passes = (3853 + 121) + (1968 + 523) + (66 + 372) + (226 + 20) + (62 + 18) + (478 + 516)
    renfe_passes += (656 + 68) + 498 + 7590
    assert c["service_segment_passes"] == renfe_passes + 295 + 60 + 500
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


async def test_lines_carry_their_zone(client: httpx.AsyncClient) -> None:
    r = await client.get("/api/network")
    assert r.status_code == 200
    zones = {ln["id"]: ln["zone"] for ln in r.json()["lines"]}
    assert zones["lav-madrid-sevilla"]["id"] == "andalucia"
    assert zones["lav-madrid-sevilla"]["name"] == "Andalucía"
    assert "Sevilla" in zones["lav-madrid-sevilla"]["cities"]
    assert zones["lav-madrid-barcelona"]["id"] == "cataluna"
    assert zones["alcazar-albacete"]["id"] == "madrid-castilla-la-mancha"
    # el orden de las zonas va de norte a sur
    assert zones["lav-madrid-barcelona"]["sort_order"] < zones["lav-madrid-sevilla"]["sort_order"]
    assert all(zone is not None for zone in zones.values())


async def test_network_endpoint(client: httpx.AsyncClient) -> None:
    r = await client.get("/api/network")
    assert r.status_code == 200
    data = r.json()
    assert [n["id"] for n in data["nodes"]][:3] == [
        "madrid-puerta-de-atocha",
        "bif-los-gavilanes",
        "bif-torrejon-de-velasco",
    ]
    assert len(data["segment_features"]["features"]) == 13 + 25 + 3 + 2 + 6 + 7 + 4 + 8 + 20
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
    assert {s["line_id"] for s in single} == {CONV, MZCR, JAEN, LBMG, LAV_GRANADA}
    # de Antequera a Granada, vía única desde la bifurcación Archidona: 5 de sus 8 tramos
    assert [s["id"].split(":")[1] for s in single if s["line_id"] == LAV_GRANADA] == [
        "bif-archidona",
        "bif-riofrio",
        "loja",
        "bif-tocon",
        "bif-la-chana",
    ]
    assert sum(1 for s in data["segments"] if s["line_id"] == JAEN and s["tracks"] == 1) == 2
    assert sum(1 for s in data["segments"] if s["line_id"] == MZCR and s["tracks"] == 1) == 3
    assert sum(1 for s in data["segments"] if s["line_id"] == LBMG and s["tracks"] == 1) == 6
    assert [line["id"] for line in data["lines"]] == [
        LAV,
        CONV,
        MZCR,
        JAEN,
        LBMG,
        ALBACETE,
        LAV_MALAGA,
        LAV_GRANADA,
        BCN,
    ]
    # la conexión a trazos de Linares-Baeza hacia Almería también desaparece: la línea cargada
    # llega a Moreda, y de allí sale a trazos lo que falta hasta Guadix y Almería
    assert "conv-linares-almeria" not in connections
    assert connections["conv-moreda-almeria"] == "moreda"
    # y la de Granada hacia Antequera: la alta velocidad está cargada y sus conexiones a trazos
    # salen de Antequera-Santa Ana, hacia Málaga, y de la bifurcación Bobadilla
    assert "av-antequera-granada" not in connections and "lav-cordoba-malaga" not in connections
    assert connections["lav-antequera-malaga"] == "antequera-santa-ana"
    assert connections["enlace-malaga-granada"] == "bif-bobadilla"
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


async def test_segments_carry_their_attributes_with_source_and_date(
    client: httpx.AsyncClient, dsn: str
) -> None:
    from oniel.db.pool import connect

    # una fila por tramo y atributo, también tras importar la red dos veces
    async with connect(dsn) as conn:
        rows = await conn.fetch("SELECT segment_id, attribute, value FROM segment_attributes")
        columns = await conn.fetch("SELECT id, tracks FROM segments")
    # el número de vías y los tres de señalización, en los 86 tramos
    gauge = {r["segment_id"] for r in rows if r["attribute"] == "gauge"}
    speed = {r["segment_id"]: r["value"] for r in rows if r["attribute"] == "max_speed_kmh"}
    assert len(rows) - len(gauge) - len(speed) == 4 * (13 + 25 + 3 + 2 + 6 + 7 + 4 + 8 + 20)
    # la velocidad declarada, solo donde OpenStreetMap no la trae: tres tramos de la alta
    # velocidad de Barcelona, a la salida de Zaragoza y a la entrada y la salida de Lleida
    assert speed == {
        f"{BCN}:bif-huesca:bif-canal-imperial": 220,
        f"{BCN}:bif-les-torres-de-sanui:lleida-pirineus": 140,
        f"{BCN}:lleida-pirineus:bif-artesa-de-lleida": 220,
    }
    # y el ancho mixto, solo en el paso por Loja y en la entrada a Granada
    assert gauge == {
        f"{LAV_GRANADA}:bif-riofrio:loja",
        f"{LAV_GRANADA}:loja:bif-tocon",
        f"{LAV_GRANADA}:bif-la-chana:granada",
    }
    attributes = {"tracks", "proteccion_tren", "bloqueo", "mando", "gauge", "max_speed_kmh"}
    assert {r["attribute"] for r in rows} == attributes
    # `segments.tracks` sigue escrito, con el mismo valor que el atributo
    tracks = {r["segment_id"]: r["value"] for r in rows if r["attribute"] == "tracks"}
    assert tracks == {r["id"]: r["tracks"] for r in columns}

    index = (await client.get("/api/lines")).json()
    by_id = {f["id"]: f["properties"] for f in index["segment_features"]["features"]}
    assert all(p["attributes"]["tracks"]["value"] == p["tracks"] for p in by_id.values())
    # la vía única de Despeñaperros viene de una sección, con su fuente y su fecha
    single = by_id[f"{CONV}:santa-cruz-de-mudela:almuradiel-viso-del-marques"]
    dr = {"source_id": "adif-declaracion-red-2026-mapas", "checked_on": "2026-11-12"}
    assert single["attributes"] == {
        "tracks": {
            "value": 1,
            "source_id": "wikipedia-lineas-300-400",
            "checked_on": "2026-11-08",
        },
        "proteccion_tren": {"value": "asfa", **dr},
        "bloqueo": {"value": "bau", **dr},
        "mando": {"value": "ctc", **dr},
    }
    # la vía doble de la alta velocidad es el valor de la línea, sin fuente propia
    double = by_id[f"{LAV}:ciudad-real:puertollano"]
    assert double["attributes"] == {
        "tracks": {"value": 2, "source_id": None, "checked_on": None},
        "proteccion_tren": {"value": "lzb_asfa", **dr},
        "bloqueo": {"value": "bca", **dr},
        # la fuente no dice el mando de la alta velocidad: el hueco viaja como valor
        "mando": {"value": "sin_dato_publicado", **dr},
    }
    # lo mismo en el detalle de la línea y en la ficha del tramo
    detail = (await client.get(f"/api/lines/{MZCR}")).json()
    assert [s["attributes"]["tracks"]["value"] for s in detail["segments"]] == [1, 1, 1]
    assert {s["attributes"]["tracks"]["source_id"] for s in detail["segments"]} == {
        "wikipedia-linea-522"
    }
    services = (await client.get(f"/api/segments/{MZCR}:manzanares:daimiel/services")).json()
    assert services["segment"]["attributes"]["tracks"]["checked_on"] == "2026-11-10"


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
    # (los otros dos, por Moreda y Granada, son rodeos de más del doble: no se listan, se cuentan)
    by_manzanares, alt = res["alternatives"]
    assert res["omitted_alternatives"] == 2
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
    assert (len(res["alternatives"]), res["omitted_alternatives"]) == (2, 2)
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
    # Daimiel y Almagro son las dos estaciones de la tercera línea, y Mengíbar-Artichuela y Jaén,
    # las de la cuarta; con esta hay 9 servicios más el día de referencia, los trenes de Jaén
    # que no entraban en la convencional. La de Linares-Baeza a Granada trae cinco estaciones
    # más y los 12 Media Distancia de ese día que no pasan por ninguna otra línea. La de Alcázar
    # de San Juan a Albacete trae 7 estaciones, de Campo de Criptana a Albacete, y un servicio
    # más: de sus 17 trenes de ese día, 16 ya estaban en la convencional y el otro, un Regional
    # Exprés de Alcázar de San Juan a Valencia, solo para en ella una vez.
    # Las de alta velocidad de Córdoba a Granada añaden Puente Genil-Herrera, Antequera-Santa Ana,
    # Antequera AV y Loja (Granada ya estaba) y 30 números de tren: los Avant de Sevilla y de
    # Málaga y los AVE de Barcelona que no paran en Madrid
    # La alta velocidad de Barcelona añade 6: Guadalajara-Yebes, Calatayud, Zaragoza-Delicias,
    # Lleida-Pirineus, Camp de Tarragona y Barcelona-Sants
    assert cov["station_count"] == 6 + 22 + 2 + 2 + 5 + 7 + 4 + 6
    # 429 servicios el jueves 12 de noviembre, el día de referencia desde que está cargada la
    # alta velocidad de Barcelona (eran 270 el viernes 13 con las ocho líneas anteriores)
    # y 4 más con los que recorren la alta velocidad Madrid – Sevilla sin parar en Madrid ni pasar
    # por otra línea cargada (los Avant de Sevilla a Córdoba y los AVE de Valencia a Sevilla)
    assert cov["service_count"] == 429 + 4
    assert {s["id"] for s in cov["sources"]} >= {
        "renfe-gtfs-av-ld-md",
        "osm-relation-1254828",
        "osm-relation-18368327",
        "osm-relation-11351144",
        "osm-relation-6759901",
        "wikipedia-linea-522",
        "fcmaf-linea-522",
        "osm-relation-11351146",
        "wikipedia-linea-402",
        "wikipedia-linea-300-alcazar-albacete",
        "osm-relation-6641023",
        "osm-relation-11350675",
        "wikipedia-lineas-410-416",
        "adif-mapa-red",
        "adif-estado-de-la-red",
        "adif-aviso-obras-autopista-ferroviaria",
    }
    assert "línea convencional" in cov["notice"]
    assert "la línea convencional Manzanares – Ciudad Real" in cov["notice"]
    assert "la línea convencional Espelúy – Jaén" in cov["notice"]
    assert "la línea convencional Alcázar de San Juan – Albacete" in cov["notice"]
    assert "la línea de alta velocidad Antequera – Granada" in cov["notice"]
    assert "y la línea de alta velocidad Madrid – Zaragoza – Barcelona" in cov["notice"]
    assert [line["id"] for line in cov["lines"]] == [
        LAV,
        CONV,
        MZCR,
        JAEN,
        LBMG,
        ALBACETE,
        LAV_MALAGA,
        LAV_GRANADA,
        BCN,
    ]
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
    # el laborable con más servicios: con la línea de Barcelona es el jueves 12, no el viernes 13
    assert cov["reference_date"] == "2026-11-12"
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
        JAEN: ["renfe"],
        LBMG: ["renfe"],
        ALBACETE: ["renfe"],
        LAV_MALAGA: ["iryo", "ouigo", "renfe"],
        LAV_GRANADA: ["renfe"],
        BCN: ["iryo", "ouigo", "renfe"],
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
    assert split[f"{LAV}:madrid-puerta-de-atocha:bif-los-gavilanes"] == {
        "renfe": 70,
        "ouigo": 12,
    }
    # en Los Gavilanes se incorporan los 8 AVE de Barcelona que no paran en Madrid, y en Yeles,
    # los 2 de Valencia
    assert split[f"{LAV}:bif-los-gavilanes:bif-torrejon-de-velasco"] == {"renfe": 78, "ouigo": 12}
    assert split[f"{LAV}:bif-yeles:bif-la-sagra"] == {"renfe": 80, "ouigo": 12}
    assert split[f"{LAV}:ciudad-real:puertollano"] == {"renfe": 102, "ouigo": 12}
    # entre Córdoba y la bifurcación de Málaga pasan además los Avant de Sevilla a Málaga y a
    # Granada, que van y vuelven por el tramo y cuentan una vez
    assert split[f"{LAV}:cordoba:bif-malaga"] == {"renfe": 124, "ouigo": 12}
    assert split[f"{LAV}:bif-malaga:majarabique"] == {"renfe": 77, "ouigo": 6}
    assert split[f"{LAV}:majarabique:sevilla-santa-justa"] == {"renfe": 75, "ouigo": 6}
    lav = [by for s, by in split.items() if s.startswith(f"{LAV}:")]
    assert len(lav) == 13 and all(set(by) == {"renfe", "ouigo"} for by in lav)
    # los 6 Ouigo de Málaga siguen por la línea de Córdoba a Málaga; a Granada solo va Renfe
    malaga = [by for s, by in split.items() if s.startswith(f"{LAV_MALAGA}:")]
    assert len(malaga) == 4 and all(by == {"renfe": 67, "ouigo": 6} for by in malaga)
    assert split[f"{LAV_GRANADA}:antequera-santa-ana:bif-bobadilla"] == {"renfe": 18}
    assert split[f"{LAV_GRANADA}:loja:bif-tocon"] == {"renfe": 24}
    with_ouigo = (f"{LAV}:", f"{LAV_MALAGA}:", f"{BCN}:")
    # en la alta velocidad de Barcelona, 11 de Ouigo en cada tramo. De Madrid salen 63 de Renfe;
    # por Vallecas entran los de Andalucía que no pasan por Atocha; en Plasencia de Jalón salen
    # los de Pamplona y Logroño, y de Camp de Tarragona a Barcelona se suman los Euromed y los
    # demás trenes del Corredor Mediterráneo
    bcn = {s.removeprefix(f"{BCN}:"): by for s, by in split.items() if s.startswith(f"{BCN}:")}
    assert len(bcn) == 20 and all(by["ouigo"] == 11 for by in bcn.values())
    assert bcn["madrid-puerta-de-atocha:bif-vallecas-av"]["renfe"] == 63
    assert bcn["bif-vallecas-av:guadalajara-yebes"]["renfe"] == 71
    assert bcn["calatayud:cambiador-plasencia-de-jalon"]["renfe"] == 79
    assert bcn["cambiador-plasencia-de-jalon:bif-moncasi"]["renfe"] == 67
    assert bcn["zaragoza-delicias:bif-huesca"]["renfe"] == 66
    assert bcn["bif-huesca:bif-canal-imperial"]["renfe"] == 62
    assert bcn["l-espluga-de-francoli:camp-de-tarragona"]["renfe"] == 78
    assert bcn["vilafranca-del-penedes:barcelona-sants"]["renfe"] == 97
    assert all(set(by) == {"renfe"} for s, by in split.items() if not s.startswith(with_ouigo))
    # las listas de trenes del tramo y de la estación llevan el operador de cada servicio
    r = await client.get(
        f"/api/segments/{LAV}:ciudad-real:puertollano/services", params={"date": "2026-11-13"}
    )
    passes = r.json()["passes"]
    ouigo = [p for p in passes if p["service"]["operator_id"] == "ouigo"]
    assert len(passes) == 114 and len(ouigo) == 12
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
    assert (dest[0]["node_id"], dest[0]["name"], dest[0]["trains"]) == ("cordoba", "Córdoba", 25)
    # cuatro de ellos, los AVE de Barcelona a Sevilla, a Málaga y a Granada, que no pasan por
    # Madrid
    assert dest[0]["products"] == ["Intercity", "AVE", "AVLO", "ALVIA"]
    assert dest[0]["operators"] == [{"operator_id": "renfe", "trains": 25}]
    assert (dest[0]["first_departure"], dest[0]["last_departure"]) == ("07:55", "22:01")
    # Por Ciudad Real pasan 23 trenes hacia Madrid, pero 11 solo dejan viajeros allí (los
    # Intercity y un Alvia que vienen de Andalucía): a Madrid se puede ir en 12
    assert by_node["madrid-puerta-de-atocha"]["trains"] == 12
    assert by_node["alcazar-de-san-juan"]["products"] == ["MD"]
    # fuera de la red cargada, el destino lleva el nombre de la parada del fichero
    outside = {d["name"]: d["trains"] for d in dest if d["node_id"] is None}
    assert outside["Málaga María Zambrano"] == 9 and outside["Badajoz"] == 1
    # 4 de los destinos que antes quedaban fuera de la red son ahora estaciones cargadas: Puente
    # Genil-Herrera, Antequera-Santa Ana, Antequera AV y Granada
    # y otros 4 por los AVE de Barcelona a Sevilla, que paran en Ciudad Real: Zaragoza-Delicias,
    # Lleida-Pirineus, Camp de Tarragona y Barcelona-Sants
    assert len(dest) == 57 and len(by_node) == 19 + 4 + 4
    assert {"zaragoza-delicias", "barcelona-sants"} <= set(by_node)
    assert {"antequera-santa-ana", "granada"} <= set(by_node)


async def test_direct_destinations_carry_each_operator(client: httpx.AsyncClient) -> None:
    body = (
        await client.get(
            "/api/nodes/madrid-puerta-de-atocha/services", params={"date": "2026-11-13"}
        )
    ).json()
    cordoba = body["destinations"][0]
    assert (cordoba["node_id"], cordoba["trains"]) == ("cordoba", 53)
    assert cordoba["operators"] == [
        {"operator_id": "renfe", "trains": 47},
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
    # la vuelta por Granada y Córdoba (689,5 km) da un rodeo de más del doble respecto al de Córdoba
    assert res["omitted_alternatives"] == 1
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
    lines = [a["line_ids"] for a in res["alternatives"]]
    assert lines == [[MZCR, CONV], [CONV]]
    assert [a["length_km"] for a in res["alternatives"]] == [309.0, 440.7]
    # los dos que bajan por Moreda y Granada hasta la bifurcación de Málaga (566,6 y 698,3 km)
    # se apartan de los anteriores en Linares-Baeza y recorren más del doble: no se listan
    assert res["omitted_alternatives"] == 2
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
    # la vuelta por Granada hasta la bifurcación de Málaga (698,3 km) no se lista
    assert r.json()["omitted_alternatives"] == 1
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
    assert r.json()["omitted_alternatives"] == 1
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
    assert body["routes"][0]["time_min"] == 39
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


async def test_history_gives_one_point_per_dataset_on_its_own_reference_day(
    client: httpx.AsyncClient,
) -> None:
    """Con un fichero por operador hay un punto por conjunto, cada uno con sus trenes."""
    segment_id = f"{LAV}:ciudad-real:puertollano"
    body = (await client.get(f"/api/segments/{segment_id}/history")).json()
    assert body["id"] == segment_id
    renfe, ouigo = body["points"]
    assert renfe == {
        "dataset_id": "renfe-gtfs-av-ld-md-2026-11-08",
        "source_id": "renfe-gtfs-av-ld-md",
        "operator_id": "renfe",
        "retrieved_on": "2026-11-08",
        "date": "2026-11-12",
        "trains": 102,
        "products": [
            {"product": "AVE", "trains": 60},
            {"product": "Intercity", "trains": 22},
            {"product": "ALVIA", "trains": 10},
            {"product": "AVLO", "trains": 10},
        ],
        # con un solo fichero de la fuente no hay anterior con el que comparar
        "change": None,
    }
    # el fichero de Ouigo empieza en junio: su día de referencia es otro, y se cuenta en él
    assert (ouigo["dataset_id"], ouigo["operator_id"]) == (OUIGO_DATASET_ID, "ouigo")
    assert (ouigo["retrieved_on"], ouigo["date"]) == ("2026-11-12", "2026-07-16")
    assert ouigo["trains"] == 13 and ouigo["products"] == [{"product": "Ouigo", "trains": 13}]
    assert ouigo["change"] is None
    # cada punto cuenta los mismos trenes que la ficha del tramo ese día
    for point in body["points"]:
        services = (
            await client.get(f"/api/segments/{segment_id}/services", params={"date": point["date"]})
        ).json()
        mine = [
            p for p in services["passes"] if p["service"]["operator_id"] == point["operator_id"]
        ]
        assert len(mine) == point["trains"]

    node = (await client.get("/api/nodes/ciudad-real/history")).json()
    assert node["id"] == "ciudad-real"
    assert [(p["operator_id"], p["date"], p["trains"]) for p in node["points"]] == [
        ("renfe", "2026-11-12", 62),
        ("ouigo", "2026-07-16", 0),  # Ouigo no para en Ciudad Real: cero, que también es un dato
    ]
    assert node["points"][0]["products"][:2] == [
        {"product": "Intercity", "trains": 20},
        {"product": "AVE", "trains": 18},
    ]
    assert node["points"][1]["products"] == []
    # y los mismos que «Trenes que paran aquí»
    calls = (await client.get("/api/nodes/ciudad-real/services")).json()["calls"]
    assert len(calls) == 62
    madrid = (await client.get("/api/nodes/madrid-puerta-de-atocha/history")).json()["points"]
    calls = (await client.get("/api/nodes/madrid-puerta-de-atocha/services")).json()["calls"]
    assert madrid[0]["trains"] == sum(c["operator_id"] == "renfe" for c in calls)
    # un apeadero sin trenes tiene sus puntos, a cero
    urda = (await client.get("/api/nodes/urda/history")).json()["points"]
    assert [p["trains"] for p in urda] == [0, 0]

    assert (await client.get("/api/nodes/no-existe/history")).status_code == 404
    assert (await client.get("/api/segments/no-existe/history")).status_code == 404


async def test_snapshot_history_matches_the_api(
    client: httpx.AsyncClient, dsn: str, tmp_path: Path
) -> None:
    """`historico/` lleva, por nodo y por tramo, lo mismo que responde `/history`."""
    from oniel.db.pool import connect
    from oniel.export.snapshot import export_snapshot, safe_name

    async with connect(dsn) as conn:
        await export_snapshot(conn, tmp_path)
    network = (await client.get("/api/network")).json()
    node_ids = {n["id"] for n in network["nodes"]}
    segment_ids = {s["id"] for s in network["segments"]}
    assert {p.stem for p in (tmp_path / "historico" / "nodes").iterdir()} == node_ids
    assert {p.stem for p in (tmp_path / "historico" / "segments").iterdir()} == {
        safe_name(s) for s in segment_ids
    }
    for kind, entity_id in [
        ("nodes", "ciudad-real"),
        ("nodes", "cordoba"),
        ("segments", f"{LAV}:ciudad-real:puertollano"),
        ("segments", f"{CONV}:andujar:villa-del-rio"),
    ]:
        exported = json.loads(
            (tmp_path / "historico" / kind / f"{safe_name(entity_id)}.json").read_text("utf-8")
        )
        assert exported == (await client.get(f"/api/{kind}/{entity_id}/history")).json()
        assert exported["points"], entity_id
    # el recuento compacto por conjunto, que lee el resumen del refresco, sigue en su sitio
    counts = json.loads(
        (tmp_path / "historico" / OUIGO_DATASET_ID / "segment-counts.json").read_text("utf-8")
    )
    assert counts["date"] == "2026-07-16"


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


async def test_alternatives_count_the_trains_of_each_segment(client: httpx.AsyncClient) -> None:
    out = (await client.get("/api/alternatives")).json()
    counts = (await client.get("/api/segment-counts")).json()
    assert out["date"] == counts["date"] == "2026-11-12"
    assert out["line_ids"] == [
        LAV,
        CONV,
        MZCR,
        JAEN,
        LBMG,
        ALBACETE,
        LAV_MALAGA,
        LAV_GRANADA,
        BCN,
    ]
    assert out["missing_operator_ids"] == ["iryo"]
    assert "líneas que Oniel tiene cargadas" in out["scope_note"]
    by_id = {s["segment_id"]: s for s in out["segments"]}
    assert len(by_id) == 54 + 4 + 8 + 20 + 2
    assert {k: s["trains"] for k, s in by_id.items() if s["trains"]} == counts["counts"]
    # hacia Sevilla no hay otra línea cargada: ningún tren tiene otro camino
    south = by_id[f"{LAV}:bif-malaga:majarabique"]
    assert (south["trains"], south["without_alternative"]) == (84, 84)
    assert all(g["alternative"] is None for g in south["groups"])
    # entre Córdoba y la bifurcación de Málaga sí, desde que Granada está unida por los dos lados
    first = by_id[f"{LAV}:cordoba:bif-malaga"]
    assert (first["trains"], first["without_alternative"]) == (135, 0)
    # al norte, la línea convencional salva el tramo: 97 km más para los trenes de Madrid a Sevilla
    north = by_id[f"{LAV}:adamuz:cordoba"]
    assert (north["trains"], north["without_alternative"]) == (113, 0)
    top = north["groups"][0]
    assert (top["trains"], top["from_name"], top["to_name"]) == (
        44,
        "Madrid-Puerta de Atocha",
        "Sevilla-Santa Justa",
    )
    assert top["alternative"]["line_ids"] == [CONV, LAV]
    assert (top["alternative"]["extra_km"], top["alternative"]["extra_min"]) == (97.0, 106)
    # otro día, otros trenes
    sunday = (await client.get("/api/alternatives", params={"date": "2026-11-15"})).json()
    assert sunday["date"] == "2026-11-15"
    assert sunday["segments"] != out["segments"]


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
    # trenes por tramo y alternativa: el mismo resultado que da la API, en un fichero aparte
    async with connect(dsn) as conn:
        alternatives = await network_repo.fetch_segment_alternatives(conn)
    assert read("alternatives.json") == alternatives.model_dump(mode="json")
    # la red entera ya no se exporta en un solo fichero: el visor no lo descargaba
    assert not (tmp_path / "network.json").exists()
    assert not (tmp_path / "segment-counts.json").exists()
    assert result["lines"] == [
        LAV,
        CONV,
        MZCR,
        JAEN,
        LBMG,
        ALBACETE,
        LAV_MALAGA,
        LAV_GRANADA,
        BCN,
    ]
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
