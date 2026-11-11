"""Escenario: una lista de modificaciones sobre la red cargada.

Un escenario no guarda la red, solo lo que cambia respecto a ella: tramos que se cierran, enlaces
esbozados entre dos nodos y velocidades distintas en un tramo. Se serializa como JSON (el modelo)
y como una cadena corta para la URL (``#/escenario/<cadena>`` en el visor, ``scenario=`` en la
API). La cadena une las modificaciones con ``;`` y los campos de cada una con ``~``:

* ``c~<tramo>``: cerrar un tramo.
* ``e~<nodo>~<nodo>~<km>~<km/h>``: enlace esbozado entre dos nodos, con longitud y velocidad.
* ``v~<tramo>~<km/h>``: cambiar la velocidad de un tramo.

``frontend/src/routing/scenario.ts`` implementa el mismo formato.
"""

from __future__ import annotations

import re
from collections.abc import Iterable

from pydantic import BaseModel, Field

#: Ids de nodo y de tramo: minúsculas, cifras, guiones y, en los tramos, dos puntos.
_ID = re.compile(r"^[a-z0-9][a-z0-9:-]*$")
#: Números de la cadena corta: cifras con punto decimal opcional.
_NUMBER = re.compile(r"^[0-9]+(\.[0-9]+)?$")


class ScenarioError(ValueError):
    """El escenario no se puede leer o no encaja con la red (tramo o nodo desconocido)."""


class SketchLink(BaseModel):
    """Enlace esbozado: une dos nodos con una longitud y una velocidad supuestas."""

    from_node_id: str
    to_node_id: str
    length_km: float = Field(gt=0)
    speed_kmh: float = Field(gt=0)

    @property
    def id(self) -> str:
        return f"enlace:{self.from_node_id}:{self.to_node_id}"


class SpeedChange(BaseModel):
    """Velocidad habitual distinta en un tramo."""

    segment_id: str
    speed_kmh: float = Field(gt=0)


class Scenario(BaseModel):
    """Modificaciones sobre la red, en el orden en que se aplican."""

    closures: list[str] = Field(default_factory=list)
    links: list[SketchLink] = Field(default_factory=list)
    speeds: list[SpeedChange] = Field(default_factory=list)

    @property
    def is_empty(self) -> bool:
        return not (self.closures or self.links or self.speeds)

    def with_closures(self, segment_ids: Iterable[str]) -> Scenario:
        """El mismo escenario con más tramos cerrados (por ejemplo, los interrumpidos un día)."""
        extra = [s for s in dict.fromkeys(segment_ids) if s not in self.closures]
        return self.model_copy(update={"closures": [*self.closures, *extra]})

    def to_code(self) -> str:
        """Cadena corta para la URL."""
        parts = [f"c~{s}" for s in self.closures]
        parts += [
            f"e~{k.from_node_id}~{k.to_node_id}~{_num(k.length_km)}~{_num(k.speed_kmh)}"
            for k in self.links
        ]
        parts += [f"v~{v.segment_id}~{_num(v.speed_kmh)}" for v in self.speeds]
        return ";".join(parts)

    @classmethod
    def from_code(cls, code: str) -> Scenario:
        """Lee la cadena corta. Una cadena vacía es el escenario sin modificaciones."""
        scenario = cls()
        for part in filter(None, (p.strip() for p in code.split(";"))):
            kind, *args = part.split("~")
            if kind == "c" and len(args) == 1:
                scenario.closures.append(_identifier(args[0]))
            elif kind == "e" and len(args) == 4:
                scenario.links.append(
                    SketchLink(
                        from_node_id=_identifier(args[0]),
                        to_node_id=_identifier(args[1]),
                        length_km=_positive(args[2]),
                        speed_kmh=_positive(args[3]),
                    )
                )
            elif kind == "v" and len(args) == 2:
                scenario.speeds.append(
                    SpeedChange(segment_id=_identifier(args[0]), speed_kmh=_positive(args[1]))
                )
            else:
                raise ScenarioError(f"No se entiende la modificación «{part}» del escenario")
        return scenario


def _identifier(value: str) -> str:
    if not _ID.match(value):
        raise ScenarioError(f"«{value}» no es un identificador de tramo o de nodo")
    return value


def _positive(value: str) -> float:
    if not _NUMBER.match(value):
        raise ScenarioError(f"«{value}» no es un número")
    number = float(value)
    if number <= 0:
        raise ScenarioError(f"«{value}» tiene que ser un número mayor que cero")
    return number


def _num(value: float) -> str:
    """Número sin ceros de sobra: 160 y no 160.0; 42.5 tal cual."""
    return str(int(value)) if value == int(value) else repr(value)
