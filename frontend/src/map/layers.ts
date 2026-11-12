// Capas de Oniel sobre el mapa base. La vía es tinta; el color solo marca estados.
// El dibujo y el grosor del trazo dicen qué vía es: alta velocidad (gruesa, con un filete claro en el
// centro), convencional (trazos blancos) y vía única (fina, con los trazos más espaciados).

import type { ExpressionSpecification, LayerSpecification } from 'maplibre-gl'

import { CAPAS_CON_TRAZO } from '../app/annotationLayers'
import { AZUL, PAPEL, ROJA, TINTA, TINTA_3 } from './colors'

export { AZUL, PAPEL, ROJA, TINTA, TINTA_3 }

export const SRC = {
  segments: 'oniel-segments',
  nodes: 'oniel-nodes',
  connections: 'oniel-connections',
} as const

export const LAYER = {
  connections: 'oniel-connections',
  connectionLabels: 'oniel-connection-labels',
  segmentsCasing: 'oniel-segments-casing',
  segmentsHalo: 'oniel-segments-halo',
  segments: 'oniel-segments',
  segmentsTicks: 'oniel-segments-ticks',
  segmentsTicksSingle: 'oniel-segments-ticks-unica',
  segmentsFillet: 'oniel-segments-filete',
  segmentsHit: 'oniel-segments-hit',
  nodesMinor: 'oniel-nodes-minor',
  nodesStations: 'oniel-nodes-stations',
  nodeLabels: 'oniel-node-labels',
  nodeLabelsSecondary: 'oniel-node-labels-secondary',
} as const

/** Tipo de línea de un tramo (propiedad `tipo`) y número de vías (propiedad `vias`). */
export const TIPO_ALTA_VELOCIDAD = 'alta-velocidad'
export const TIPO_CONVENCIONAL = 'convencional'

/** Los tres trazos que distingue el mapa; la vía única manda sobre el tipo de línea. */
export type Trazo = 'alta-velocidad' | 'convencional' | 'via-unica'

/** Factor de grosor de cada trazo: a zoom 5 son 4,2 px, 2,55 px y 1,5 px. */
export const GROSOR: Record<Trazo, number> = { 'alta-velocidad': 1.4, convencional: 0.85, 'via-unica': 0.5 }

const isStation: ExpressionSpecification = ['==', ['get', 'kind'], 'estacion']
const isSecondary: ExpressionSpecification = ['==', ['get', 'rank'], 'secundario']
const altaVelocidad: ExpressionSpecification = ['==', ['get', 'tipo'], TIPO_ALTA_VELOCIDAD]
const viaUnica: ExpressionSpecification = ['==', ['get', 'vias'], 1]
const emphasised: ExpressionSpecification = [
  'any',
  ['boolean', ['feature-state', 'seleccionado'], false],
  ['boolean', ['feature-state', 'cerrado'], false],
]

/**
 * Tramo con una anotación vigente hoy de un tipo con trazo propio. Cada capa del registro marca
 * sus tramos con una propiedad (no un estado): `interrumpido` la de las interrupciones.
 */
const marcado = (propiedad: string): ExpressionSpecification => ['boolean', ['get', propiedad], false]
/** Por cada capa con trazo, su condición y el valor que le toca; van seguidos dentro de un `case`. */
const porCapa = (valor: (capa: (typeof CAPAS_CON_TRAZO)[number]) => string | number) =>
  CAPAS_CON_TRAZO.flatMap((capa) => [marcado(capa.propiedad), valor(capa)])

// El rojo es «sin circulación»: real (interrupción vigente) o simulada (cierre). Un tramo
// interrumpido sigue en rojo cuando se selecciona; la selección la marcan el grosor y el halo azul.
const segmentColor = [
  'case',
  ['boolean', ['feature-state', 'cerrado'], false],
  ROJA,
  ...porCapa((capa) => capa.color),
  ['boolean', ['feature-state', 'seleccionado'], false],
  AZUL,
  ['boolean', ['feature-state', 'elegido'], false],
  AZUL,
  TINTA,
] as ExpressionSpecification

