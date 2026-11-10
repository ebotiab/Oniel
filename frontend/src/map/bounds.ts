// Encuadres del mapa. Sin dependencias para que las pruebas Playwright puedan importarlos.

/** Par de esquinas [[oeste, sur], [este, norte]] en grados. */
export type Caja = [[number, number], [number, number]]

/** Encuadre inicial: el corredor de las líneas cargadas (Madrid–Sevilla y Madrid–Córdoba por Alcázar). */
export const SPAIN_BOUNDS: Caja = [
  [-7.2, 36.6],
  [-2.6, 40.9],
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
