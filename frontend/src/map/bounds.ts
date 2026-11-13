// Encuadres del mapa. Sin dependencias para que las pruebas Playwright puedan importarlos.

/** Par de esquinas [[oeste, sur], [este, norte]] en grados. */
export type Caja = [[number, number], [number, number]]

/**
 * Encuadre inicial y de «Toda la red»: la caja de las líneas cargadas, de Sevilla a Barcelona y de
 * Málaga a Zaragoza, con algo de margen. Hay que ensancharla cuando una línea nueva se salga de
 * ella (`frontend/e2e/mapa.spec.ts` lo comprueba con los nodos del índice).
 */
export const SPAIN_BOUNDS: Caja = [
  [-6.2, 36.5],
  [2.4, 41.9],
]

/**
 * Hasta dónde se puede mover el mapa: la península, Portugal, Baleares y una franja de los países
 * vecinos. MapLibre obliga a que todo el lienzo quepa dentro, y en escritorio el panel tapa unos
 * cinco grados por la izquierda; por eso el límite oeste va bastante más allá de Portugal.
 */
export const IBERIA_BOUNDS: Caja = [
  [-12.5, 34],
  [6, 46],
]
