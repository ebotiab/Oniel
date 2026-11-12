"""Selección de viajes del GTFS para la línea convencional: entran los que la recorren y no otros."""

from __future__ import annotations

from collections import Counter

import pytest
from conftest import DATA_DIR

from oniel.gtfs.reader import GtfsFeed
from oniel.gtfs.trips import calls_for_trip, calls_on_line, route_for_trip, select_trips_for_spec
from oniel.network.build import build_network
from oniel.network.spec import NetworkSpec, load_network_spec
from oniel.repo.network_repo import coverage_notice
from oniel.sim.passes import LineNode, LineSegment, resolve_passes

CONV_SPEC = DATA_DIR / "curated" / "convencional-madrid-alcazar-cordoba.json"


@pytest.fixture(scope="module")
def conv_spec() -> NetworkSpec:
    return load_network_spec(CONV_SPEC)


def _stop_names(feed: GtfsFeed, trip_id: str) -> list[str]:
    trip = feed.trips[trip_id]
    return [feed.stops[s.stop_id].name for s in trip.stop_times]


def test_conventional_filter_selects_the_trains_that_use_the_line(
    feed: GtfsFeed, conv_spec: NetworkSpec
) -> None:
    trips = select_trips_for_spec(feed, conv_spec)
    products = Counter(t.product for t in trips)
    assert products["MD"] > 300 and products["PROXIMDAD"] > 50
    # 8 Alvia Barcelona–Córdoba por el filtro de corredor; 4 Alvia y 20 Intercity Madrid-Atocha
    # Cercanías–Andalucía por las reglas de recorrido (van por esta línea hasta Manzanares)
    assert products["ALVIA"] == 8 + 4 and products["Intercity"] == 20
    assert "AVE" not in products and "AVLO" not in products
    names = {
        _stop_names(feed, t.trip_id)[0] + " → " + _stop_names(feed, t.trip_id)[-1] for t in trips
    }
    assert "Jaén → Madrid-Chamartín-Clara Campoamor" in names
    assert "Barcelona-Sants → Córdoba-Julio Anguita" in names
    assert "Alcázar de San Juan → Ciudad Real" in names
    assert "Cádiz → Jaén" in names
    assert "Madrid-Atocha Cercanías → Sevilla-Santa Justa" in names


def test_every_selected_stop_is_mapped_and_every_trip_resolves(
    feed: GtfsFeed, conv_spec: NetworkSpec
) -> None:
    net = build_network(conv_spec, DATA_DIR)
    nodes = {n.spec.id: LineNode(n.spec.id, n.km, n.lon, n.lat) for n in net.nodes}
    segments = [LineSegment(s.id, s.km_from, s.km_to) for s in net.segments]
    for trip in select_trips_for_spec(feed, conv_spec):
        route = route_for_trip(conv_spec, trip)
        calls = calls_on_line(calls_for_trip(trip, feed, conv_spec, route=route), route)
        assert all(c.node_id or c.exit_node_ids for c in calls), trip.train_number
        passes, resolution = resolve_passes(calls, nodes, segments)
        assert resolution == "completa"
        assert passes, trip.train_number


def test_madrid_jaen_train_passes_through_despenaperros_as_estimated(
    feed: GtfsFeed, conv_spec: NetworkSpec
) -> None:
    net = build_network(conv_spec, DATA_DIR)
    nodes = {n.spec.id: LineNode(n.spec.id, n.km, n.lon, n.lat) for n in net.nodes}
    segments = [LineSegment(s.id, s.km_from, s.km_to) for s in net.segments]
    trips = [t for t in select_trips_for_spec(feed, conv_spec) if t.train_number == "18032"]
    assert trips
    trip = max(trips, key=lambda t: len(t.stop_times))
    passes, _ = resolve_passes(calls_for_trip(trip, feed, conv_spec), nodes, segments)
    by_segment = {p.segment_id.split(":", 1)[1]: p for p in passes}
    # para en Santa Cruz de Mudela y en Almuradiel: paso publicado
    assert by_segment["santa-cruz-de-mudela:almuradiel-viso-del-marques"].kind == "publicado"
    # entre Almuradiel y Linares-Baeza no para: pasos estimados por Venta de Cárdenas y Vadollano
    assert by_segment["venta-de-cardenas:vilches"].kind == "estimado"
    assert by_segment["vilches:vadollano"].kind == "estimado"
    # sale de la línea en Espelúy hacia Jaén: no recorre Espelúy–Andújar
    assert "espeluy:andujar" not in by_segment


