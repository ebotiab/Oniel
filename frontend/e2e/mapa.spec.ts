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
  test('la vía se dibuja sin esperar a las teselas del mapa base', async ({ page }) => {
    // Las teselas de OpenFreeMap no llegan nunca: como con una conexión muy lenta.
    await page.route(/tiles\.openfreemap\.org\/.*\.pbf/, () => {})
    await page.goto('/')
    await page.waitForFunction(() => (globalThis as unknown as ConMapa).__onielMap?.getSource('oniel-segments') !== undefined)
    const estado = await page.evaluate(() => {
      const map = (globalThis as unknown as ConMapa).__onielMap!
      return { cargado: map.loaded(), capaDeVia: map.getLayer('oniel-segments') !== undefined }
    })
    expect(estado).toEqual({ cargado: false, capaDeVia: true })
  })

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

  test('al ensanchar la ventana de móvil a escritorio, el tramo seleccionado se vuelve a encuadrar fuera del panel', async ({ page }) => {
    const avisos: string[] = []
    page.on('console', (m) => {
      if (/cannot fit/i.test(m.text())) avisos.push(m.text())
    })
    await page.setViewportSize({ width: 375, height: 812 })
    await page.goto('/tramo/lav-madrid-sevilla:urda:ciudad-real')
    await expect(page.getByTestId('detalle-tramo')).toBeVisible()
    await page.waitForFunction(() => (globalThis as unknown as ConMapa).__onielMap?.loaded() === true)
    await page.setViewportSize({ width: 1280, height: 800 })
    // los dos extremos del tramo (Urda y Ciudad Real) caben en el hueco que deja el panel, de 440 px
    const extremos = () =>
      page.evaluate(() => {
        const map = (globalThis as unknown as ConMapa).__onielMap!
        if (map.isMoving()) return null
        return [map.project([-3.821849, 39.418953]), map.project([-3.913263, 38.985441])].map((p) => ({ x: p.x, y: p.y }))
      })
    await expect
      .poll(async () => {
        const e = await extremos()
        return e !== null && e.every((p) => p.x > 440 && p.x < 1280 && p.y > 0 && p.y < 800)
      })
      .toBe(true)
    // MapLibre no ha descartado el encuadre por medir todavía el lienzo del móvil
    expect(avisos).toEqual([])
  })
})

/** Espera a que el mapa deje de moverse y devuelve su encuadre: [[oeste, sur], [este, norte]]. */
async function encuadre(page: Page) {
  await page.waitForFunction(() => !(globalThis as unknown as ConMapa).__onielMap!.isMoving())
  return page.evaluate(() => (globalThis as unknown as ConMapa).__onielMap!.getBounds().toArray() as [[number, number], [number, number]])
}

/**
 * El encuadre enseña la vía única de punta a punta: Despeñaperros, al norte, y Granada, al sur, donde
 * acaba la línea de Moreda. No llega al norte de la península: en el móvil el lienzo sigue por detrás
 * de la hoja y alcanza Madrid, pero no los Pirineos.
 */
async function encuadraLaViaUnica(page: Page) {
  await expect
    .poll(async () => {
      const [[oeste, sur], [este, norte]] = await encuadre(page)
      return oeste < -3.61 && este > -3.5 && sur < 37.18 && norte > 38.4 && norte < 42.5
    })
    .toBe(true)
}

