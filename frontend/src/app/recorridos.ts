// Comparador de recorridos: qué recorridos entre dos estaciones se enseñan, cuáles están cortados
// hoy, cómo se nombran y qué trenes directos sigue cada uno. El cálculo de los recorridos es el del
// grafo (`src/routing`), el mismo que hace el servidor; aquí solo se decide cómo se presentan. No
// usa la API: funciona igual con la instantánea estática. El método está en `docs/simulacion.md`,
// «Comparar recorridos».

import type { InterruptionOut, LineSummary, NodeCall, Route, SegmentOut } from '../data/types.ts'
import { findRoutes, type Graph } from '../routing/graph.ts'
import { ScenarioError, scenarioFromCode, scenarioToCode, withClosures, type Scenario } from '../routing/scenario.ts'
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
  /** «Por la alta velocidad», «Por Ciudad Real», «Por Córdoba y la línea convencional». */
  titulo: string
  /** «Invierte la marcha en Córdoba.», cuando las vías no le dejan girar y tiene que llegar a una estación y volver. */
  inversion: string | null
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
  /** Cierres y velocidades del escenario, en palabras, para decir con qué red se compara. Las vías supuestas van aparte. */
  escenario: string[]
  /**
   * Los recorridos que usarían una vía supuesta del escenario, del más corto al más largo. Cuando el
   * escenario trae alguna, `recorridos` son los de la red tal como está: lo que existe y lo que no
   * van en listas distintas.
   */
  supuestos: Recorrido[]
}

/** Recorridos por una vía supuesta que se enseñan. */
export const SUPUESTOS_A_LA_VISTA = 2

/** Un tramo del recorrido que es una vía supuesta del escenario y no un tramo de la red. */
export function esViaSupuesta(segmentId: string): boolean {
  return segmentId.startsWith('enlace:')
}

