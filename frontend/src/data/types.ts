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

/** Valor de un atributo de tramo: un número o un texto corto que el visor traduce. */
export type AttributeScalar = number | string | boolean

/** El valor de un atributo en un tramo, con el id de su fuente registrada y el día en que se comprobó. */
export interface AttributeValue {
  value: AttributeScalar
  source_id: string | null
  checked_on: string | null
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
  /** Número de vías: el mismo valor que `attributes.tracks`, a mano para el mapa, el esquema y los recorridos. */
  tracks: number | null
  /** Atributos declarados por secciones, por clave. Una API anterior a ellos no trae el campo. */
  attributes?: Record<string, AttributeValue>
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
 * Un hito fechado de una anotación: la fecha conocida (AAAA, AAAA-MM o AAAA-MM-DD), qué pasó y el
 * id de su fuente, que es una de las `sources` de la anotación.
 */
export interface Milestone {
  date: string
  text: string
  source_id: string
}

/**
 * Anotación de red: algo que pasa sobre la red entre dos fechas según una fuente. `kind` dice qué
 * es y `status`, en qué estado está. El alcance es uno de tres: de un nodo a otro de una línea
 * (con los tramos que quedan entre ambos en `segment_ids`), un nodo (`node_id`) o una `geometry`
 * propia. Está vigente los días start_date <= día < ended_on, sin límite por el lado que sea nulo.
 */
export interface AnnotationOut {
  id: string
  kind: string
  status: string
  line_id: string | null
  from_node_id: string | null
  to_node_id: string | null
  from_name: string | null
  to_name: string | null
  km_from: number | null
  km_to: number | null
  /** Tramos afectados; vacío si el alcance es un nodo o una geometría propia. */
  segment_ids: string[]
  node_id: string | null
  node_name: string | null
  geometry: GeoJSON.Geometry | null
  start_date: string | null
  expected_end_date: string | null
  expected_end_text: string | null
  ended_on: string | null
  title: string | null
  reason: string | null
  note: string | null
  /** Hitos fechados, del más antiguo al más reciente. Falta en las respuestas anteriores a los proyectos. */
  milestones?: Milestone[]
  sources: SourceRef[]
  checked_on: string
  /** Solo en los tipos que cortan la circulación: «Horario publicado; sin circulación real desde el … (fuente)». */
  schedule_note: string | null
}

/**
 * Interrupción del servicio: la anotación de tipo `interrupcion`, que va siempre de un nodo a otro
 * de una línea, tiene fecha de inicio y corta la circulación en sus tramos.
 */
export interface InterruptionOut extends AnnotationOut {
  kind: 'interrupcion'
  line_id: string
  from_node_id: string
  to_node_id: string
  from_name: string
  to_name: string
  km_from: number
  km_to: number
  start_date: string
  reason: string
  schedule_note: string
}

/**
 * Una interrupción tal y como la sirven las respuestas anteriores a las anotaciones (clave
 * `interruptions`, que queda como alias temporal): sin tipo ni estado.
 */
export type LegacyInterruption = Omit<InterruptionOut, 'kind' | 'status' | 'node_id' | 'node_name' | 'geometry' | 'title'>

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
  /** Todas las anotaciones registradas, vigentes o no; el visor decide por fecha. */
  annotations: AnnotationOut[]
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
  /** Falta en las respuestas de una API anterior a las anotaciones, que solo trae el alias. */
  annotations?: AnnotationOut[]
  /** Alias temporal de las anotaciones de tipo `interrupcion`. */
  interruptions?: LegacyInterruption[]
  simplify_tolerance_m: number
}

/** El detalle de una línea: nodos con sus textos, geometría completa y pasos por tramo. */
export interface LineDetailOut {
  line: LineSummary
  nodes: NodeOut[]
  segments: SegmentOut[]
  segment_features: FeatureCollection
  connections: ConnectionOut[]
  annotations?: AnnotationOut[]
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
  /** Si aquí se puede subir al tren y bajar de él: algunos solo dejan o solo recogen viajeros. */
  boards?: boolean
  alights?: boolean
}

/** Una estación a la que se llega sin cambiar de tren desde un nodo, el día de la consulta. */
export interface Destination {
  /** Nodo de la red cargada, si el destino está en ella. */
  node_id: string | null
  stop_id: string
  name: string
  trains: number
  /** Tipos de servicio, del que más trenes tiene al que menos. */
  products: string[]
  operators: { operator_id: string; trains: number }[]
  first_departure: string
  last_departure: string
}

export interface NodeServicesOut {
  node: NodeOut
  date: string
  calls: NodeCall[]
  /** Falta si responde una API anterior a los destinos directos. */
  destinations?: Destination[]
}

/** Los trenes de un fichero de horarios en una estación o un tramo, en su día de referencia. */
export interface HistoryPoint {
  dataset_id: string
  source_id: string
  operator_id?: string | null
  /** Día en que se descargó el fichero. */
  retrieved_on: string
  /** Día de referencia del fichero: el laborable con más servicios de sus primeros treinta días. */
  date: string
  trains: number
  products: { product: string; trains: number }[]
}

/** Un punto por fichero de horarios importado, del descargado antes al más reciente. */
export interface ServiceHistoryOut {
  id: string
  points: HistoryPoint[]
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
