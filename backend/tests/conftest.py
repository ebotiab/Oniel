from __future__ import annotations

import os
from pathlib import Path

import pytest

from oniel.gtfs.reader import GtfsFeed, read_feed
from oniel.network.build import BuiltNetwork, build_network
from oniel.network.spec import NetworkSpec, load_network_spec

BACKEND = Path(__file__).resolve().parents[1]
DATA_DIR = BACKEND / "data"
SPEC = DATA_DIR / "curated" / "lav-madrid-sevilla.json"
CONV_SPEC = DATA_DIR / "curated" / "convencional-madrid-alcazar-cordoba.json"
MZCR_SPEC = DATA_DIR / "curated" / "manzanares-ciudad-real.json"
JAEN_SPEC = DATA_DIR / "curated" / "espeluy-jaen.json"
LBMG_SPEC = DATA_DIR / "curated" / "linares-baeza-moreda-granada.json"
ALBACETE_SPEC = DATA_DIR / "curated" / "alcazar-albacete.json"
LAV_MALAGA_SPEC = DATA_DIR / "curated" / "lav-cordoba-malaga.json"
LAV_GRANADA_SPEC = DATA_DIR / "curated" / "lav-antequera-granada.json"
BCN_SPEC = DATA_DIR / "curated" / "lav-madrid-barcelona.json"
LAV_VALENCIA_SPEC = DATA_DIR / "curated" / "lav-madrid-valencia.json"
#: Los dos baipases de la alta velocidad de Barcelona: líneas cortas que cuelgan de ella.
BYPASS_ZARAGOZA_SPEC = DATA_DIR / "curated" / "baipas-zaragoza.json"
BYPASS_LLEIDA_SPEC = DATA_DIR / "curated" / "baipas-lleida.json"
LAV_ALICANTE_SPEC = DATA_DIR / "curated" / "lav-albacete-alicante.json"
LAV_MURCIA_SPEC = DATA_DIR / "curated" / "lav-monforte-murcia.json"
MEDITERRANEO_SPEC = DATA_DIR / "curated" / "valencia-castello-tarragona.json"
LINK_MONFORTE_SPEC = DATA_DIR / "curated" / "enlace-monforte-del-cid.json"
#: Las líneas cargadas, en el orden de importación.
SPECS = [
    SPEC,
    CONV_SPEC,
    MZCR_SPEC,
    JAEN_SPEC,
    LBMG_SPEC,
    ALBACETE_SPEC,
    LAV_MALAGA_SPEC,
    LAV_GRANADA_SPEC,
    BCN_SPEC,
    LAV_VALENCIA_SPEC,
    BYPASS_ZARAGOZA_SPEC,
    BYPASS_LLEIDA_SPEC,
    LAV_ALICANTE_SPEC,
    LAV_MURCIA_SPEC,
    MEDITERRANEO_SPEC,
    LINK_MONFORTE_SPEC,
]
SOURCES = DATA_DIR / "curated" / "sources.json"
#: Fichero de horarios fijo de las pruebas: el del 8 de noviembre de 2026, por su nombre. Los
#: recuentos que se comprueban son los suyos y no cambian aunque `sources.json` declare otros
#: ficheros más recientes para producción.
FEED = DATA_DIR / "raw" / "renfe" / "google_transit_av_ld_md_2026-11-08.zip"
FEED_SOURCE_ID = "renfe-gtfs-av-ld-md"
FEED_OPERATOR_ID = "renfe"
FEED_DATASET_ID = "renfe-gtfs-av-ld-md-2026-11-08"
#: Fichero de Ouigo España, descargado del Punto de Acceso Nacional el 12 de noviembre de 2026.
#: También es fijo y por su nombre. Sus paradas llevan el código UIC («0071» y el de Adif).
OUIGO_FEED = DATA_DIR / "raw" / "ouigo" / "gtfs_ouigo_2026-11-12.zip"
OUIGO_SOURCE_ID = "ouigo-gtfs-nap"
OUIGO_OPERATOR_ID = "ouigo"
OUIGO_DATASET_ID = "ouigo-gtfs-nap-2026-11-12"
OUIGO_STOP_ID_PREFIX = "0071"
OUIGO_PRODUCT = "Ouigo"


@pytest.fixture(scope="session")
def spec() -> NetworkSpec:
    return load_network_spec(SPEC)


@pytest.fixture(scope="session")
def built(spec: NetworkSpec) -> BuiltNetwork:
    return build_network(spec, DATA_DIR)


@pytest.fixture(scope="session")
def feed() -> GtfsFeed:
    return read_feed(FEED)


@pytest.fixture(scope="session")
def ouigo_feed() -> GtfsFeed:
    return read_feed(OUIGO_FEED, stop_id_prefix=OUIGO_STOP_ID_PREFIX)


def database_url_for_tests() -> str | None:
    """Base de datos para las pruebas de integración: ONIEL_TEST_DATABASE_URL o ninguna."""
    return os.environ.get("ONIEL_TEST_DATABASE_URL")


requires_db = pytest.mark.skipif(
    database_url_for_tests() is None,
    reason="define ONIEL_TEST_DATABASE_URL para las pruebas con PostgreSQL",
)
