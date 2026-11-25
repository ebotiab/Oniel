import { expect, test } from '@playwright/test'

import { indice } from './instantanea.ts'
import { irA } from './navegar.ts'

test.describe('Guía del atlas', () => {
  test('el esquema abre las fichas de la línea y atrás devuelve a la guía', async ({ page }) => {
    await page.goto('/guia')
    const guia = page.getByRole('main', { name: 'Guía del atlas' })
    await expect(guia).toBeVisible()
    await expect(page).toHaveTitle('Guía del atlas · Oniel')
    await expect(page.locator('link[rel="canonical"]')).toHaveAttribute('href', 'https://oniel.vercel.app/guia')
    const estaciones = indice.nodes.filter(n => n.line_id === 'manzanares-ciudad-real' && n.kind === 'estacion')
    const enlaces = guia.getByRole('list', { name: 'Estaciones de la línea, en orden' }).getByRole('link')
    await expect(enlaces).toHaveText(estaciones.map(n => n.name))
    for (const [i, estacion] of estaciones.entries()) {
      await expect(enlaces.nth(i)).toHaveAttribute('href', `/nodo/${estacion.id}`)
    }
    await guia.getByRole('link', { name: 'Daimiel', exact: true }).click()
    await expect(page.getByTestId('detalle-nodo').getByRole('heading', { name: 'Daimiel' })).toBeVisible()
    await page.goBack()
    await expect(guia).toBeVisible()
    await guia.getByRole('link', { name: 'Ver la línea en el mapa' }).click()
    await expect(page).toHaveURL(/\/linea\/manzanares-ciudad-real$/)
    await expect(page.locator('#linea-titulo')).toContainText('Manzanares')
  })

  test('las preguntas abren un tramo y dos recorridos reales', async ({ page }) => {
    await page.goto('/guia')
    const guia = page.getByRole('main', { name: 'Guía del atlas' })
    await guia.getByRole('link', { name: '¿Qué hay entre Daimiel y Almagro?' }).click()
    await expect(page.getByTestId('detalle-tramo')).toContainText('Daimiel')
    await page.goBack()
    await guia.getByRole('link', { name: '¿Por dónde se va de Madrid a Valladolid?' }).click()
    await expect(page.getByTestId('recorrido').nth(1)).toContainText('Ávila')
    await irA(page, 'guia')
    await irA(page, 'mapa')
    await expect(page).toHaveURL(/\/recorridos\/madrid-chamartin\/valladolid-campo-grande$/)
  })

  test('el enlace directo se lee aunque no carguen los datos de la red', async ({ page }) => {
    await page.route('**/data/**', route => route.abort())
    await page.route('**/api/**', route => route.abort())
    await page.goto('/guia')
    const guia = page.getByRole('main', { name: 'Guía del atlas' })
    await expect(guia.getByRole('heading', { name: 'Cómo interpretar los datos' })).toBeVisible()
    await expect(guia.getByRole('link', { name: 'Cobertura y fuentes' })).toHaveAttribute('href', '/cobertura')
    await guia.getByRole('link', { name: 'Glosario' }).click()
    await expect(page.getByTestId('pagina-glosario')).toBeVisible()
  })
})
