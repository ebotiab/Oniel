import { readFileSync } from 'node:fs'

import type { AlternativesOut, CoverageOut, LineSummary, NetworkIndexOut, ZoneOut } from '../src/data/types.ts'

// Los totales de la red, leídos de la instantánea que el visor carga (frontend/public/data).
//
// Ninguna prueba escribe a mano un total de la red: cuántas líneas hay, cuántos kilómetros suman,
// cuántas tiene una zona, cuántos tramos o cuántos proyectos. Esos números cambian con cada línea
// que se añade, y una prueba que los lleva escritos falla por un cambio que no es suyo. La prueba
// que necesita uno lo pide aquí: sigue comprobando que el visor enseña lo que dicen los datos (que
// un baipás no cuenta como línea, que la zona dice cuántas tiene), y al añadir una línea no hay que
// tocarla. Lo que una prueba afirma con un número escrito es de su línea, de su estación o de su
// tramo, y solo cambia cuando cambia esa línea (CLAUDE.md, «Pruebas»).
//
// Las cuentas se hacen aquí aparte, sin llamar a las funciones del visor, para que sigan siendo
// una comprobación suya y no un espejo.

const leer = <T>(ruta: string) => JSON.parse(readFileSync(new URL(ruta, import.meta.url), 'utf-8')) as T

/** El índice de la red: líneas, nodos, tramos con la geometría simplificada y anotaciones. */
export const indice = leer<NetworkIndexOut>('../public/data/index.json')
/** «Cobertura y fuentes»: las cifras de la red, los operadores y las fuentes. */
export const cobertura = leer<CoverageOut>('../public/data/coverage.json')
/** El análisis de los tramos sin otro camino. */
export const alternativas = leer<AlternativesOut>('../public/data/alternatives.json')

const miles = (n: number) => String(Math.round(n)).replace(/\B(?=(\d{3})+$)/g, '.')
const escapar = (texto: string) => texto.replace(/[.*+?^${}()|[\]\\]/g, '\\$&')
const sinAcentos = (texto: string) =>
  texto
    .normalize('NFD')
    .replace(/[̀-ͯ]/g, '')
    .toLowerCase()

/** «1 línea», «4 líneas»: como lo dice la lista en la cabecera de cada zona. */
export const cuantasLineas = (n: number) => (n === 1 ? '1 línea' : `${miles(n)} líneas`)

/**
 * Las líneas que cuentan como tales y tienen su renglón en la lista: un baipás o un enlace cuelga de
 * la suya y no cuenta (docs/diseno.md, «Baipases» y «Enlaces entre líneas»).
 */
export const lineasDeLista: LineSummary[] = indice.lines.filter((l) => !l.bypass_of && !l.link_of)
/** Los baipases y enlaces, que van colgados de su línea. */
export const colgadas: LineSummary[] = indice.lines.filter((l) => l.bypass_of || l.link_of)

/** Kilómetros de toda la red, con los baipases y los enlaces sumados. */
export const kmDeLaRed = indice.lines.reduce((suma, l) => suma + l.length_km, 0)

/** El recuento con el que abre la vista de la red: «23 líneas · 4.754 km». */
export const recuentoDeLaRed = `${cuantasLineas(lineasDeLista.length)} · ${miles(kmDeLaRed)} km`
/** Lo mismo, como patrón para el principio de la ficha de la red. */
export const FICHA_RED = new RegExp(`^${escapar(recuentoDeLaRed)}`)
/** La segunda cifra de la ficha de la red: «145 estaciones». */
export const estacionesDeLaRed = `${miles(cobertura.station_count)} estaciones`

const esAltaVelocidad = (l: LineSummary) => l.gauge_mm === 1435 || /alta velocidad/i.test(l.name)

