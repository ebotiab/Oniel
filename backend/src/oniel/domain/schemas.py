"""Modelos públicos de la API (también los usa la exportación estática del visor)."""

from __future__ import annotations

import datetime as dt
from typing import Any, Literal

from pydantic import BaseModel, Field


class Source(BaseModel):
    id: str
    name: str
    publisher: str
    url: str | None = None
    license: str | None = None
    license_url: str | None = None
    retrieved_on: dt.date | None = None
    coverage: str | None = None
    notes: str | None = None


class Operator(BaseModel):
    id: str
    name: str
    role: Literal["operador", "administrador_infraestructura"]


class LineSummary(BaseModel):
    id: str
    name: str
    short_name: str | None = None
    sort_order: int = 1
    mode: str
    infrastructure_manager: Operator | None = None
    gauge_mm: int | None = None
    electrification: str | None = None
    max_speed_kmh: int | None = None
    opened_on: dt.date | None = None
    length_km: float
    reference_length_km: float | None = None
    status: Literal["disponible", "prevista"]
    description: str | None = None
    source_id: str | None = None
    node_count: int
    segment_count: int


class NodeOut(BaseModel):
    id: str
    name: str
    kind: Literal["estacion", "paet", "pb", "bifurcacion", "cambiador", "referencia"]
    rank: Literal["principal", "secundario"] = "principal"
    lon: float
    lat: float
    adif_code: str | None = None
    description: str | None = None
    details: dict[str, Any] = Field(default_factory=dict)
    line_id: str
    km: float
    reference_pk_km: float | None = None
    seq: int


class SegmentOut(BaseModel):
    id: str
    line_id: str
    seq: int
    from_node_id: str
    to_node_id: str
    from_name: str
    to_name: str
    km_from: float
    km_to: float
    length_km: float
    max_speed_kmh: int | None = None
    typical_speed_kmh: int | None = None
    tracks: int | None = None
    status: Literal["disponible", "prevista"]
    source_id: str | None = None


class ConnectionOut(BaseModel):
    id: str
    node_id: str
    name: str
    towards: str
    status: Literal["no_cargada", "disponible"]
    line_id: str | None = None


class SourceRef(BaseModel):
    """Lo justo de una fuente para citarla junto a un dato: quién lo publica y dónde."""

    id: str
    name: str
    publisher: str
    url: str | None = None


class InterruptionOut(BaseModel):
    """Interrupción del servicio entre dos nodos de una línea, con sus fechas y sus fuentes.

    Está vigente los días ``start_date <= día < ended_on`` (sin límite si ``ended_on`` es nulo).
    """

    id: str
    line_id: str
    from_node_id: str
    to_node_id: str
    from_name: str
    to_name: str
    km_from: float
    km_to: float
    segment_ids: list[str]
    start_date: dt.date
    expected_end_date: dt.date | None = None
    expected_end_text: str | None = None
    ended_on: dt.date | None = None
    reason: str
    note: str | None = None
    sources: list[SourceRef]
    checked_on: dt.date
    #: Nota para los pasos por tramo: «Horario publicado; sin circulación real desde el … (fuente)».
    schedule_note: str

    def active_on(self, day: dt.date) -> bool:
        return self.start_date <= day and (self.ended_on is None or day < self.ended_on)


class Feature(BaseModel):
    type: Literal["Feature"] = "Feature"
    id: str
    geometry: dict[str, Any]
    properties: dict[str, Any]


class FeatureCollection(BaseModel):
    type: Literal["FeatureCollection"] = "FeatureCollection"
    features: list[Feature]


class NetworkOut(BaseModel):
    """Todo lo que el visor necesita para dibujar la red disponible."""

    lines: list[LineSummary]
    nodes: list[NodeOut]
    segments: list[SegmentOut]
    connections: list[ConnectionOut]
    line_features: FeatureCollection
    segment_features: FeatureCollection
    node_features: FeatureCollection
    connection_features: FeatureCollection
    #: Todas las interrupciones registradas, vigentes o ya terminadas; el visor decide por fecha.
    interruptions: list[InterruptionOut] = Field(default_factory=list)


class CoverageOut(BaseModel):
    lines: list[LineSummary]
    total_length_km: float
    station_count: int
    service_count: int
    operators: list[Operator]
    feed_start: dt.date | None = None
    feed_end: dt.date | None = None
    reference_date: dt.date | None = None
    sources: list[Source]
    notice: str


class ServiceOut(BaseModel):
    id: str
    operator_id: str
    train_number: str
    product: str
    origin_name: str | None = None
    destination_name: str | None = None
    resolution: Literal["completa", "parcial"]
    valid_from: dt.date
    valid_to: dt.date


class StopOut(BaseModel):
    seq: int
    stop_id: str
    stop_name: str
    arrival: str
    departure: str
    node_id: str | None = None


class ServiceDetail(ServiceOut):
    stops: list[StopOut]


class SegmentPassOut(BaseModel):
    service: ServiceOut
    kind: Literal["publicado", "estimado", "indeterminado"]
    enter: str | None = None
    exit: str | None = None
    enter_margin_min: float
    exit_margin_min: float
    km_increasing: bool | None = None
    direction_label: str
    basis: str


class SegmentServicesOut(BaseModel):
    segment: SegmentOut
    date: dt.date
    passes: list[SegmentPassOut]
    counts: dict[str, int]
    #: Interrupciones vigentes en el tramo ese día: los pasos son los del horario publicado.
    interruptions: list[InterruptionOut] = Field(default_factory=list)


class NodeServicesOut(BaseModel):
    node: NodeOut
    date: dt.date
    calls: list[dict[str, Any]]


class ClosureRequest(BaseModel):
    segment_id: str
    date: dt.date
    start: dt.time
    end: dt.time


class ClosureResultItem(BaseModel):
    service: ServiceOut
    status: Literal["afectado_publicado", "afectado_estimado", "indeterminado", "no_afectado"]
    kind: Literal["publicado", "estimado", "indeterminado"]
    enter: str | None = None
    exit: str | None = None
    direction_label: str
    explanation: str
    from_previous_day: bool = False


class ClosureAlternative(BaseModel):
    """Otra línea cargada que une dos nodos de la línea cerrada situados a ambos lados del tramo."""

    line_id: str
    line_name: str
    from_node_id: str
    from_name: str
    to_node_id: str
    to_name: str
    length_km: float
    closed_line_length_km: float
    via: list[str]
    single_track_km: float
    note: str
    #: Interrupciones vigentes ese día en algún tramo del recorrido alternativo.
    interruptions: list[InterruptionOut] = Field(default_factory=list)


class ClosureResult(BaseModel):
    request: ClosureRequest
    segment: SegmentOut
    window_label: str
    counts: dict[str, int]
    items: list[ClosureResultItem]
    alternatives: list[ClosureAlternative] = Field(default_factory=list)
    #: Interrupciones vigentes ese día en el tramo que se cierra: el cierre simulado se suma a una real.
    interruptions: list[InterruptionOut] = Field(default_factory=list)
    method: str
    caveats: list[str]
