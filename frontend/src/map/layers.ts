// Capas de Oniel sobre el mapa base. La vía es tinta; el color solo marca estados.
// El grosor del trazo distingue la categoría de la vía: alta velocidad, convencional y vía única.

import type { ExpressionSpecification, LayerSpecification } from 'maplibre-gl'

export const PAPEL = '#EDEFE9'
export const TINTA = '#17201E'
export const TINTA_3 = '#8B9490'
export const AZUL = '#1E4F9A'
export const ROJA = '#B4232A'

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
  segmentsHit: 'oniel-segments-hit',
  nodesMinor: 'oniel-nodes-minor',
  nodesStations: 'oniel-nodes-stations',
  nodeLabels: 'oniel-node-labels',
  nodeLabelsSecondary: 'oniel-node-labels-secondary',
} as const

/** Factor de grosor de un tramo: 1 alta velocidad, 0,8 convencional, 0,6 vía única (propiedad `peso`). */
export const PESO_ALTA_VELOCIDAD = 1
export const PESO_CONVENCIONAL = 0.8
export const PESO_VIA_UNICA = 0.6

const isStation: ExpressionSpecification = ['==', ['get', 'kind'], 'estacion']
const isSecondary: ExpressionSpecification = ['==', ['get', 'rank'], 'secundario']
const peso: ExpressionSpecification = ['coalesce', ['get', 'peso'], 1]
const emphasised: ExpressionSpecification = [
  'any',
  ['boolean', ['feature-state', 'seleccionado'], false],
  ['boolean', ['feature-state', 'cerrado'], false],
]

const segmentColor: ExpressionSpecification = [
  'case',
  ['boolean', ['feature-state', 'cerrado'], false],
  ROJA,
  ['boolean', ['feature-state', 'seleccionado'], false],
  AZUL,
  TINTA,
]

/** Grosor que crece con el zoom y se multiplica por el peso de la vía. */
function weighted(low: number, high: number, lowEmph: number, highEmph: number): ExpressionSpecification {
  return [
    'interpolate',
    ['linear'],
    ['zoom'],
    5,
    ['*', ['case', emphasised, lowEmph, low], peso],
    12,
    ['*', ['case', emphasised, highEmph, high], peso],
  ]
}

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
        'line-color': segmentColor,
        'line-width': ['interpolate', ['linear'], ['zoom'], 5, 10, 10, 18],
        'line-opacity': [
          'case',
          ['boolean', ['feature-state', 'cerrado'], false],
          0.2,
          ['boolean', ['feature-state', 'seleccionado'], false],
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
    {
      id: LAYER.segmentsTicks,
      type: 'line',
      source: SRC.segments,
      paint: {
        'line-color': PAPEL,
        'line-width': weighted(1.4, 2.2, 1.4, 2.2),
        'line-dasharray': [0.5, 3.2],
      },
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
