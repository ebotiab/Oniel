"""El fichero de Iryo: una compilación no oficial que usa los códigos de estación de Adif."""

from __future__ import annotations

from collections import Counter

import pytest
from conftest import DATA_DIR, SOURCES, SPECS

from oniel.gtfs.reader import GtfsFeed, read_feed, rename_stops
from oniel.gtfs.trips import select_trips_for_spec
from oniel.network.spec import FeedSpec, load_feeds, load_network_spec


@pytest.fixture(scope="module")
def declared() -> FeedSpec:
    return next(f for f in load_feeds(SOURCES) if f.operator_id == "iryo")


@pytest.fixture(scope="module")
def iryo_feed(declared: FeedSpec) -> GtfsFeed:
    return read_feed(
        DATA_DIR / declared.file,
        stop_id_prefix=declared.stop_id_prefix,
        stop_id_aliases=declared.stop_id_aliases,
    )


def test_the_feed_is_read_with_adif_codes(declared: FeedSpec, iryo_feed: GtfsFeed) -> None:
    """Trae 135 viajes; Puertollano viene como 37700 y se lee con el código de Adif, 37300."""
    assert iryo_feed.agency_name == "iryo" and len(iryo_feed.trips) == 135
    assert (iryo_feed.feed_start.isoformat(), iryo_feed.feed_end.isoformat()) == (
        "2026-11-05",
        "2027-12-11",
    )
    assert declared.stop_id_aliases == {"37700": "37300"}
    assert "37700" not in iryo_feed.stops and iryo_feed.stops["37300"].name == "Puertollano"
    # sin el alias el código del fichero no es el de ninguna estación asignada
    plain = read_feed(DATA_DIR / declared.file)
    assert "37700" in plain.stops and "37300" not in plain.stops
    # sus nombres no son los de Adif: por eso no renombra las paradas (`names_stops`)
    assert iryo_feed.stops["60000"].name == "Madrid Atocha"
    assert declared.names_stops is False
    # no rotula los trenes (el nombre de la ruta hace de producto): Oniel los muestra como Iryo
    assert declared.product == "Iryo"
    assert all(t.train_number.isdigit() for t in iryo_feed.trips.values())


def test_iryo_trains_run_only_along_the_lines_that_declare_it(iryo_feed: GtfsFeed) -> None:
    """Sus viajes entran en las cinco líneas que declaran a Iryo, con todas sus paradas asignadas,
    y en ninguna otra."""
    trips_by_line: dict[str, int] = {}
    for path in SPECS:
        spec = load_network_spec(path)
        if spec.line.bypass_of is not None:
            continue  # los trenes de un baipás salen al resolver su línea
        trips = select_trips_for_spec(iryo_feed, spec)
        declares = any(o.id == "iryo" for o in spec.operators)
        assert bool(trips) == declares, spec.line.id
        if trips:
            trips_by_line[spec.line.id] = len(trips)
            unmapped = Counter(
                s for t in trips for s in iryo_feed.stop_ids_of(t) if s not in spec.stop_mappings
            )
            assert not unmapped, (spec.line.id, unmapped)
    assert trips_by_line == {
        "lav-madrid-sevilla": 64,
        "lav-cordoba-malaga": 29,
        "lav-madrid-barcelona": 64,
        "lav-madrid-valencia": 24,
        "lav-albacete-alicante": 6,
    }


def test_its_stops_take_the_names_oniel_already_has(declared: FeedSpec) -> None:
    """Al importarlo, sus paradas se llaman como en los ficheros oficiales: una estación no tiene
    dos nombres según de quién sea el tren."""
    feed = read_feed(DATA_DIR / declared.file, stop_id_aliases=declared.stop_id_aliases)
    assert feed.stops["60000"].name == "Madrid Atocha"
    rename_stops(feed, {"60000": "Madrid-Puerta de Atocha", "99999": "Otra"})
    assert feed.stops["60000"].name == "Madrid-Puerta de Atocha"
    # las demás quedan como estaban y no se añade ninguna
    assert feed.stops["71801"].name == "Barcelona Sants" and "99999" not in feed.stops
