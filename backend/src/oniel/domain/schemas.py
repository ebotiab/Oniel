"""Modelos públicos de la API (también los usa la exportación estática del visor)."""

from __future__ import annotations

import datetime as dt
from typing import Any, Literal

from pydantic import BaseModel, Field, computed_field

from oniel.domain.annotations import INTERRUPTION
from oniel.routing.graph import Route, RouteLeg
from oniel.routing.scenario import Scenario


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
    #: Fuente registrada de la que salen sus datos (sus horarios, si es un operador).
    source_id: str | None = None
    #: De un operador de trenes: si sus horarios están cargados o no los publica en abierto.
    timetable: Literal["cargado", "no_publicado"] | None = None


class ZoneOut(BaseModel):
    """Zona en la que el visor agrupa las líneas; una clasificación de Oniel, sin fuente."""

    id: str
    name: str
    sort_order: int
    #: Ciudades de la zona; el visor nombra las que tienen estación cargada.
    cities: list[str] = Field(default_factory=list)


class LineSummary(BaseModel):
    id: str
    name: str
    short_name: str | None = None
    sort_order: int = 1
    zone: ZoneOut | None = None
    mode: str
    infrastructure_manager: Operator | None = None
    #: Operadores de trenes que circulan por la línea, tengan o no sus horarios cargados.
    operator_ids: list[str] = Field(default_factory=list)
    gauge_mm: int | None = None
    electrification: str | None = None
    max_speed_kmh: int | None = None
    opened_on: dt.date | None = None
    length_km: float
    reference_length_km: float | None = None
    status: Literal["disponible", "prevista"]
    description: str | None = None
    source_id: str | None = None
    #: Si la línea es un baipás, el id de la línea de la que lo es (``LineSpec.bypass_of``).
    bypass_of: str | None = None
    #: Si la línea es un enlace, el id de la línea de la que cuelga (``LineSpec.link_of``).
    link_of: str | None = None
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


class AttributeValue(BaseModel):
    """El valor de un atributo en un tramo, con el id de su fuente y el día en que se comprobó."""

    value: int | float | str | bool
    source_id: str | None = None
    checked_on: dt.date | None = None


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
    #: Número de vías: el mismo valor que ``attributes["tracks"]``, a mano para el mapa, el
    #: esquema y el cálculo de recorridos.
    tracks: int | None = None
    #: Atributos del tramo declarados por secciones en la especificación de la línea, por clave.
    attributes: dict[str, AttributeValue] = Field(default_factory=dict)
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


class MilestoneOut(BaseModel):
    """Un hito fechado de una anotación: la fecha conocida (año, mes o día), qué pasó y su fuente.

    ``source_id`` es el id de una de las ``sources`` de la anotación, para no repetirla entera.
    """

    date: str
    text: str
    source_id: str


class AnnotationOut(BaseModel):
    """Anotación de red: algo que pasa sobre la red entre dos fechas según una fuente.

    ``kind`` dice qué es (``interrupcion`` hoy) y ``status``, en qué estado está. El alcance es uno
    de tres: entre dos nodos de una línea (``line_id``, ``from_node_id``, ``to_node_id``, con sus
    nombres, sus kilómetros y los tramos que quedan entre ambos en ``segment_ids``), un nodo
    (``node_id``) o una ``geometry`` propia. Está vigente los días ``start_date <= día < ended_on``
    (sin límite por el lado que sea nulo).
    """

    id: str
    kind: str
    status: str
    line_id: str | None = None
    from_node_id: str | None = None
    to_node_id: str | None = None
    from_name: str | None = None
    to_name: str | None = None
    km_from: float | None = None
    km_to: float | None = None
    #: Tramos de la red afectados; vacío si el alcance es un nodo o una geometría propia.
    segment_ids: list[str] = Field(default_factory=list)
    node_id: str | None = None
    node_name: str | None = None
    geometry: dict[str, Any] | None = None
    start_date: dt.date | None = None
    expected_end_date: dt.date | None = None
    expected_end_text: str | None = None
    ended_on: dt.date | None = None
    title: str | None = None
    reason: str | None = None
    note: str | None = None
    #: Hitos fechados, del más antiguo al más reciente.
    milestones: list[MilestoneOut] = Field(default_factory=list)
    sources: list[SourceRef]
    checked_on: dt.date
    #: Nota para los pasos por tramo cuando el tipo corta la circulación: «Horario publicado; sin
    #: circulación real desde el … (fuente)». Nula en los demás tipos.
    schedule_note: str | None = None

    def active_on(self, day: dt.date) -> bool:
        started = self.start_date is None or self.start_date <= day
        return started and (self.ended_on is None or day < self.ended_on)


