"""Especificaciones curadas (data/curated/*.json): líneas, fuentes e interrupciones."""

from __future__ import annotations

import datetime as dt
import json
from pathlib import Path
from typing import Any, Literal

from pydantic import BaseModel, ConfigDict, Field, field_validator, model_validator

NodeKind = Literal["estacion", "paet", "pb", "bifurcacion", "cambiador", "referencia"]
NodeRank = Literal["principal", "secundario"]


class Position(BaseModel):
    lon: float | None = None
    lat: float | None = None
    km: float | None = None

    @model_validator(mode="after")
    def _one_of(self) -> Position:
        has_coords = self.lon is not None and self.lat is not None
        if has_coords == (self.km is not None):
            raise ValueError("una posición lleva lon/lat o km, no ambas cosas ni ninguna")
        return self


class NodeSpec(BaseModel):
    id: str
    name: str
    kind: NodeKind
    adif_code: str | None = None
    #: «principal» se dibuja siempre; «secundario» se atenúa y se oculta en el esquema compacto.
    rank: NodeRank = "principal"
    #: El nodo lo define otra línea (por ejemplo una estación común): esta línea solo lo
    #: incorpora a su kilometraje y no sobrescribe su nombre, posición ni descripción.
    shared: bool = False
    position: Position
    reference_pk_km: float | None = None
    description: str | None = None
    details: dict[str, Any] = Field(default_factory=dict)

    @model_validator(mode="after")
    def _shared_needs_coords(self) -> NodeSpec:
        if self.shared and self.position.km is not None:
            raise ValueError(f"el nodo compartido {self.id} necesita lon/lat para situarlo")
        return self


class ConnectionSpec(BaseModel):
    id: str
    node_id: str
    name: str
    towards: str
    status: Literal["no_cargada", "disponible"] = "no_cargada"
    sketch: list[tuple[float, float]] = Field(default_factory=list)


class ViaLine(BaseModel):
    """Un trecho del camino hasta una parada que está en otra línea cargada: el tren entra en la
    línea ``line`` por el nodo ``node`` y sigue por ella hasta el nodo del trecho siguiente o,
    en el último, hasta la parada."""

    line: str
    node: str


class StopMapping(BaseModel):
    node: str | None = None
    exits: list[str] = Field(default_factory=list)
    #: Solo con ``exits``: la parada es un nodo de otra línea cargada y este es el camino hasta
    #: ella desde la salida, línea a línea. Lo normal es un solo trecho (se escribe como un
    #: objeto); un tren que cruza una tercera línea antes de llegar lleva una lista. Permite
    #: repartir el tiempo con la distancia por esas líneas en vez de la línea recta, y explicar
    #: en el visor por dónde sigue el tren.
    via: list[ViaLine] = Field(default_factory=list)

    @field_validator("via", mode="before")
    @classmethod
    def _one_or_many(cls, value: object) -> object:
        if value is None:
            return []
        return [value] if isinstance(value, dict | ViaLine) else value

    @model_validator(mode="after")
    def _one_of(self) -> StopMapping:
        if (self.node is None) == (not self.exits):
            raise ValueError("una parada se asigna a un nodo o a una lista de salidas")
        if self.via and self.node is not None:
            raise ValueError("«via» solo tiene sentido en una parada que es salida de la línea")
        lines = [v.line for v in self.via]
        if any(a == b for a, b in zip(lines, lines[1:], strict=False)):
            raise ValueError("«via» repite la misma línea en dos trechos seguidos")
        return self


class OperatorSpec(BaseModel):
    id: str
    name: str
    role: Literal["operador", "administrador_infraestructura"]
    source_id: str | None = None


class GeometryPart(BaseModel):
    """Trozo de línea tomado de una relación OSM: el camino más corto entre dos puntos."""

    model_config = ConfigDict(populate_by_name=True)

    source_id: str
    file: str
    relation_id: int
    from_point: tuple[float, float] = Field(alias="from")
    to_point: tuple[float, float] = Field(alias="to")


