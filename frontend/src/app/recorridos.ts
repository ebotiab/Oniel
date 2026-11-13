// Comparador de recorridos: qué recorridos entre dos estaciones se enseñan, cuáles están cortados
// hoy, cómo se nombran y qué trenes directos sigue cada uno. El cálculo de los recorridos es el del
// grafo (`src/routing`), el mismo que hace el servidor; aquí solo se decide cómo se presentan. No
// usa la API: funciona igual con la instantánea estática. El método está en `docs/simulacion.md`,
// «Comparar recorridos».

import type { InterruptionOut, LineSummary, NodeCall, Route, SegmentOut } from '../data/types.ts'
import { findRoutes, type Graph } from '../routing/graph.ts'
import { ScenarioError, scenarioFromCode, withClosures, type Scenario } from '../routing/scenario.ts'
import { formatKm, lineKind, parentOf, shortStop } from './state.ts'

/** Recorridos que se enseñan, del más corto al más largo. El grafo ya descarta los desproporcionados. */
export const RECORRIDOS_A_LA_VISTA = 3

/** Por qué un recorrido no se puede hacer entero: una interrupción real vigente o un cierre del escenario. */
export interface Corte {
  id: string
  from_name: string
  to_name: string
  /** La interrupción registrada; nula si el corte es un cierre hipotético del escenario. */
  interruption: InterruptionOut | null
}

export interface Recorrido {
  /** Clave estable del recorrido: los tramos que recorre. */
  key: string
  route: Route
  /** «Por la alta velocidad», «Por Manzanares y Ciudad Real», «Por Córdoba y la línea convencional». */
  titulo: string
  /** «Recorre tres líneas», cuando encadena más de una. */
  lineas: string | null
  /** Lo que el recorrido rodea por un baipás y cuánto más recorre el tren que entra en esas estaciones. */
  baipases: string | null
  cortes: Corte[]
  /** El más corto que no está cortado, cuando el más corto de todos sí lo está. */
  alternativa: boolean
  /** Primer y último tramo de cada trecho: un tren que pasa por todos sigue este recorrido. */
  tramosClave: string[]
}

export interface Comparacion {
  recorridos: Recorrido[]
  /** Los que el grafo encuentra y no se enseñan por pasar de `RECORRIDOS_A_LA_VISTA`. */
  ocultos: number
  /** Todos los recorridos a la vista están cortados y no hay otro que no lo esté. */
  sinPaso: boolean
  /** El escenario de la URL no se entiende o no encaja con la red: se ha ignorado. */
  escenarioIlegible: boolean
  /** Modificaciones del escenario, en palabras, para decir con qué red se compara. */
  escenario: string[]
}

const NUMERO = ['cero', 'una', 'dos', 'tres', 'cuatro', 'cinco', 'seis', 'siete', 'ocho']

/** «A», «A y B», «A, B y C». */
export function enumerar(nombres: string[]): string {
  if (nombres.length <= 1) return nombres.join('')
  return `${nombres.slice(0, -1).join(', ')} y ${nombres[nombres.length - 1]}`
}

/** Minutos como los dice un horario: «40 min», «1 h 21 min», «2 h». */
export function formatDuracion(minutos: number): string {
  const h = Math.floor(minutos / 60)
  const m = minutos % 60
  if (h === 0) return `${m} min`
  return m === 0 ? `${h} h` : `${h} h ${m} min`
}

/** Minutos entre dos horas «HH:MM» del mismo día. */
export function minutosEntre(desde: string, hasta: string): number {
  const aMinutos = (hora: string) => Number(hora.slice(0, 2)) * 60 + Number(hora.slice(3, 5))
  return aMinutos(hasta) - aMinutos(desde)
}

function leerEscenario(code: string | undefined): { scenario: Scenario; ilegible: boolean } {
  try {
    return { scenario: scenarioFromCode(code ?? ''), ilegible: false }
  } catch {
    return { scenario: scenarioFromCode(''), ilegible: true }
  }
}

/** El nombre de un recorrido: por dónde pasa de una línea a otra o, si es una sola, qué línea es. */
function titular(route: Route, lines: Map<string, LineSummary>): string {
  if (route.legs.length > 1) return `Por ${enumerar(route.legs.slice(0, -1).map((leg) => shortStop(leg.to_name)))}`
  const line = route.legs[0]?.line_id ? lines.get(route.legs[0].line_id) : undefined
  if (!line) return 'Por un enlace hipotético'
  return lineKind(line) === 'alta velocidad' ? 'Por la alta velocidad' : 'Por la línea convencional'
}

/**
 * Lo que un recorrido rodea por sus baipases, en una frase, o nada si no va por ninguno. Un baipás es
 * parte de su línea y el recorrido se mide por él; la frase dice qué estaciones deja a un lado y cuánto
 * más recorre el tren que para en ellas.
 */
