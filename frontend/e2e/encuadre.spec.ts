import { type Page, expect, test } from '@playwright/test'
import type { Map as MapLibreMap } from 'maplibre-gl'

import { IBERIA_BOUNDS, IBERIA_BOUNDS_MOVIL } from '../src/map/bounds.ts'
import { type Cabecera, type Rect, cabecerasEnLienzo, encuadrarLinea, extremosDeLinea, nombreCorto } from '../src/map/encuadre.ts'
import { indice } from './instantanea.ts'

// Al abrir una línea, el mapa la encuadra con sus dos cabeceras enteras, cada una con su rótulo, fuera de
// la cabecera de la página, del panel, de la leyenda y de los controles (docs/diseno.md, «Encuadre»).

type ConMapa = { __onielMap?: MapLibreMap }

/** Las cabeceras de una línea, leídas de la instantánea: los nodos que solo tocan un tramo suyo. */
function cabecerasDe(lineId: string): Cabecera[] {
  const tramos = indice.segment_features.features.filter((f) => f.properties.line_id === lineId).map((f) => ({ from_node_id: String(f.properties.from_node_id), to_node_id: String(f.properties.to_node_id) }))
  return extremosDeLinea(tramos).map((id) => {
    const n = indice.nodes.find((x) => x.id === id)!
    return { lon: n.lon, lat: n.lat, rotulo: nombreCorto(n.name), estacion: n.kind === 'estacion', secundario: n.rank === 'secundario' }
  })
}

function cajaDe(lineId: string): [[number, number], [number, number]] {
  const caja: [[number, number], [number, number]] = [
    [Infinity, Infinity],
    [-Infinity, -Infinity],
  ]
  for (const f of indice.segment_features.features) {
    if (f.properties.line_id !== lineId || f.geometry.type !== 'LineString') continue
    for (const c of f.geometry.coordinates) {
      caja[0] = [Math.min(caja[0][0], c[0]!), Math.min(caja[0][1], c[1]!)]
      caja[1] = [Math.max(caja[1][0], c[0]!), Math.max(caja[1][1], c[1]!)]
    }
  }
  return caja
}

const seTocan = (a: Rect, b: Rect) => a.left < b.right && a.right > b.left && a.top < b.bottom && a.bottom > b.top

// La cuenta, sin navegador, en todas las líneas cargadas y con las dos pantallas de la revisión: el hueco y
// lo que estorba son los que deja la página en cada una (cabecera de 56 px, panel de 440, leyenda abajo a
// la derecha, botones del zoom arriba a la derecha, hoja recogida de 150 px en el móvil).
const PANTALLAS = [
  {
    nombre: 'escritorio (1366 × 850)',
    ancho: 1366,
    alto: 850,
    libre: { left: 456, top: 72, right: 1350, bottom: 794 },
    estorbos: [
      { left: 1319, top: 68, right: 1362, bottom: 140 },
      { left: 1120, top: 593, right: 1356, bottom: 804 },
    ],
    limites: IBERIA_BOUNDS,
    zoomMin: 4.5,
  },
  {
    nombre: 'móvil (390 × 844)',
    ancho: 390,
    alto: 844,
    libre: { left: 10, top: 62, right: 380, bottom: 612 },
    estorbos: [{ left: 343, top: 64, right: 386, bottom: 136 }],
    limites: IBERIA_BOUNDS_MOVIL,
    zoomMin: 4.1,
  },
]

for (const p of PANTALLAS) {
  test(`el encuadre de cada línea deja sus cabeceras a la vista, ${p.nombre}`, () => {
    const fallos: string[] = []
    for (const linea of indice.lines) {
      const cabeceras = cabecerasDe(linea.id)
      const vista = encuadrarLinea({ ancho: p.ancho, alto: p.alto, libre: p.libre, estorbos: p.estorbos, caja: cajaDe(linea.id), cabeceras, limites: p.limites, zoomMin: p.zoomMin, zoomMax: 10 })
      cabecerasEnLienzo(cabeceras, vista, p.ancho, p.alto).forEach((r, i) => {
        const fuera = r.left < p.libre.left - 1 || r.top < p.libre.top - 1 || r.right > p.libre.right + 1 || r.bottom > p.libre.bottom + 1
        if (fuera || p.estorbos.some((e) => seTocan(r, e))) fallos.push(`${linea.id}: ${cabeceras[i]!.rotulo}`)
      })
    }
    expect(fallos).toEqual([])
  })
}

/** Las cabeceras de la línea abierta que no se ven enteras en la página: fuera del mapa o debajo de algo. */
async function cabecerasTapadas(page: Page, lineId: string): Promise<string[] | null> {
  const cabeceras = cabecerasDe(lineId)
  const estado = await page.evaluate(() => {
    const map = (globalThis as unknown as ConMapa).__onielMap
    if (!map || map.isMoving() || map.getSource('oniel-segments') === undefined) return null
    const rects = (sel: string) =>
      [...map.getContainer().ownerDocument.querySelectorAll(sel)]
        .map((el) => el.getBoundingClientRect())
        .filter((r) => r.width > 0 && r.height > 0)
        .map((r) => ({ left: r.left, top: r.top, right: r.right, bottom: r.bottom }))
    const marco = map.getContainer().getBoundingClientRect()
    return {
      center: map.getCenter().toArray() as [number, number],
      zoom: map.getZoom(),
      ancho: marco.width,
      alto: marco.height,
      encima: rects('.cabecera, .panel, .leyenda, .maplibregl-ctrl-top-right .maplibregl-ctrl, .maplibregl-ctrl-bottom-right .maplibregl-ctrl'),
    }
  })
  if (!estado) return null
  return cabecerasEnLienzo(cabeceras, estado, estado.ancho, estado.alto).flatMap((r, i) => {
    const fuera = r.left < 0 || r.top < 0 || r.right > estado.ancho || r.bottom > estado.alto
    return fuera || estado.encima.some((e) => seTocan(r, e)) ? [cabeceras[i]!.rotulo] : []
  })
}

// En la página de verdad, con lo que miden la cabecera, el panel, la leyenda y los controles: las líneas
// que la revisión del 22 de noviembre de 2026 encontró cortadas, en escritorio y en el móvil.
for (const lineId of ['lav-ourense-santiago', 'madrid-avila-valladolid', 'lav-madrid-barcelona', 'sevilla-huelva', 'palencia-santander']) {
  test(`al abrir ${lineId}, sus cabeceras quedan a la vista y sin nada encima`, async ({ page }) => {
    await page.goto(`/linea/${lineId}`)
    await expect(page.getByTestId('cabecera-linea')).toBeAttached()
    await expect.poll(() => cabecerasTapadas(page, lineId)).toEqual([])
  })
}
