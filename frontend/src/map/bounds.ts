// Encuadres del mapa. Sin dependencias para que las pruebas Playwright puedan importarlos.

/** Par de esquinas [[oeste, sur], [este, norte]] en grados. */
export type Caja = [[number, number], [number, number]]

/**
 * Encuadre inicial y de «Toda la red»: la península entera, de Fisterra al cabo de Creus y de
 * Tarifa a la Estaca de Bares, para que no haya que moverlo cada vez que entra una línea
 * (`docs/diseno.md`, «Encuadre»). `frontend/e2e/mapa.spec.ts` comprueba con los nodos del índice
 * que ninguna línea cargada se sale de él.
 */
export const SPAIN_BOUNDS: Caja = [
  [-9.3, 36.0],
  [3.3, 43.8],
]

/**
 * Hasta dónde se puede mover el mapa: la península, Portugal, Baleares y una franja de los países
 * vecinos. MapLibre obliga a que todo el lienzo quepa dentro, y en escritorio el panel tapa unos
 * siete grados por la izquierda; por eso el límite oeste va bastante más allá de Portugal: con
 * −18 la península entera cabe a la derecha del panel en una pantalla de 1280 × 800.
 */
export const IBERIA_BOUNDS: Caja = [
  [-18, 34],
  [6, 46],
]
