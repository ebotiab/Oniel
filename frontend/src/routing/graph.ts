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
/**
 * Un recorrido se descarta si, donde se aparta de otro más corto, su rodeo mide más de estas veces
 * lo que el otro recorre entre los mismos dos puntos (`strays`).
 */
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
  /**
   * Los baipases: el id de cada línea que lo es y el de la línea de la que lo es. Un baipás cuenta
   * como parte de su línea: pasar a él o volver de él no es cambiar de línea, y dos caminos que solo
   * se distinguen por ir por él o por lo que rodea son el mismo recorrido.
   */
  bypassOf: Map<string, string>
  /**
   * Los enlaces: el id de cada línea que lo es y el de la línea de la que cuelga. Un enlace también
   * cuenta como parte de su línea, pero no une dos nodos de ella: va de uno de sus nodos a un nodo
   * de otra línea, y con las dos forma un triángulo.
   */
  linkOf: Map<string, string>
  /**
   * De cada tramo que es lado del triángulo de un enlace, de qué enlace y qué lado: el enlace (0) y
   * el trecho de cada una de las dos líneas desde un extremo del enlace hasta el nodo en el que se
   * juntan. Las vías de un triángulo así no dejan doblar sus esquinas: de un lado a otro solo se
   * pasa invirtiendo la marcha, y un recorrido no lo hace.
   */
  linkSides: Map<string, readonly [string, number]>
  adjacent: Map<string, Edge[]>
}

/** Rodeo que salva un tramo cerrado: sale de su línea en un nodo y vuelve a ella en otro. */
export interface Detour {
  route: Route
  /** Kilómetros entre esos dos nodos por la línea del tramo cerrado. */
  closed_line_length_km: number
}

/** Los rodeos que salvan un tramo cerrado y cuántos más largos se han dejado fuera. */
export interface ClosureDetours {
  detours: Detour[]
  /** Rodeos que existen y no se listan, por desproporcionados o por pasar del tope. */
  omitted: number
}

/** Un paso del camino: la arista y el nodo al que llega. */
type Step = [Edge, string]

function makeGraph(
  nodes: Graph['nodes'],
  edges: Edge[],
  lineNames: Graph['lineNames'],
  lineKm: Graph['lineKm'],
  bypassOf: Graph['bypassOf'],
  linkOf: Graph['linkOf'],
): Graph {
  const adjacent = new Map<string, Edge[]>()
  for (const edge of edges) {
    for (const end of [edge.a, edge.b]) {
      const list = adjacent.get(end)
      if (list) list.push(edge)
      else adjacent.set(end, [edge])
    }
  }
  return { nodes, edges, lineNames, lineKm, bypassOf, linkOf, linkSides: linkSides(edges, lineKm, bypassOf, linkOf), adjacent }
}

