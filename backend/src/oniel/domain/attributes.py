"""Atributos de tramo: lo que cambia a lo largo de una línea, declarado por secciones.

Un atributo (el número de vías hoy; la señalización, el bloqueo o la electrificación después) se
declara en la especificación de la línea de nodo a nodo (``attribute_sections``), se reparte a los
tramos con un único mecanismo (``oniel.network.build.distribute_attributes``), se guarda en la
tabla ``segment_attributes`` y sale en ``SegmentOut.attributes`` con su fuente y su fecha de
comprobación. Añadir un atributo es declarar sus secciones; aquí solo se anota lo que un atributo
exige además: que cubra toda la línea, de qué tipo es su valor o qué campo de la línea lo da
donde ninguna sección lo declara.
"""

from __future__ import annotations

import datetime as dt
from dataclasses import dataclass

#: Valor de un atributo: un número o un texto corto (una clave que el visor traduce).
AttributeScalar = int | float | str | bool


@dataclass(frozen=True)
class AttributeRule:
    """Lo que un atributo exige además de estar declarado por secciones."""

    #: Tipo del valor; las secciones con otro tipo no se admiten.
    value_type: type
    #: Todo tramo de la línea ha de tener valor: si falta en alguno, la línea no se construye.
    required: bool = False
    #: Campo de ``LineSpec`` con el valor de la línea entera, que vale donde no hay sección.
    line_field: str | None = None


TRACKS = "tracks"

#: Atributos con alguna exigencia. Los demás son opcionales, sin valor por línea y de tipo libre.
ATTRIBUTE_RULES: dict[str, AttributeRule] = {
    # El número de vías lo usan el mapa, el esquema y el cálculo de recorridos: no puede faltar.
    TRACKS: AttributeRule(value_type=int, required=True, line_field="tracks"),
}


@dataclass(frozen=True)
class AttributeValue:
    """El valor de un atributo en un tramo, con la fuente que lo da y cuándo se comprobó."""

    value: AttributeScalar
    source_id: str | None = None
    checked_on: dt.date | None = None


def value_matches(value: AttributeScalar, expected: type) -> bool:
    """Si ``value`` es del tipo esperado; un booleano no vale como número."""
    if isinstance(value, bool):
        return expected is bool
    if expected is float:
        return isinstance(value, int | float)
    return isinstance(value, expected)
