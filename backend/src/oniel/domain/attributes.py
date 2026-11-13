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
    #: Los valores que admite, si es una lista cerrada de claves que el visor traduce.
    values: frozenset[str] | None = None
    #: Cada sección ha de citar su fuente y el día en que se comprobó.
    sourced: bool = False


TRACKS = "tracks"
PROTECCION_TREN = "proteccion_tren"
BLOQUEO = "bloqueo"
MANDO = "mando"
MAX_SPEED = "max_speed_kmh"

#: La fuente consultada no da el dato para ese tramo. Es un valor declarado, con su fuente y su
#: fecha como cualquier otro: dice que se miró y no estaba, que no es lo mismo que no haber mirado.
SIN_DATO_PUBLICADO = "sin_dato_publicado"

#: Atributos con alguna exigencia. Los demás son opcionales, sin valor por línea y de tipo libre.
ATTRIBUTE_RULES: dict[str, AttributeRule] = {
    # El número de vías lo usan el mapa, el esquema y el cálculo de recorridos: no puede faltar.
    TRACKS: AttributeRule(value_type=int, required=True, line_field="tracks"),
    # Señalización, según el mapa 4 de la Declaración sobre la Red (docs/datos.md, «Señalización
    # y protección del tren»). Los tres cubren toda línea cargada y cada sección cita su fuente.
    # Sistema de protección del tren: ASFA, LZB con ASFA de respaldo o ERTMS, solo o con ASFA.
    PROTECCION_TREN: AttributeRule(
        value_type=str,
        required=True,
        sourced=True,
        values=frozenset(
            {
                "asfa",
                "lzb_asfa",
                "ertms_n1",
                # ERTMS de nivel 1 con ASFA de respaldo: la alta velocidad de Barcelona y la de Valencia
                "ertms_n1_asfa",
                "ertms_n2",
                # ERTMS con ASFA de respaldo, como lo dibuja el mapa en las líneas de Málaga y Granada
                "ertms_n1_n2_asfa",
                "ertms_n2_asfa",
                SIN_DATO_PUBLICADO,
            }
        ),
    ),
    # Bloqueo: de control automático (BCA), automático banalizado (BAB), de vía doble (BAD) o
    # de vía única (BAU), o de liberación automática en vía única (BLAU). ``bab_bad`` y ``bca_bsl``
    # son tramos que cambian de uno a otro donde no hay nodo; el segundo acaba en el bloqueo de
    # señalización lateral (BSL) de la entrada de la alta velocidad a Valencia.
    BLOQUEO: AttributeRule(
        value_type=str,
        required=True,
        sourced=True,
        values=frozenset(
            {"bca", "bab", "bad", "bau", "blau", "bab_bad", "bca_bsl", SIN_DATO_PUBLICADO}
        ),
    ),
    # Velocidad máxima del tramo cuando la geometría no la trae o la trae mal (las entradas a
    # Zaragoza-Delicias y a Lleida-Pirineus): la sección manda sobre lo que diga la geometría.
    # Es opcional; donde no se declara vale la velocidad de las vías de la fuente de geometría.
    MAX_SPEED: AttributeRule(value_type=int, sourced=True),
    # Mando: desde dónde se gobiernan las señales y los desvíos del tramo. ``sin_ctc`` es un
    # tramo cuyo bloqueo el mapa rotula sin «ctc», cuando la leyenda distingue los dos casos:
    # la fuente dice que no hay control de tráfico centralizado, que no es lo mismo que callar.
    MANDO: AttributeRule(
        value_type=str,
        required=True,
        sourced=True,
        values=frozenset({"ctc", "sin_ctc", SIN_DATO_PUBLICADO}),
    ),
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