/** Los lados del triángulo de cada enlace, con la misma regla que el servidor (`Graph.link_sides`). */
function linkSides(edges: Edge[], lineKm: Graph['lineKm'], bypassOf: Graph['bypassOf'], linkOf: Graph['linkOf']): Graph['linkSides'] {
  const sides = new Map<string, readonly [string, number]>()
  for (const [lineId, parent] of linkOf) {
    const own = lineKm.get(lineId)
    const onParent = lineKm.get(parent)
    if (!own || own.size < 2 || !onParent) continue
    const ids = [...own.keys()]
    const ends = [ids.reduce((x, y) => (own.get(y)! < own.get(x)! ? y : x)), ids.reduce((x, y) => (own.get(y)! > own.get(x)! ? y : x))]
    const joins = ends.filter((n) => onParent.has(n))
    const away = ends.filter((n) => !onParent.has(n))
    if (joins.length !== 1 || away.length !== 1) continue
    const [join, far] = [joins[0]!, away[0]!]
    let best: { around: number; other: string; apex: string } | null = null
    for (const other of [...lineKm.keys()].sort()) {
      const km = lineKm.get(other)!
      if (other === lineId || other === parent || !km.has(far) || bypassOf.has(other) || linkOf.has(other)) continue
      for (const apex of [...km.keys()].sort()) {
        if (!onParent.has(apex) || apex === far || apex === join) continue
        const around = Math.abs(km.get(apex)! - km.get(far)!) + Math.abs(onParent.get(apex)! - onParent.get(join)!)
        if (best === null || around < best.around) best = { around, other, apex }
      }
    }
    if (best === null) continue
    for (const edge of edges) if (edge.line_id === lineId) sides.set(edge.id, [lineId, 0])
    const others: [string, string, string][] = [
      [best.other, far, best.apex],
      [parent, best.apex, join],
    ]
    others.forEach(([side, a, b], i) => {
      const km = lineKm.get(side)!
      const [lo, hi] = [Math.min(km.get(a)!, km.get(b)!), Math.max(km.get(a)!, km.get(b)!)]
      for (const edge of edges) {
        if (edge.line_id !== side || !km.has(edge.a) || !km.has(edge.b)) continue
        const [near, beyond] = [Math.min(km.get(edge.a)!, km.get(edge.b)!), Math.max(km.get(edge.a)!, km.get(edge.b)!)]
        if (lo - KM_TOLERANCE <= near && beyond <= hi + KM_TOLERANCE) sides.set(edge.id, [lineId, i + 1])
      }
    })
  }
  return sides
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
  const bypassOf = new Map(network.lines.flatMap((l) => (l.bypass_of ? [[l.id, l.bypass_of] as const] : [])))
  const linkOf = new Map(network.lines.flatMap((l) => (l.link_of ? [[l.id, l.link_of] as const] : [])))
  return makeGraph(nodes, edges, new Map(network.lines.map((l) => [l.id, l.name])), lineKm, bypassOf, linkOf)
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
  return makeGraph(graph.nodes, edges, graph.lineNames, graph.lineKm, graph.bypassOf, graph.linkOf)
}

/**
 * La línea por la que cuenta un tramo: la suya o, si es de un baipás o de un enlace, la línea de la
 * que cuelga. Un enlace esbozado cuenta como una línea propia.
 */
const lineKey = (graph: Graph, edge: Edge) =>
  edge.line_id === null ? edge.id : (graph.bypassOf.get(edge.line_id) ?? graph.linkOf.get(edge.line_id) ?? edge.line_id)

/** Por cada baipás, la línea de la que lo es y los dos nodos de esta que une. */
function bypassSpans(graph: Graph): { parent: string; a: string; b: string }[] {
  const spans: { parent: string; a: string; b: string }[] = []
  for (const [lineId, parent] of graph.bypassOf) {
    const km = graph.lineKm.get(lineId)
    const parentKm = graph.lineKm.get(parent)
    if (!km || km.size < 2 || !parentKm) continue
    const ids = [...km.keys()]
    const first = ids.reduce((x, y) => (km.get(y)! < km.get(x)! ? y : x))
    const last = ids.reduce((x, y) => (km.get(y)! > km.get(x)! ? y : x))
    if (!parentKm.has(first) || !parentKm.has(last)) continue
    const [a, b] = first < last ? [first, last] : [last, first]
    spans.push({ parent, a, b })
  }
  return spans
}