function baipasesDe(route: Route, graph: Graph, lines: Map<string, LineSummary>, segments: Map<string, SegmentOut>): string | null {
  const suyos = new Set(route.segment_ids)
  const rodeados: string[] = []
  const estaciones: string[] = []
  let ahorro = 0
  for (const line of lines.values()) {
    const propios = [...segments.values()].filter((s) => s.line_id === line.id)
    if (!line.bypass_of || !propios.length || !propios.every((s) => suyos.has(s.id))) continue
    const km = graph.lineKm.get(line.id)
    const enLinea = graph.lineKm.get(line.bypass_of)
    if (!km || !enLinea) continue
    const extremos = [...km.keys()].filter((n) => enLinea.has(n)).sort((a, b) => enLinea.get(a)! - enLinea.get(b)!)
    const [a, b] = [extremos[0], extremos.at(-1)]
    if (!a || !b || a === b) continue
    rodeados.push(line.name.replace(/^Baipás de /, ''))
    ahorro += enLinea.get(b)! - enLinea.get(a)! - Math.abs(km.get(b)! - km.get(a)!)
    for (const [id, at] of [...enLinea].sort((x, y) => x[1] - y[1])) {
      const node = graph.nodes.get(id)
      if (node?.kind === 'estacion' && node.rank === 'principal' && at > enLinea.get(a)! && at < enLinea.get(b)!) estaciones.push(node.name)
    }
  }
  if (!rodeados.length) return null
  const rodea = `Rodea ${enumerar(rodeados)} por ${rodeados.length === 1 ? 'su baipás' : 'sus baipases'}`
  if (!estaciones.length) return `${rodea}.`
  return `${rodea}; el tren que para en ${enumerar(estaciones.map((e, i) => (i ? `en ${e}` : e)))} recorre ${formatKm(ahorro)} km más.`
}

/**
 * Primer y último tramo de cada trecho del recorrido. Un baipás o un enlace es parte de su línea: no abre trecho, y
 * así el tren que entra en la estación que el baipás rodea sigue contando en el recorrido.
 */
function tramosClave(route: Route, segments: Map<string, SegmentOut>, lines: Map<string, LineSummary>): string[] {
  const clave = new Set<string>()
  let anterior: string | null | undefined
  let ultimo: string | undefined
  for (const id of route.segment_ids) {
    // Un enlace hipotético no es un tramo de ninguna línea ni tiene trenes: cuenta como trecho propio.
    const propia = segments.get(id)?.line_id ?? null
    const lineId = propia === null ? null : (parentOf(lines.get(propia) ?? {}) ?? propia)
    if (lineId !== anterior || lineId === null) {
      if (ultimo) clave.add(ultimo)
      clave.add(id)
    }
    anterior = lineId
    ultimo = id
  }
  if (ultimo) clave.add(ultimo)
  return [...clave]
}

/**
 * Los recorridos que el comparador enseña entre dos nodos. Los cierres del escenario y las
 * interrupciones vigentes no quitan recorridos: los señalan como cortados, para que se vea cuál se
 * pierde y cuál queda. Los enlaces y las velocidades del escenario sí cambian la red.
 */
