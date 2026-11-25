import { expect, test, type Locator, type Page } from '@playwright/test'

import { indice } from './instantanea.ts'
import { irA } from './navegar.ts'

const TRAMO = 'manzanares-ciudad-real:daimiel:almagro'

/** Recorre controles reales, sin colocar el foco por código ni usar el ratón. */
async function tabHasta(page: Page, destino: Locator) {
  for (let i = 0; i < 80; i++) {
    if (await destino.evaluate(el => el === el.ownerDocument.activeElement)) return
    await page.keyboard.press('Tab')
  }
  await expect(destino).toBeFocused()
}

test.describe('Guía del atlas', () => {
  test('se puede empezar sin desplazar la página y las cuatro estaciones abren su ficha', async ({ page }) => {
    await page.goto('/guia')
    const guia = page.getByRole('main', { name: 'Guía del atlas' })
    await expect(guia).toBeVisible()
    await expect(page).toHaveTitle('Guía del atlas · Oniel')
    await expect(page.locator('link[rel="canonical"]')).toHaveAttribute('href', 'https://oniel.vercel.app/guia')
    await expect(guia.getByRole('link', { name: 'Ver la línea en el mapa' })).toBeInViewport()
    await expect(guia.locator('details[open]')).toHaveCount(0)
    const estaciones = indice.nodes.filter(n => n.line_id === 'manzanares-ciudad-real' && n.kind === 'estacion')
    const enlaces = guia.getByRole('list', { name: 'Estaciones de la línea, en orden' }).getByRole('link')
    await expect(enlaces).toHaveText(estaciones.map(n => n.name))
    for (const [i, estacion] of estaciones.entries()) {
      await expect(enlaces.nth(i)).toHaveAttribute('href', `/nodo/${estacion.id}`)
      await enlaces.nth(i).click()
      await expect(page.getByTestId('detalle-nodo').getByRole('heading', { name: estacion.name, exact: true })).toBeVisible()
      await page.goBack()
      await expect(enlaces.nth(i)).toBeFocused()
    }
    expect(await guia.evaluate(el => el.scrollWidth <= el.clientWidth)).toBe(true)
  })

  test('de la guía al mapa, a una estación y a un tramo, y vuelta por el menú', async ({ page }) => {
    await page.goto('/guia')
    await page.getByRole('link', { name: 'Ver la línea en el mapa' }).click()
    await expect(page).toHaveURL(/\/linea\/manzanares-ciudad-real$/)
    await expect(page.locator('#linea-titulo')).toContainText('Manzanares')
    await expect(page.locator('.maplibregl-canvas')).toBeVisible()
    await page.getByTestId('esquema-nodo-daimiel').click()
    await expect(page.getByTestId('destinos-directos')).toContainText('Alcázar de San Juan')
    await page.getByRole('button', { name: 'Toda la línea' }).click()
    await page.getByTestId('esquema-tramo-2').click()
    await expect(page.getByTestId('detalle-tramo')).toContainText('Vía única')
    await expect(page.getByTestId('detalle-tramo')).toContainText('calculada')
    await irA(page, 'guia')
    await expect(page.getByRole('main', { name: 'Guía del atlas' })).toBeVisible()
    await irA(page, 'mapa')
    await expect(page).toHaveURL(new RegExp(`/tramo/${TRAMO}$`))
  })

  test('las preguntas de línea y estación llevan al detalle que explican', async ({ page }) => {
    await page.goto('/guia')
    await page.locator('#guia-por-donde summary').click()
    await page.getByRole('link', { name: 'Seguir Manzanares – Ciudad Real' }).click()
    await expect(page.getByTestId('esquema-nodo-almagro')).toBeVisible()
    await page.goBack()
    await expect(page.getByRole('link', { name: 'Seguir Manzanares – Ciudad Real' })).toBeFocused()
    await page.locator('#guia-estacion summary').click()
    await page.getByRole('link', { name: 'Consultar los destinos de Daimiel' }).click()
    await expect(page.getByTestId('destino-alcazar-de-san-juan')).toBeVisible()
    await page.getByTestId('destino-alcazar-de-san-juan').click()
    await expect(page.getByTestId('detalle-nodo').getByRole('heading', { name: 'Alcázar de San Juan' })).toBeVisible()
    await irA(page, 'guia')
    await expect(page.locator('#guia-estacion')).toHaveAttribute('open', '')
    await expect(page.getByRole('link', { name: 'Consultar los destinos de Daimiel' })).toBeFocused()
  })

  test('comparar los dos caminos conserva la pregunta, el desplazamiento y el foco al volver', async ({ page }) => {
    await page.goto('/guia')
    await page.locator('#guia-comparar summary').click()
    const enlace = page.getByRole('link', { name: 'Comparar Madrid – Valladolid' })
    await enlace.scrollIntoViewIfNeeded()
    const antes = await page.getByTestId('pagina-guia').evaluate(el => el.scrollTop)
    await enlace.click()
    const recorridos = page.getByTestId('recorrido')
    await expect(recorridos).toHaveCount(2)
    await expect(recorridos.nth(0)).toContainText('Segovia-Guiomar')
    await expect(recorridos.nth(1)).toContainText('Ávila')
    await expect(recorridos.nth(0)).toContainText('sin paradas')
    await expect(recorridos.nth(1)).toContainText('Ningún tren directo')
    await recorridos.nth(1).getByRole('button', { name: 'Por la línea convencional' }).click()
    await expect(recorridos.nth(1).getByRole('button', { name: 'Por la línea convencional' })).toHaveAttribute('aria-pressed', 'true')
    await recorridos.nth(0).getByRole('button', { name: 'Por la alta velocidad' }).click()
    await expect(recorridos.nth(0).getByRole('button', { name: 'Por la alta velocidad' })).toHaveAttribute('aria-pressed', 'true')
    await irA(page, 'guia')
    await expect(page.locator('#guia-comparar')).toHaveAttribute('open', '')
    await expect(enlace).toBeFocused()
    expect(await page.getByTestId('pagina-guia').evaluate(el => el.scrollTop)).toBeCloseTo(antes, 0)
    await irA(page, 'mapa')
    await expect(page).toHaveURL(/\/recorridos\/madrid-chamartin\/valladolid-campo-grande$/)
  })

  test('permite comprobar las fechas y las fuentes y consultar un concepto del glosario', async ({ page }) => {
    await page.goto('/guia')
    await page.locator('#guia-horarios summary').click()
    await expect(page.locator('#guia-horarios')).toContainText('no muestra la posición en directo')
    const fechas = page.getByRole('link', { name: 'Consultar fechas y fuentes de los horarios' })
    await fechas.click()
    await expect(page.getByTestId('cobertura-validez')).toContainText('Horarios válidos del')
    await page.getByTestId('cobertura-indice').getByRole('link', { name: 'Operadores de trenes' }).click()
    await expect(page.getByTestId('operador-renfe')).toContainText('Descargado')
    await page.getByTestId('cobertura-indice').getByRole('link', { name: 'Fuentes y licencias' }).click()
    await page.getByTestId('fuentes-horarios').locator('summary').click()
    await expect(page.getByTestId('fuentes-horarios').getByRole('link').first()).toBeVisible()
    await irA(page, 'guia')
    await expect(fechas).toBeFocused()
    await page.getByRole('link', { name: 'cómo se cruzan dos trenes en vía única' }).click()
    await expect(page.getByTestId('glosario-cruces-en-via-unica')).toHaveAttribute('aria-current', 'true')
    await page.goBack()
    await expect(page.getByRole('link', { name: 'cómo se cruzan dos trenes en vía única' })).toBeFocused()
  })

  test('el cierre se ofrece aparte como hipótesis y abre el formulario del tramo', async ({ page }) => {
    await page.goto('/guia')
    await expect(page.getByRole('link', { name: 'Probar un cierre hipotético' })).toBeHidden()
    await page.locator('#guia-cierre summary').click()
    await expect(page.locator('#guia-cierre')).toContainText('no un aviso de una incidencia real')
    await page.getByRole('link', { name: 'Probar un cierre hipotético' }).click()
    await expect(page).toHaveURL(new RegExp(`/tramo/${TRAMO}/cierre$`))
    await expect(page.getByTestId('panel-simulacion')).toContainText('Cierre hipotético')
    await expect(page.getByTestId('sim-fecha')).toBeVisible()
    await page.getByRole('button', { name: 'Volver al tramo' }).click()
    await expect(page.getByTestId('detalle-tramo')).toContainText('Daimiel – Almagro')
    await irA(page, 'guia')
    await expect(page.getByRole('link', { name: 'Probar un cierre hipotético' })).toBeFocused()
  })

  test('el recorrido con teclado abre la pregunta y el tramo y devuelve el foco al ejemplo', async ({ page }, testInfo) => {
    await page.goto('/guia')
    await page.keyboard.press('Tab')
    await expect(page.getByRole('link', { name: 'Ir a la guía' })).toBeFocused()
    await page.keyboard.press('Enter')
    await expect(page.getByRole('main', { name: 'Guía del atlas' })).toBeFocused()
    const pregunta = page.locator('#guia-tramo summary')
    await tabHasta(page, pregunta)
    await page.keyboard.press('Enter')
    await page.keyboard.press('Tab')
    const enlace = page.getByRole('link', { name: 'Ver el tramo Daimiel – Almagro' })
    await expect(enlace).toBeFocused()
    await page.keyboard.press('Enter')
    await expect(page.getByTestId('detalle-tramo')).toContainText('Daimiel – Almagro')
    if (testInfo.project.name === 'movil') {
      await tabHasta(page, page.getByTestId('nav-menu-boton'))
      await page.keyboard.press('Enter')
    }
    await tabHasta(page, page.getByTestId('nav-guia'))
    await page.keyboard.press('Enter')
    await expect(enlace).toBeFocused()
    await page.keyboard.press('Shift+Tab')
    await expect(pregunta).toBeFocused()
    await page.keyboard.press('Space')
    await expect(enlace).toBeHidden()
  })

  test('la guía y sus explicaciones se leen aunque no carguen los datos de la red', async ({ page }) => {
    await page.route(url => url.pathname.startsWith('/data/') || url.pathname.startsWith('/api/'), route => route.abort())
    await page.goto('/guia')
    const guia = page.getByRole('main', { name: 'Guía del atlas' })
    await expect(guia.getByRole('heading', { name: 'Hasta dónde llega el atlas' })).toBeVisible()
    await guia.locator('#guia-tramo summary').click()
    await expect(guia.locator('#guia-tramo')).toContainText('«Estimado» no quiere decir retrasado')
    await expect(guia.getByRole('link', { name: 'Cobertura y fuentes', exact: true })).toHaveAttribute('href', '/cobertura')
    await guia.getByRole('link', { name: 'Glosario', exact: true }).click()
    await expect(page.getByTestId('pagina-glosario')).toBeVisible()
  })
})
