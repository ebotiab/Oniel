from __future__ import annotations

import os
from pathlib import Path

import pytest

BACKEND = Path(__file__).resolve().parents[1]
DATA_DIR = BACKEND / "data"
SPEC = DATA_DIR / "curated" / "lav-madrid-sevilla.json"
SOURCES = DATA_DIR / "curated" / "sources.json"
FEED = DATA_DIR / "raw" / "renfe" / "google_transit_av_ld_md_2026-11-08.zip"


@pytest.fixture(scope="session")
def spec():
    from oniel.network.spec import load_network_spec

    return load_network_spec(SPEC)


@pytest.fixture(scope="session")
def built(spec):
    from oniel.network.build import build_network

    return build_network(spec, DATA_DIR)


@pytest.fixture(scope="session")
def feed():
    from oniel.gtfs.reader import read_feed

    return read_feed(FEED)


def database_url_for_tests() -> str | None:
    """Base de datos para las pruebas de integración: ONIEL_TEST_DATABASE_URL o ninguna."""
    return os.environ.get("ONIEL_TEST_DATABASE_URL")


requires_db = pytest.mark.skipif(
    database_url_for_tests() is None,
    reason="define ONIEL_TEST_DATABASE_URL para las pruebas con PostgreSQL",
)