test.describe('Trazo de la vía', () => {
  test('el mapa separa el tipo de línea del número de vías y el esquema usa los mismos trazos', async ({ page }) => {
    await mapaListo(page)
    const trazos = await page.evaluate(() => {
      const map = (globalThis as unknown as ConMapa).__onielMap!
      const vistos = new Set<string>()
      for (const f of map.querySourceFeatures('oniel-segments')) vistos.add(`${f.properties.tipo}/${f.properties.vias}`)
      return [...vistos].sort()
    })
    expect(trazos).toEqual(['alta-velocidad/2', 'convencional/1', 'convencional/2'])
    // cada trazo tiene su capa de dibujo: filete, trazos blancos y trazos espaciados
    const capas = await page.evaluate(() => {
      const map = (globalThis as unknown as ConMapa).__onielMap!
      return ['oniel-segments-filete', 'oniel-segments-ticks', 'oniel-segments-ticks-unica'].map((id) => map.getLayer(id) !== undefined)
    })
    expect(capas).toEqual([true, true, true])

    const asa = page.getByRole('button', { name: 'Ampliar el panel' })
    if (await asa.isVisible()) await asa.click() // en móvil, la hoja empieza plegada
    await page.getByTestId('linea-lav-madrid-sevilla').click()
    await expect(page.locator('[data-testid="esquema"] [data-trazo="alta-velocidad"]').first()).toBeAttached()
    await page.getByTestId('volver-red').click()
    await page.getByTestId('linea-convencional-madrid-alcazar-cordoba').click()
    await expect(page.locator('[data-testid="esquema"] [data-trazo="convencional"]').first()).toBeAttached()
    await expect(page.locator('[data-testid="esquema"] [data-trazo="via-unica"]').first()).toBeAttached()
    await expect(page.locator('[data-testid="esquema"] [data-trazo="alta-velocidad"]')).toHaveCount(0)
  })

  test('la leyenda muestra los tres trazos y resalta en el mapa el que se señala', async ({ page }, info) => {
    test.skip(info.project.name === 'movil', 'la leyenda solo existe en escritorio')
    await mapaListo(page)
    const opacidad = () =>
      page.evaluate(() => JSON.stringify((globalThis as unknown as ConMapa).__onielMap!.getPaintProperty('oniel-segments', 'line-opacity') ?? 1))
    const mapa = page.getByTestId('mapa')
    await expect(page.getByTestId('leyenda-alta-velocidad')).toHaveText('Alta velocidad')
    await expect(page.getByTestId('leyenda-convencional')).toHaveText('Línea convencional')
    await expect(page.getByTestId('leyenda-via-unica')).toHaveText('Vía única')
    expect(await opacidad()).toBe('1')

    // pasar por encima resalta sin fijar y sin mover el mapa
    const antes = await encuadre(page)
    await page.getByTestId('leyenda-via-unica').hover()
    await expect(mapa).toHaveAttribute('data-resaltado', 'via-unica')
    expect(await opacidad()).toContain('vias')
    expect(await encuadre(page)).toEqual(antes)
    await page.mouse.move(700, 400)
    await expect(mapa).not.toHaveAttribute('data-resaltado')
    expect(await opacidad()).toBe('1')

    // un clic lo deja fijado; otro lo suelta
    await page.getByTestId('leyenda-alta-velocidad').click()
    await page.mouse.move(700, 400)
    await expect(mapa).toHaveAttribute('data-resaltado', 'alta-velocidad')
    await expect(page.getByTestId('leyenda-alta-velocidad')).toHaveAttribute('aria-pressed', 'true')
    expect(await opacidad()).toContain('alta-velocidad')
    await page.getByTestId('leyenda-alta-velocidad').click()
    await page.mouse.move(700, 400)
    await expect(mapa).not.toHaveAttribute('data-resaltado')

    // al fijar un trazo, el mapa lo encuadra
    await page.getByTestId('leyenda-via-unica').click()
    await encuadraLaViaUnica(page)
  })

  test('en escritorio la escala no queda detrás de la leyenda aunque la atribución esté desplegada', async ({ page }, info) => {
    test.skip(info.project.name === 'movil', 'la leyenda sobre el mapa solo existe en escritorio')
    await mapaListo(page)
    const atribucion = page.locator('.maplibregl-ctrl-attrib')
    await expect(atribucion).toHaveClass(/maplibregl-compact-show/)
    const [leyenda, escala, a] = [await page.locator('.leyenda').boundingBox(), await page.locator('.maplibregl-ctrl-scale').boundingBox(), await atribucion.boundingBox()]
    // la escala va en el renglón de la atribución, a su izquierda y por debajo de la leyenda
    expect(leyenda && escala && a && escala.y >= leyenda.y + leyenda.height && escala.x + escala.width <= a.x).toBe(true)
  })

  test('en el móvil la escala y el botón de la atribución caben en un renglón tras el primer toque', async ({ page }, info) => {
    test.skip(info.project.name !== 'movil', 'en escritorio hay sitio para las dos')
    await mapaListo(page)
    const atribucion = page.locator('.maplibregl-ctrl-attrib')
    const escala = page.locator('.maplibregl-ctrl-scale')
    // al llegar, la atribución está desplegada y la escala va encima
    await expect(atribucion).toHaveClass(/maplibregl-compact-show/)
    // un toque en cualquier parte, aquí en el panel, la pliega
    await page.getByRole('button', { name: 'Ampliar el panel' }).click()
    await expect(atribucion).not.toHaveClass(/maplibregl-compact-show/)
    // con la hoja abierta el mapa es muy bajo y la escala se quita; al recogerla, vuelve junto a «i»
    await expect(escala).toBeHidden()
    await page.getByRole('button', { name: 'Reducir el panel' }).click()
    await expect(escala).toBeVisible()
    const [a, e] = [await atribucion.boundingBox(), await escala.boundingBox()]
    expect(a && e && Math.abs(a.y + a.height - (e.y + e.height)) <= 2 && e.x + e.width <= a.x).toBe(true)
    // el botón «i» la vuelve a enseñar entera, con su enlace a OpenStreetMap
    await atribucion.locator('.maplibregl-ctrl-attrib-button').click()
    await expect(atribucion.getByRole('link', { name: 'OpenStreetMap' })).toBeVisible()
  })

  test('en el móvil la leyenda de los trazos va sobre el esquema y resalta el que se toca', async ({ page }, info) => {
    test.skip(info.project.name !== 'movil', 'en escritorio la leyenda va sobre el mapa')
    await mapaListo(page)
    await page.getByRole('button', { name: 'Ampliar el panel' }).click()
    const mapa = page.getByTestId('mapa')
    const leyenda = page.getByTestId('leyenda-trazos')
    // la vista de la red no la lleva: la lista de líneas ya enseña la muestra de cada tipo
    await expect(page.getByTestId('vista-red')).toBeVisible()
    await expect(leyenda).toHaveCount(0)

    // en la vista de una línea, los tres trazos sobre el esquema
    await page.goto('/linea/lav-madrid-sevilla')
    await expect(leyenda.getByRole('button')).toHaveText(['Alta velocidad', 'Línea convencional', 'Vía única'])
    await page.getByTestId('leyenda-via-unica').click()
    await expect(mapa).toHaveAttribute('data-resaltado', 'via-unica')
    await expect(page.getByTestId('leyenda-via-unica')).toHaveAttribute('aria-pressed', 'true')
    // y el mapa lo encuadra, aunque esa línea no tenga vía única
    await encuadraLaViaUnica(page)
    await page.getByTestId('leyenda-via-unica').click()
    await expect(mapa).not.toHaveAttribute('data-resaltado')

    // al abrir un tramo, el resaltado se suelta
    await page.getByTestId('leyenda-alta-velocidad').click()
    await expect(mapa).toHaveAttribute('data-resaltado', 'alta-velocidad')
    await page.getByTestId('esquema-tramo-5').click()
    await expect(page.getByTestId('detalle-tramo')).toBeVisible()
    await expect(leyenda).toHaveCount(0)
    await expect(mapa).not.toHaveAttribute('data-resaltado')
  })
})