def test_high_speed_filter_is_unchanged(feed: GtfsFeed, spec: NetworkSpec) -> None:
    trips = select_trips_for_spec(feed, spec)
    assert len(trips) == 335


def test_ouigo_trains_run_only_along_the_high_speed_line(
    ouigo_feed: GtfsFeed, spec: NetworkSpec, conv_spec: NetworkSpec
) -> None:
    """El fichero de Ouigo usa códigos UIC y rotula «TGV 6477»: al leerlo quedan los códigos de
    Adif y el número de tren, y sus viajes por Córdoba y Madrid-Puerta de Atocha entran en la LAV."""
    assert ouigo_feed.agency_name == "OUIGO Espana" and len(ouigo_feed.trips) == 69
    assert ouigo_feed.stops["60000"].name == "Madrid-Puerta de Atocha"
    assert not any(stop_id.startswith("0071") for stop_id in ouigo_feed.stops)
    trips = select_trips_for_spec(ouigo_feed, spec)
    # 8 Madrid–Sevilla, 13 Madrid–Málaga y 4 que enlazan Barcelona con Sevilla o Málaga por Madrid
    assert len(trips) == 25 and len({t.train_number for t in trips}) == 20
    assert all(t.train_number.isdigit() for t in trips)
    ends = Counter(
        " – ".join(
            sorted({_stop_names(ouigo_feed, t.trip_id)[0], _stop_names(ouigo_feed, t.trip_id)[-1]})
        )
        for t in trips
    )
    assert ends == {
        "Madrid-Puerta de Atocha – Sevilla-Santa Justa": 8,
        "Madrid-Puerta de Atocha – Malaga Maria Zambrano": 13,
        "Barcelona-Sants – Sevilla-Santa Justa": 2,
        "Barcelona-Sants – Malaga Maria Zambrano": 2,
    }
    # ninguno para en una estación de la línea convencional
    assert select_trips_for_spec(ouigo_feed, conv_spec) == []
    # y todas sus paradas tienen asignación en la LAV
    for trip in trips:
        assert ouigo_feed.stop_ids_of(trip) <= set(spec.stop_mappings)


def test_stop_names_and_train_numbers_are_normalised() -> None:
    from oniel.gtfs.reader import stop_name, train_number

    assert stop_name("MADRID-PUERTA DE ATOCHA") == "Madrid-Puerta de Atocha"
    assert stop_name("ELCHE AV/ELX AV") == "Elche Av/Elx Av"
    assert stop_name("Córdoba-Julio Anguita") == "Córdoba-Julio Anguita"
    assert train_number("TGV 6477", "TGV") == "6477"
    assert train_number("02070", "AVE") == "02070"
    assert train_number("6477", "") == "6477"


def test_coverage_notice_lists_the_loaded_lines() -> None:
    from oniel.domain.schemas import LineSummary

    def line(id_: str, name: str) -> LineSummary:
        return LineSummary(
            id=id_,
            name=name,
            mode="ferrocarril",
            length_km=1.0,
            status="disponible",
            node_count=0,
            segment_count=0,
        )

    one = coverage_notice([line("a", "Línea de alta velocidad Madrid – Sevilla")])
    assert one.startswith(
        "Esta versión de Oniel carga únicamente la línea de alta velocidad Madrid – Sevilla"
    )
    two = coverage_notice(
        [
            line("a", "Línea de alta velocidad Madrid – Sevilla"),
            line("b", "Línea convencional Madrid – Córdoba"),
        ]
    )
    assert (
        "carga la línea de alta velocidad Madrid – Sevilla y la línea convencional Madrid – Córdoba"
        in two
    )