/**
 * Caminos simples desde `start` hasta un nodo meta, en profundidad. Un camino termina al llegar a
 * una meta; solo atraviesa los nodos que `mayPass` admite y no cambia de línea más de `maxChanges`
 * veces. Cada enlace esbozado cuenta como una línea, y un baipás o un enlace cargado, como parte de
 * la suya. Tampoco pasa de un lado a otro del triángulo de un enlace: sería invertir la marcha.
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
      const [from, to] = [previous && graph.linkSides.get(previous.id), graph.linkSides.get(edge.id)]
      if (from && to && from[0] === to[0] && from[1] !== to[1]) continue
      const total = changes + (previous !== undefined && lineKey(graph, previous) !== lineKey(graph, edge) ? 1 : 0)
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
  // Trechos: aristas seguidas de la misma línea, con sus baipases dentro.
  const groups: { start: string; steps: Step[] }[] = []
  let at = start
  for (const step of steps) {
    const last = groups.at(-1)
    if (last && lineKey(graph, last.steps.at(-1)![0]) === lineKey(graph, step[0])) last.steps.push(step)
    else groups.push({ start: at, steps: [step] })
    at = step[1]
  }
  let length = 0
  const legs = groups.map<RouteLeg>((group) => {
    const edges = group.steps.map(([e]) => e)
    const end = group.steps.at(-1)![1]
    const own = edges[0]!.line_id
    // El trecho es de la línea; si todo él va por un baipás, del baipás.
    const lineId = own === null || edges.every((e) => e.line_id === own) ? own : lineKey(graph, edges[0]!)
    // Por una línea, la distancia es la diferencia de sus kilómetros (lo que vaya por un baipás suyo,
    // la de los kilómetros del baipás); un enlace trae la suya.
    let legLength = edges[0]!.length_km
    if (own !== null) {
      legLength = 0
      let runLine = own
      let runStart = group.start
      let here = group.start
      for (const [edge, next] of group.steps) {
        if (edge.line_id !== null && edge.line_id !== runLine) {
          const km = graph.lineKm.get(runLine)!
          legLength += Math.abs(km.get(here)! - km.get(runStart)!)
          runLine = edge.line_id
          runStart = here
        }
        here = next
      }
      const km = graph.lineKm.get(runLine)!
      legLength += Math.abs(km.get(here)! - km.get(runStart)!)
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
    line_ids: [...new Set(legs.flatMap((leg) => (leg.line_id !== null ? [leg.line_id] : [])))],
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
 * Lo que tienen en común los caminos que solo se distinguen por ir por un baipás o por lo que rodea:
 * la lista de sus tramos, con una misma marca en lugar de los tramos del baipás o de los de su línea
 * entre los dos nodos que el baipás une, cuando el camino los recorre de punta a punta.
 */
function bypassKey(graph: Graph, start: string, steps: Step[]): string {
  const spans = bypassSpans(graph)
  const edges = steps.map(([e]) => e)
  if (!spans.length) return edges.map((e) => e.id).join('|')
  const nodes = [start, ...steps.map(([, n]) => n)]
  const key: string[] = []
  let i = 0
  while (i < edges.length) {
    let whole: { mark: string; next: number } | null = null
    for (const { parent, a, b } of spans) {
      if ((nodes[i] !== a && nodes[i] !== b) || lineKey(graph, edges[i]!) !== parent) continue
      // hasta el otro nodo sin salir de la línea ni cambiar entre ella y el baipás
      const far = nodes[i] === a ? b : a
      let j = i
      while (j < edges.length && edges[j]!.line_id === edges[i]!.line_id && nodes[j + 1] !== far) j++
      if (j < edges.length && edges[j]!.line_id === edges[i]!.line_id) {
        whole = { mark: `~${parent}:${a}:${b}`, next: j + 1 }
        break
      }
    }
    if (whole === null) {
      key.push(edges[i]!.id)
      i++
    } else {
      key.push(whole.mark)
      i = whole.next
    }
  }
  return key.join('|')
}

/** De los caminos que solo cambian un baipás por lo que rodea, el primero (el más corto). */
function withoutBypassTwins(graph: Graph, ordered: { start: string; steps: Step[] }[]): { start: string; steps: Step[] }[] {
  const seen = new Set<string>()
  return ordered.filter((f) => {
    const key = `${f.start}|${bypassKey(graph, f.start, f.steps)}`
    if (seen.has(key)) return false
    seen.add(key)
    return true
  })
}

/**
 * Si un camino se aparta de otro más corto y da un rodeo desproporcionado hasta reencontrarlo. Se
 * quitan los tramos que los dos comparten al principio y al final y se compara lo que queda: el
 * camino se descarta si su parte propia mide más de `maxRatio` veces la del corto. Sin tramos
 * comunes es la comparación de las dos longitudes enteras, y vale igual en los dos sentidos.
 */
function strays(steps: Step[], shorter: Step[], maxRatio: number): boolean {
  const shared = Math.min(steps.length, shorter.length)
  let head = 0
  while (head < shared && steps[head]![0].id === shorter[head]![0].id) head++
  let tail = 0
  while (tail < shared - head && steps[steps.length - 1 - tail]![0].id === shorter[shorter.length - 1 - tail]![0].id) tail++
  let own = 0
  for (const [edge] of steps.slice(head, steps.length - tail)) own += edge.length_km
  let other = 0
  for (const [edge] of shorter.slice(head, shorter.length - tail)) other += edge.length_km
  return own > other * maxRatio
}

