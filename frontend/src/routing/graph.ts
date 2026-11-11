// Grafo de todas las líneas cargadas y recorridos entre dos nodos, calculados en el cliente sobre
// la red que compone el visor (`data/network.ts`) para que el modo estático no dependa de la API.
// Las líneas, los nodos y los tramos salen enteros del índice (`index.json` o /api/lines), así que
// el grafo está completo al arrancar, sin esperar al detalle de ninguna línea.
//
// Es el mismo cálculo que `backend/src/oniel/routing/graph.py`, con los mismos nombres: los dos
// tienen que dar lo mismo, y `e2e/rutas.spec.ts` lo comprueba con un caso compartido. El método
// está en `docs/simulacion.md`, «Grafo y escenarios».

import type { LineSummary, NodeOut, Route, RouteLeg, SegmentOut } from '../data/types.ts'
import { ScenarioError, emptyScenario, linkId, withClosures, type Scenario } from './scenario.ts'

/**
 * Veces que un recorrido pasa de una línea a otra si no se pide otra cosa. Es un freno técnico
 * (hasta seis líneas encadenadas), no un criterio: lo que descarta recorridos es `maxRatio`.
 */
export const DEFAULT_MAX_CHANGES = 5
/** Un recorrido se descarta si mide más de estas veces lo que mide el más corto. */
export const DEFAULT_MAX_RATIO = 2
/** Tope de recorridos devueltos. */
export const MAX_ROUTES = 12
const KM_TOLERANCE = 0.05
const SKETCH_NAME = 'Enlace esbozado'

interface GraphNode {
  id: string
  name: string
  kind: string
  rank: string
}

/** Un tramo (o un enlace esbozado, con `line_id` nulo) entre dos nodos. */
interface Edge {
  id: string
  line_id: string | null
  a: string
  b: string
  length_km: number
  /** Velocidad habitual; la máxima si no hay habitual; nula si no se conoce ninguna. */
  speed_kmh: number | null
  tracks: number | null
}

export interface Graph {
  nodes: Map<string, GraphNode>
  edges: Edge[]
  lineNames: Map<string, string>
  /** Kilómetro de cada nodo en cada línea a la que pertenece. */
  lineKm: Map<string, Map<string, number>>
  adjacent: Map<string, Edge[]>
}

/** Rodeo que salva un tramo cerrado: sale de su línea en un nodo y vuelve a ella en otro. */
export interface Detour {
  route: Route
  /** Kilómetros entre esos dos nodos por la línea del tramo cerrado. */
  closed_line_length_km: number
}

/** Un paso del camino: la arista y el nodo al que llega. */
type Step = [Edge, string]

function makeGraph(nodes: Graph['nodes'], edges: Edge[], lineNames: Graph['lineNames'], lineKm: Graph['lineKm']): Graph {
  const adjacent = new Map<string, Edge[]>()
  for (const edge of edges) {
    for (const end of [edge.a, edge.b]) {
      const list = adjacent.get(end)
      if (list) list.push(edge)
      else adjacent.set(end, [edge])
    }
  }
  return { nodes, edges, lineNames, lineKm, adjacent }
}

/** Grafo de la red disponible. `nodes` trae cada nodo una vez por línea, con su km en ella. */
export function buildGraph(network: { lines: LineSummary[]; nodes: NodeOut[]; segments: SegmentOut[] }): Graph {
  const nodes = new Map<string, GraphNode>()
  const lineKm = new Map<string, Map<string, number>>()
  for (const n of network.nodes) {
    if (!nodes.has(n.id)) nodes.set(n.id, { id: n.id, name: n.name, kind: n.kind, rank: n.rank })
    let km = lineKm.get(n.line_id)
    if (!km) lineKm.set(n.line_id, (km = new Map()))
    km.set(n.id, n.km)
  }
  const edges = network.segments
    .filter((s) => s.status === 'disponible')
    .map<Edge>((s) => ({
      id: s.id,
      line_id: s.line_id,
      a: s.from_node_id,
      b: s.to_node_id,
      length_km: s.length_km,
      speed_kmh: s.typical_speed_kmh || s.max_speed_kmh || null,
      tracks: s.tracks,
    }))
  return makeGraph(nodes, edges, new Map(network.lines.map((l) => [l.id, l.name])), lineKm)
}

