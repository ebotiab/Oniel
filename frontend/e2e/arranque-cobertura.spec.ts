import { expect, test, type Page } from '@playwright/test'
import type { Map as MapLibreMap } from 'maplibre-gl'

import { cobertura, indice } from './instantanea.ts'
import { irA } from './navegar.ts'

const estatico = Boolean(process.env.ONIEL_E2E_STATIC)
type ConMapa = { __onielMap?: MapLibreMap }

/** Retiene solo este recurso; al soltarlo, el servidor entrega el fichero real. */
async function retener(page: Page, url: string) {
  let soltar!: () => void
  const retenida = new Promise<void>((resolve) => { soltar = resolve })
  await page.route(url, async (route) => {
    await retenida
    await route.continue().catch(() => {}) // puede haberse cancelado al cerrar la página
  })
  return soltar
}

async function ampliarPanel(page: Page) {
  const asa = page.getByRole('button', { name: 'Ampliar el panel' })
  if (await asa.isVisible()) await asa.click()
}

test.describe('Arranque sin esperar a la cobertura', () => {
  for (const entrada of ['/', '/nodo/puertollano']) {
    test(`el índice permite abrir Puertollano desde ${entrada} con la cobertura retenida`, async ({ page }) => {
      // El índice y los detalles se sirven sin interceptar: son los ficheros reales de la instantánea.
      const soltar = await retener(page, '**/data/coverage.json')
      try {
        const respuestaIndice = page.waitForResponse('**/data/index.json')
        await page.goto(entrada)
        expect((await respuestaIndice).ok()).toBe(true)
        if (entrada === '/') {
          await expect(page.getByTestId('vista-red')).toBeVisible({ timeout: 5_000 })
          // La red se dibuja y el visitante puede acercarse antes de recibir la cobertura.
          await page.waitForFunction(() => (globalThis as unknown as ConMapa).__onielMap?.getLayer('oniel-segments') !== undefined)
          const zoom = await page.evaluate(() => (globalThis as unknown as ConMapa).__onielMap!.getZoom())
          await page.getByRole('button', { name: 'Zoom in', exact: true }).click()
          await expect.poll(() => page.evaluate(() => (globalThis as unknown as ConMapa).__onielMap!.getZoom())).toBeGreaterThan(zoom)
          const lupa = page.getByTestId('buscador-abrir')
          if (await lupa.isVisible()) await lupa.click()
          await page.getByRole('combobox', { name: 'Buscar una estación o una línea' }).fill('Puertollano')
          await page.getByRole('option', { name: /Puertollano/ }).click()
        }
        await expect(page.getByRole('heading', { name: 'Puertollano', exact: true })).toBeVisible({ timeout: 5_000 })
        await expect(page.getByTestId('detalle-nodo')).toContainText('Tramos que salen de aquí')
        await expect(page).toHaveURL(/\/nodo\/puertollano$/)
        await expect(page.getByRole('heading', { name: 'Puertollano', exact: true })).toBeInViewport()
        await ampliarPanel(page)
        await expect(page.getByTestId('estado-cobertura')).toContainText('Cargando la cobertura y las fuentes…')
        await expect(page.locator('.lista-servicios li').first()).toBeAttached()
        await page.getByTestId('mas-detalle').locator('summary').click()
        await expect(page.getByTestId('pie-fuente')).toHaveCount(0)
        const respuestaCobertura = page.waitForResponse('**/data/coverage.json')
        soltar()
        expect((await respuestaCobertura).ok()).toBe(true)
        // La misma ficha incorpora las fuentes y conserva la selección sin recargar.
        await expect(page.getByTestId('estado-cobertura')).toHaveCount(0)
        await expect(page.getByTestId('pie-fuente').first()).toContainText('Colaboradores de OpenStreetMap')
        await expect(page.getByRole('heading', { name: 'Puertollano', exact: true })).toBeVisible()
        await expect(page).toHaveURL(/\/nodo\/puertollano$/)
      } finally {
        soltar()
      }
    })
  }

  test('si falla la cobertura, la estación y sus tramos siguen utilizables y explican qué falta', async ({ page }) => {
    await page.route('**/data/coverage.json', (route) => route.abort('failed'))
    await page.goto('/nodo/puertollano')
    await ampliarPanel(page)
    await expect(page.getByRole('heading', { name: 'Puertollano', exact: true })).toBeVisible()
    const aviso = page.getByTestId('estado-cobertura')
    await expect(aviso).toContainText('No se han podido cargar la cobertura y las fuentes.')
    await expect(aviso).toContainText('Faltan las fuentes, la información de los operadores y la vigencia de los horarios.')
    await expect(page.getByText('No se ha podido cargar la red.', { exact: false })).toHaveCount(0)
    await expect(page.locator('.lista-servicios li').first()).toBeAttached()
    await page.getByTestId('detalle-nodo').getByRole('button', { name: 'Ciudad Real – Puertollano', exact: true }).click()
    await expect(page.getByTestId('detalle-tramo')).toBeVisible()
    await expect(page.getByTestId('lista-servicios').locator('li').first()).toBeAttached()
    await expect(aviso).toBeVisible()
  })

  for (const falla of [false, true]) {
    test(`la página de cobertura muestra su estado y permite volver al mapa cuando ${falla ? 'falla' : 'tarda'}`, async ({ page }) => {
      const soltar = falla ? () => {} : await retener(page, '**/data/coverage.json')
      if (falla) await page.route('**/data/coverage.json', (route) => route.abort('failed'))
      try {
        await page.goto('/cobertura')
        const pagina = page.getByTestId('pagina-cobertura')
        await expect(pagina.getByRole('heading', { name: 'Cobertura y fuentes' })).toBeVisible()
        await expect(pagina.getByTestId('estado-cobertura')).toContainText(falla ? 'No se han podido cargar' : 'Cargando la cobertura')
        if (!falla) {
          soltar()
          await expect(pagina.getByTestId('cobertura-cifras')).toBeVisible()
          await expect(pagina.getByTestId('estado-cobertura')).toHaveCount(0)
        }
        await irA(page, 'mapa')
        await expect(page.getByTestId('vista-red')).toBeVisible()
      } finally {
        soltar()
      }
    })
  }

  test('si tampoco llega el índice, conserva el aviso de error de la red', async ({ page }) => {
    test.skip(!estatico, 'el error espera al sondeo de la API fuera del modo estático')
    await page.route('**/data/index.json', (route) => route.abort('failed'))
    const soltar = await retener(page, '**/data/coverage.json')
    try {
      await page.goto('/nodo/puertollano')
      await expect(page.getByText('No se ha podido cargar la red. Comprueba la conexión o el servidor de Oniel.')).toBeVisible()
      await expect(page.getByTestId('detalle-nodo')).toHaveCount(0)
    } finally {
      soltar()
    }
  })
})