/** Distancia en línea recta entre dos puntos, en kilómetros: lo mínimo que mediría una vía entre ellos. */
export function lineaRecta(a: { lon: number; lat: number }, b: { lon: number; lat: number }): number {
  const rad = (g: number) => (g * Math.PI) / 180
  const h = Math.sin(rad(b.lat - a.lat) / 2) ** 2 + Math.cos(rad(a.lat)) * Math.cos(rad(b.lat)) * Math.sin(rad(b.lon - a.lon) / 2) ** 2
  return 2 * 6371.0088 * Math.asin(Math.sqrt(h))
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

/** «Recorre tres líneas», o «Recorre dos líneas y la vía supuesta»: la vía que no existe no cuenta como línea. */
function lineasDe(route: Route): string | null {
  const reales = route.legs.filter((leg) => leg.line_id).length
  const supuesta = reales < route.legs.length
  if (route.legs.length < 2) return null
  const n = `${NUMERO[reales] ?? reales} ${reales === 1 ? 'línea' : 'líneas'}`
  return supuesta ? `Recorre ${n} y la vía supuesta` : `Recorre ${n}`
}

/** Ciudades o estaciones que caben en el nombre de un recorrido. */
const NOMBRES_EN_EL_TITULO = 3

/** Como mucho `NOMBRES_EN_EL_TITULO`, repartidos por el recorrido: el primero, el último y los de en medio. */
function repartidos(nombres: string[]): string[] {
  if (nombres.length <= NOMBRES_EN_EL_TITULO) return nombres
  return Array.from({ length: NOMBRES_EN_EL_TITULO }, (_, i) => nombres[Math.round((i * (nombres.length - 1)) / (NOMBRES_EN_EL_TITULO - 1))]!)
}

/** «Por la alta velocidad» o «Por la línea convencional», según por dónde va la mayor parte del recorrido. */
function porTipoDeLinea(route: Route, lines: Map<string, LineSummary>): string {
  const largo = route.legs.reduce<Route['legs'][number] | undefined>((a, b) => (a && a.length_km >= b.length_km ? a : b), undefined)
  const line = largo?.line_id ? lines.get(largo.line_id) : undefined
  if (!line) return 'Por la vía supuesta'
  return lineKind(line) === 'alta velocidad' ? 'Por la alta velocidad' : 'Por la línea convencional'
}

/** Un nombre sin acentos ni signos, para comparar el de una estación con el de una ciudad. */
const llano = (texto: string) =>
  texto
    .normalize('NFD')
    .replace(/[\u0300-\u036f]/g, '')
    .toLowerCase()
    .replace(/[^a-z0-9]+/g, ' ')
    .trim()

/**
 * Pone nombre a los recorridos de una lista. El de una sola línea se llama por su tipo («Por la alta
 * velocidad»). El que encadena varias, por las ciudades por las que pasa: las de las zonas (las de
 * la lista de líneas) con estación en el recorrido y las estaciones en las que cambia de línea. De
 * ellas se quedan las que no están en todos los demás recorridos de la lista, que son las que lo
 * distinguen. Nunca se nombra por sus bifurcaciones: quien llega no sabe dónde están.
 */
function nombrar(recorridos: Recorrido[], graph: Graph, lines: Map<string, LineSummary>): void {
  const ciudades = [...new Set([...lines.values()].flatMap((l) => l.zone?.cities ?? []))].map((c) => ({ nombre: c, clave: llano(c) }))
  const ciudadDe = (nodeId: string): string | null => {
    const node = graph.nodes.get(nodeId)
    if (node?.kind !== 'estacion') return null
    const nombre = llano(node.name)
    return ciudades.find((c) => nombre.startsWith(c.clave))?.nombre ?? null
  }
  const pasos = recorridos.map(({ route }) => {
    if (route.legs.length < 2) return []
    const extremos = new Set([ciudadDe(route.from_node_id), ciudadDe(route.to_node_id)])
    const cambios = new Set(route.legs.slice(0, -1).map((leg) => leg.to_node_id))
    const hitos = route.node_ids.slice(1, -1).flatMap((id) => {
      const ciudad = ciudadDe(id)
      if (ciudad) return extremos.has(ciudad) ? [] : [ciudad]
      const node = graph.nodes.get(id)
      return cambios.has(id) && node?.kind === 'estacion' ? [shortStop(node.name)] : []
    })
    return [...new Set(hitos)]
  })
  recorridos.forEach((r, i) => {
    const mios = pasos[i]!
    const otros = pasos.filter((_, j) => j !== i)
    const propios = otros.length ? mios.filter((n) => !otros.every((o) => o.includes(n))) : mios
    const nombres = repartidos(propios.length ? propios : mios)
    r.titulo = nombres.length ? `Por ${enumerar(nombres)}` : porTipoDeLinea(r.route, lines)
  })
  // Dos recorridos con el mismo nombre se distinguen por el tipo de la línea que solo recorre uno.
  for (const r of recorridos) {
    const iguales = recorridos.filter((o) => o !== r && o.titulo === r.titulo)
    if (!iguales.length || !r.titulo.startsWith('Por ') || /^Por la (alta velocidad|línea convencional|vía supuesta)$/.test(r.titulo)) continue
    const propia = r.route.line_ids.find((id) => iguales.every((o) => !o.route.line_ids.includes(id)))
    const line = propia ? lines.get(propia) : undefined
    if (line) r.titulo += lineKind(line) === 'alta velocidad' ? ' y la alta velocidad' : ' y la línea convencional'
  }
  // Y dos de una sola línea del mismo tipo (dos líneas convencionales), por el nombre de su línea.
  for (const r of recorridos) {
    const line = r.route.legs.length === 1 && r.route.legs[0]?.line_id ? lines.get(r.route.legs[0].line_id) : undefined
    if (line && recorridos.some((o) => o !== r && o.titulo === r.titulo)) r.titulo = `Por la ${line.name.replace(/^Línea/, 'línea')}`
  }
}

/** «Invierte la marcha en Córdoba.», o nada si el recorrido no la invierte. */
function inversionDe(route: Route, graph: Graph): string | null {
  const donde = [...new Set(route.reverse_node_ids.map((id) => shortStop(graph.nodes.get(id)?.name)))].filter(Boolean)
  return donde.length ? `Invierte la marcha en ${enumerar(donde)}.` : null
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
    titulo: porTipoDeLinea(route, lines),
    inversion: inversionDe(route, graph),
    lineas: lineasDe(route),
    baipases: baipasesDe(route, graph, lines, segments),
    cortes: cortesDe(route),
    alternativa: false,
    tramosClave: tramosClave(route, segments, lines),
  })
  const recorridos = found.slice(0, RECORRIDOS_A_LA_VISTA).map(presentar)
  let sinPaso = false
  if (recorridos[0]?.cortes.length) {
    let libre = recorridos.find((r) => r.cortes.length === 0)
    // Se busca el más corto con la red de hoy, mida lo que mida. Hace falta también cuando alguno de
    // los que se enseñan no está cortado: puede haber otro más corto que no estaba a la vista, como el
    // que entra en una estación cuando su baipás está cerrado.
    const conocidos = new Set(graph.edges.map((e) => e.id))
    const hoy = withClosures(scenario, [...interrupted.keys()].filter((id) => conocidos.has(id)))
    const [route] = findRoutes(graph, from, to, hoy, undefined, null)
    if (route && (!libre || route.length_km < libre.route.length_km)) {
      const key = route.segment_ids.join('|')
      libre = recorridos.find((r) => r.key === key && r.cortes.length === 0)
      if (!libre) {
        libre = presentar(route)
        // en su sitio, del más corto al más largo
        const sitio = recorridos.findIndex((r) => r.route.length_km > route.length_km)
        recorridos.splice(sitio === -1 ? recorridos.length : sitio, 0, libre)
      }
    } else if (!libre) sinPaso = true
    if (libre) libre.alternativa = true
  }
  nombrar(recorridos, graph, lines)
  const escenario = [
    ...scenario.closures.map((id) => {
      const s = segments.get(id)
      return `cierre de ${s ? `${s.from_name} – ${s.to_name}` : id}`
    }),
    ...scenario.speeds.map((v) => {
      const s = segments.get(v.segment_id)
      return `${s ? `${s.from_name} – ${s.to_name}` : v.segment_id} a ${v.speed_kmh} km/h`
    }),
  ]
  // Con una vía supuesta, lo que existe se calcula aparte, sin ella: así no desplaza de la lista a
  // ningún recorrido de hoy, y los que la usarían se enseñan junto a ellos, no en su lugar.
  if (scenario.links.length) {
    const hoy = compararRecorridos(graph, network, from, to, interrupted, scenarioToCode({ ...scenario, links: [] }))
    const supuestos = found.filter((r) => r.segment_ids.some(esViaSupuesta)).slice(0, SUPUESTOS_A_LA_VISTA).map(presentar)
    nombrar(supuestos, graph, lines)
    return { ...hoy, escenarioIlegible: ilegible, escenario, supuestos }
  }
  return { recorridos, ocultos: Math.max(0, found.length - RECORRIDOS_A_LA_VISTA), sinPaso, escenarioIlegible: ilegible, escenario, supuestos: [] }
}

