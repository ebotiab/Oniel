// Tipos públicos de la API de Oniel (espejo de backend/src/oniel/domain/schemas.py).

export type NodeKind = 'estacion' | 'paet' | 'pb' | 'bifurcacion' | 'cambiador' | 'referencia'
export type NodeRank = 'principal' | 'secundario'
export type PassKind = 'publicado' | 'estimado' | 'indeterminado'
export type ClosureStatus = 'afectado_publicado' | 'afectado_estimado' | 'indeterminado' | 'no_afectado'

export interface Source {
  id: string
  name: string
  publisher: string
  url: string | null
  license: string | null
  license_url: string | null
  retrieved_on: string | null
  coverage: string | null
  notes: string | null
}

export interface Operator {
  id: string
  name: string
  role: 'operador' | 'administrador_infraestructura'
  /** Fuente registrada de la que salen sus datos (sus horarios, si es un operador). */
  source_id?: string | null
  /** De un operador de trenes: si sus horarios están cargados o no los publica en abierto. */
  timetable?: 'cargado' | 'no_publicado' | null
}

/** Un fichero de horarios importado: de qué fuente y operador es y qué días cubre. */
export interface DatasetOut {
  id: string
  source_id: string
  operator_id: string | null
  retrieved_on: string
  valid_from: string
  valid_to: string
}

export interface LineSummary {
  id: string
  name: string
  short_name: string | null
  sort_order: number
  mode: string
  infrastructure_manager: Operator | null
  /** Operadores de trenes que circulan por la línea, tengan o no sus horarios cargados. */
  operator_ids?: string[]
  gauge_mm: number | null
  electrification: string | null
  max_speed_kmh: number | null
  opened_on: string | null
  length_km: number
  reference_length_km: number | null
  status: 'disponible' | 'prevista'
  description: string | null
  source_id: string | null
  node_count: number
  segment_count: number
}

export interface NodeOut {
  id: string
  name: string
  kind: NodeKind
  rank: NodeRank
  lon: number
  lat: number
  adif_code: string | null
  description: string | null
  details: { contexto_2026?: string; fuentes?: { title: string; url: string }[] } & Record<string, unknown>
  line_id: string
  km: number
  reference_pk_km: number | null
  seq: number
}

export interface SegmentOut {
  id: string
  line_id: string
  seq: number
  from_node_id: string
  to_node_id: string
  from_name: string
  to_name: string
  km_from: number
  km_to: number
  length_km: number
  max_speed_kmh: number | null
  typical_speed_kmh: number | null
  tracks: number | null
  status: 'disponible' | 'prevista'
  source_id: string | null
}

export interface ConnectionOut {
  id: string
  node_id: string
  name: string
  towards: string
  status: 'no_cargada' | 'disponible'
  line_id: string | null
}

/** Lo justo de una fuente para citarla junto a un dato. */
export interface SourceRef {
  id: string
  name: string
  publisher: string
  url: string | null
}

/**
 * Interrupción del servicio entre dos nodos de una línea. Está vigente los días
 * start_date <= día < ended_on, o sin límite mientras ended_on sea nulo.
 */
export interface InterruptionOut {
  id: string
  line_id: string
  from_node_id: string
  to_node_id: string
  from_name: string
  to_name: string
  km_from: number
  km_to: number
  segment_ids: string[]
  start_date: string
  expected_end_date: string | null
  expected_end_text: string | null
  ended_on: string | null
  reason: string
  note: string | null
  sources: SourceRef[]
  checked_on: string
  /** «Horario publicado; sin circulación real desde el … (fuente)». */
  schedule_note: string
}

export interface Feature<P = Record<string, unknown>> {
  type: 'Feature'
  id: string
  geometry: GeoJSON.Geometry
  properties: P
}

export interface FeatureCollection<P = Record<string, unknown>> {
  type: 'FeatureCollection'
  features: Feature<P>[]
}

/**
 * La red tal y como la usa el visor. Ya no llega en una sola respuesta: se compone en memoria a
 * partir del índice y de las líneas cargadas (src/data/network.ts).
 */
export interface NetworkOut {
  lines: LineSummary[]
  nodes: NodeOut[]
  segments: SegmentOut[]
  connections: ConnectionOut[]
  segment_features: FeatureCollection
  node_features: FeatureCollection
  connection_features: FeatureCollection
  /** Todas las registradas, vigentes o no. Falta en las respuestas anteriores a esta capa. */
  interruptions?: InterruptionOut[]
}

/** Un nodo en el índice: sin descripción ni detalles, que llegan con su línea. */
export type NodeIndexOut = Omit<NodeOut, 'description' | 'details'>

