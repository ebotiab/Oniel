"""Destinos directos de un nodo: cómo se agrupan las paradas posteriores de cada tren."""

from __future__ import annotations

from oniel.repo.services_repo import DirectStop, group_destinations


def _stop(
    service: str,
    dest: str,
    departure_s: float,
    *,
    node: bool = True,
    product: str = "MD",
    operator: str = "renfe",
    stop_id: str | None = None,
) -> DirectStop:
    return DirectStop(
        service_id=service,
        operator_id=operator,
        product=product,
        departure_s=departure_s,
        node_id=dest if node else None,
        stop_id=stop_id or f"stop-{dest}",
        name=dest.title(),
    )


def test_destinations_are_ordered_by_frequency_then_by_name() -> None:
    out = group_destinations(
        [
            _stop("t1", "zafra", 8 * 3600),
            _stop("t1", "merida", 8 * 3600),
            _stop("t2", "merida", 12 * 3600),
            _stop("t3", "almorchon", 9 * 3600),
        ]
    )
    assert [(d.name, d.trains) for d in out] == [("Merida", 2), ("Almorchon", 1), ("Zafra", 1)]


def test_a_destination_carries_products_operators_and_first_and_last_departure() -> None:
    out = group_destinations(
        [
            _stop("a", "cordoba", 21 * 3600 + 20 * 60, product="AVE"),
            _stop("b", "cordoba", 6 * 3600, product="AVE"),
            _stop("c", "cordoba", 10 * 3600 + 5 * 60, product="Ouigo", operator="ouigo"),
            _stop("d", "cordoba", 9 * 3600, product="ALVIA"),
        ]
    )
    (cordoba,) = out
    assert cordoba.node_id == "cordoba" and cordoba.trains == 4
    # del tipo de servicio y del operador con más trenes al que menos; a igualdad, por nombre
    assert cordoba.products == ["AVE", "ALVIA", "Ouigo"]
    assert [(o.operator_id, o.trains) for o in cordoba.operators] == [("renfe", 3), ("ouigo", 1)]
    assert (cordoba.first_departure, cordoba.last_departure) == ("06:00", "21:20")


def test_a_train_counts_once_per_destination_even_with_two_stops_in_the_same_node() -> None:
    # Madrid-Puerta de Atocha tiene dos paradas en el fichero (la de alta velocidad y Cercanías)
    out = group_destinations(
        [
            _stop("t1", "madrid", 7 * 3600, stop_id="60000"),
            _stop("t1", "madrid", 7 * 3600, stop_id="18000"),
        ]
    )
    assert [(d.node_id, d.stop_id, d.trains) for d in out] == [("madrid", "60000", 1)]


def test_a_destination_outside_the_network_is_named_by_its_stop() -> None:
    out = group_destinations(
        [
            _stop("t1", "badajoz", 15 * 3600, node=False, stop_id="37606"),
            _stop("t2", "badajoz", 25 * 3600, node=False, stop_id="37606"),
        ]
    )
    (badajoz,) = out
    assert (badajoz.node_id, badajoz.stop_id, badajoz.name) == (None, "37606", "Badajoz")
    # una salida pasada la medianoche del día de servicio se marca
    assert badajoz.last_departure == "01:00 (+1)"