/**
 * Velocidad habitual de las líneas cargadas de cada tipo: la mediana de sus tramos, pesada por
 * kilómetros y redondeada a la decena. Es lo que el comparador propone para una vía supuesta.
 */
export function velocidadesHabituales(network: { lines: LineSummary[]; segments: SegmentOut[] }): { convencional: number; altaVelocidad: number } {
  const lines = new Map(network.lines.map((l) => [l.id, l]))
  const mediana = (tipo: ReturnType<typeof lineKind>, sinDato: number): number => {
    const tramos = network.segments
      .filter((s) => {
        const line = lines.get(s.line_id)
        return line && lineKind(line) === tipo && (s.typical_speed_kmh ?? s.max_speed_kmh)
      })
      .map((s) => [(s.typical_speed_kmh ?? s.max_speed_kmh)!, s.length_km] as const)
      .sort((a, b) => a[0] - b[0])
    const mitad = tramos.reduce((km, t) => km + t[1], 0) / 2
    let acumulado = 0
    for (const [kmh, km] of tramos) {
      acumulado += km
      if (acumulado >= mitad) return Math.round(kmh / 10) * 10
    }
    return sinDato
  }
  return { convencional: mediana('convencional', 160), altaVelocidad: mediana('alta velocidad', 300) }
}

