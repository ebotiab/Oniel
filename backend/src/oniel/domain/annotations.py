"""Anotaciones de red: los tipos que hay, con sus estados válidos, y los textos que generan.

Una anotación es algo que pasa sobre la red entre dos fechas según una fuente: una interrupción
del servicio hoy; una obra o un proyecto después. Todas comparten modelo
(``oniel.network.spec.AnnotationSpec``), fichero curado, tabla y endpoint. Lo que distingue a un
tipo se declara aquí, en ``ANNOTATION_KINDS``: añadir uno es añadir una entrada.
"""

from __future__ import annotations

import datetime as dt
from dataclasses import dataclass
from typing import Literal

#: Dónde cae una anotación: entre dos nodos de una línea, en un nodo o con geometría propia.
Scope = Literal["tramo", "nodo", "geometria"]


@dataclass(frozen=True)
class AnnotationKind:
    """Lo que un tipo de anotación exige a sus entradas."""

    id: str
    #: Cómo se nombra una entrada en los mensajes de validación, con artículo («la interrupción»).
    label: str
    #: Estados válidos, en el orden en que suelen sucederse.
    statuses: tuple[str, ...]
    #: Estados que dan la anotación por terminada: exigen ``ended_on``, y los demás lo excluyen.
    ended_statuses: frozenset[str]
    #: Alcances que admite.
    scopes: tuple[Scope, ...]
    #: Campos opcionales en el modelo que este tipo exige («start_date», «reason», «title»).
    required: tuple[str, ...] = ()
    #: Mientras está vigente no circulan trenes por sus tramos: los pasos llevan una nota y los
    #: recorridos que los cruzan se señalan como cortados.
    cuts_service: bool = False


INTERRUPTION = "interrupcion"
PROJECT = "proyecto"

ANNOTATION_KINDS: dict[str, AnnotationKind] = {
    kind.id: kind
    for kind in (
        AnnotationKind(
            id=INTERRUPTION,
            label="la interrupción",
            statuses=("vigente", "terminada"),
            ended_statuses=frozenset({"terminada"}),
            scopes=("tramo",),
            required=("start_date", "reason"),
            cuts_service=True,
        ),
        # Lo previsto, en obras o parado alrededor de la red: una línea o un enlace nuevos (con
        # geometría propia, un esbozo), o una actuación sobre un tramo o un nodo que ya existe.
        AnnotationKind(
            id=PROJECT,
            label="el proyecto",
            statuses=(
                "en_estudio",
                "en_proyecto",
                "licitado",
                "en_obras",
                "parado",
                "sin_ejecutar",
                "en_servicio",
            ),
            ended_statuses=frozenset({"en_servicio"}),
            scopes=("tramo", "nodo", "geometria"),
            required=("title", "reason"),
        ),
    )
}

MONTHS = (
    "enero",
    "febrero",
    "marzo",
    "abril",
    "mayo",
    "junio",
    "julio",
    "agosto",
    "septiembre",
    "octubre",
    "noviembre",
    "diciembre",
)


def spanish_date(day: dt.date) -> str:
    """«28 de octubre de 2026»."""
    return f"{day.day} de {MONTHS[day.month - 1]} de {day.year}"


def source_label(publisher: str) -> str:
    """Nombre breve de quien publica la fuente, para citarlo entre paréntesis.

    El registro de fuentes admite varios editores separados por punto y coma («Adif; Europa
    Press»): se cita el primero, que es quien da el dato.
    """
    return publisher.split(";")[0].strip()


def schedule_note(start: dt.date, ended_on: dt.date | None, publisher: str) -> str:
    """Nota de los pasos por un tramo interrumpido: el horario existe, los trenes no circulan."""
    span = f"desde el {spanish_date(start)}"
    if ended_on is not None:
        span += f" hasta la reanudación del {spanish_date(ended_on)}"
    return f"Horario publicado; sin circulación real {span} ({source_label(publisher)})."


def alternative_note(from_name: str, to_name: str, start: dt.date, publisher: str) -> str:
    """Frase que se añade a un recorrido alternativo que cruza un tramo interrumpido."""
    return (
        f" En esa fecha el recorrido no está disponible: no hay circulación entre {from_name} y"
        f" {to_name} desde el {spanish_date(start)} ({source_label(publisher)})."
    )