export interface ZonaDeLista {
  zona: ZoneOut
  /**
   * Las líneas que la lista enseña en la zona, en su orden: primero la alta velocidad y, en cada tipo, de la
   * más larga a la más corta. Son las suyas y las de otra zona que paran en una de sus ciudades.
   */
  lineas: LineSummary[]
  /** Las ciudades de la zona con estación en alguna de esas líneas: las que dice la zona cuando está plegada. */
  ciudades: string[]
}

/** Las estaciones por las que pasa cada línea, sin acentos: las suyas y las de otra línea que tocan sus tramos. */
const paradas: Map<string, Set<string>> = (() => {
  const nombre = new Map(indice.nodes.filter((n) => n.kind === 'estacion').map((n) => [n.id, sinAcentos(n.name)]))
  const out = new Map<string, Set<string>>()
  const anotar = (linea: string, texto: string | undefined) => {
    if (texto) out.set(linea, (out.get(linea) ?? new Set<string>()).add(texto))
  }
  for (const n of indice.nodes) anotar(n.line_id, nombre.get(n.id))
  for (const f of indice.segment_features.features) for (const id of [f.properties.from_node_id, f.properties.to_node_id]) anotar(String(f.properties.line_id), nombre.get(String(id)))
  return out
})()

/** Si una línea pasa por una ciudad: alguna de sus estaciones empieza por su nombre, o la línea la nombra. */
export const paraEn = (lineId: string, ciudad: string) => {
  const nombre = sinAcentos(indice.lines.find((l) => l.id === lineId)?.name ?? '').replace(/[^a-z0-9ñ]+/g, ' ')
  return [...(paradas.get(lineId) ?? [])].some((e) => e.startsWith(sinAcentos(ciudad))) || ` ${nombre} `.includes(` ${sinAcentos(ciudad)} `)
}

/**
 * Las zonas de la lista de líneas, de norte a sur, cada una con sus líneas y sus ciudades. Una línea está
 * en la zona que declara y en cada otra zona en la que para en una de sus ciudades (docs/diseno.md,
 * «Elegir línea»).
 */
export const zonas: ZonaDeLista[] = (() => {
  const porId = new Map<string, ZonaDeLista>()
  for (const linea of lineasDeLista) {
    if (!linea.zone) throw new Error(`La línea ${linea.id} no declara zona`)
    if (!porId.has(linea.zone.id)) porId.set(linea.zone.id, { zona: linea.zone, lineas: [], ciudades: [] })
  }
  for (const z of porId.values()) z.lineas = lineasDeLista.filter((l) => l.zone!.id === z.zona.id || z.zona.cities.some((c) => paraEn(l.id, c)))
  return [...porId.values()]
    .sort((a, b) => a.zona.sort_order - b.zona.sort_order)
    .map((z) => ({
      ...z,
      lineas: z.lineas.sort((a, b) => Number(esAltaVelocidad(b)) - Number(esAltaVelocidad(a)) || b.length_km - a.length_km),
      ciudades: z.zona.cities.filter((c) => z.lineas.some((l) => paraEn(l.id, c))),
    }))
})()

/** El identificador de prueba del renglón de una línea en una zona: el de otra zona lleva la zona detrás. */
export const renglonDe = (linea: LineSummary, zonaId: string) => (linea.zone?.id === zonaId ? `linea-${linea.id}` : `linea-${linea.id}--${zonaId}`)

/** Una zona de la lista, por su id (`zone.id` en la especificación de sus líneas). */
export function zona(id: string): ZonaDeLista {
  const z = zonas.find((x) => x.zona.id === id)
  if (!z) throw new Error(`No hay ninguna línea en la zona ${id}`)
  return z
}

/** La zona en la que la lista enseña una línea; la de un baipás o un enlace es la de la línea de la que cuelga. */
export function zonaDeLinea(lineId: string): string {
  const linea = indice.lines.find((l) => l.id === lineId)
  if (!linea) throw new Error(`La instantánea no tiene la línea ${lineId}`)
  const madre = indice.lines.find((l) => l.id === (linea.bypass_of ?? linea.link_of)) ?? linea
  if (!madre.zone) throw new Error(`La línea ${madre.id} no declara zona`)
  return madre.zone.id
}