class GeometrySource(BaseModel):
    """O una relación OSM encadenada en el orden de sus miembros, o varias partes trazadas."""

    source_id: str
    file: str | None = None
    relation_id: int | None = None
    parts: list[GeometryPart] = Field(default_factory=list)

    @model_validator(mode="after")
    def _one_of(self) -> GeometrySource:
        single = self.file is not None and self.relation_id is not None
        if single == bool(self.parts):
            raise ValueError("geometry_source lleva file+relation_id o una lista de parts")
        return self


class TrackSection(BaseModel):
    """Número de vías entre dos nodos; lo que no se declara usa ``line.tracks``."""

    from_node: str
    to_node: str
    tracks: int
    note: str | None = None


class LineSpec(BaseModel):
    id: str
    name: str
    short_name: str | None = None
    sort_order: int = 1
    mode: str = "ferrocarril"
    infrastructure_manager: str
    gauge_mm: int | None = None
    electrification: str | None = None
    max_speed_kmh: int | None = None
    tracks: int = 2
    opened_on: str | None = None
    reference_length_km: float | None = None
    #: PK de referencia del origen de la línea, cuando su numeración no empieza en cero (la de
    #: Manzanares a Ciudad Real continúa la de Madrid: Manzanares es el PK 197,3).
    pk_origin_km: float = 0.0
    #: Diferencia admitida entre el PK de referencia y el kilómetro medido sobre la geometría.
    pk_tolerance_km: float = 1.5
    status: Literal["disponible", "prevista"] = "disponible"
    description: str | None = None
    geometry_source: GeometrySource
    verification_source_id: str | None = None


class CorridorFilter(BaseModel):
    description: str = ""
    required_stop_ids: list[str] = Field(default_factory=list)
    any_of_stop_ids: list[str] = Field(default_factory=list)
    #: Mínimo de paradas distintas del viaje que sean nodos de la línea.
    min_node_stops: int = 0
    exclude_stop_ids: list[str] = Field(default_factory=list)


class RouteOverride(BaseModel):
    """Viajes que recorren esta línea solo en parte de su recorrido y siguen por otra línea cargada,
    o que la cruzan sin parar en ella entre paradas de otras líneas.

    Un viaje encaja si su horario lleva ``consecutive_stop_ids`` seguidas, en ese orden o en el
    inverso. La regla se escribe en el sentido de esa secuencia: para un viaje en sentido
    contrario, ``from_stop_id`` y ``to_stop_id`` se intercambian. Los viajes que encajan entran
    en la línea aunque no pasen el filtro de corredor, y solo se resuelven con las paradas desde
    ``from_stop_id`` hasta ``to_stop_id`` (por defecto, desde el origen o hasta el destino). Si
    una de esas dos paradas no es un nodo de la línea, el tren sale o entra por la salida que le
    da su asignación. ``stop_mappings`` sustituye, solo para estos viajes, la asignación general
    de las paradas que indique.
    """

    id: str
    description: str
    consecutive_stop_ids: list[str] = Field(min_length=2)
    from_stop_id: str | None = None
    to_stop_id: str | None = None
    stop_mappings: dict[str, StopMapping] = Field(default_factory=dict)

    @model_validator(mode="after")
    def _consistent(self) -> RouteOverride:
        if len(set(self.consecutive_stop_ids)) != len(self.consecutive_stop_ids):
            raise ValueError(f"la regla {self.id} repite paradas en consecutive_stop_ids")
        for ref in (self.from_stop_id, self.to_stop_id):
            if ref is not None and ref not in self.consecutive_stop_ids:
                raise ValueError(
                    f"la regla {self.id}: la parada {ref} tiene que estar en consecutive_stop_ids"
                )
        if self.from_stop_id is not None and self.from_stop_id == self.to_stop_id:
            raise ValueError(f"la regla {self.id} empieza y termina en la misma parada")
        if self.from_stop_id is None and self.to_stop_id is None and not self.stop_mappings:
            raise ValueError(f"la regla {self.id} no cambia nada: ni tramo ni asignaciones")
        return self

    def mapping_for(self, stop_id: str, general: dict[str, StopMapping]) -> StopMapping | None:
        return self.stop_mappings.get(stop_id) or general.get(stop_id)


