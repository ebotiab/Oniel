import { expect, test, type Page } from '@playwright/test'
import type { Map as MapLibreMap } from 'maplibre-gl'

import { IBERIA_BOUNDS } from '../src/map/bounds.ts'

// El visor expone el mapa en window.__onielMap en desarrollo, que es como lo arranca Playwright.
// Las pruebas se tipan con la configuración de Node, sin DOM, así que dentro del navegador se llega
// a él por globalThis (el código de page.evaluate se serializa: no puede usar funciones de fuera).
type ConMapa = { __onielMap?: MapLibreMap }

async function mapaListo(page: Page) {
  await page.goto('/')
  await expect(page.locator('.maplibregl-canvas')).toBeVisible()
  await page.waitForFunction(() => (globalThis as unknown as ConMapa).__onielMap?.loaded() === true)
}

test.describe('Navegar por el mapa', () => {
  test('el mapa no sale de la península ni de sus vecinos', async ({ page }) => {
    await mapaListo(page)
    const vistas = await page.evaluate(() => {
      const map = (globalThis as unknown as ConMapa).__onielMap!
      const encuadre = () => map.getBounds().toArray() as [[number, number], [number, number]]
      map.jumpTo({ center: [10, 51], zoom: 5 }) // Alemania
      const alemania = encuadre()
      map.jumpTo({ center: [-100, 40], zoom: 0 }) // Estados Unidos, con el zoom del planeta entero
      const eeuu = encuadre()
      map.jumpTo({ center: [-4, 40], zoom: 0 }) // alejar al máximo sobre España
      const alejado = encuadre()
      return { alemania, eeuu, alejado }
    })
    const [[oeste, sur], [este, norte]] = IBERIA_BOUNDS
    const holgura = 1e-6
    for (const [nombre, [[w, s], [e, n]]] of Object.entries(vistas)) {
      expect(w, `${nombre}: borde oeste`).toBeGreaterThanOrEqual(oeste - holgura)
      expect(e, `${nombre}: borde este`).toBeLessThanOrEqual(este + holgura)
      expect(s, `${nombre}: borde sur`).toBeGreaterThanOrEqual(sur - holgura)
      expect(n, `${nombre}: borde norte`).toBeLessThanOrEqual(norte + holgura)
    }
  })

  test('el mapa se queda con el norte arriba aunque se arrastre con el botón derecho', async ({ page }) => {
    await mapaListo(page)
    const caja = await page.locator('.maplibregl-canvas').boundingBox()
    expect(caja).not.toBeNull()
    const x = caja!.x + caja!.width * 0.7
    const y = caja!.y + caja!.height * 0.35
    await page.mouse.move(x, y)
    await page.mouse.down({ button: 'right' })
    await page.mouse.move(x + 160, y + 80, { steps: 12 })
    await page.mouse.up({ button: 'right' })
    const giro = await page.evaluate(() => {
      const map = (globalThis as unknown as ConMapa).__onielMap!
      return { bearing: map.getBearing(), pitch: map.getPitch() }
    })
    expect(giro).toEqual({ bearing: 0, pitch: 0 })
  })
})
