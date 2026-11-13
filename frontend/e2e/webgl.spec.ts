import { expect, test, type Page } from '@playwright/test'

import { abrirZona } from './navegar.ts'

// En un navegador sin WebGL2 MapLibre no puede crear el mapa. El visor lo explica en el hueco del mapa
// y todo lo que no depende de él sigue funcionando. La prueba quita WebGL al navegador anulando
// `getContext` antes de que cargue la página.

/** El visor compilado como en producción, con token de Logfire de mentira (playwright.config.ts). */
const URL_TELEMETRIA = `http://127.0.0.1:${Number(process.env.ONIEL_E2E_PORT_TELEMETRIA ?? Number(process.env.ONIEL_E2E_PORT ?? 5199) + 1)}`
const LOGFIRE = 'https://logfire-us.pydantic.dev'

interface Lienzo {
  prototype: { getContext: (tipo: string, ...resto: unknown[]) => unknown }
}

/** El navegador de la prueba deja de dar contextos WebGL, como uno sin aceleración gráfica. */
async function sinWebgl(page: Page) {
  await page.addInitScript(() => {
    const lienzo = (globalThis as unknown as { HTMLCanvasElement: Lienzo }).HTMLCanvasElement
    const original = lienzo.prototype.getContext
    lienzo.prototype.getContext = function (this: unknown, tipo: string, ...resto: unknown[]) {
      return /webgl/.test(tipo) ? null : original.call(this, tipo, ...resto)
    }
  })
}

/** En el móvil la hoja empieza plegada: se amplía para ver la lista entera. */
async function abrirHoja(page: Page) {
  const asa = page.getByRole('button', { name: 'Ampliar el panel' })
  if (await asa.isVisible()) await asa.click()
}

test.describe('Sin WebGL2', () => {
  test('el hueco del mapa explica por qué no hay mapa y la lista de líneas sigue funcionando', async ({ page }) => {
    const errores: Error[] = []
    page.on('pageerror', (e) => errores.push(e))
    await sinWebgl(page)
    await page.goto('/')
    const aviso = page.getByTestId('mapa-sin-webgl')
    await expect(aviso.getByText('Este navegador no puede dibujar el mapa')).toBeVisible()
    await expect(aviso).toContainText('El mapa necesita WebGL2')
    await expect(aviso).toContainText('no es nada que hayas hecho mal')
    await expect(aviso).toContainText('prueba con otro navegador')
    await expect(page.getByTestId('mapa')).toHaveCount(0)
    if (process.env.ONIEL_CAPTURAS) await page.screenshot({ path: `${process.env.ONIEL_CAPTURAS}/sin-webgl-${test.info().project.name}.png` })

    // La lista de líneas, la ficha de la línea y el buscador no dependen del mapa.
    await abrirHoja(page)
    await abrirZona(page, 'andalucia')
    await page.getByTestId('linea-lav-madrid-sevilla').click()
    await expect(page).toHaveURL(/\/linea\/lav-madrid-sevilla/)
    await expect(page.getByRole('button', { name: '← Toda la red' })).toBeVisible()
    const lupa = page.getByTestId('buscador-abrir')
    if (await lupa.isVisible()) await lupa.click()
    await page.getByRole('combobox', { name: 'Buscar una estación o una línea' }).fill('alcazar')
    await page.getByRole('option').first().click()
    await expect(page).toHaveURL(/\/nodo\/alcazar-de-san-juan$/)
    await expect(page.getByTestId('detalle-nodo')).toBeVisible()
    await expect(aviso).toBeVisible()
    expect(errores).toEqual([])
  })

  test('en el visor publicado no llega nada a Logfire', async ({ page }) => {
    const peticiones: string[] = []
    await page.route(`${LOGFIRE}/**`, async (route) => {
      peticiones.push(route.request().url())
      await route.fulfill({ status: 200, contentType: 'application/json', body: '{}' })
    })
    await sinWebgl(page)
    const sdk = page.waitForResponse((r) => /\/assets\/logfire-.*\.js$/.test(new URL(r.url()).pathname))
    await page.goto(`${URL_TELEMETRIA}/`)
    await expect(page.getByTestId('mapa-sin-webgl')).toBeVisible()
    // Con el SDK ya cargado, lo pendiente se envía al ocultar la página.
    expect((await sdk).ok()).toBe(true)
    await page.evaluate(() => (globalThis as unknown as { dispatchEvent(e: unknown): void }).dispatchEvent(new Event('pagehide')))
    await page.waitForTimeout(1_000)
    expect(peticiones).toEqual([])
  })
})