class NetworkSpec(BaseModel):
    line: LineSpec
    operators: list[OperatorSpec]
    nodes: list[NodeSpec]
    track_sections: list[TrackSection] = Field(default_factory=list)
    connections: list[ConnectionSpec] = Field(default_factory=list)
    stop_mappings: dict[str, StopMapping] = Field(default_factory=dict)
    corridor_filter: CorridorFilter = Field(default_factory=CorridorFilter)
    route_overrides: list[RouteOverride] = Field(default_factory=list)

    @model_validator(mode="after")
    def _consistent(self) -> NetworkSpec:
        ids = {n.id for n in self.nodes}
        if len(ids) != len(self.nodes):
            raise ValueError("ids de nodo repetidos")
        for c in self.connections:
            if c.node_id not in ids:
                raise ValueError(f"la conexión {c.id} apunta a un nodo desconocido {c.node_id}")
        self._check_mappings(self.stop_mappings, ids, "la parada")
        for t in self.track_sections:
            for ref in (t.from_node, t.to_node):
                if ref not in ids:
                    raise ValueError(f"el tramo de vías {t.from_node}–{t.to_node} apunta a {ref}")
        rule_ids = [r.id for r in self.route_overrides]
        if len(set(rule_ids)) != len(rule_ids):
            raise ValueError("ids de regla de recorrido repetidos en route_overrides")
        for r in self.route_overrides:
            self._check_mappings(r.stop_mappings, ids, f"la regla {r.id}: la parada")
            for boundary in (r.from_stop_id, r.to_stop_id):
                if boundary is not None and r.mapping_for(boundary, self.stop_mappings) is None:
                    raise ValueError(
                        f"la regla {r.id}: la parada {boundary} no tiene asignación en stop_mappings"
                    )
        return self

    def _check_mappings(self, mappings: dict[str, StopMapping], ids: set[str], what: str) -> None:
        for stop_id, m in mappings.items():
            for ref in [m.node, *m.exits]:
                if ref is not None and ref not in ids:
                    raise ValueError(f"{what} {stop_id} apunta a un nodo desconocido {ref}")
            if any(v.line == self.line.id for v in m.via):
                raise ValueError(f"{what} {stop_id}: «via» apunta a esta misma línea")

    @property
    def node_stop_ids(self) -> frozenset[str]:
        """Paradas GTFS que son nodos de la línea (no salidas hacia fuera)."""
        return frozenset(s for s, m in self.stop_mappings.items() if m.node is not None)


class SourceSpec(BaseModel):
    id: str
    name: str
    publisher: str
    url: str | None = None
    license: str | None = None
    license_url: str | None = None
    retrieved_on: str | None = None
    coverage: str | None = None
    notes: str | None = None
    file: str | None = None


class FeedSpec(BaseModel):
    """Un fichero de horarios que carga `import all` (clave ``feeds`` de sources.json).

    Cada fichero es un conjunto de datos: se guarda con su fuente, su operador y el día en que se
    descargó, y los anteriores siguen en la lista mientras se quiera conservar su histórico.
    """

    model_config = ConfigDict(extra="forbid")

    #: Ruta relativa a ``data/``, con la fecha de descarga en el nombre.
    file: str
    source_id: str
    operator_id: str
    retrieved_on: dt.date


