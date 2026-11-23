// Encuadre de una línea en el hueco que dejan la cabecera, el panel, la leyenda y los controles.
// Sin dependencias, como `bounds.ts`, para que las pruebas Playwright puedan importarlo.

import type { Caja } from './bounds.ts'

/** Rectángulo en píxeles del lienzo del mapa, con el origen arriba a la izquierda. */
export interface Rect {
  left: number
  top: number
  right: number
  bottom: number
}

/** Una cabecera de la línea: la estación (o bifurcación) en la que acaba, con el rótulo que lleva en el mapa. */
export interface Cabecera {
  lon: number
  lat: number
  rotulo: string
  estacion: boolean
  /** De rango secundario: su rótulo es más pequeño y solo sale de cerca. */
  secundario: boolean
}

export interface Encuadre {
  center: [number, number]
  zoom: number
}

interface Peticion {
  /** Tamaño del lienzo. */
  ancho: number
  alto: number
  /** Lo que queda a la vista: el lienzo sin la cabecera de la página, sin el panel y sin la hoja. */
  libre: Rect
  /** Lo que tapa el mapa dentro de ese hueco: la leyenda y los controles. Una cabecera no cae debajo. */
  estorbos: Rect[]
  /** Caja del trazado de la línea. */
  caja: Caja
  cabeceras: Cabecera[]
  /** Hasta dónde deja moverse el mapa: todo el lienzo tiene que caber dentro. */
  limites: Caja
  zoomMin: number
  zoomMax: number
}

const TESELA = 512
const mercX = (lon: number) => (lon + 180) / 360
const mercY = (lat: number) => (1 - Math.log(Math.tan(Math.PI / 4 + (lat * Math.PI) / 360)) / Math.PI) / 2
const lonDe = (x: number) => x * 360 - 180
const latDe = (y: number) => (Math.atan(Math.exp(Math.PI * (1 - 2 * y))) * 360) / Math.PI - 90

/** A partir de qué zoom lleva rótulo un nodo: lo que declaran `nodeLabels` y `nodeLabelsSecondary` en `layers.ts`. */
const zoomDeRotulo = (c: Cabecera) => (c.secundario ? 7.5 : 5.5)

/** Tamaño del rótulo de un nodo a un zoom: el mismo que declaran esas dos capas. */
export function tamanoRotulo(zoom: number, c: Pick<Cabecera, 'estacion' | 'secundario'>): number {
  const tramo = (z0: number, a: number, z1: number, b: number) => a + (b - a) * Math.min(1, Math.max(0, (zoom - z0) / (z1 - z0)))
  if (c.secundario) return tramo(7.5, 10, 11, 12)
  return c.estacion ? tramo(5, 11.5, 10, 14) : tramo(5, 10.5, 10, 11.5)
}

/**
 * Lo que ocupa una cabecera alrededor de su punto, en píxeles: el círculo y, a su derecha, el rótulo.
 * El ancho del rótulo se estima por letras (0,62 del cuerpo, algo más que la media de Noto Sans Bold),
 * para no depender de medir el texto: así la prueba y el mapa hacen la misma cuenta. Con el mapa tan
 * lejos que el nodo no lleva rótulo, solo cuenta el círculo.
 */
export function huecoCabecera(c: Cabecera, zoom: number): Rect {
  if (zoom < zoomDeRotulo(c)) return { left: -10, top: -10, right: 10, bottom: 10 }
  const cuerpo = tamanoRotulo(zoom, c)
  return { left: -10, top: -cuerpo * 0.8, right: cuerpo * 0.9 + c.rotulo.length * cuerpo * 0.62 + 4, bottom: cuerpo * 0.8 }
}

const seTocan = (a: Rect, b: Rect) => a.left < b.right && a.right > b.left && a.top < b.bottom && a.bottom > b.top
const dentro = (a: Rect, b: Rect) => a.left >= b.left - 0.5 && a.right <= b.right + 0.5 && a.top >= b.top - 0.5 && a.bottom <= b.bottom + 0.5

/** Dónde cae en el lienzo cada cabecera, con su rótulo, con un centro y un zoom dados. */
export function cabecerasEnLienzo(cabeceras: Cabecera[], vista: Encuadre, ancho: number, alto: number): Rect[] {
  const s = TESELA * 2 ** vista.zoom
  const cx = mercX(vista.center[0]) * s
  const cy = mercY(vista.center[1]) * s
  return cabeceras.map((c) => {
    const x = mercX(c.lon) * s - cx + ancho / 2
    const y = mercY(c.lat) * s - cy + alto / 2
    const h = huecoCabecera(c, vista.zoom)
    return { left: x + h.left, top: y + h.top, right: x + h.right, bottom: y + h.bottom }
  })
}