#: Una interrupción del servicio es una anotación de tipo ``interrupcion``: el nombre queda como
#: alias para lo que solo trata con ellas (pasos por tramo, simulación, recorridos).
InterruptionOut = AnnotationOut


class WithAnnotations(BaseModel):
    """Respuesta que lleva las anotaciones de red y, como alias temporal, las interrupciones."""

    #: Todas las anotaciones registradas, vigentes o ya terminadas; el visor decide por fecha.
    annotations: list[AnnotationOut] = Field(default_factory=list)

    @computed_field  # type: ignore[prop-decorator]
    @property
    def interruptions(self) -> list[AnnotationOut]:
        """Alias temporal: las anotaciones de tipo ``interrupcion``, para los visores anteriores."""
        return [a for a in self.annotations if a.kind == INTERRUPTION]


class Feature(BaseModel):
    type: Literal["Feature"] = "Feature"
    id: str
    geometry: dict[str, Any]
    properties: dict[str, Any]


class FeatureCollection(BaseModel):
    type: Literal["FeatureCollection"] = "FeatureCollection"
    features: list[Feature]


class NetworkOut(WithAnnotations):
    """Todo lo que el visor necesita para dibujar la red disponible."""

    lines: list[LineSummary]
    nodes: list[NodeOut]
    segments: list[SegmentOut]
    connections: list[ConnectionOut]
    line_features: FeatureCollection
    segment_features: FeatureCollection
    node_features: FeatureCollection
    connection_features: FeatureCollection


class NodeIndexOut(BaseModel):
    """Un nodo en el índice de la red: lo justo para situarlo, buscarlo y saber de qué línea es."""

    id: str
    name: str
    kind: Literal["estacion", "paet", "pb", "bifurcacion", "cambiador", "referencia"]
    rank: Literal["principal", "secundario"] = "principal"
    lon: float
    lat: float
    adif_code: str | None = None
    line_id: str
    km: float
    reference_pk_km: float | None = None
    seq: int


class NetworkIndexOut(WithAnnotations):
    """Índice ligero de toda la red: lo que el visor descarga al arrancar.

    Lleva las líneas, todos los nodos sin sus textos, los tramos con la geometría simplificada
    (sus datos van en ``properties``, como en ``NetworkOut.segment_features``), las conexiones y
    las anotaciones. El detalle de cada línea se pide aparte (``LineDetailOut``).
    """

    lines: list[LineSummary]
    nodes: list[NodeIndexOut]
    segment_features: FeatureCollection
    connections: list[ConnectionOut]
    connection_features: FeatureCollection
    #: Tolerancia con la que se ha simplificado la geometría de los tramos, en metros.
    simplify_tolerance_m: float


class LineDetailOut(WithAnnotations):
    """El detalle de una línea: nodos con sus textos, tramos con la geometría completa y recuentos.

    ``annotations`` son las registradas en la línea o en sus nodos, vigentes o ya terminadas.
    """

    line: LineSummary
    nodes: list[NodeOut]
    segments: list[SegmentOut]
    segment_features: FeatureCollection
    #: Conexiones que salen de algún nodo de la línea.
    connections: list[ConnectionOut]
    #: Día de los recuentos; nulo si no hay horarios cargados.
    date: dt.date | None = None
    #: Pasos por tramo ese día, por id de tramo; los tramos sin pasos no aparecen.
    counts: dict[str, int] = Field(default_factory=dict)
    #: Los mismos pasos separados por operador: por id de tramo, cuántos son de cada uno.
    counts_by_operator: dict[str, dict[str, int]] = Field(default_factory=dict)
    #: El mayor recuento de toda la red ese día: las barras de todas las líneas van a su escala.
    network_max_count: int = 0