const haloColor = [
  'case',
  ['boolean', ['feature-state', 'cerrado'], false],
  ROJA,
  ['boolean', ['feature-state', 'seleccionado'], false],
  AZUL,
  ['boolean', ['feature-state', 'elegido'], false],
  AZUL,
  ...porCapa((capa) => capa.color),
  TINTA,
] as ExpressionSpecification

/** Opacidad del halo de un tramo seleccionado: más marcada si además lleva una anotación con trazo. */
const haloSeleccionado = ['case', ...porCapa((capa) => capa.haloSeleccionado), 0.16] as ExpressionSpecification

const esAltaVelocidad: ExpressionSpecification = ['all', altaVelocidad, ['!', viaUnica]]
const esConvencional: ExpressionSpecification = ['all', ['!', altaVelocidad], ['!', viaUnica]]
const factor: ExpressionSpecification = ['case', viaUnica, GROSOR['via-unica'], altaVelocidad, GROSOR['alta-velocidad'], GROSOR.convencional]

/** Grosor que crece con el zoom y se multiplica por el factor de la vía. */
function weighted(low: number, high: number, lowEmph: number, highEmph: number): ExpressionSpecification {
  return [
    'interpolate',
    ['linear'],
    ['zoom'],
    5,
    ['*', ['case', emphasised, lowEmph, low], factor],
    12,
    ['*', ['case', emphasised, highEmph, high], factor],
  ]
}

/** Capas que dibujan la vía y se atenúan cuando la leyenda resalta un trazo. */
export const CAPAS_DE_VIA = [LAYER.segments, LAYER.segmentsTicks, LAYER.segmentsTicksSingle, LAYER.segmentsFillet] as const

/** Opacidad de la vía: entera, o con el trazo resaltado entero y los demás atenuados. */
export function opacidadDeVia(resaltado: Trazo | null): ExpressionSpecification | number {
  if (!resaltado) return 1
  const es = resaltado === 'via-unica' ? viaUnica : resaltado === 'alta-velocidad' ? esAltaVelocidad : esConvencional
  return ['case', es, 1, 0.18]
}

/**
 * Opacidad de la vía mientras se comparan recorridos: los tramos de los recorridos a la vista,
 * enteros; el resto de la red, atenuado. El elegido lo dicen el azul y el halo de la selección.
 */
export const OPACIDAD_RECORRIDOS: ExpressionSpecification = ['case', ['boolean', ['feature-state', 'recorrido'], false], 1, 0.18]