/**
 * El centro y el zoom con los que una línea se ve entera: su trazado dentro del hueco libre y cada
 * cabecera, con su rótulo, dentro de él y fuera de la leyenda y de los controles. Prueba del zoom más
 * cercano al más lejano y, en cada uno, varias colocaciones dentro de la holgura que queda, empezando
 * por la centrada; se queda con la primera que cumple. Cuenta con que el mapa no sale de sus límites:
 * un centro que el mapa no admitiría se corrige antes de comprobarlo.
 */
export function encuadrarLinea(p: Peticion): Encuadre {
  const margen = 6
  const colocaciones = [0.5, 0.25, 0.75, 0, 1]
  const pares = colocaciones.flatMap((fx) => colocaciones.map((fy) => [fx, fy] as const)).sort((a, b) => Math.hypot(a[0] - 0.5, a[1] - 0.5) - Math.hypot(b[0] - 0.5, b[1] - 0.5))
  const anchoLibre = p.libre.right - p.libre.left
  const altoLibre = p.libre.bottom - p.libre.top
  let ultimo: Encuadre | null = null
  for (let zoom = p.zoomMax; zoom >= p.zoomMin - 1e-9; zoom -= 0.05) {
    const s = TESELA * 2 ** zoom
    // El contenido en píxeles del mundo a este zoom: el trazado con un margen y cada cabecera con su rótulo.
    const cont: Rect = {
      left: mercX(p.caja[0][0]) * s - margen,
      right: mercX(p.caja[1][0]) * s + margen,
      top: mercY(p.caja[1][1]) * s - margen,
      bottom: mercY(p.caja[0][1]) * s + margen,
    }
    for (const c of p.cabeceras) {
      const h = huecoCabecera(c, zoom)
      const x = mercX(c.lon) * s
      const y = mercY(c.lat) * s
      cont.left = Math.min(cont.left, x + h.left)
      cont.right = Math.max(cont.right, x + h.right)
      cont.top = Math.min(cont.top, y + h.top)
      cont.bottom = Math.max(cont.bottom, y + h.bottom)
    }
    const holguraX = anchoLibre - (cont.right - cont.left)
    const holguraY = altoLibre - (cont.bottom - cont.top)
    // Los centros que el mapa admite a este zoom: el lienzo entero dentro de los límites.
    const minCx = mercX(p.limites[0][0]) * s + p.ancho / 2
    const maxCx = mercX(p.limites[1][0]) * s - p.ancho / 2
    const minCy = mercY(p.limites[1][1]) * s + p.alto / 2
    const maxCy = mercY(p.limites[0][1]) * s - p.alto / 2
    if (minCx > maxCx || minCy > maxCy) continue
    for (const [fx, fy] of pares) {
      // El contenido se coloca en el hueco con esa parte de la holgura a su izquierda y encima.
      const izquierda = p.libre.left + holguraX * fx
      const arriba = p.libre.top + holguraY * fy
      const cx = Math.min(maxCx, Math.max(minCx, cont.left - izquierda + p.ancho / 2))
      const cy = Math.min(maxCy, Math.max(minCy, cont.top - arriba + p.alto / 2))
      const vista: Encuadre = { center: [lonDe(cx / s), latDe(cy / s)], zoom }
      if (fx === 0.5 && fy === 0.5) ultimo = vista
      if (holguraX < 0 || holguraY < 0) break
      const trazado: Rect = { left: cont.left - cx + p.ancho / 2, right: cont.right - cx + p.ancho / 2, top: cont.top - cy + p.alto / 2, bottom: cont.bottom - cy + p.alto / 2 }
      if (!dentro(trazado, p.libre)) continue
      if (cabecerasEnLienzo(p.cabeceras, vista, p.ancho, p.alto).some((r) => p.estorbos.some((e) => seTocan(r, e)))) continue
      return vista
    }
  }
  // No cabe ni con el zoom mínimo (no debería ocurrir con la red cargada): lo más lejano, centrado.
  return ultimo ?? { center: [(p.caja[0][0] + p.caja[1][0]) / 2, (p.caja[0][1] + p.caja[1][1]) / 2], zoom: p.zoomMin }
}

/** Las cabeceras de una línea: los nodos en los que acaba, es decir, los que solo tocan un tramo suyo. */
export function extremosDeLinea(tramos: { from_node_id: string; to_node_id: string }[]): string[] {
  const veces = new Map<string, number>()
  for (const t of tramos) for (const id of [t.from_node_id, t.to_node_id]) veces.set(id, (veces.get(id) ?? 0) + 1)
  return [...veces].filter(([, n]) => n === 1).map(([id]) => id)
}

/** El nombre de un nodo como va rotulado en el mapa: más corto que el oficial cuando este no cabe. */
export function nombreCorto(name: string): string {
  return name
    .replace('Villanueva de Córdoba-Los Pedroches', 'Villanueva de Córdoba')
    .replace('Almuradiel-Viso del Marqués', 'Almuradiel')
    .replace('Campus Universitario de Rabanales', 'Rabanales')
    .replace('Bifurcación ', 'Bif. ')
}