class DatasetOut(BaseModel):
    """Un fichero de horarios importado: de qué fuente es, cuándo se descargó y qué días cubre."""

    id: str
    source_id: str
    operator_id: str | None = None
    file: str
    sha256: str
    retrieved_on: dt.date
    valid_from: dt.date
    valid_to: dt.date


class CoverageOut(BaseModel):
    lines: list[LineSummary]
    total_length_km: float
    station_count: int
    service_count: int
    operators: list[Operator]
    feed_start: dt.date | None = None
    feed_end: dt.date | None = None
    reference_date: dt.date | None = None
    #: Conjuntos de datos activos el día de referencia: de ellos salen las cifras y los horarios.
    datasets: list[DatasetOut] = Field(default_factory=list)
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


class DestinationOperatorOut(BaseModel):
    operator_id: str
    trains: int


class DestinationOut(BaseModel):
    """Una estación a la que se llega sin cambiar de tren desde un nodo, un día."""

    #: Nodo de la red cargada, si el destino está en ella; si no, solo se conoce la parada.
    node_id: str | None = None
    stop_id: str
    name: str
    trains: int
    #: Tipos de servicio (producto comercial), del que más trenes tiene al que menos.
    products: list[str]
    #: Trenes de cada operador, del que más tiene al que menos; suman ``trains``.
    operators: list[DestinationOperatorOut]
    #: Primera y última salida del nodo hacia el destino, ``HH:MM``.
    first_departure: str
    last_departure: str


class NodeServicesOut(BaseModel):
    node: NodeOut
    date: dt.date
    calls: list[dict[str, Any]]
    #: Destinos directos del día, del más frecuente al menos.
    destinations: list[DestinationOut] = Field(default_factory=list)


class HistoryProductOut(BaseModel):
    """Trenes de un tipo de servicio en un punto del histórico."""

    product: str
    trains: int


class HistoryChangeOut(BaseModel):
    """Un conjunto frente al anterior de su fuente, contados los dos en los mismos días."""

    #: El conjunto anterior de la misma fuente y el día en que se descargó.
    previous_dataset_id: str
    previous_retrieved_on: dt.date
    #: Los días que se cuentan: las primeras semanas del conjunto nuevo que cubren los dos.
    date_from: dt.date
    date_to: dt.date
    #: Trenes en esos días según el conjunto anterior y según este; uno por tren y día.
    trains_before: int
    trains_after: int


class HistoryPointOut(BaseModel):
    """Los trenes de un conjunto de datos en una estación o un tramo, en su día de referencia."""

    dataset_id: str
    source_id: str
    operator_id: str | None = None
    #: Día en que se descargó el fichero de horarios.
    retrieved_on: dt.date
    #: Día de referencia del conjunto: el laborable con más servicios de sus primeros treinta días.
    date: dt.date
    trains: int
    #: Por tipo de servicio, del que más trenes tiene al que menos.
    products: list[HistoryProductOut] = Field(default_factory=list)
    #: Qué cambia respecto al conjunto anterior de su fuente; falta en el primero de cada una.
    change: HistoryChangeOut | None = None


class ServiceHistoryOut(BaseModel):
    """Cómo cambia el servicio de un nodo o de un tramo de un fichero de horarios a otro."""

    #: Id del nodo o del tramo.
    id: str
    #: Un punto por conjunto de datos, del descargado antes al más reciente.
    points: list[HistoryPointOut]


