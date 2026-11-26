// Acceso a datos. El visor arranca siempre con la instantánea estática exportada por
// `oniel-data export snapshot` (mismo origen, en caché) y pasa a la API (VITE_API_URL, o el proxy
// /api en desarrollo) en cuanto /healthz responde. La API en Render duerme tras 15 minutos sin
// tráfico y tarda más de un minuto en despertar: por eso nunca se espera a ella para pintar la red.
//
// La red se carga por partes: al arrancar, solo el índice (líneas, nodos sin textos y geometría
// simplificada); el detalle de cada línea se pide al abrirla o al acercar el mapa a ella, y se
// guarda en memoria para no pedirlo dos veces.

import type {
  AlternativesOut,
  ClosureRequest,
  ClosureResult,
  CoverageOut,
  LineDetailOut,
  NetworkIndexOut,
  NodeServicesOut,
  SegmentServicesOut,
  ServiceHistoryOut,
} from './types'

export type DataMode = 'api' | 'estatico'
/** buscando: sondeo en curso; disponible: la API responde; ausente: sin API o agotados los intentos. */
export type ApiStatus = 'buscando' | 'disponible' | 'ausente'

const configured = import.meta.env.VITE_API_URL as string | undefined
const forceStatic = import.meta.env.VITE_DATA_MODE === 'estatico'
export const API_BASE = (configured ?? '').replace(/\/$/, '')

/** Cada intento de /healthz espera este tiempo; el proxy de Render retiene la petición mientras despierta. */
const WAKE_ATTEMPT_MS = 3_000
/** Espera total antes de dar la API por ausente. VITE_API_WAKE_MS la acorta en las pruebas. */
const WAKE_TOTAL_MS = Number(import.meta.env.VITE_API_WAKE_MS) || 150_000
/** Pausa entre intentos; la última se repite. */
const WAKE_DELAYS_MS = [2_000, 4_000, 8_000, 15_000]

let status: ApiStatus = forceStatic ? 'ausente' : 'buscando'
const listeners = new Set<(s: ApiStatus) => void>()

function setStatus(next: ApiStatus) {
  if (next === status) return
  status = next
  for (const listener of listeners) listener(next)
}

export function apiStatus(): ApiStatus {
  return status
}

/** Avisa de cada cambio de estado de la API; devuelve la función para darse de baja. */
export function onApiStatus(listener: (s: ApiStatus) => void): () => void {
  listeners.add(listener)
  return () => {
    listeners.delete(listener)
  }
}

export function currentMode(): DataMode {
  return status === 'disponible' ? 'api' : 'estatico'
}

export class ApiError extends Error {
  status: number
  constructor(message: string, status: number) {
    super(message)
    this.status = status
  }
}

async function getJson<T>(path: string, init?: RequestInit): Promise<T> {
  const res = await fetch(path, init)
  if (!res.ok) {
    let detail = res.statusText
    try {
      const body = (await res.json()) as { detail?: string }
      if (body.detail) detail = body.detail
    } catch {
      /* sin cuerpo */
    }
    throw new ApiError(detail, res.status)
  }
  return (await res.json()) as T
}

// El plazo cubre también la lectura del cuerpo si el servidor solo envía las cabeceras.
function readJson<T>(path: string): Promise<T> {
  return getJson<T>(path, { signal: AbortSignal.timeout(5_000) })
}

async function ping(timeoutMs: number): Promise<boolean> {
  try {
    const res = await fetch(`${API_BASE}/healthz`, { cache: 'no-store', signal: AbortSignal.timeout(timeoutMs) })
    return res.ok
  } catch {
    return false
  }
}

const sleep = (ms: number) => new Promise<void>((resolve) => setTimeout(resolve, ms))

let waking: Promise<ApiStatus> | null = null

/**
 * Despierta la API y resuelve con su estado final. Hay un solo sondeo por página: cada llamada
 * devuelve la misma promesa, así que la simulación puede esperar a él sin lanzar otro.
 */
export function wakeApi(): Promise<ApiStatus> {
  if (status !== 'buscando') return Promise.resolve(status)
  waking ??= (async () => {
    const started = Date.now()
    for (let attempt = 0; ; attempt++) {
      if (await ping(WAKE_ATTEMPT_MS)) {
        setStatus('disponible')
        return status
      }
      const delay = WAKE_DELAYS_MS[Math.min(attempt, WAKE_DELAYS_MS.length - 1)]!
      if (Date.now() - started + delay + WAKE_ATTEMPT_MS > WAKE_TOTAL_MS) break
      await sleep(delay)
    }
    setStatus('ausente')
    return status
  })()
  return waking
}

/** Nombre de fichero de un identificador en la instantánea: sin dos puntos, como lo escribe el exportador. */
function safeName(id: string): string {
  return encodeURIComponent(id.replaceAll(':', '--'))
}

export async function fetchIndex(source: DataMode = currentMode()): Promise<NetworkIndexOut> {
  return source === 'api' ? getJson(`${API_BASE}/api/lines`) : getJson('/data/index.json')
}

const lineCache = new Map<string, Promise<LineDetailOut>>()