export function compararRecorridos(
  graph: Graph,
  network: { lines: LineSummary[]; segments: SegmentOut[] },
  from: string,
  to: string,
  interrupted: Map<string, InterruptionOut[]>,
  scenarioCode?: string,
): Comparacion {
  const leido = leerEscenario(scenarioCode)
  let { scenario } = leido
  let ilegible = leido.ilegible
  const lines = new Map(network.lines.map((l) => [l.id, l]))
  const segments = new Map(network.segments.map((s) => [s.id, s]))
  const base: Scenario = { ...scenario, closures: [] }
  let found: Route[]
  try {
    found = findRoutes(graph, from, to, base)
    // un cierre sobre un tramo que no existe hace el escenario inválido, como en el servidor
    for (const id of scenario.closures) if (!segments.has(id)) throw new ScenarioError(id)
  } catch (e) {
    if (!(e instanceof ScenarioError)) throw e
    scenario = scenarioFromCode('')
    ilegible = true
    found = findRoutes(graph, from, to)
  }
  const cerrados = new Set(scenario.closures)
  const cortesDe = (route: Route): Corte[] => {
    const cortes = new Map<string, Corte>()
    for (const id of route.segment_ids) {
      const s = segments.get(id)
      if (cerrados.has(id) && s) cortes.set(id, { id, from_name: s.from_name, to_name: s.to_name, interruption: null })
      for (const i of interrupted.get(id) ?? []) cortes.set(i.id, { id: i.id, from_name: i.from_name, to_name: i.to_name, interruption: i })
    }
    return [...cortes.values()]
  }
  const presentar = (route: Route): Recorrido => ({
    key: route.segment_ids.join('|'),
    route,
    titulo: titular(route, lines),
    lineas: route.legs.length > 1 ? `Recorre ${NUMERO[route.legs.length] ?? route.legs.length} líneas` : null,
    baipases: baipasesDe(route, graph, lines, segments),
    cortes: cortesDe(route),
    alternativa: false,
    tramosClave: tramosClave(route, segments, lines),
  })
  const recorridos = found.slice(0, RECORRIDOS_A_LA_VISTA).map(presentar)
  let sinPaso = false
  if (recorridos[0]?.cortes.length) {
    let libre = recorridos.find((r) => r.cortes.length === 0)
    if (!libre) {
      // Todos los que se enseñan están cortados: se busca el más corto con la red de hoy, mida lo que mida.
      const conocidos = new Set(graph.edges.map((e) => e.id))
      const hoy = withClosures(scenario, [...interrupted.keys()].filter((id) => conocidos.has(id)))
      const [route] = findRoutes(graph, from, to, hoy, undefined, null)
      if (route) {
        libre = presentar(route)
        recorridos.push(libre)
      } else sinPaso = true
    }
    if (libre) libre.alternativa = true
  }
  // Un recorrido que cambia de línea en estaciones por las que otro también pasa se confunde con él
  // («Por Córdoba», cuando los dos pasan por Córdoba): se le añade la línea que solo recorre él.
  for (const r of recorridos) {
    if (r.route.legs.length < 2) continue
    const cambios = r.route.legs.slice(0, -1).map((leg) => leg.to_node_id)
    const otro = recorridos.find((o) => o !== r && cambios.every((id) => o.route.node_ids.includes(id)))
    const propia = otro && r.route.line_ids.find((id) => !otro.route.line_ids.includes(id))
    const line = propia ? lines.get(propia) : undefined
    if (line) r.titulo += lineKind(line) === 'alta velocidad' ? ' y la alta velocidad' : ' y la línea convencional'
  }
  // Dos recorridos con el mismo nombre (dos líneas convencionales) se distinguen por su línea.
  for (const r of recorridos) {
    const line = r.route.legs.length === 1 && r.route.legs[0]?.line_id ? lines.get(r.route.legs[0].line_id) : undefined
    if (line && recorridos.some((o) => o !== r && o.titulo === r.titulo)) r.titulo = `Por la ${line.name.replace(/^Línea/, 'línea')}`
  }
  const nombre = (id: string) => graph.nodes.get(id)?.name ?? id
  const escenario = [
    ...scenario.closures.map((id) => {
      const s = segments.get(id)
      return `cierre de ${s ? `${s.from_name} – ${s.to_name}` : id}`
    }),
    ...scenario.links.map((k) => `enlace hipotético entre ${nombre(k.from_node_id)} y ${nombre(k.to_node_id)}`),
    ...scenario.speeds.map((v) => {
      const s = segments.get(v.segment_id)
      return `${s ? `${s.from_name} – ${s.to_name}` : v.segment_id} a ${v.speed_kmh} km/h`
    }),
  ]
  return { recorridos, ocultos: Math.max(0, found.length - RECORRIDOS_A_LA_VISTA), sinPaso, escenarioIlegible: ilegible, escenario }
}

/** Un tren que para en las dos estaciones, en ese orden. */
export interface TrenDirecto {
  service_id: string
  train_number: string
  product: string
  departure: string
  arrival: string
  minutes: number
}

/**
 * Trenes que paran en el origen y después en el destino, por hora de salida. No cuentan los que en
 * el origen solo dejan viajeros ni los que en el destino solo los recogen: es el mismo criterio de
 * los destinos directos de la ficha de una estación (`destinations_from_node` en el backend).
 */
export function trenesDirectos(enOrigen: NodeCall[], enDestino: NodeCall[]): TrenDirecto[] {
  const destino = new Map(enDestino.map((c) => [c.service_id, c]))
  const trenes: TrenDirecto[] = []
  for (const c of enOrigen) {
    const llegada = destino.get(c.service_id)
    if (c.boards === false || llegada?.alights === false) continue
    const departure = c.departure ?? c.arrival
    const arrival = llegada?.arrival ?? llegada?.departure
    if (!departure || !arrival) continue
    const minutes = minutosEntre(departure, arrival)
    if (minutes > 0) trenes.push({ service_id: c.service_id, train_number: c.train_number, product: c.product, departure, arrival, minutes })
  }
  return trenes.sort((a, b) => (a.departure < b.departure ? -1 : a.departure > b.departure ? 1 : 0))
}

/** De los trenes directos, los que siguen un recorrido: pasan por todos sus tramos clave. */
export function trenesDelRecorrido(recorrido: Recorrido, trenes: TrenDirecto[], pasos: Map<string, Set<string>>): TrenDirecto[] {
  return trenes.filter((t) => recorrido.tramosClave.every((id) => pasos.get(id)?.has(t.service_id)))
}