/**
 * Lo que cambiaría con la vía supuesta respecto a hoy, en una o dos frases: el tiempo del recorrido
 * más rápido que la usa frente al más rápido de hoy, y los kilómetros del más corto frente al más
 * corto de hoy. Nulo si ningún recorrido la usa.
 */
export function diferenciaConSupuesto(hoy: Recorrido[], supuestos: Recorrido[]): string | null {
  const porTiempo = (lista: Recorrido[]) => lista.filter((r) => r.route.time_min !== null).sort((a, b) => a.route.time_min! - b.route.time_min!)[0]
  const porKm = (lista: Recorrido[]) => [...lista].sort((a, b) => a.route.length_km - b.route.length_km)[0]
  const corto = porKm(supuestos)
  if (!corto) return null
  const rapido = porTiempo(supuestos)
  const cortoHoy = porKm(hoy)
  const rapidoHoy = porTiempo(hoy)
  if (!cortoHoy) {
    const tiempo = rapido ? `, y el más rápido tardaría ${formatDuracion(rapido.route.time_min!)} sin paradas` : ''
    return `Hoy no hay ningún recorrido entre estas dos estaciones con las líneas cargadas. Con esta vía, el más corto mediría ${formatKm(corto.route.length_km)} km${tiempo}.`
  }
  const frases: string[] = []
  if (rapido && rapidoHoy) {
    const d = rapido.route.time_min! - rapidoHoy.route.time_min!
    const comparado = d === 0 ? 'lo mismo que' : `${formatDuracion(Math.abs(d))} ${d < 0 ? 'menos' : 'más'} que`
    const porDonde = rapidoHoy.titulo.replace(/^Por /, 'por ')
    frases.push(`El más rápido con esta vía tardaría ${formatDuracion(rapido.route.time_min!)} sin paradas: ${comparado} el más rápido de hoy (${formatDuracion(rapidoHoy.route.time_min!)}, ${porDonde}).`)
  }
  const k = corto.route.length_km - cortoHoy.route.length_km
  const comparado = Math.abs(k) < 0.05 ? 'lo mismo que' : `${formatKm(Math.abs(k))} km ${k < 0 ? 'menos' : 'más'} que`
  frases.push(`El más corto mediría ${formatKm(corto.route.length_km)} km: ${comparado} el más corto de hoy.`)
  return frases.join(' ')
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

/**
 * De los trenes directos, cuántos no siguen ninguno de los recorridos. El comparador solo conoce las
 * líneas cargadas: un tren que va, aunque sea en parte, por una vía que no lo está (la línea de Mérida
 * a Sevilla por Zafra, el enlace por el que los trenes de Madrid a Pamplona evitan Zaragoza) para en
 * las dos estaciones y no pasa por los tramos de ningún recorrido.
 */
export function trenesFueraDeLosRecorridos(recorridos: Recorrido[], trenes: TrenDirecto[], pasos: Map<string, Set<string>>): number {
  return trenes.filter((t) => !recorridos.some((r) => trenesDelRecorrido(r, [t], pasos).length > 0)).length
}

/** Lo anterior, en una frase para poner tras «Hay N trenes directos…»; nada si todos siguen algún recorrido. */
export function fraseTrenesFuera(fuera: number, directos: number, recorridos: number): string | null {
  if (fuera <= 0 || directos <= 0) return null
  const estos = recorridos === 1 ? 'este recorrido' : 'ninguno de estos recorridos'
  const porque = `${fuera === 1 ? 'sigue' : 'siguen'}, al menos en parte, una vía que Oniel no tiene cargada`
  if (fuera >= directos) {
    if (directos === 1) return `No va por ${estos}: ${porque}.`
    return recorridos === 1 ? `Ninguno va por este recorrido: ${porque}.` : `Ninguno va por estos recorridos: ${porque}.`
  }
  return `De ellos, ${fuera} no ${fuera === 1 ? 'va' : 'van'} por ${estos}: ${porque}.`
}
