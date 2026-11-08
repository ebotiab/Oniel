export type Selection = { type: 'tramo'; id: string } | { type: 'nodo'; id: string } | null

export interface Route {
  selection: Selection
  simulacion: boolean
}

/** Ruta en el hash: #/tramo/<id>, #/nodo/<id>, #/tramo/<id>/cierre */
export function parseHash(hash: string): Route {
  const parts = hash.replace(/^#\/?/, '').split('/').filter(Boolean).map(decodeURIComponent)
  const [kind, id, action] = parts
  if ((kind === 'tramo' || kind === 'nodo') && id) {
    return { selection: { type: kind, id }, simulacion: kind === 'tramo' && action === 'cierre' }
  }
  return { selection: null, simulacion: false }
}

export function toHash(route: Route): string {
  if (!route.selection) return '#/'
  const base = `#/${route.selection.type}/${encodeURIComponent(route.selection.id).replace(/%3A/gi, ':')}`
  return route.simulacion && route.selection.type === 'tramo' ? `${base}/cierre` : base
}

export function formatKm(km: number): string {
  return km.toLocaleString('es-ES', { minimumFractionDigits: 1, maximumFractionDigits: 1 })
}

export function formatDate(iso: string): string {
  const d = new Date(`${iso}T12:00:00`)
  return d.toLocaleDateString('es-ES', { weekday: 'long', day: 'numeric', month: 'long', year: 'numeric' })
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
  'Córdoba-Julio Anguita': 'Córdoba',
  'Málaga María Zambrano': 'Málaga',
  'Villanueva de Córdoba-Los Pedroches': 'Villanueva de Córdoba',
  'Madrid-Chamartín-Clara Campoamor': 'Madrid-Chamartín',
  'Cuenca-Fernando Zóbel': 'Cuenca',
  'Albacete-Los Llanos': 'Albacete',
  'San Fernando-Bahía Sur': 'San Fernando',
}

/** Nombre corto de una parada para listas densas. */
export function shortStop(name: string | null | undefined): string {
  if (!name) return ''
  return SHORT_STOP_NAMES[name] ?? name
}
