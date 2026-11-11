import {
  type GeoJSONSource,
  LngLatBounds,
  Map as MapLibreMap,
  NavigationControl,
  ScaleControl,
  type MapGeoJSONFeature,
  type MapMouseEvent,
  type StyleSpecification,
  setWorkerUrl,
} from 'maplibre-gl'
import workerUrl from 'maplibre-gl/dist/maplibre-gl-worker.mjs?url'
import 'maplibre-gl/dist/maplibre-gl.css'
import { useEffect, useRef } from 'react'

import type { InterruptionOut, NetworkOut } from '../data/types'
import type { Selection } from '../app/state'
import { lineKind } from '../app/state'
import { IBERIA_BOUNDS, SPAIN_BOUNDS } from './bounds'
import { CAPAS_DE_VIA, LAYER, SRC, TIPO_ALTA_VELOCIDAD, TIPO_CONVENCIONAL, onielLayers, opacidadDeVia, type Trazo } from './layers'
import baseStyle from './style/oniel-base.json'

interface Props {
  network: NetworkOut | null
  selection: Selection
  hoverId: string | null
  closedSegmentId: string | null
  /** Interrupciones vigentes hoy, por id de tramo: esos tramos se dibujan en rojo. */
  interrupted: Map<string, InterruptionOut[]>
  /** Trazo que resalta la leyenda: los demás se atenúan. */
  highlight?: Trazo | null
  onSelect: (sel: Selection) => void
  onHover: (id: string | null) => void
  /** Hueco (px) que ocupa el panel a la izquierda en escritorio o abajo en móvil. */
  padding: { left: number; bottom: number }
  /** Línea a la vista sin nada seleccionado: el mapa la encuadra. Sin ella, encuadra la red. */
  lineId?: string | null
}

// El worker de MapLibre se sirve como fichero propio para que funcione igual en desarrollo y en producción.
setWorkerUrl(workerUrl)

function shortName(name: string): string {
  return name
    .replace('Villanueva de Córdoba-Los Pedroches', 'Villanueva de Córdoba')
    .replace('Almuradiel-Viso del Marqués', 'Almuradiel')
    .replace('Campus Universitario de Rabanales', 'Rabanales')
    .replace('Bifurcación ', 'Bif. ')
}

/** Tipo de la línea de un tramo, para dibujar su trazo. */
function segmentKind(net: NetworkOut, lineId: unknown): string {
  const line = net.lines.find((l) => l.id === lineId)
  return line && lineKind(line) === 'alta velocidad' ? TIPO_ALTA_VELOCIDAD : TIPO_CONVENCIONAL
}

/** Asigna ids numéricos para feature-state y guarda la correspondencia. */
function withNumericIds<P extends Record<string, unknown>>(fc: { features: { id: string; geometry: GeoJSON.Geometry; properties: P }[] }) {
  const index = new Map<string, number>()
  const features = fc.features.map((f, i) => {
    index.set(f.id, i + 1)
    return { type: 'Feature' as const, id: i + 1, geometry: f.geometry, properties: { ...f.properties, oniel_id: f.id } }
  })
  return { data: { type: 'FeatureCollection' as const, features }, index }
}