class InterruptionSpec(BaseModel):
    """Interrupción del servicio en parte de una línea cargada (data/curated/interrupciones.json).

    Va de ``from_node`` a ``to_node``, dos nodos de la misma línea en el orden de su kilometraje, y
    afecta a todos los tramos que quedan entre ambos. Las fechas son días completos: no hay
    circulación desde ``start_date`` y, si ya terminó, vuelve a haberla desde ``ended_on``.
    """

    model_config = ConfigDict(extra="forbid")

    id: str
    line_id: str
    from_node: str
    to_node: str
    start_date: dt.date
    #: Previsión de fin publicada por la fuente, como fecha o como texto («otoño de 2027»).
    expected_end_date: dt.date | None = None
    expected_end_text: str | None = None
    #: Día en que se reanudó la circulación; sin él, la interrupción sigue vigente.
    ended_on: dt.date | None = None
    #: Motivo en una frase neutra.
    reason: str = Field(min_length=1)
    #: Precisión opcional: hasta dónde llegan los trenes, qué sigue en servicio.
    note: str | None = None
    #: Ids de ``sources.json``; la primera es la fuente principal, la que se cita junto a la fecha.
    source_ids: list[str] = Field(min_length=1)
    #: Día de la última comprobación en las fuentes.
    checked_on: dt.date

    @model_validator(mode="after")
    def _consistent(self) -> InterruptionSpec:
        if self.from_node == self.to_node:
            raise ValueError(f"la interrupción {self.id} empieza y termina en el mismo nodo")
        if len(set(self.source_ids)) != len(self.source_ids):
            raise ValueError(f"la interrupción {self.id} repite fuentes")
        if self.expected_end_date is not None and self.expected_end_date < self.start_date:
            raise ValueError(f"la interrupción {self.id} prevé terminar antes de empezar")
        if self.ended_on is not None:
            if self.ended_on < self.start_date:
                raise ValueError(f"la interrupción {self.id} termina antes de empezar")
            if self.ended_on > self.checked_on:
                raise ValueError(
                    f"la interrupción {self.id} termina después de la fecha de consulta"
                )
        return self

    def active_on(self, day: dt.date) -> bool:
        return self.start_date <= day and (self.ended_on is None or day < self.ended_on)


class InterruptionsFile(BaseModel):
    model_config = ConfigDict(extra="forbid")

    interruptions: list[InterruptionSpec]

    @model_validator(mode="after")
    def _unique_ids(self) -> InterruptionsFile:
        ids = [i.id for i in self.interruptions]
        if len(set(ids)) != len(ids):
            raise ValueError("ids de interrupción repetidos")
        return self


def load_network_spec(path: Path) -> NetworkSpec:
    return NetworkSpec.model_validate(json.loads(path.read_text(encoding="utf-8")))


def load_interruptions(path: Path) -> list[InterruptionSpec]:
    raw = json.loads(path.read_text(encoding="utf-8"))
    return InterruptionsFile.model_validate(raw).interruptions


def load_sources(path: Path) -> list[SourceSpec]:
    raw = json.loads(path.read_text(encoding="utf-8"))
    return [SourceSpec.model_validate(s) for s in raw["sources"]]


def load_feeds(path: Path) -> list[FeedSpec]:
    """Ficheros de horarios declarados en sources.json, del más antiguo al más reciente.

    Cada uno tiene que citar una fuente registrada y no puede repetirse.
    """
    raw = json.loads(path.read_text(encoding="utf-8"))
    feeds = [FeedSpec.model_validate(f) for f in raw.get("feeds", [])]
    known = {s["id"] for s in raw["sources"]}
    for feed in feeds:
        if feed.source_id not in known:
            raise ValueError(f"{feed.file} cita la fuente {feed.source_id}, que no está registrada")
    files = [f.file for f in feeds]
    if len(set(files)) != len(files):
        raise ValueError("ficheros de horarios repetidos en feeds")
    return sorted(feeds, key=lambda f: (f.retrieved_on, f.file))
