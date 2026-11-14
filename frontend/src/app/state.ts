import type { LineSummary } from '../data/types.ts'
import { annotationLayer, layerByRoute } from './annotationLayers.ts'
import { scenarioFromCode } from '../routing/scenario.ts'

/** Lo seleccionado: un tramo, un nodo o una anotación con ficha propia (un proyecto), con su tipo. */
export type Selection = { type: 'tramo'; id: string } | { type: 'nodo'; id: string } | { type: 'anotacion'; kind: string; id: string } | null

export interface Route {
  selection: Selection
  simulacion: boolean
  /** Línea a la vista en el panel cuando no hay nada seleccionado; sin ella, la vista de la red. */
  linea?: string | null
  /** La página «Cobertura y fuentes» está abierta. */
  cobertura?: boolean
  /** Escenario abierto desde la URL, como cadena corta (`frontend/src/routing/scenario.ts`). */
  escenario?: string
  /** El comparador de recorridos está abierto, con las estaciones que ya se han elegido. */
  recorridos?: Comparador
  /** La vista «Tramos sin otro camino» está abierta. */
  sinOtroCamino?: boolean
  /** El glosario está abierto; con `entrada`, en ese término o concepto. */
  glosario?: { entrada: string | null }
}

/** Lo que va en la URL del comparador: las dos estaciones y, si lo hay, el escenario con el que se compara. */
export interface Comparador {
  from: string | null
  to: string | null
  escenario?: string
}

/**
 * Ruta en la dirección. Toda vista del visor tiene la suya, para poder compartir un enlace exacto:
 * / (la vista de la red), /linea/<id>, /tramo/<id>, /nodo/<id>, /tramo/<id>/cierre, /escenario/<cadena>,
 * /recorridos/<desde>/<hasta> (y, detrás, el escenario; «-» es una estación sin elegir), /glosario,
 * /glosario/<entrada>, /cobertura, /sin-otro-camino y, por cada tipo de anotación con ficha propia, la ruta que declara su capa
 * (/proyecto/<id>).
 *
 * `parseRoute` interpreta la ruta y `routePath` la construye: ninguna vista arma direcciones a mano.
 */
export function parseRoute(pathname: string): Route {
  const parts = pathname.split('/').filter(Boolean).map(decode)
  const [kind, id, action] = parts
  if ((kind === 'tramo' || kind === 'nodo') && id) {
    return { selection: { type: kind, id }, simulacion: kind === 'tramo' && action === 'cierre' }
  }
  const capa = kind ? layerByRoute(kind) : undefined
  if (capa && id) return { selection: { type: 'anotacion', kind: capa.kind, id }, simulacion: false }
  if (kind === 'linea' && id) return { selection: null, simulacion: false, linea: id }
  if (kind === 'cobertura') return { selection: null, simulacion: false, cobertura: true }
  if (kind === 'sin-otro-camino') return { selection: null, simulacion: false, sinOtroCamino: true }
  if (kind === 'glosario') return { selection: null, simulacion: false, glosario: { entrada: id ?? null } }
  if (kind === 'recorridos') {
    const end = (value: string | undefined) => (value && value !== '-' ? value : null)
    const escenario = parts[3]
    return { selection: null, simulacion: false, recorridos: { from: end(id), to: end(action), ...(escenario ? { escenario } : {}) } }
  }
  if (kind === 'escenario' && id) {
    // Un escenario que cierra un tramo abre la simulación de ese cierre; la URL lo conserva entero.
    try {
      const closed = scenarioFromCode(id).closures[0]
      if (closed) return { selection: { type: 'tramo', id: closed }, simulacion: true, escenario: id }
    } catch {
      /* cadena ilegible: se ignora */
    }
  }
  return { selection: null, simulacion: false }
}

/** Un trozo de la ruta tal y como se escribió; si no se puede descodificar (un «%» suelto), se deja como está. */
function decode(part: string): string {
  try {
    return decodeURIComponent(part)
  } catch {
    return part
  }
}

/**
 * Hasta noviembre de 2026 las rutas iban detrás de una almohadilla (`/#/tramo/<id>`). Esos enlaces siguen
 * valiendo: devuelve la ruta limpia que corresponde a ese hash, o nulo si el hash no es una ruta antigua
 * (por ejemplo `#panel`, el salto al contenido).
 */
