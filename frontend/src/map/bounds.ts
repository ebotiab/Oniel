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
 * vecinos. MapLibre obliga a que todo el lienzo quepa dentro, así que la caja fija también cuánto
 * se puede alejar el mapa. En escritorio el panel tapa unos siete grados por la izquierda; por eso
 * el límite oeste va bastante más allá de Portugal: con −18 la península entera cabe a la derecha
 * del panel en una pantalla de 1280 × 800. En el móvil la pantalla es alta y estrecha, y para que
 * quepa a lo ancho de Badajoz a Barcelona hace falta más latitud de la que ocupa la península: por
 * eso el norte y el sur pasaron de 34–46 a 30,5–48,5 cuando la red llegó a Extremadura. Canarias
 * sigue fuera.
 */
export const IBERIA_BOUNDS: Caja = [
  [-18, 30.5],
  [6, 48.5],
]
