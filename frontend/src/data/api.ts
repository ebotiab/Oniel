// Acceso a datos. Con VITE_API_URL (o el proxy /api en desarrollo) habla con la API;
// sin ella, lee la instantánea estática exportada por `oniel-data export snapshot`.

import type {
  ClosureRequest,
  ClosureResult,
  CoverageOut,
  NetworkOut,
  NodeServicesOut,
  SegmentServicesOut,
} from './types'

export type DataMode = 'api' | 'estatico'

const configured = import.meta.env.VITE_API_URL as string | undefined
const forceStatic = import.meta.env.VITE_DATA_MODE === 'estatico'
export const API_BASE = (configured ?? '').replace(/\/$/, '')

let mode: DataMode | null = forceStatic ? 'estatico' : null

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

/** Averigua una sola vez si hay API; si no responde, pasa a modo estático. */
export async function detectMode(): Promise<DataMode> {
  if (mode) return mode
  try {
    await getJson<{ status: string }>(`${API_BASE}/healthz`)
    mode = 'api'
  } catch {
    mode = 'estatico'
  }
  return mode
}

export function currentMode(): DataMode {
  return mode ?? 'estatico'
}

export async function fetchNetwork(): Promise<NetworkOut> {
  return (await detectMode()) === 'api'
    ? getJson(`${API_BASE}/api/network`)
    : getJson('/data/network.json')
}

export async function fetchCoverage(): Promise<CoverageOut> {
  return (await detectMode()) === 'api'
    ? getJson(`${API_BASE}/api/coverage`)
    : getJson('/data/coverage.json')
}

export async function fetchSegmentCounts(date?: string): Promise<{ date: string; counts: Record<string, number> }> {
  if ((await detectMode()) === 'api') {
    const q = date ? `?date=${date}` : ''
    return getJson(`${API_BASE}/api/segment-counts${q}`)
  }
  return getJson('/data/segment-counts.json')
}

export async function fetchSegmentServices(segmentId: string, date?: string): Promise<SegmentServicesOut> {
  if ((await detectMode()) === 'api') {
    const q = date ? `?date=${date}` : ''
    return getJson(`${API_BASE}/api/segments/${encodeURIComponent(segmentId)}/services${q}`)
  }
  return getJson(`/data/segments/${encodeURIComponent(segmentId.replaceAll(':', '--'))}.json`)
}

export async function fetchNodeServices(nodeId: string, date?: string): Promise<NodeServicesOut> {
  if ((await detectMode()) === 'api') {
    const q = date ? `?date=${date}` : ''
    return getJson(`${API_BASE}/api/nodes/${encodeURIComponent(nodeId)}/services${q}`)
  }
  return getJson(`/data/nodes/${encodeURIComponent(nodeId)}.json`)
}

export async function simulateClosure(req: ClosureRequest): Promise<ClosureResult> {
  if ((await detectMode()) !== 'api') {
    throw new ApiError('La simulación necesita el servidor de Oniel; esta vista previa solo muestra datos estáticos.', 503)
  }
  return getJson(`${API_BASE}/api/simulations/closure`, {
    method: 'POST',
    headers: { 'content-type': 'application/json' },
    body: JSON.stringify(req),
  })
}