class ClosureRequest(BaseModel):
    segment_id: str
    date: dt.date
    start: dt.time
    end: dt.time
    #: Escenario como cadena corta (``oniel.routing``): el cierre de ``segment_id`` se le suma.
    scenario: str = ""


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
    """Recorrido por otras líneas cargadas entre dos nodos de la línea cerrada, uno a cada lado del tramo.

    Sale del grafo de rutas (``oniel.routing``). ``line_id`` y ``line_name`` son los de la primera
    línea del recorrido; cuando encadena varias, ``legs`` trae un trecho por cada una.
    """

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
    line_ids: list[str] = Field(default_factory=list)
    legs: list[RouteLeg] = Field(default_factory=list)
    #: Minutos a la velocidad habitual de cada tramo, sin paradas.
    time_min: int | None = None
    segment_ids: list[str] = Field(default_factory=list)


class ClosureResult(BaseModel):
    request: ClosureRequest
    segment: SegmentOut
    window_label: str
    counts: dict[str, int]
    items: list[ClosureResultItem]
    alternatives: list[ClosureAlternative] = Field(default_factory=list)
    #: Rodeos más largos que existen y no se listan por desproporcionados (``closure_detours``).
    omitted_alternatives: int = 0
    #: Interrupciones vigentes ese día en el tramo que se cierra: el cierre simulado se suma a una real.
    interruptions: list[InterruptionOut] = Field(default_factory=list)
    method: str
    caveats: list[str]


class RouteOut(Route):
    """Un recorrido del grafo, con las interrupciones vigentes en él el día pedido."""

    interruptions: list[InterruptionOut] = Field(default_factory=list)


class RoutesOut(BaseModel):
    """Recorridos entre dos nodos con la red de un escenario, del más corto al más largo."""

    from_node_id: str
    to_node_id: str
    #: El escenario aplicado, como modelo y como cadena corta para la URL.
    scenario: Scenario
    scenario_code: str
    date: dt.date | None = None
    max_changes: int
    max_ratio: float
    routes: list[RouteOut]
    method: str


class AlternativeRouteOut(BaseModel):
    """El camino más corto que queda entre dos nodos con un tramo cerrado, y lo que añade."""

    length_km: float
    time_min: int | None
    #: Diferencia con el recorrido del tren; negativa si el otro camino es más corto.
    extra_km: float
    extra_min: int | None
    single_track_km: float
    line_ids: list[str]
    #: Estaciones principales intermedias, en el orden en que se recorren.
    via: list[str]


class SegmentTrainGroupOut(BaseModel):
    """Trenes de un tramo que siguen el mismo recorrido por las líneas cargadas."""

    #: Nodos por los que el grupo entra y sale de las líneas cargadas.
    from_node_id: str
    from_name: str
    to_node_id: str
    to_name: str
    trains: int
    by_operator: dict[str, int]
    #: Lo que mide y tarda ese recorrido, con la misma vara que la alternativa.
    length_km: float
    time_min: int | None
    line_ids: list[str]
    #: Nulo si con el tramo cerrado no queda ningún camino en las líneas cargadas.
    alternative: AlternativeRouteOut | None


class SegmentAlternativesOut(BaseModel):
    """Los trenes de un tramo un día y cuántos tienen otro camino si el tramo se corta."""

    segment_id: str
    trains: int
    by_operator: dict[str, int]
    with_alternative: int
    without_alternative: int
    #: Del grupo con más trenes al que menos.
    groups: list[SegmentTrainGroupOut]


class AlternativesOut(BaseModel):
    """Trenes por tramo y alternativa en las líneas cargadas, para toda la red."""

    #: Día de los trenes; nulo si no hay horarios cargados.
    date: dt.date | None
    #: Las líneas en las que se busca el otro camino: «sin alternativa» se refiere solo a ellas.
    line_ids: list[str]
    #: Operadores que circulan por esas líneas y cuyos trenes no están contados.
    missing_operator_ids: list[str]
    scope_note: str
    method: str
    #: Un elemento por tramo, en el orden de la red.
    segments: list[SegmentAlternativesOut]
