// Compone la red que usa el visor a partir del índice y de las líneas ya cargadas. Del índice
// salen todas las líneas, nodos y tramos (el grafo entero, para buscar, enlazar y calcular
// recorridos); de cada línea cargada, los textos de sus nodos y la geometría completa.

import type { Feature, LineDetailOut, NetworkIndexOut, NetworkOut, NodeOut } from './types'

export type LineDetails = Readonly<Record<string, LineDetailOut>>

export function composeNetwork(index: NetworkIndexOut, details: LineDetails): NetworkOut {
  const loaded = Object.values(details)
  // Un nodo común a varias líneas tiene los mismos textos en todas: basta con que una esté cargada.
  const full = new Map<string, NodeOut>()
  const geometry = new Map<string, GeoJSON.Geometry>()
  for (const d of loaded) {
    for (const n of d.nodes) full.set(n.id, n)
    for (const f of d.segment_features.features) geometry.set(f.id, f.geometry)
  }
  const nodes: NodeOut[] = index.nodes.map((n) => {
    const known = full.get(n.id)
    return { ...n, description: known?.description ?? null, details: known?.details ?? {} }
  })
  // Un nodo compartido aparece una vez por línea en `nodes` pero una sola vez en el mapa.
  const nodeFeatures: Feature[] = []
  const seen = new Set<string>()
  for (const n of index.nodes) {
    if (seen.has(n.id)) continue
    seen.add(n.id)
    const { id, ...properties } = n
    nodeFeatures.push({
      type: 'Feature',
      id,
      geometry: { type: 'Point', coordinates: [n.lon, n.lat] },
      properties: { ...properties, line_ids: index.nodes.filter((m) => m.id === id).map((m) => m.line_id) },
    })
  }
  return {
    lines: index.lines,
    nodes,
    segments: index.segment_features.features.map((f) => ({ id: f.id, ...f.properties })),
    connections: index.connections,
    // Mismo orden que el índice, con cualquier origen: el mapa numera los tramos por su posición.
    segment_features: {
      type: 'FeatureCollection',
      features: index.segment_features.features.map((f) => ({ ...f, geometry: geometry.get(f.id) ?? f.geometry })),
    },
    node_features: { type: 'FeatureCollection', features: nodeFeatures },
    connection_features: index.connection_features,
    interruptions: index.interruptions ?? [],
  }
}