export function MapView({ network, selection, hoverId, closedSegmentId, interrupted, highlight = null, onSelect, onHover, padding, lineId = null }: Props) {
  const containerRef = useRef<HTMLDivElement>(null)
  const mapRef = useRef<MapLibreMap | null>(null)
  const idsRef = useRef<{ segments: Map<string, number>; nodes: Map<string, number> }>({ segments: new Map(), nodes: new Map() })
  const readyRef = useRef(false)
  // Lo último que encuadró el mapa: 'red', una línea o una selección. De entrada, la red.
  const framedRef = useRef('red')
  const callbacks = useRef({ onSelect, onHover })
  callbacks.current = { onSelect, onHover }
  const networkRef = useRef<NetworkOut | null>(network)
  networkRef.current = network
  // Se deduce de la red, así que cambia a la vez que ella: addNetwork lo lee de aquí.
  const interruptedRef = useRef(interrupted)
  interruptedRef.current = interrupted
  const highlightRef = useRef(highlight)
  highlightRef.current = highlight
  const stateRef = useRef({ selection, hoverId, closedSegmentId })
  stateRef.current = { selection, hoverId, closedSegmentId }

  // Crear el mapa una sola vez
  useEffect(() => {
    if (!containerRef.current || mapRef.current) return
    const reduced = window.matchMedia('(prefers-reduced-motion: reduce)').matches
    const map = new MapLibreMap({
      container: containerRef.current,
      style: baseStyle as unknown as StyleSpecification,
      bounds: SPAIN_BOUNDS,
      fitBoundsOptions: { padding: { top: 70, right: 40, bottom: 40, left: padding.left + 40 } },
      // El mapa no sale de la península y sus vecinos: el lienzo entero se queda dentro de la caja,
      // así que el zoom mínimo efectivo depende de la pantalla (unos 5,8 en escritorio, 5,4 en móvil).
      maxBounds: IBERIA_BOUNDS,
      minZoom: 4.5,
      maxZoom: 15,
      // Siempre con el norte arriba y sin inclinar, como una hoja de mapa.
      dragRotate: false,
      pitchWithRotate: false,
      maxPitch: 0,
      attributionControl: { compact: true },
      fadeDuration: reduced ? 0 : 200,
    })
    map.touchZoomRotate.disableRotation()
    map.keyboard.disableRotation()
    map.addControl(new NavigationControl({ showCompass: false }), 'top-right')
    map.addControl(new ScaleControl({ unit: 'metric' }), 'bottom-right')
    map.on('load', () => {
      readyRef.current = true
      if (networkRef.current) addNetwork(map, networkRef.current)
    })
    mapRef.current = map
    if (import.meta.env.DEV) (window as unknown as { __onielMap?: MapLibreMap }).__onielMap = map
    map.on('error', (e) => console.error('[oniel mapa]', e.error?.message ?? e))
    return () => {
      map.remove()
      mapRef.current = null
      readyRef.current = false
    }
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [])

  // Cargar la red cuando llegue
  useEffect(() => {
    const map = mapRef.current
    if (!map || !network || !readyRef.current) return
    addNetwork(map, network)
  }, [network])

  function addNetwork(map: MapLibreMap, net: NetworkOut) {
    const segs = withNumericIds({
      features: net.segment_features.features.map((f) => ({
        ...f,
        properties: {
          ...f.properties,
          tipo: segmentKind(net, f.properties.line_id),
          vias: f.properties.tracks === 1 ? 1 : 2,
          interrumpido: interruptedRef.current.has(f.id),
        },
      })),
    })
    const nodes = withNumericIds({
      features: net.node_features.features.map((f) => ({
        ...f,
        properties: { ...f.properties, short_name: shortName(String(f.properties.name)) },
      })),
    })
    const conns = withNumericIds(net.connection_features)
    idsRef.current = { segments: segs.index, nodes: nodes.index }
    const existing = map.getSource(SRC.segments) as GeoJSONSource | undefined
    if (existing) {
      // La red ya está dibujada (la instantánea); la de la API la sustituye sin recrear capas ni eventos.
      existing.setData(segs.data)
      ;(map.getSource(SRC.nodes) as GeoJSONSource).setData(nodes.data)
      ;(map.getSource(SRC.connections) as GeoJSONSource).setData(conns.data)
      applyStates(map)
      return
    }
    map.addSource(SRC.segments, { type: 'geojson', data: segs.data })
    map.addSource(SRC.nodes, { type: 'geojson', data: nodes.data })
    map.addSource(SRC.connections, { type: 'geojson', data: conns.data })
    for (const layer of onielLayers()) {
      try {
        map.addLayer(layer)
      } catch (err) {
        console.error('[oniel mapa] no se pudo añadir la capa', layer.id, err)
      }
    }

    const pick = (features: MapGeoJSONFeature[]): string | null => {
      const f = features[0]
      return f ? String(f.properties.oniel_id) : null
    }
    map.on('click', (e: MapMouseEvent) => {
      const nodeHits = map.queryRenderedFeatures(e.point, { layers: [LAYER.nodesStations, LAYER.nodesMinor] })
      const nodeId = pick(nodeHits)
      if (nodeId) return callbacks.current.onSelect({ type: 'nodo', id: nodeId })
      const segHits = map.queryRenderedFeatures(e.point, { layers: [LAYER.segmentsHit] })
      const segId = pick(segHits)
      if (segId) return callbacks.current.onSelect({ type: 'tramo', id: segId })
      callbacks.current.onSelect(null)
    })
    map.on('mousemove', (e: MapMouseEvent) => {
      const hits = map.queryRenderedFeatures(e.point, { layers: [LAYER.nodesStations, LAYER.nodesMinor, LAYER.segmentsHit] })
      const id = pick(hits)
      map.getCanvas().style.cursor = id ? 'pointer' : ''
      const segHit = hits.find((h: MapGeoJSONFeature) => h.layer.id === LAYER.segmentsHit)
      callbacks.current.onHover(segHit ? String(segHit.properties.oniel_id) : null)
    })
    map.on('mouseout', () => callbacks.current.onHover(null))
    applyStates(map)
    applyHighlight(map)
  }

  function applyHighlight(map: MapLibreMap) {
    const opacity = opacidadDeVia(highlightRef.current)
    for (const id of CAPAS_DE_VIA) if (map.getLayer(id)) map.setPaintProperty(id, 'line-opacity', opacity)
  }

  // Resaltar el trazo que señala la leyenda
  useEffect(() => {
    const map = mapRef.current
    if (!map || !map.getSource(SRC.segments)) return
    applyHighlight(map)
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [highlight])

  function applyStates(map: MapLibreMap) {
    const { selection, hoverId, closedSegmentId } = stateRef.current
    const { segments, nodes } = idsRef.current
    for (const [id, fid] of segments) {
      map.setFeatureState(
        { source: SRC.segments, id: fid },
        {
          seleccionado: selection?.type === 'tramo' && selection.id === id,
          hover: hoverId === id,
          cerrado: closedSegmentId === id,
        },
      )
    }
    for (const [id, fid] of nodes) {
      map.setFeatureState({ source: SRC.nodes, id: fid }, { seleccionado: selection?.type === 'nodo' && selection.id === id })
    }
  }

  // Estados visuales
  useEffect(() => {
    const map = mapRef.current
    if (!map || !map.getSource(SRC.segments)) return
    applyStates(map)
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [selection, hoverId, closedSegmentId])

  // Encuadrar la selección
  useEffect(() => {
    const map = mapRef.current
    if (!map || !network) return
    const reduced = window.matchMedia('(prefers-reduced-motion: reduce)').matches
    const pad = { top: 80, right: 60, bottom: padding.bottom + 40, left: padding.left + 60 }
    if (!selection) {
      const key = lineId ? `linea:${lineId}` : 'red'
      if (framedRef.current === key) return
      framedRef.current = key
      const b = new LngLatBounds()
      if (lineId)
        for (const f of network.segment_features.features)
          if (f.properties.line_id === lineId && f.geometry.type === 'LineString') for (const c of f.geometry.coordinates) b.extend([c[0]!, c[1]!])
      map.fitBounds(b.isEmpty() ? SPAIN_BOUNDS : b, { padding: pad, maxZoom: 10, duration: reduced ? 0 : 700 })
      return
    }
    framedRef.current = `${selection.type}:${selection.id}`
    if (selection.type === 'tramo') {
      const f = network.segment_features.features.find((x) => x.id === selection.id)
      if (!f || f.geometry.type !== 'LineString') return
      const b = new LngLatBounds()
      for (const c of f.geometry.coordinates) b.extend([c[0]!, c[1]!])
      map.fitBounds(b, { padding: pad, maxZoom: 10, duration: reduced ? 0 : 700 })
    } else {
      const n = network.nodes.find((x) => x.id === selection.id)
      if (!n) return
      // offset desplaza el punto hacia el centro del hueco que deja el panel
      map.easeTo({
        center: [n.lon, n.lat],
        zoom: Math.max(map.getZoom(), 9),
        offset: [padding.left / 2, -padding.bottom / 2],
        duration: reduced ? 0 : 700,
      })
    }
  }, [selection, lineId, network, padding.left, padding.bottom])

  return <div ref={containerRef} className="mapa" role="region" aria-label="Mapa de la red ferroviaria" data-testid="mapa" data-resaltado={highlight ?? undefined} />
}