/** Índice ligero de toda la red: lo que se descarga al arrancar. */
export interface NetworkIndexOut {
  lines: LineSummary[]
  nodes: NodeIndexOut[]
  /** Tramos con la geometría simplificada; sus datos van en properties. */
  segment_features: FeatureCollection<Omit<SegmentOut, 'id'>>
  connections: ConnectionOut[]
  connection_features: FeatureCollection
  interruptions?: InterruptionOut[]
  simplify_tolerance_m: number
}

/** El detalle de una línea: nodos con sus textos, geometría completa y pasos por tramo. */
export interface LineDetailOut {
  line: LineSummary
  nodes: NodeOut[]
  segments: SegmentOut[]
  segment_features: FeatureCollection
  connections: ConnectionOut[]
  interruptions?: InterruptionOut[]
  date: string | null
  counts: Record<string, number>
  /** Los mismos pasos separados por operador: por id de tramo, cuántos son de cada uno. */
  counts_by_operator?: Record<string, Record<string, number>>
  /** El mayor recuento de toda la red ese día, para dibujar las barras de todas las líneas a la misma escala. */
  network_max_count: number
}

export interface CoverageOut {
  lines: LineSummary[]
  total_length_km: number
  station_count: number
  service_count: number
  operators: Operator[]
  feed_start: string | null
  feed_end: string | null
  reference_date: string | null
  /** Conjuntos de datos activos el día de referencia, uno por fuente de horarios. */
  datasets?: DatasetOut[]
  sources: Source[]
  notice: string
}

export interface ServiceOut {
  id: string
  operator_id: string
  train_number: string
  product: string
  origin_name: string | null
  destination_name: string | null
  resolution: 'completa' | 'parcial'
  valid_from: string
  valid_to: string
}

export interface SegmentPassOut {
  service: ServiceOut
  kind: PassKind
  enter: string | null
  exit: string | null
  enter_margin_min: number
  exit_margin_min: number
  km_increasing: boolean | null
  direction_label: string
  basis: string
}

export interface SegmentServicesOut {
  segment: SegmentOut
  date: string
  passes: SegmentPassOut[]
  counts: Record<PassKind, number>
  /** Interrupciones vigentes en el tramo el día de los pasos. */
  interruptions?: InterruptionOut[]
}

export interface NodeCall {
  service_id: string
  operator_id?: string
  train_number: string
  product: string
  origin_name: string | null
  destination_name: string | null
  arrival: string | null
  departure: string | null
}

export interface NodeServicesOut {
  node: NodeOut
  date: string
  calls: NodeCall[]
}

export interface ClosureRequest {
  segment_id: string
  date: string
  start: string
  end: string
  /** Escenario como cadena corta: sus otras modificaciones cuentan al buscar la alternativa. */
  scenario?: string
}

export interface ClosureResultItem {
  service: ServiceOut
  status: ClosureStatus
  kind: PassKind
  enter: string | null
  exit: string | null
  direction_label: string
  explanation: string
  from_previous_day: boolean
}

/** Trecho de un recorrido por una sola línea (o por un enlace esbozado, sin `line_id`). */
export interface RouteLeg {
  line_id: string | null
  line_name: string
  from_node_id: string
  from_name: string
  to_node_id: string
  to_name: string
  length_km: number
  time_min: number | null
  single_track_km: number
}

/** Un recorrido entre dos nodos sobre el grafo de todas las líneas, con lo que cuesta. */
export interface Route {
  from_node_id: string
  from_name: string
  to_node_id: string
  to_name: string
  length_km: number
  /** Minutos a la velocidad habitual de cada tramo, sin paradas; nulo si falta alguna velocidad. */
  time_min: number | null
  single_track_km: number
  line_ids: string[]
  legs: RouteLeg[]
  /** Estaciones principales intermedias, en el orden en que se recorren. */
  via: string[]
  node_ids: string[]
  segment_ids: string[]
}

/**
 * Recorrido por otras líneas cargadas entre dos nodos de la línea cerrada, uno a cada lado del
 * tramo. `line_id` y `line_name` son los de la primera línea; si encadena varias, `legs` las trae.
 */
export interface ClosureAlternative {
  line_id: string
  line_name: string
  from_node_id: string
  from_name: string
  to_node_id: string
  to_name: string
  length_km: number
  closed_line_length_km: number
  via: string[]
  single_track_km: number
  note: string
  /** Interrupciones vigentes ese día en el recorrido alternativo. */
  interruptions?: InterruptionOut[]
  line_ids?: string[]
  legs?: RouteLeg[]
  time_min?: number | null
  segment_ids?: string[]
}

export interface ClosureResult {
  request: ClosureRequest
  segment: SegmentOut
  window_label: string
  counts: Record<ClosureStatus, number>
  items: ClosureResultItem[]
  alternatives: ClosureAlternative[]
  /** Interrupciones vigentes ese día en el tramo que se cierra. */
  interruptions?: InterruptionOut[]
  method: string
  caveats: string[]
}