/** El grafo con las modificaciones del escenario: cierres, velocidades y enlaces. */
export function applyScenario(graph: Graph, scenario: Scenario): Graph {
  const known = new Set(graph.edges.map((e) => e.id))
  for (const id of [...scenario.closures, ...scenario.speeds.map((v) => v.segment_id)]) {
    if (!known.has(id)) throw new ScenarioError(`No hay ningún tramo con id ${id}`)
  }
  const closed = new Set(scenario.closures)
  const speed = new Map(scenario.speeds.map((v) => [v.segment_id, v.speed_kmh]))
  const edges = graph.edges.filter((e) => !closed.has(e.id)).map((e) => (speed.has(e.id) ? { ...e, speed_kmh: speed.get(e.id)! } : e))
  for (const link of scenario.links) {
    for (const id of [link.from_node_id, link.to_node_id]) {
      if (!graph.nodes.has(id)) throw new ScenarioError(`No hay ningún nodo con id ${id}`)
    }
    if (link.from_node_id === link.to_node_id) throw new ScenarioError('Un enlace tiene que unir dos nodos distintos')
    edges.push({ id: linkId(link), line_id: null, a: link.from_node_id, b: link.to_node_id, length_km: link.length_km, speed_kmh: link.speed_kmh, tracks: null })
  }
  return makeGraph(graph.nodes, edges, graph.lineNames, graph.lineKm)
}

const lineKey = (edge: Edge) => edge.line_id ?? edge.id

/**
 * Caminos simples desde `start` hasta un nodo meta, en profundidad. Un camino termina al llegar a
 * una meta; solo atraviesa los nodos que `mayPass` admite y no cambia de línea más de `maxChanges`
 * veces. Cada enlace esbozado cuenta como una línea.
 */
function walk(
  graph: Graph,
  start: string,
  isGoal: (node: string) => boolean,
  mayPass: (node: string) => boolean,
  edgeOk: (edge: Edge) => boolean,
  maxChanges: number | null,
): Step[][] {
  const found: Step[][] = []
  const path: Step[] = []
  const visited = new Set([start])
  const visit = (node: string, changes: number) => {
    for (const edge of graph.adjacent.get(node) ?? []) {
      const next = edge.a === node ? edge.b : edge.a
      if (visited.has(next) || !edgeOk(edge)) continue
      const previous = path.at(-1)?.[0]
      const total = changes + (previous !== undefined && lineKey(previous) !== lineKey(edge) ? 1 : 0)
      if (maxChanges !== null && total > maxChanges) continue
      path.push([edge, next])
      if (isGoal(next)) found.push([...path])
      else if (mayPass(next)) {
        visited.add(next)
        visit(next, total)
        visited.delete(next)
      }
      path.pop()
    }
  }
  visit(start, 0)
  return found
}

/** Redondeo a una décima, con la misma fórmula que el servidor. */
const round1 = (value: number) => Math.floor(value * 10 + 0.5) / 10

function rawLength(steps: Step[]): number {
  let total = 0
  for (const [edge] of steps) total += edge.length_km
  return total
}

function timeMin(edges: Edge[]): number | null {
  let hours = 0
  for (const edge of edges) {
    if (!edge.speed_kmh) return null
    hours += edge.length_km / edge.speed_kmh
  }
  return Math.floor(hours * 60 + 0.5)
}

function singleTrack(edges: Edge[]): number {
  let total = 0
  for (const edge of edges) if (edge.tracks === 1) total += edge.length_km
  return total
}

function toRoute(graph: Graph, start: string, steps: Step[]): Route {
  const name = (id: string) => graph.nodes.get(id)!.name
  // Trechos: aristas seguidas de la misma línea.
  const groups: { start: string; steps: Step[] }[] = []
  let at = start
  for (const step of steps) {
    const last = groups.at(-1)
    if (last && lineKey(last.steps.at(-1)![0]) === lineKey(step[0])) last.steps.push(step)
    else groups.push({ start: at, steps: [step] })
    at = step[1]
  }
  let length = 0
  const legs = groups.map<RouteLeg>((group) => {
    const edges = group.steps.map(([e]) => e)
    const end = group.steps.at(-1)![1]
    const lineId = edges[0]!.line_id
    // Por una línea, la distancia es la diferencia de sus kilómetros; un enlace trae la suya.
    let legLength = edges[0]!.length_km
    if (lineId !== null) {
      const km = graph.lineKm.get(lineId)!
      legLength = Math.abs(km.get(end)! - km.get(group.start)!)
    }
    length += legLength
    return {
      line_id: lineId,
      line_name: lineId !== null ? graph.lineNames.get(lineId)! : SKETCH_NAME,
      from_node_id: group.start,
      from_name: name(group.start),
      to_node_id: end,
      to_name: name(end),
      length_km: round1(legLength),
      time_min: timeMin(edges),
      single_track_km: round1(singleTrack(edges)),
    }
  })
  const edges = steps.map(([e]) => e)
  const end = steps.at(-1)![1]
  const inner = steps.slice(0, -1).map(([, n]) => graph.nodes.get(n)!)
  return {
    from_node_id: start,
    from_name: name(start),
    to_node_id: end,
    to_name: name(end),
    length_km: round1(length),
    time_min: timeMin(edges),
    single_track_km: round1(singleTrack(edges)),
    line_ids: [...new Set(edges.flatMap((e) => (e.line_id !== null ? [e.line_id] : [])))],
    legs,
    via: inner.filter((n) => n.kind === 'estacion' && n.rank === 'principal').map((n) => n.name),
    node_ids: [start, ...steps.map(([, n]) => n)],
    segment_ids: edges.map((e) => e.id),
  }
}

