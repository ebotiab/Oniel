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
import { useEffect, useRef } from 'react'

import { CAPAS_CON_TRAZO, dibujoDe } from '../app/annotationLayers'
import type { AnnotationOut, NetworkOut } from '../data/types'
import type { Selection } from '../app/state'
import { lineKind } from '../app/state'
import { IBERIA_BOUNDS, SPAIN_BOUNDS } from './bounds'
import { CAPAS_DE_VIA, LAYER, OPACIDAD_RECORRIDOS, SRC, TIPO_ALTA_VELOCIDAD, TIPO_CONVENCIONAL, onielLayers, opacidadDeVia, type Trazo } from './layers'
import baseStyle from './style/oniel-base.json'

interface Props {
  network: NetworkOut | null
  selection: Selection
  hoverId: string | null
  closedSegmentId: string | null
  /** Anotaciones vigentes hoy, por id de tramo: sus tramos se dibujan como diga la capa de su tipo. */
  annotated: Map<string, AnnotationOut[]>
  /** Anotaciones vigentes hoy: las que tienen geometría propia se dibujan como diga su capa. */
  annotations: AnnotationOut[]
  /** Trazo que resalta la leyenda: los demás se atenúan. */
  highlight?: Trazo | null
  /** Trazo que la leyenda pide encuadrar al fijarlo; `n` cambia en cada petición para repetir el encuadre. */
  frame?: { trazo: Trazo; n: number } | null
  onSelect: (sel: Selection) => void
  onHover: (id: string | null) => void
  /** Líneas con algún tramo a la vista cuando el mapa está cerca: conviene tener su geometría completa. */
  onNearLines?: (lineIds: string[]) => void
  /** Hueco (px) que ocupa el panel a la izquierda en escritorio o abajo en móvil. */
  padding: { left: number; bottom: number }
  /** Línea a la vista sin nada seleccionado: el mapa la encuadra. Sin ella, encuadra la red. */
  lineId?: string | null
  /** Comparador de recorridos abierto: qué se resalta. Nulo fuera del comparador. */
  recorridos?: RecorridosEnMapa | null
}

/** Lo que el comparador de recorridos pinta en el mapa, por ids de tramo y de nodo. */
export interface RecorridosEnMapa {
  /** Tramos de todos los recorridos a la vista: el resto de la red se atenúa. */
  todos: string[]
  /** Tramos del recorrido elegido: van en el azul de la selección. */
  elegido: string[]
  /** Las estaciones elegidas. */
  extremos: string[]
}

/**
 * A partir de este zoom el mapa pide el detalle de las líneas que tiene a la vista. Más lejos basta
 * la geometría simplificada del índice: su tolerancia (200 m) queda por debajo de un píxel.
 */
const ZOOM_DETALLE = 8
/** El mismo ancho con el que `App` pasa a la composición de móvil. */
const MOVIL = '(max-width: 760px)'

type Caja = [number, number, number, number]