export function legacyHashPath(hash: string): string | null {
  return hash.startsWith('#/') ? hash.slice(1) : null
}

/** Un identificador o un escenario en la URL, con los dos puntos y el punto y coma a la vista. */
function code(value: string): string {
  return encodeURIComponent(value).replace(/%3A/gi, ':').replace(/%3B/gi, ';')
}

export function routePath(route: Route): string {
  if (route.cobertura) return '/cobertura'
  if (route.glosario) return route.glosario.entrada ? `/glosario/${encodeURIComponent(route.glosario.entrada)}` : '/glosario'
  if (route.sinOtroCamino) return '/sin-otro-camino'
  if (route.recorridos) {
    const { from, to, escenario } = route.recorridos
    const parts = escenario ? [from ?? '-', to ?? '-', escenario] : to ? [from ?? '-', to] : from ? [from] : []
    return ['/recorridos', ...parts.map(code)].join('/')
  }
  if (!route.selection) return route.linea ? `/linea/${encodeURIComponent(route.linea)}` : '/'
  if (route.escenario && route.simulacion) return `/escenario/${code(route.escenario)}`
  if (route.selection.type === 'anotacion') {
    const ruta = annotationLayer(route.selection.kind)?.ruta
    return ruta ? `/${ruta}/${encodeURIComponent(route.selection.id)}` : '/'
  }
  const base = `/${route.selection.type}/${encodeURIComponent(route.selection.id).replace(/%3A/gi, ':')}`
  return route.simulacion && route.selection.type === 'tramo' ? `${base}/cierre` : base
}

/** El enlace a la ficha propia de una anotación; nulo si su tipo no la tiene. */
export function annotationHref(a: { kind: string; id: string }): string | null {
  if (!annotationLayer(a.kind)?.ruta) return null
  return routePath({ selection: { type: 'anotacion', kind: a.kind, id: a.id }, simulacion: false })
}

export function formatKm(km: number): string {
  return km.toLocaleString('es-ES', { minimumFractionDigits: 1, maximumFractionDigits: 1 })
}

/** Un recuento con el punto de los millares: 1170 → «1.170». */
export function formatCount(n: number): string {
  return n.toLocaleString('es-ES', { useGrouping: 'always', maximumFractionDigits: 0 })
}

/**
 * La línea de la que cuelga otra: la de un baipás (el de Zaragoza, el de Lleida) es la que rodea, y la
 * de un enlace entre dos líneas (el de Monforte del Cid), la que su especificación declara.
 */
export function parentOf(line: Pick<LineSummary, 'bypass_of' | 'link_of'>): string | null {
  return line.bypass_of ?? line.link_of ?? null
}

/**
 * Las líneas que se cuentan y se listan como tales. Un baipás o un enlace es parte de la línea de la
 * que cuelga: va bajo ella y no suma en el recuento de líneas.
 */
export function mainLines<L extends Pick<LineSummary, 'id' | 'bypass_of' | 'link_of'>>(lines: L[]): L[] {
  const ids = new Set(lines.map((l) => l.id))
  return lines.filter((l) => !ids.has(parentOf(l) ?? ''))
}

/** Los baipases y los enlaces que cuelgan de una línea, en el orden en que se recorren desde su origen. */
export function bypassesOf<L extends Pick<LineSummary, 'id' | 'bypass_of' | 'link_of' | 'sort_order'>>(lines: L[], lineId: string): L[] {
  return lines.filter((l) => parentOf(l) === lineId).sort((a, b) => a.sort_order - b.sort_order)
}

/** «3 líneas · 976 km»: el recuento de la red, igual de largo con tres líneas que con cien. */
export function networkCount(lines: LineSummary[]): string {
  const km = lines.reduce((sum, l) => sum + l.length_km, 0)
  const n = mainLines(lines).length
  return `${formatCount(n)} ${n === 1 ? 'línea' : 'líneas'} · ${formatCount(Math.round(km))} km`
}

/** Fecha de hoy como AAAA-MM-DD (en UTC, como el resto de fechas ISO que maneja la API). */
export function todayIso(): string {
  return new Date().toISOString().slice(0, 10)
}

export function formatDate(iso: string): string {
  const d = new Date(`${iso}T12:00:00`)
  return d.toLocaleDateString('es-ES', { weekday: 'long', day: 'numeric', month: 'long', year: 'numeric' })
}