/** Del más corto al más largo; a igual longitud, por los tramos que recorre. */
function sorted(found: { start: string; steps: Step[] }[]): { start: string; steps: Step[] }[] {
  const keyed = found.map((f) => ({ f, length: rawLength(f.steps), ids: f.steps.map(([e]) => e.id) }))
  keyed.sort((x, y) => {
    if (x.length !== y.length) return x.length < y.length ? -1 : 1
    for (let i = 0; i < Math.min(x.ids.length, y.ids.length); i++) {
      if (x.ids[i] !== y.ids[i]) return x.ids[i]! < y.ids[i]! ? -1 : 1
    }
    return x.ids.length - y.ids.length
  })
  return keyed.map((k) => k.f)
}

/**
 * Recorridos distintos entre dos nodos con la red del escenario, del más corto al más largo: los
 * caminos que no pasan dos veces por el mismo nodo, cambian de línea como mucho `maxChanges`
 * veces (`null`, sin tope) y no miden más de `maxRatio` veces lo que mide el más corto (`null`,
 * sin descartar ninguno por largo).
 */
export function findRoutes(
  graph: Graph,
  fromNodeId: string,
  toNodeId: string,
  scenario?: Scenario,
  maxChanges: number | null = DEFAULT_MAX_CHANGES,
  maxRatio: number | null = DEFAULT_MAX_RATIO,
): Route[] {
  for (const id of [fromNodeId, toNodeId]) {
    if (!graph.nodes.has(id)) throw new ScenarioError(`No hay ningún nodo con id ${id}`)
  }
  if (fromNodeId === toNodeId) return []
  const g = scenario ? applyScenario(graph, scenario) : graph
  const found = walk(
    g,
    fromNodeId,
    (n) => n === toNodeId,
    () => true,
    () => true,
    maxChanges,
  ).map((steps) => ({ start: fromNodeId, steps }))
  let ordered = sorted(found)
  if (maxRatio !== null && ordered.length) {
    const limit = rawLength(ordered[0]!.steps) * maxRatio
    ordered = ordered.filter((f) => rawLength(f.steps) <= limit)
  }
  return ordered.slice(0, MAX_ROUTES).map((f) => toRoute(g, f.start, f.steps))
}

/**
 * Rodeos que salvan el tramo `segmentId` cerrado, del más corto al más largo. Un rodeo sale de la
 * línea del tramo en un nodo situado antes del cierre, no vuelve a tocarla hasta un nodo situado
 * después y no usa ninguno de sus tramos. El resto del escenario se aplica también.
 */
export function closureDetours(graph: Graph, segmentId: string, scenario?: Scenario): Detour[] {
  const closed = graph.edges.find((e) => e.id === segmentId)
  if (!closed || closed.line_id === null) throw new ScenarioError(`No hay ningún tramo con id ${segmentId}`)
  const lineId = closed.line_id
  const km = graph.lineKm.get(lineId)!
  const [lo, hi] = [km.get(closed.a)!, km.get(closed.b)!].sort((x, y) => x - y) as [number, number]
  const g = applyScenario(graph, withClosures(scenario ?? emptyScenario(), [segmentId]))
  const onLine = [...km.keys()]
  // Los nodos anteriores, del más cercano al tramo al más lejano.
  const before = onLine.filter((n) => km.get(n)! <= lo + KM_TOLERANCE).sort((x, y) => km.get(y)! - km.get(x)!)
  const after = new Set(onLine.filter((n) => km.get(n)! >= hi - KM_TOLERANCE))
  const found = before.flatMap((start) =>
    walk(
      g,
      start,
      (n) => after.has(n),
      (n) => !km.has(n),
      (e) => e.line_id !== lineId,
      null,
    ).map((steps) => ({ start, steps })),
  )
  return sorted(found)
    .slice(0, MAX_ROUTES)
    .map((f) => ({ route: toRoute(g, f.start, f.steps), closed_line_length_km: round1(km.get(f.steps.at(-1)![1])! - km.get(f.start)!) }))
}