/** Caja de cada tramo (oeste, sur, este, norte) con su línea, para saber qué líneas hay a la vista. */
function segmentBoxes(net: NetworkOut): { lineId: string; box: Caja }[] {
  const out: { lineId: string; box: Caja }[] = []
  for (const f of net.segment_features.features) {
    if (f.geometry.type !== 'LineString') continue
    const box: Caja = [Infinity, Infinity, -Infinity, -Infinity]
    for (const c of f.geometry.coordinates) {
      box[0] = Math.min(box[0], c[0]!)
      box[1] = Math.min(box[1], c[1]!)
      box[2] = Math.max(box[2], c[0]!)
      box[3] = Math.max(box[3], c[1]!)
    }
    out.push({ lineId: String(f.properties.line_id), box })
  }
  return out
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

/**
 * Márgenes para encuadrar algo en lo que el panel deja a la vista. En el móvil (panel abajo) son más
 * justos: el hueco es pequeño y, con poco zoom, el límite sur del mapa impide subir lo encuadrado.
 */
function framePadding(padding: { left: number; bottom: number }) {
  return padding.left === 0
    ? { top: 64, right: 24, bottom: padding.bottom + 12, left: 24 }
    : { top: 80, right: 60, bottom: padding.bottom + 40, left: padding.left + 60 }
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

export function MapView({ network, selection, hoverId, closedSegmentId, annotated, annotations, highlight = null, frame = null, onSelect, onHover, onNearLines, padding, lineId = null, recorridos = null }: Props) {
  const containerRef = useRef<HTMLDivElement>(null)
  const mapRef = useRef<MapLibreMap | null>(null)
  const idsRef = useRef<{ segments: Map<string, number>; nodes: Map<string, number>; annotations: Map<string, number> }>({ segments: new Map(), nodes: new Map(), annotations: new Map() })
  const readyRef = useRef(false)
  // Lo último que encuadró el mapa: 'red', una línea o una selección. De entrada, la red.
  const framedRef = useRef('red')
  const callbacks = useRef({ onSelect, onHover, onNearLines })
  callbacks.current = { onSelect, onHover, onNearLines }
  const boxesRef = useRef<{ lineId: string; box: Caja }[]>([])
  const networkRef = useRef<NetworkOut | null>(network)
  networkRef.current = network
  // Se deduce de la red, así que cambia a la vez que ella: addNetwork lo lee de aquí.
  const annotatedRef = useRef(annotated)
  annotatedRef.current = annotated
  const annotationsRef = useRef(annotations)
  annotationsRef.current = annotations
  const highlightRef = useRef(highlight)
  highlightRef.current = highlight
  const stateRef = useRef({ selection, hoverId, closedSegmentId, recorridos })
  stateRef.current = { selection, hoverId, closedSegmentId, recorridos }

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
    // La red se añade en cuanto el estilo está listo ('style.load'), sin esperar a 'load', que no salta
    // hasta que llegan las teselas y los rótulos del mapa base: con una conexión lenta eran varios segundos.
    map.once('style.load', () => {
      readyRef.current = true
      if (networkRef.current) addNetwork(map, networkRef.current)
    })
    map.on('moveend', () => reportNearLines(map))
    mapRef.current = map
    if (import.meta.env.DEV) (window as unknown as { __onielMap?: MapLibreMap }).__onielMap = map
    map.on('error', (e) => console.error('[oniel mapa]', e.error?.message ?? e))
    // En el móvil la atribución desplegada ocupa un renglón entero de un mapa muy bajo. MapLibre la pliega al
    // arrastrar el mapa; aquí se pliega con cualquier toque fuera de ella, también en el panel. Queda tras el
    // botón «i» y en «Cobertura y fuentes».
    const fold = (event: PointerEvent) => {
      if (!window.matchMedia(MOVIL).matches) return
      const attrib = map.getContainer().querySelector('.maplibregl-ctrl-attrib')
      if (attrib && !(event.target instanceof Node && attrib.contains(event.target))) attrib.classList.remove('maplibregl-compact-show')
    }
    window.addEventListener('pointerdown', fold)
    return () => {
      window.removeEventListener('pointerdown', fold)
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

  /** Avisa de las líneas con algún tramo dentro del encuadre cuando el mapa está lo bastante cerca. */
  function reportNearLines(map: MapLibreMap) {
    if (map.getZoom() < ZOOM_DETALLE || !callbacks.current.onNearLines) return
    const view = map.getBounds()
    const [w, s, e, n] = [view.getWest(), view.getSouth(), view.getEast(), view.getNorth()]
    const near = new Set<string>()
    for (const { lineId, box } of boxesRef.current) if (box[0] <= e && box[2] >= w && box[1] <= n && box[3] >= s) near.add(lineId)
    if (near.size) callbacks.current.onNearLines([...near])
  }

  function addNetwork(map: MapLibreMap, net: NetworkOut) {
    boxesRef.current = segmentBoxes(net)
    // Cada capa con trazo marca sus tramos con su propiedad (`interrumpido`, la de las interrupciones).
    const marcas = (id: string) => {
      const kinds = new Set(annotatedRef.current.get(id)?.map((a) => a.kind))
      return Object.fromEntries(CAPAS_CON_TRAZO.map((capa) => [capa.propiedad, kinds.has(capa.kind)]))
    }
    const segs = withNumericIds({
      features: net.segment_features.features.map((f) => ({
        ...f,
        properties: {
          ...f.properties,
          tipo: segmentKind(net, f.properties.line_id),
          vias: f.properties.tracks === 1 ? 1 : 2,
          ...marcas(f.id),
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
    // Las anotaciones con geometría propia y capa que las dibuje: una línea de puntos o de trazos con su nombre.
    const notes = withNumericIds({
      features: annotationsRef.current.flatMap((a) => {
        const dibujo = dibujoDe(a)
        return dibujo && a.geometry ? [{ id: a.id, geometry: a.geometry, properties: { kind: a.kind, dibujo, name: a.title ?? '' } }] : []
      }),
    })
    idsRef.current = { segments: segs.index, nodes: nodes.index, annotations: notes.index }
    const existing = map.getSource(SRC.segments) as GeoJSONSource | undefined
    if (existing) {
      // La red ya está dibujada: la geometría completa de una línea recién cargada, o la red de la API,
      // sustituyen a lo anterior sin recrear capas ni eventos.
      existing.setData(segs.data)
      ;(map.getSource(SRC.nodes) as GeoJSONSource).setData(nodes.data)
      ;(map.getSource(SRC.connections) as GeoJSONSource).setData(conns.data)
      ;(map.getSource(SRC.annotations) as GeoJSONSource).setData(notes.data)
      applyStates(map)
      reportNearLines(map)
      return
    }
    map.addSource(SRC.segments, { type: 'geojson', data: segs.data })
    map.addSource(SRC.nodes, { type: 'geojson', data: nodes.data })
    map.addSource(SRC.connections, { type: 'geojson', data: conns.data })
    map.addSource(SRC.annotations, { type: 'geojson', data: notes.data })
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
      // Debajo de la vía: una anotación con geometría propia solo se toca donde no hay red cargada.
      const note = map.queryRenderedFeatures(e.point, { layers: [LAYER.annotationsHit] })[0]
      if (note) return callbacks.current.onSelect({ type: 'anotacion', kind: String(note.properties.kind), id: String(note.properties.oniel_id) })
      callbacks.current.onSelect(null)
    })
    map.on('mousemove', (e: MapMouseEvent) => {
      const hits = map.queryRenderedFeatures(e.point, { layers: [LAYER.nodesStations, LAYER.nodesMinor, LAYER.segmentsHit, LAYER.annotationsHit] })
      const id = pick(hits)
      map.getCanvas().style.cursor = id ? 'pointer' : ''
      const segHit = hits.find((h: MapGeoJSONFeature) => h.layer.id === LAYER.segmentsHit)
      callbacks.current.onHover(segHit ? String(segHit.properties.oniel_id) : null)
    })
    map.on('mouseout', () => callbacks.current.onHover(null))
    applyStates(map)
    applyHighlight(map)
    reportNearLines(map)
  }

  function applyHighlight(map: MapLibreMap) {
    // Comparando recorridos manda el comparador: la leyenda no atenúa otra vez lo que ya está atenuado.
    const opacity = stateRef.current.recorridos?.todos.length ? OPACIDAD_RECORRIDOS : opacidadDeVia(highlightRef.current)
    for (const id of CAPAS_DE_VIA) if (map.getLayer(id)) map.setPaintProperty(id, 'line-opacity', opacity)
  }

  // Resaltar el trazo que señala la leyenda
  useEffect(() => {
    const map = mapRef.current
    if (!map || !map.getSource(SRC.segments)) return
    applyHighlight(map)
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [highlight, recorridos])

  function applyStates(map: MapLibreMap) {
    const { selection, hoverId, closedSegmentId, recorridos } = stateRef.current
    const { segments, nodes, annotations: notes } = idsRef.current
    const enRecorrido = new Set(recorridos?.todos)
    const elegido = new Set(recorridos?.elegido)
    const extremos = new Set(recorridos?.extremos)
    for (const [id, fid] of segments) {
      map.setFeatureState(
        { source: SRC.segments, id: fid },
        {
          seleccionado: selection?.type === 'tramo' && selection.id === id,
          hover: hoverId === id,
          cerrado: closedSegmentId === id,
          recorrido: enRecorrido.has(id),
          elegido: elegido.has(id),
        },
      )
    }
    for (const [id, fid] of notes) {
      map.setFeatureState({ source: SRC.annotations, id: fid }, { seleccionado: selection?.type === 'anotacion' && selection.id === id })
    }
    for (const [id, fid] of nodes) {
      map.setFeatureState({ source: SRC.nodes, id: fid }, { seleccionado: (selection?.type === 'nodo' && selection.id === id) || extremos.has(id) })
    }
  }

  // Estados visuales
  useEffect(() => {
    const map = mapRef.current
    if (!map || !map.getSource(SRC.segments)) return
    applyStates(map)
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [selection, hoverId, closedSegmentId, recorridos])

  // Encuadrar la selección. La red se lee de la referencia: que llegue el detalle de una línea cambia
  // la red, pero no debe volver a mover el mapa.
  const hasNetwork = network !== null
  const recorridosKey = recorridos ? recorridos.todos.join('|') : null
  useEffect(() => {
    const map = mapRef.current
    const network = networkRef.current
    if (!map || !network) return
    const reduced = window.matchMedia('(prefers-reduced-motion: reduce)').matches
    const pad = framePadding({ left: padding.left, bottom: padding.bottom })
    // Al pasar de móvil a escritorio el margen cambia antes de que MapLibre haya medido el lienzo nuevo:
    // con el ancho antiguo el margen del panel no cabe y el encuadre se descarta. Se mide antes de encuadrar.
    const caja = map.getContainer()
    const lienzo = map.getCanvas()
    if (caja.clientWidth !== lienzo.clientWidth || caja.clientHeight !== lienzo.clientHeight) map.resize()
    if (!selection && recorridosKey !== null) {
      // Comparando recorridos, el mapa encuadra los que se enseñan; mientras se eligen estaciones, no se mueve.
      const ids = new Set(stateRef.current.recorridos?.todos)
      if (!ids.size || framedRef.current === `recorridos:${recorridosKey}`) return
      framedRef.current = `recorridos:${recorridosKey}`
      const b = new LngLatBounds()
      for (const f of network.segment_features.features)
        if (ids.has(f.id) && f.geometry.type === 'LineString') for (const c of f.geometry.coordinates) b.extend([c[0]!, c[1]!])
      if (!b.isEmpty()) map.fitBounds(b, { padding: pad, maxZoom: 10, duration: reduced ? 0 : 700 })
      return
    }
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
    if (selection.type === 'anotacion') {
      // Una anotación se encuadra entera: su geometría propia o, si va de nodo a nodo, sus tramos.
      const a = annotationsRef.current.find((x) => x.id === selection.id)
      if (!a) return
      const b = new LngLatBounds()
      const extend = (coords: unknown): void => {
        if (!Array.isArray(coords)) return
        if (typeof coords[0] === 'number' && typeof coords[1] === 'number') b.extend([coords[0], coords[1]])
        else for (const part of coords) extend(part)
      }
      if (a.geometry && 'coordinates' in a.geometry) extend(a.geometry.coordinates)
      const ids = new Set(a.segment_ids)
      for (const f of network.segment_features.features) if (ids.has(f.id) && 'coordinates' in f.geometry) extend(f.geometry.coordinates)
      const n = a.node_id ? network.nodes.find((x) => x.id === a.node_id) : undefined
      if (n) b.extend([n.lon, n.lat])
      if (!b.isEmpty()) map.fitBounds(b, { padding: pad, maxZoom: 10, duration: reduced ? 0 : 700 })
      return
    }
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
  }, [selection, lineId, recorridosKey, hasNetwork, padding.left, padding.bottom])

  // Encuadrar el trazo que se fija en la leyenda: todos los tramos de ese tipo, en toda la red.
  useEffect(() => {
    const map = mapRef.current
    const network = networkRef.current
    if (!map || !network || !frame) return
    const b = new LngLatBounds()
    for (const f of network.segment_features.features) {
      if (f.geometry.type !== 'LineString') continue
      const unica = f.properties.tracks === 1
      const tipo = unica ? 'via-unica' : segmentKind(network, f.properties.line_id)
      if (tipo === frame.trazo) for (const c of f.geometry.coordinates) b.extend([c[0]!, c[1]!])
    }
    if (b.isEmpty()) return
    const reduced = window.matchMedia('(prefers-reduced-motion: reduce)').matches
    framedRef.current = `trazo:${frame.trazo}`
    map.fitBounds(b, { padding: framePadding(padding), maxZoom: 10, duration: reduced ? 0 : 700 })
    // Solo al pedirlo: que cambie el hueco del panel no vuelve a mover el mapa.
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [frame])

  return <div ref={containerRef} className="mapa" role="region" aria-label="Mapa de la red ferroviaria" data-testid="mapa" data-resaltado={highlight ?? undefined} data-recorrido-elegido={recorridos?.elegido.length || undefined} />
}
