import { expect, test } from '@playwright/test'

import { META_RED, SITIO } from '../src/app/meta.ts'
import { indice } from './instantanea.ts'

// El segundo servidor de Playwright sirve la compilación, igual que en producción.
const puerto = Number(process.env.ONIEL_E2E_PORT_TELEMETRIA ?? Number(process.env.ONIEL_E2E_PORT ?? 5199) + 1)
test.use({ baseURL: `http://127.0.0.1:${puerto}` })

test('robots anuncia un sitemap con todas las vistas estáticas, una sola vez', async ({ request }) => {
  const robots = await request.get('/robots.txt')
  expect(robots.status()).toBe(200)
  expect(robots.headers()['content-type']).toContain('text/plain')
  expect(await robots.text()).toContain(`Sitemap: ${SITIO}/sitemap.xml`)

  const sitemap = await request.get('/sitemap.xml')
  expect(sitemap.status()).toBe(200)
  expect(sitemap.headers()['content-type']).toContain('xml')
  const xml = await sitemap.text()
  expect(xml).toContain('<urlset xmlns="http://www.sitemaps.org/schemas/sitemap/0.9">')
  const urls = Array.from(xml.matchAll(/<loc>([^<]+)<\/loc>/g), (m) => m[1])
  const rutas = [
    '/', '/cobertura', '/glosario', '/recorridos', '/sin-otro-camino',
    ...indice.lines.map((linea) => `/linea/${linea.id}`),
    ...indice.nodes.map((nodo) => `/nodo/${nodo.id}`),
    ...indice.segment_features.features.map((tramo) => `/tramo/${tramo.id}`),
  ]
  expect(urls.sort()).toEqual(rutas.map((ruta) => SITIO + ruta).sort())
})

test.describe('Lectura sin JavaScript', () => {
  test.use({ javaScriptEnabled: false })

  test('la portada enlaza cada línea de la instantánea y se puede leer su ficha', async ({ page }) => {
    await page.goto('/')
    await expect(page.getByRole('heading', { level: 1 })).toHaveText(META_RED.title)
    await expect(page.getByRole('main')).toContainText(META_RED.description)
    const enlaces = page.getByRole('navigation').getByRole('link')
    expect(await enlaces.evaluateAll((lista) => lista.map((a) => a.getAttribute('href')))).toEqual(
      indice.lines.map((linea) => `/linea/${linea.id}`),
    )
    const linea = indice.lines[0]!
    await page.getByRole('link', { name: linea.name, exact: true }).click()
    await expect(page.getByRole('heading', { level: 1 })).toContainText(linea.name)
    await expect(page.getByRole('main')).toContainText('km en el mapa')
    await expect(page.locator('link[rel="canonical"]')).toHaveAttribute('href', `${SITIO}/linea/${linea.id}`)
    await page.getByRole('link', { name: 'Volver al mapa de la red' }).click()
    await expect(page.getByRole('heading', { level: 1 })).toHaveText(META_RED.title)
  })
})

test('al arrancar el mapa, el visor sustituye la lectura inicial', async ({ page }) => {
  await page.goto('/')
  await expect(page.getByTestId('vista-red')).toBeVisible()
  await expect(page.locator('.lectura-inicial')).toHaveCount(0)
})
