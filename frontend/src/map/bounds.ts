// Encuadres del mapa. Sin dependencias para que las pruebas Playwright puedan importarlos.

/** Par de esquinas [[oeste, sur], [este, norte]] en grados. */
export type Caja = [[number, number], [number, number]]

/**
 * Encuadre inicial y de «Toda la red»: la caja de las líneas cargadas, de Badajoz a Barcelona y de
 * Málaga a Zaragoza, con algo de margen. Hay que ensancharla cuando una línea nueva se salga de
 * ella (`frontend/e2e/mapa.spec.ts` lo comprueba con los nodos del índice).
 */
export const SPAIN_BOUNDS: Caja = [
  [-7.2, 36.5],
  [2.4, 41.9],
]

/**
 * Hasta dónde se puede mover el mapa: la península, Portugal, Baleares y una franja de los países
 * vecinos. MapLibre obliga a que todo el lienzo quepa dentro, así que la caja fija también cuánto
 * se puede alejar el mapa, y tiene que dejar que la red entera quepa en lo que el panel no tapa:
 * en escritorio el panel cubre el tercio izquierdo, y por eso el límite oeste va bastante más allá
 * de Portugal (pasó de −12,5 a −14,5 cuando la red llegó a Badajoz); en el móvil la pantalla es
 * alta y estrecha, y para que quepa de Badajoz a Barcelona a lo ancho hace falta más latitud de la
 * que ocupa la península (de 34–46 pasó a 30,5–48,5). Canarias sigue fuera.
 */
export const IBERIA_BOUNDS: Caja = [
  [-14.5, 30.5],
  [6, 48.5],
]