export function onielLayers(): LayerSpecification[] {
  return [
    {
      id: LAYER.connections,
      type: 'line',
      source: SRC.connections,
      paint: { 'line-color': TINTA_3, 'line-width': 1.8, 'line-dasharray': [2, 2.6] },
      layout: { 'line-cap': 'round' },
    },
    {
      id: LAYER.connectionLabels,
      type: 'symbol',
      source: SRC.connections,
      minzoom: 6,
      layout: {
        'symbol-placement': 'line',
        'text-field': ['get', 'name'],
        'text-font': ['Noto Sans Regular'],
        'text-size': 10.5,
        'text-max-angle': 30,
      },
      paint: { 'text-color': '#6B7470', 'text-halo-color': PAPEL, 'text-halo-width': 1.6 },
    },
    {
      id: LAYER.segmentsHalo,
      type: 'line',
      source: SRC.segments,
      paint: {
        'line-color': haloColor,
        'line-width': ['interpolate', ['linear'], ['zoom'], 5, 10, 10, 18],
        'line-opacity': [
          'case',
          ['boolean', ['feature-state', 'cerrado'], false],
          0.2,
          ['boolean', ['feature-state', 'seleccionado'], false],
          haloSeleccionado,
          ['boolean', ['feature-state', 'elegido'], false],
          0.16,
          ['boolean', ['feature-state', 'hover'], false],
          0.1,
          0,
        ],
      },
      layout: { 'line-cap': 'round', 'line-join': 'round' },
    },
    {
      id: LAYER.segmentsCasing,
      type: 'line',
      source: SRC.segments,
      paint: { 'line-color': PAPEL, 'line-width': weighted(6.5, 10, 6.5, 10) },
      layout: { 'line-cap': 'round', 'line-join': 'round' },
    },
    {
      id: LAYER.segments,
      type: 'line',
      source: SRC.segments,
      paint: {
        'line-color': segmentColor,
        'line-width': weighted(3, 5, 4.5, 7),
      },
      layout: { 'line-cap': 'round', 'line-join': 'round' },
    },
    // Línea convencional de vía doble: los trazos blancos clásicos.
    {
      id: LAYER.segmentsTicks,
      type: 'line',
      source: SRC.segments,
      filter: esConvencional,
      paint: { 'line-color': PAPEL, 'line-width': weighted(1.4, 2.2, 1.4, 2.2), 'line-dasharray': [0.5, 3.2] },
    },
    // Vía única: los mismos trazos, más espaciados.
    {
      id: LAYER.segmentsTicksSingle,
      type: 'line',
      source: SRC.segments,
      filter: viaUnica,
      paint: { 'line-color': PAPEL, 'line-width': weighted(1.4, 2.2, 1.4, 2.2), 'line-dasharray': [0.5, 9] },
    },
    // Alta velocidad: un filete claro continuo por el centro.
    {
      id: LAYER.segmentsFillet,
      type: 'line',
      source: SRC.segments,
      filter: esAltaVelocidad,
      paint: { 'line-color': PAPEL, 'line-width': weighted(0.95, 1.6, 1.1, 1.8) },
      layout: { 'line-cap': 'round', 'line-join': 'round' },
    },
    {
      id: LAYER.segmentsHit,
      type: 'line',
      source: SRC.segments,
      paint: { 'line-color': TINTA, 'line-width': 22, 'line-opacity': 0 },
    },
    {
      id: LAYER.nodesMinor,
      type: 'circle',
      source: SRC.nodes,
      filter: ['!', isStation],
      minzoom: 6,
      paint: {
        'circle-radius': ['interpolate', ['linear'], ['zoom'], 6, 3, 11, 5],
        'circle-color': ['case', ['boolean', ['feature-state', 'seleccionado'], false], AZUL, TINTA],
        'circle-stroke-color': PAPEL,
        'circle-stroke-width': 1.5,
      },
    },
    {
      id: LAYER.nodesStations,
      type: 'circle',
      source: SRC.nodes,
      filter: isStation,
      paint: {
        'circle-radius': ['interpolate', ['linear'], ['zoom'], 5, ['case', isSecondary, 3, 5], 11, ['case', isSecondary, 5.5, 8]],
        'circle-color': PAPEL,
        'circle-stroke-color': ['case', ['boolean', ['feature-state', 'seleccionado'], false], AZUL, TINTA],
        'circle-stroke-width': ['case', ['boolean', ['feature-state', 'seleccionado'], false], 3.5, ['case', isSecondary, 1.8, 2.5]],
      },
    },
    {
      id: LAYER.nodeLabels,
      type: 'symbol',
      source: SRC.nodes,
      filter: ['!', isSecondary],
      layout: {
        'text-field': ['get', 'short_name'],
        'text-font': ['case', isStation, ['literal', ['Noto Sans Bold']], ['literal', ['Noto Sans Regular']]],
        'text-size': ['interpolate', ['linear'], ['zoom'], 5, ['case', isStation, 11.5, 10.5], 10, ['case', isStation, 14, 11.5]],
        'text-offset': [0.9, 0],
        'text-anchor': 'left',
        'text-justify': 'left',
        'text-optional': true,
        'symbol-sort-key': ['case', isStation, 0, 1],
      },
      minzoom: 5.5,
      paint: {
        'text-color': ['case', isStation, TINTA, '#4B5551'],
        'text-halo-color': PAPEL,
        'text-halo-width': 1.8,
      },
    },
    {
      id: LAYER.nodeLabelsSecondary,
      type: 'symbol',
      source: SRC.nodes,
      filter: isSecondary,
      minzoom: 7.5,
      layout: {
        'text-field': ['get', 'short_name'],
        'text-font': ['Noto Sans Regular'],
        'text-size': ['interpolate', ['linear'], ['zoom'], 7.5, 10, 11, 12],
        'text-offset': [0.8, 0],
        'text-anchor': 'left',
        'text-justify': 'left',
        'text-optional': true,
        'symbol-sort-key': 2,
      },
      paint: {
        'text-color': '#4B5551',
        'text-halo-color': PAPEL,
        'text-halo-width': 1.6,
      },
    },
  ]
}