function lineAt(path: string, date?: string): Promise<LineDetailOut> {
  let pending = lineCache.get(path)
  if (!pending) {
    pending = readJson<LineDetailOut>(path).then((detail) => date ? forDay(detail, date) : detail)
    lineCache.set(path, pending)
    pending.catch(() => lineCache.delete(path))
  }
  return pending
}

function forDay<T extends { date: string | null }>(data: T, date?: string): T {
  if (!data.date || (date && data.date !== date)) throw new Error('Horario sin la fecha solicitada.')
  return data
}

/** El trazado estático sirve incluso si sus recuentos son de otro día. La ficha comprueba su fecha. */
export function fetchLine(lineId: string, source: DataMode = currentMode(), date?: string): Promise<LineDetailOut> {
  const snapshot = () => lineAt(`/data/lines/${safeName(lineId)}.json`)
  if (source === 'estatico') return snapshot()
  const path = `${API_BASE}/api/lines/${encodeURIComponent(lineId)}${dayQuery(date)}`
  return lineAt(path, date).catch(snapshot)
}

export async function fetchCoverage(source: DataMode = currentMode()): Promise<CoverageOut> {
  return source === 'api' ? getJson(`${API_BASE}/api/coverage`) : getJson('/data/coverage.json')
}

function dayQuery(date?: string): string {
  return date ? `?date=${encodeURIComponent(date)}` : ''
}

const inFlight = new Map<string, Promise<unknown>>()

/** Comparte la consulta hasta que termine, incluido el respaldo. Al volver se prueba la API. */
function readWithSnapshot<T>(path: string, snapshot: string, read: (url: string) => Promise<T>): Promise<T> {
  const mode = currentMode()
  const key = mode + path
  const pending = inFlight.get(key)
  if (pending) return pending as Promise<T>
  const query = mode === 'api' ? read(API_BASE + path).catch(() => read(snapshot)) : read(snapshot)
  const result = query.finally(() => inFlight.delete(key))
  inFlight.set(key, result)
  return result
}

function snapshotName(kind: 'nodes' | 'segments', id: string) {
  return kind === 'nodes' ? encodeURIComponent(id) : safeName(id)
}

function services<T extends NodeServicesOut | SegmentServicesOut>(kind: 'nodes' | 'segments', id: string, date?: string): Promise<T> {
  const path = `/api/${kind}/${encodeURIComponent(id)}/services${dayQuery(date)}`
  return readWithSnapshot(path, `/data/${kind}/${snapshotName(kind, id)}.json`, async (url) => forDay(await readJson<T>(url), date))
}

export function fetchSegmentServices(segmentId: string, date?: string): Promise<SegmentServicesOut> {
  return services('segments', segmentId, date)
}

export function fetchNodeServices(nodeId: string, date?: string): Promise<NodeServicesOut> {
  return services('nodes', nodeId, date)
}

export function fetchHistory(kind: 'nodes' | 'segments', id: string): Promise<ServiceHistoryOut> {
  return readWithSnapshot(`/api/${kind}/${encodeURIComponent(id)}/history`, `/data/historico/${kind}/${snapshotName(kind, id)}.json`, readJson<ServiceHistoryOut>)
}

const alternativesCache = new Map<string, Promise<AlternativesOut>>()

/**
 * Trenes por tramo y si las líneas cargadas les ofrecen otro camino. No se pide al arrancar: solo
 * al abrir la ficha de un tramo o la vista «Tramos sin otro camino», y una vez por origen y día.
 */
export function fetchAlternatives(date?: string): Promise<AlternativesOut> {
  const mode = currentMode()
  const key = `${mode}:${date ?? ''}`
  let pending = alternativesCache.get(key)
  if (!pending) {
    // La instantánea ya lleva calculado su día de referencia. Una fecha explícita exige el mismo
    // día en cualquiera de los dos orígenes; los fallos se olvidan para poder volver a intentarlo.
    const forRequestedDay = (data: AlternativesOut) => {
      if (date && data.date !== date) throw new Error(`Falta el análisis de alternativas del ${date}.`)
      return data
    }
    pending = readJson<AlternativesOut>('/data/alternatives.json').then(forRequestedDay)
    if (mode === 'api') {
      const url = `${API_BASE}/api/alternatives${date ? `?date=${date}` : ''}`
      pending = pending.catch(() => readJson<AlternativesOut>(url).then(forRequestedDay))
    }
    alternativesCache.set(key, pending)
    pending.catch(() => alternativesCache.delete(key))
  }
  return pending
}

export async function simulateClosure(req: ClosureRequest): Promise<ClosureResult> {
  // Si la API aún está despertando, la simulación espera a que responda en vez de fallar.
  if ((await wakeApi()) !== 'disponible') {
    throw new ApiError('La simulación necesita el servidor de Oniel; esta vista previa solo muestra datos estáticos.', 503)
  }
  return getJson(`${API_BASE}/api/simulations/closure`, {
    method: 'POST',
    headers: { 'content-type': 'application/json' },
    body: JSON.stringify(req),
  })
}
