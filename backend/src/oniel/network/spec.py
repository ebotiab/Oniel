"""Especificación curada de una línea (data/curated/*.json)."""

from __future__ import annotations

import json
from pathlib import Path
from typing import Any, Literal

from pydantic import BaseModel, Field, model_validator

NodeKind = Literal["estacion", "paet", "pb", "bifurcacion", "cambiador", "referencia"]


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
    position: Position
    reference_pk_km: float | None = None
    description: str | None = None
    details: dict[str, Any] = Field(default_factory=dict)


class ConnectionSpec(BaseModel):
    id: str
    node_id: str
    name: str
    towards: str
    status: Literal["no_cargada", "disponible"] = "no_cargada"
    sketch: list[tuple[float, float]] = Field(default_factory=list)


class StopMapping(BaseModel):
    node: str | None = None
    exits: list[str] = Field(default_factory=list)

    @model_validator(mode="after")
    def _one_of(self) -> StopMapping:
        if (self.node is None) == (not self.exits):
            raise ValueError("una parada se asigna a un nodo o a una lista de salidas")
        return self


class OperatorSpec(BaseModel):
    id: str
    name: str
    role: Literal["operador", "administrador_infraestructura"]
    source_id: str | None = None


class GeometrySource(BaseModel):
    source_id: str
    file: str
    relation_id: int


class LineSpec(BaseModel):
    id: str
    name: str
    short_name: str | None = None
    mode: str = "ferrocarril"
    infrastructure_manager: str
    gauge_mm: int | None = None
    electrification: str | None = None
    max_speed_kmh: int | None = None
    opened_on: str | None = None
    reference_length_km: float | None = None
    status: Literal["disponible", "prevista"] = "disponible"
    description: str | None = None
    geometry_source: GeometrySource
    verification_source_id: str | None = None


class CorridorFilter(BaseModel):
    description: str = ""
    required_stop_ids: list[str] = Field(default_factory=list)
    any_of_stop_ids: list[str] = Field(default_factory=list)


class NetworkSpec(BaseModel):
    line: LineSpec
    operators: list[OperatorSpec]
    nodes: list[NodeSpec]
    connections: list[ConnectionSpec] = Field(default_factory=list)
    stop_mappings: dict[str, StopMapping] = Field(default_factory=dict)
    corridor_filter: CorridorFilter = Field(default_factory=CorridorFilter)

    @model_validator(mode="after")
    def _consistent(self) -> NetworkSpec:
        ids = {n.id for n in self.nodes}
        if len(ids) != len(self.nodes):
            raise ValueError("ids de nodo repetidos")
        for c in self.connections:
            if c.node_id not in ids:
                raise ValueError(f"la conexión {c.id} apunta a un nodo desconocido {c.node_id}")
        for stop_id, m in self.stop_mappings.items():
            for ref in [m.node, *m.exits]:
                if ref is not None and ref not in ids:
                    raise ValueError(f"la parada {stop_id} apunta a un nodo desconocido {ref}")
        return self


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


def load_network_spec(path: Path) -> NetworkSpec:
    return NetworkSpec.model_validate(json.loads(path.read_text(encoding="utf-8")))


def load_sources(path: Path) -> list[SourceSpec]:
    raw = json.loads(path.read_text(encoding="utf-8"))
    return [SourceSpec.model_validate(s) for s in raw["sources"]]