test.describe('La API despierta con la cobertura pendiente', { tag: '@api' }, () => {
  test.skip(estatico, 'en modo estático no se sondea la API')

  for (const falla of [false, true]) {
    test(`el índice pasa a la API aunque su cobertura ${falla ? 'falle' : 'tarde'}, sin retroceder a la instantánea`, async ({ page }) => {
      const soltarEstatica = await retener(page, '**/data/coverage.json')
      let despertar!: () => void
      const dormida = new Promise<void>((resolve) => { despertar = resolve })
      await page.route('**/healthz', async (route) => {
        await dormida
        await route.fulfill({ json: { status: 'ok' } }).catch(() => {})
      })
      await page.route('**/api/lines', (route) => route.fulfill({ json: {
        ...indice,
        nodes: indice.nodes.map((n) => n.id === 'puertollano' ? { ...n, name: 'Puertollano desde la API' } : n),
      } }))
      // El resto de la API usa la misma instantánea; esta prueba no necesita un backend local.
      await page.route(/\/api\/(lines\/[^/?]+|nodes\/[^/?]+\/services)(\?|$)/, (route) => {
        const ruta = new URL(route.request().url()).pathname.replace('/api/', '/data/').replace(/\/services$/, '')
        return route.fulfill({ path: `public${ruta}.json` })
      })
      await page.route('**/api/nodes/*/history', (route) => route.fulfill({ path: 'public/data/historico/nodes/puertollano.json' }))
      let soltarApi!: () => void
      const pendiente = new Promise<void>((resolve) => { soltarApi = resolve })
      await page.route('**/api/coverage', async (route) => {
        if (falla) return route.abort('failed')
        await pendiente
        await route.fulfill({ json: { ...cobertura, sources: cobertura.sources.map((s) => ({ ...s, publisher: 'Fuente recibida de la API' })) } })
      })
      try {
        await page.goto('/nodo/puertollano')
        await expect(page.getByRole('heading', { name: 'Puertollano', exact: true })).toBeVisible()
        despertar()
        await expect(page.getByRole('heading', { name: 'Puertollano desde la API', exact: true })).toBeVisible()
        await ampliarPanel(page)
        await page.getByTestId('mas-detalle').locator('summary').click()
        if (!falla) {
          soltarApi()
          await expect(page.getByTestId('pie-fuente').first()).toContainText('Fuente recibida de la API')
        }
        const respuesta = page.waitForResponse('**/data/coverage.json')
        soltarEstatica()
        await respuesta
        await expect(page.getByTestId('estado-cobertura')).toHaveCount(0)
        await expect(page.getByTestId('pie-fuente').first()).toContainText(falla ? 'Colaboradores de OpenStreetMap' : 'Fuente recibida de la API')
        await expect(page.getByRole('heading', { name: 'Puertollano desde la API', exact: true })).toBeVisible()
      } finally {
        despertar()
        soltarApi()
        soltarEstatica()
      }
    })
  }
})
