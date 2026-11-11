// Índice de búsqueda del visor: estaciones, otros puntos de la red y líneas, por nombre o por código de Adif.
// Se construye en el cliente a partir de network.json, así que funciona igual sin API.

import type { LineSummary, NetworkOut, NodeKind } from '../data/types'
import { formatKm, lineKind, lineLabel } from './state'

export type SearchTarget = { type: 'nodo'; id: string } | { type: 'linea'; id: string }

export interface SearchEntry {
  key: string
  target: SearchTarget
  name: string
  /** Segunda línea del resultado: qué es y dónde está, en palabras del visitante. */
  detail: string
  adifCode: string | null
  /** Las estaciones principales van antes que los apeaderos a igualdad de coincidencia. */
  weight: number
  words: string[]
  text: string
}

export interface SearchHit {
  entry: SearchEntry
  /** La consulta ha coincidido con el código de Adif y no con el nombre: el resultado lo enseña. */
  byCode: boolean
}

export type SearchScope = 'todo' | 'nodos'

const NODE_KIND: Record<NodeKind, string> = {
  estacion: 'Estación',
  paet: 'Puesto de adelantamiento (PAET)',
  pb: 'Puesto de banalización',
  bifurcacion: 'Bifurcación',
  cambiador: 'Cambiador de ancho',
  referencia: 'Punto de referencia',
}

/** Minúsculas, sin acentos ni signos: «Alcázar de San Juan» → «alcazar de san juan». */
export function normalize(text: string): string {
  return text
    .normalize('NFD')
    .replace(/[̀-ͯ]/g, '')
    .toLowerCase()
    .replace(/[^a-z0-9]+/g, ' ')
    .trim()
}

function joinNames(names: string[]): string {
  if (names.length <= 1) return names.join('')
  return `${names.slice(0, -1).join(', ')} y ${names[names.length - 1]}`
}

function lineEntry(line: LineSummary): SearchEntry {
  const text = normalize(line.name)
  return {
    key: `linea:${line.id}`,
    target: { type: 'linea', id: line.id },
    name: lineLabel(line),
    detail: `Línea ${lineKind(line) === 'alta velocidad' ? 'de alta velocidad' : 'convencional'} · ${formatKm(line.length_km)} km`,
    adifCode: null,
    weight: 0,
    words: text.split(' '),
    text,
  }
}

export function buildIndex(network: NetworkOut, scope: SearchScope = 'todo'): SearchEntry[] {
  const lineById = new Map(network.lines.map((l) => [l.id, l]))
  // Un nodo común a varias líneas aparece una vez por línea en network.nodes: aquí es un solo resultado.
  const nodes = new Map<string, SearchEntry & { lines: string[] }>()
  for (const n of network.nodes) {
    const line = lineById.get(n.line_id)
    const found = nodes.get(n.id)
    if (found) {
      if (line) found.lines.push(lineLabel(line))
      if (n.rank === 'principal') found.weight = 0
      continue
    }
    const text = normalize(n.name)
    nodes.set(n.id, {
      key: `nodo:${n.id}`,
      target: { type: 'nodo', id: n.id },
      name: n.name,
      detail: NODE_KIND[n.kind],
      adifCode: n.adif_code,
      weight: n.rank === 'principal' ? 0 : 1,
      words: text.split(' '),
      text,
      lines: line ? [lineLabel(line)] : [],
    })
  }
  const entries: SearchEntry[] = []
  for (const { lines, ...entry } of nodes.values()) {
    entries.push({ ...entry, detail: lines.length ? `${entry.detail} · ${joinNames(lines)}` : entry.detail })
  }
  if (scope === 'todo') for (const l of network.lines) entries.push(lineEntry(l))
  return entries
}

/** 0: el nombre empieza por la consulta; 1: alguna palabra empieza por ella; 2: la contiene; null: no coincide. */
function nameScore(entry: SearchEntry, tokens: string[], query: string): number | null {
  if (entry.text.startsWith(query)) return 0
  let score = 1
  for (const t of tokens) {
    if (entry.words.some((w) => w.startsWith(t))) continue
    if (!entry.text.includes(t)) return null
    score = 2
  }
  return score
}

/** Resultados ordenados: mejor coincidencia primero y, a igualdad, estaciones principales y orden alfabético. */
export function search(index: SearchEntry[], raw: string, limit = 8): SearchHit[] {
  const query = normalize(raw)
  if (!query) return []
  const tokens = query.split(' ')
  const isCode = /^\d+$/.test(query)
  const hits: { hit: SearchHit; score: number }[] = []
  for (const entry of index) {
    const byName = nameScore(entry, tokens, query)
    if (byName !== null) hits.push({ hit: { entry, byCode: false }, score: byName })
    else if (isCode && entry.adifCode?.startsWith(query)) hits.push({ hit: { entry, byCode: true }, score: entry.adifCode === query ? 0 : 1 })
  }
  hits.sort(
    (a, b) =>
      a.score - b.score ||
      a.hit.entry.weight - b.hit.entry.weight ||
      (a.hit.entry.target.type === b.hit.entry.target.type ? 0 : a.hit.entry.target.type === 'nodo' ? -1 : 1) ||
      a.hit.entry.name.localeCompare(b.hit.entry.name, 'es'),
  )
  return hits.slice(0, limit).map((h) => h.hit)
}