/** Día y mes abreviados («13 nov»), para rótulos donde no cabe la fecha completa. */
export function formatDayShort(iso: string): string {
  const d = new Date(`${iso}T12:00:00`)
  return d.toLocaleDateString('es-ES', { day: 'numeric', month: 'short' }).replace('.', '')
}

/** Día, mes abreviado y año («8 nov 2026»), para fechar un dato en un renglón. */
export function formatDayShortYear(iso: string): string {
  const d = new Date(`${iso}T12:00:00`)
  return d.toLocaleDateString('es-ES', { day: 'numeric', month: 'short', year: 'numeric' }).replace('.', '')
}

export const KIND_LABEL: Record<string, string> = {
  estacion: 'Estación',
  paet: 'Puesto de adelantamiento y estacionamiento',
  pb: 'Puesto de banalización',
  bifurcacion: 'Bifurcación',
  cambiador: 'Cambiador de ancho',
  referencia: 'Punto de referencia',
}

const SHORT_STOP_NAMES: Record<string, string> = {
  'Madrid-Puerta de Atocha-Almudena Grandes': 'Madrid-Puerta de Atocha',
  'Madrid-Atocha Cercanías': 'Madrid-Atocha',
  'Córdoba-Julio Anguita': 'Córdoba',
  'Málaga María Zambrano': 'Málaga',
  // el fichero de Ouigo escribe los nombres sin tildes
  'Malaga Maria Zambrano': 'Málaga',
  'Cordoba-Central': 'Córdoba',
  'Villanueva de Córdoba-Los Pedroches': 'Villanueva de Córdoba',
  'Madrid-Chamartín-Clara Campoamor': 'Madrid-Chamartín',
  'Cuenca-Fernando Zóbel': 'Cuenca',
  'Albacete-Los Llanos': 'Albacete',
  'San Fernando-Bahía Sur': 'San Fernando',
  'Alicante/Alacant-Terminal': 'Alicante',
  'València-Estació del Nord': 'Valencia',
  'Campus Universitario de Rabanales': 'Rabanales',
  'Almuradiel-Viso del Marqués': 'Almuradiel',
}

/** Nombre corto de una parada para listas densas. */
export function shortStop(name: string | null | undefined): string {
  if (!name) return ''
  return SHORT_STOP_NAMES[name] ?? name
}

const PRODUCT_LABELS: Record<string, string> = {
  'REG.EXP.': 'Regional Exprés',
  PROXIMDAD: 'Proximidad',
  REGIONAL: 'Regional',
}

/** Nombre del producto comercial tal y como lo entiende un visitante. */
/** «Iryo», «Iryo y Ouigo», «Renfe, Iryo y Ouigo». */
export function listaEs(items: string[]): string {
  return new Intl.ListFormat('es', { style: 'long', type: 'conjunction' }).format(items)
}

export function productLabel(product: string): string {
  return PRODUCT_LABELS[product] ?? product
}

/** «Línea de alta velocidad Madrid – Sevilla» → «Madrid – Sevilla». */
export function lineLabel(line: LineSummary): string {
  return line.name.replace(/^Línea (de alta velocidad|convencional)\s+/i, '')
}

/** Etiqueta breve para listas: extremos y, si los hay, los puntos intermedios del nombre. */
export function lineShortLabel(line: LineSummary): string {
  const parts = lineLabel(line).split(' – ')
  if (parts.length <= 2) return parts.join(' – ')
  return `${parts[0]} – ${parts[parts.length - 1]} por ${parts.slice(1, -1).join(' y ')}`
}

export function lineKind(line: LineSummary): 'alta velocidad' | 'convencional' {
  return line.gauge_mm === 1435 || /alta velocidad/i.test(line.name) ? 'alta velocidad' : 'convencional'
}

export function gaugeLabel(gauge: number | null): string {
  if (gauge === 1435) return 'ancho estándar'
  if (gauge === 1668) return 'ancho ibérico'
  if (gauge === 1000) return 'ancho métrico'
  return gauge ? `ancho ${gauge} mm` : 'ancho sin dato'
}

export function tracksLabel(tracks: number | null): string {
  if (tracks === 1) return 'Vía única'
  if (tracks === 2) return 'Vía doble'
  if (tracks && tracks > 2) return `${tracks} vías`
  return 'sin dato'
}
