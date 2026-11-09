// Acceso a datos. El visor arranca siempre con la instantánea estática exportada por
// `oniel-data export snapshot` (mismo origen, en caché) y pasa a la API (VITE_API_URL, o el proxy
// /api en desarrollo) en cuanto /healthz responde. La API en Render duerme tras 15 minutos sin
// tráfico y tarda más de un minuto en despertar: por eso nunca se espera a ella para pintar la red.

import type {
  ClosureRequest,
  ClosureResult,
  CoverageOut,
  NetworkOut,
  NodeServicesOut,
  SegmentServicesOut,
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

export async function fetchNetwork(source: DataMode = currentMode()): Promise<NetworkOut> {
  return source === 'api' ? getJson(`${API_BASE}/api/network`) : getJson('/data/network.json')
}

export async function fetchCoverage(source: DataMode = currentMode()): Promise<CoverageOut> {
  return source === 'api' ? getJson(`${API_BASE}/api/coverage`) : getJson('/data/coverage.json')
}

export async function fetchSegmentCounts(
  date?: string,
  source: DataMode = currentMode(),
): Promise<{ date: string; counts: Record<string, number> }> {
  if (source === 'api') {
    const q = date ? `?date=${date}` : ''
    return getJson(`${API_BASE}/api/segment-counts${q}`)
  }
  return getJson('/data/segment-counts.json')
}

export async function fetchSegmentServices(segmentId: string, date?: string): Promise<SegmentServicesOut> {
  if (currentMode() === 'api') {
    const q = date ? `?date=${date}` : ''
    return getJson(`${API_BASE}/api/segments/${encodeURIComponent(segmentId)}/services${q}`)
  }
  return getJson(`/data/segments/${encodeURIComponent(segmentId.replaceAll(':', '--'))}.json`)
}

export async function fetchNodeServices(nodeId: string, date?: string): Promise<NodeServicesOut> {
  if (currentMode() === 'api') {
    const q = date ? `?date=${date}` : ''
    return getJson(`${API_BASE}/api/nodes/${encodeURIComponent(nodeId)}/services${q}`)
  }
  return getJson(`/data/nodes/${encodeURIComponent(nodeId)}.json`)
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
