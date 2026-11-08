"""Selección de viajes del GTFS para la línea convencional: entran los que la recorren y no otros."""

from __future__ import annotations

from collections import Counter

import pytest
from conftest import DATA_DIR

from oniel.gtfs.importer import calls_for_trip, select_trips_for_spec
from oniel.gtfs.reader import GtfsFeed
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
    assert products["MD"] > 300 and products["ALVIA"] == 8 and products["PROXIMDAD"] > 50
    assert "AVE" not in products and "AVLO" not in products and "Intercity" not in products
    names = {
        _stop_names(feed, t.trip_id)[0] + " → " + _stop_names(feed, t.trip_id)[-1] for t in trips
    }
    assert "Jaén → Madrid-Chamartín-Clara Campoamor" in names
    assert "Barcelona-Sants → Córdoba-Julio Anguita" in names
    assert "Alcázar de San Juan → Ciudad Real" in names
    assert "Cádiz → Jaén" in names
    # los Intercity Madrid-Atocha Cercanías–Andalucía solo paran en Madrid, Ciudad Real y
    # Córdoba: no se puede fijar su recorrido y quedan fuera de esta línea
    assert "Madrid-Atocha Cercanías → Sevilla-Santa Justa" not in names


def test_every_selected_stop_is_mapped_and_every_trip_resolves(
    feed: GtfsFeed, conv_spec: NetworkSpec
) -> None:
    net = build_network(conv_spec, DATA_DIR)
    nodes = {n.spec.id: LineNode(n.spec.id, n.km, n.lon, n.lat) for n in net.nodes}
    segments = [LineSegment(s.id, s.km_from, s.km_to) for s in net.segments]
    for trip in select_trips_for_spec(feed, conv_spec):
        calls = calls_for_trip(trip, feed, conv_spec)
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
