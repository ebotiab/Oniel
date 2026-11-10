"""Textos de las interrupciones del servicio: fechas en español y la nota de los horarios."""

from __future__ import annotations

import datetime as dt

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