/** El principio de la cabecera de una zona: «›Extremadura4 líneas». Con `extra`, las que una prueba le añade. */
export const cabeceraDeZona = (z: ZonaDeLista, extra = 0) => new RegExp(`^›${escapar(z.zona.name)}${escapar(cuantasLineas(z.lineas.length + extra))}(?!\\d)`)

/**
 * Cómo empieza la frase de «otro camino» en la ficha de un tramo, según el análisis de la instantánea:
 * «sus 55 trenes no tendrían otro camino», «sus 56 trenes tendrían otro camino» o «10 de sus 12 trenes
 * no tendrían otro camino». Que un tramo tenga otro camino depende de qué otras líneas hay cargadas,
 * y cuántos trenes lleva, de cuáles de ellos entran en la red: la prueba de una línea no lo escribe.
 */
export function fraseOtroCamino(segmentId: string): string {
  const s = alternativas.segments.find((x) => x.segment_id === segmentId)
  if (!s || s.trains < 2) throw new Error(`El análisis no tiene el tramo ${segmentId} con más de un tren`)
  if (s.without_alternative === s.trains) return `sus ${s.trains} trenes no tendrían otro camino`
  if (s.without_alternative === 0) return `sus ${s.trains} trenes tendrían otro camino`
  return `${s.without_alternative} de sus ${s.trains} trenes no tendría${s.without_alternative === 1 ? '' : 'n'} otro camino`
}

/** Una línea en «Tramos sin otro camino»: cuántos de sus tramos dejan a todos sus trenes sin él. */
export interface LineaSinOtroCamino {
  id: string
  /** Sus tramos sin otro camino, con los de sus baipases y enlaces. */
  tramos: number
  /** Los tramos de la línea, más los de sus baipases y enlaces que figuran. */
  total: number
  /** Los trenes del tramo que menos lleva y los del que más. */
  min: number
  max: number
}

/**
 * «Tramos sin otro camino», contado sobre el análisis de la instantánea: los tramos con trenes en los
 * que ninguno tendría otro camino, los demás tramos con trenes y un renglón por línea, de la que deja
 * a más trenes sin camino a la que menos (los tramos de un baipás o un enlace van con su línea).
 */
export const sinOtroCamino: { sin: number; con: number; lineas: LineaSinOtroCamino[] } = (() => {
  const lineaDe = new Map(indice.segment_features.features.map((f) => [String(f.id), f.properties.line_id]))
  const conTrenes = alternativas.segments.filter((s) => s.trains > 0)
  const sin = conTrenes.filter((s) => s.without_alternative === s.trains)
  const porLinea = new Map<string, { propios: number[]; colgados: number[] }>()
  for (const s of sin) {
    const propia = indice.lines.find((l) => l.id === lineaDe.get(s.segment_id))
    if (!propia) throw new Error(`El índice no tiene el tramo ${s.segment_id}`)
    const madre = propia.bypass_of ?? propia.link_of ?? propia.id
    const fila = porLinea.get(madre) ?? { propios: [], colgados: [] }
    ;(madre === propia.id ? fila.propios : fila.colgados).push(s.trains)
    porLinea.set(madre, fila)
  }
  const lineas = [...porLinea.entries()]
    .map(([id, { propios, colgados }]) => {
      const trenes = [...propios, ...colgados]
      return { id, tramos: trenes.length, total: indice.lines.find((l) => l.id === id)!.segment_count + colgados.length, min: Math.min(...trenes), max: Math.max(...trenes) }
    })
    .sort((a, b) => b.max - a.max || b.tramos - a.tramos)
  return { sin: sin.length, con: conTrenes.length - sin.length, lineas }
})()