/**
 * Recorridos distintos entre dos nodos con la red del escenario, del más corto al más largo: los
 * caminos que no pasan dos veces por el mismo nodo, cambian de línea como mucho `maxChanges`
 * veces (`null`, sin tope) y no dan un rodeo de más de `maxRatio` veces respecto a otro más corto,
 * medido donde se apartan de él (`strays`; `null`, sin descartar ninguno por largo). Un baipás es
 * parte de su línea: de los caminos que solo se distinguen por ir por él o por la estación que rodea
 * queda el más corto, y cuenta como un recorrido.
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
  let ordered = withoutBypassTwins(g, sorted(found))
  if (maxRatio !== null) {
    const kept: typeof ordered = []
    for (const candidate of ordered) {
      if (!kept.some((shorter) => strays(candidate.steps, shorter.steps, maxRatio))) kept.push(candidate)
    }
    ordered = kept
  }
  return ordered.slice(0, MAX_ROUTES).map((f) => toRoute(g, f.start, f.steps))
}

/** Los tramos de la línea entre dos de sus nodos, en el sentido en que crecen sus kilómetros. */
function along(graph: Graph, lineId: string, a: string, b: string): Step[] {
  const km = graph.lineKm.get(lineId)!
  const lo = km.get(a)! - KM_TOLERANCE
  const hi = km.get(b)! + KM_TOLERANCE
  const steps: { at: number; step: Step }[] = []
  for (const edge of graph.edges) {
    if (edge.line_id !== lineId || !km.has(edge.a) || !km.has(edge.b)) continue
    const [near, far] = km.get(edge.a)! <= km.get(edge.b)! ? [edge.a, edge.b] : [edge.b, edge.a]
    if (km.get(near)! >= lo && km.get(far)! <= hi) steps.push({ at: km.get(near)!, step: [edge, far] })
  }
  return steps.sort((x, y) => x.at - y.at).map((s) => s.step)
}

/**
 * Rodeos que salvan el tramo `segmentId` cerrado, del más corto al más largo. Un rodeo sale de la
 * línea del tramo en un nodo situado antes del cierre, no vuelve a tocarla hasta un nodo situado
 * después y no usa ninguno de sus tramos. El resto del escenario se aplica también.
 *
 * Como en `findRoutes`, se descarta el rodeo desproporcionado respecto a otro más corto (`maxRatio`;
 * `null`, sin descartar ninguno). Para comparar dos rodeos que salen de la línea y vuelven a ella en
 * nodos distintos, se completa cada uno con los tramos de la propia línea hasta cubrir el mismo
 * trecho. El más corto se conserva siempre, y `omitted` cuenta los que se dejan fuera.
 */
export function closureDetours(
  graph: Graph,
  segmentId: string,
  scenario?: Scenario,
  maxRatio: number | null = DEFAULT_MAX_RATIO,
): ClosureDetours {
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
  const unique = withoutBypassTwins(g, sorted(found))
  let ordered = unique
  if (maxRatio !== null) {
    const whole = (f: { start: string; steps: Step[] }, first: string, last: string): Step[] => [
      ...along(graph, lineId, first, f.start),
      ...f.steps,
      ...along(graph, lineId, f.steps.at(-1)![1], last),
    ]
    const kept: typeof ordered = []
    for (const candidate of ordered) {
      const end = candidate.steps.at(-1)![1]
      const strayed = kept.some((shorter) => {
        const first = km.get(candidate.start)! <= km.get(shorter.start)! ? candidate.start : shorter.start
        const shorterEnd = shorter.steps.at(-1)![1]
        const last = km.get(end)! >= km.get(shorterEnd)! ? end : shorterEnd
        return strays(whole(candidate, first, last), whole(shorter, first, last), maxRatio)
      })
      if (!strayed) kept.push(candidate)
    }
    ordered = kept
  }
  const listed = ordered.slice(0, MAX_ROUTES)
  return {
    detours: listed.map((f) => ({ route: toRoute(g, f.start, f.steps), closed_line_length_km: round1(km.get(f.steps.at(-1)![1])! - km.get(f.start)!) })),
    omitted: unique.length - listed.length,
  }
}
