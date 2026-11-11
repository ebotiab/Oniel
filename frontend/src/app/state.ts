import type { LineSummary } from '../data/types'

export type Selection = { type: 'tramo'; id: string } | { type: 'nodo'; id: string } | null

export interface Route {
  selection: Selection
  simulacion: boolean
  /** Línea a la vista en el panel cuando no hay nada seleccionado. */
  linea?: string | null
  /** El panel «Cobertura y fuentes» está abierto. */
  cobertura?: boolean
}

/**
 * Ruta en el hash. Toda vista del visor tiene la suya, para poder compartir un enlace exacto:
 * #/linea/<id>, #/tramo/<id>, #/nodo/<id>, #/tramo/<id>/cierre y #/cobertura.
 */
export function parseHash(hash: string): Route {
  const parts = hash.replace(/^#\/?/, '').split('/').filter(Boolean).map(decodeURIComponent)
  const [kind, id, action] = parts
  if ((kind === 'tramo' || kind === 'nodo') && id) {
    return { selection: { type: kind, id }, simulacion: kind === 'tramo' && action === 'cierre' }
  }
  if (kind === 'linea' && id) return { selection: null, simulacion: false, linea: id }
  if (kind === 'cobertura') return { selection: null, simulacion: false, cobertura: true }
  return { selection: null, simulacion: false }
}

export function toHash(route: Route): string {
  if (route.cobertura) return '#/cobertura'
  if (!route.selection) return route.linea ? `#/linea/${encodeURIComponent(route.linea)}` : '#/'
  const base = `#/${route.selection.type}/${encodeURIComponent(route.selection.id).replace(/%3A/gi, ':')}`
  return route.simulacion && route.selection.type === 'tramo' ? `${base}/cierre` : base
}

export function formatKm(km: number): string {
  return km.toLocaleString('es-ES', { minimumFractionDigits: 1, maximumFractionDigits: 1 })
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
export function productLabel(product: string): string {
  return PRODUCT_LABELS[product] ?? product
}

/** «Línea de alta velocidad Madrid – Sevilla» → «Madrid – Sevilla». */
export function lineLabel(line: LineSummary): string {
  return line.name.replace(/^Línea (de alta velocidad|convencional)\s+/i, '')
}

/** Etiqueta breve para pestañas: extremos y, si los hay, los puntos intermedios del nombre. */
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
