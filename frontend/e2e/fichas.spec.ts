import { expect, test, type Page } from '@playwright/test'

const TRAMO = 'lav-madrid-sevilla:urda:ciudad-real'

/** En el móvil la ficha vive en la hoja inferior: hay que ampliarla para verla entera. */
async function abrirHoja(page: Page) {
  const asa = page.getByRole('button', { name: 'Ampliar el panel' })
  if (await asa.isVisible()) await asa.click()
}

test.describe('Fichas: lo esencial primero y el detalle plegado', () => {
  test('en un tramo el detalle está plegado, se abre y muestra los puntos kilométricos y la fuente', async ({ page }) => {
    await page.goto(`/#/tramo/${TRAMO}`)
    const ficha = page.getByTestId('detalle-tramo')
    await expect(ficha).toBeVisible()
    // a la vista, sin abrir nada: cuánto mide, a qué velocidad se circula y cuántas vías tiene
    await expect(ficha).toContainText('51,1 km')
    await expect(ficha).toContainText('270 km/h')
    await expect(page.getByTestId('tramo-vias')).toHaveText('Vía doble')
    const detalle = page.getByTestId('mas-detalle')
    await expect(detalle.locator('summary')).toHaveText('Más detalle')
    await expect(detalle).not.toHaveAttribute('open')
    await expect(page.getByTestId('tramo-pk')).toBeHidden()
    await expect(page.getByTestId('pie-fuente')).toBeHidden()
    await detalle.locator('summary').click()
    await expect(page.getByTestId('tramo-pk')).toHaveText('del 119,7 al 170,8')
    await expect(page.getByTestId('pie-fuente')).toContainText(/Fuente del trazado: Colaboradores de OpenStreetMap, consultada el 8 de noviembre de 2026/)
    await expect(page.getByTestId('pie-fuente')).toContainText('osm-relation-1254828')
  })

  test('en un nodo el detalle está plegado, se abre y muestra el punto kilométrico, el código y la fuente', async ({ page }) => {
    await page.goto('/#/nodo/urda')
    const ficha = page.getByTestId('detalle-nodo')
    await expect(ficha).toBeVisible()
    // lo técnico no es lo primero que se lee
    await expect(ficha.locator('.sobre').first()).toHaveText('Puesto de adelantamiento y estacionamiento')
    const detalle = page.getByTestId('mas-detalle')
    await expect(detalle).not.toHaveAttribute('open')
    await expect(page.getByTestId('nodo-pk')).toBeHidden()
    await expect(ficha.getByText('37107')).toBeHidden()
    await detalle.locator('summary').click()
    await expect(page.getByTestId('nodo-pk')).toHaveText('km 119,7')
    await expect(ficha.getByText('37107')).toBeVisible()
    await expect(page.getByTestId('pie-fuente')).toContainText(/Fuente del trazado: Colaboradores de OpenStreetMap/)
  })

  test('el detalle se abre con el teclado y sigue abierto al pasar a otra ficha', async ({ page }) => {
    await page.goto(`/#/tramo/${TRAMO}`)
    const resumen = page.getByTestId('mas-detalle').locator('summary')
    await resumen.focus()
    await page.keyboard.press('Enter')
    await expect(page.getByTestId('tramo-pk')).toBeVisible()
    // el nodo de un extremo: su detalle ya está abierto, porque el visitante lo dejó así
    await page.getByTestId('detalle-tramo').getByRole('button', { name: 'Ciudad Real' }).click()
    await expect(page.getByTestId('detalle-nodo')).toBeVisible()
    await expect(page.getByTestId('mas-detalle')).toHaveAttribute('open')
    await expect(page.getByTestId('nodo-pk').first()).toBeVisible()
    // y al cerrarlo, se queda cerrado en la siguiente
    await page.getByTestId('mas-detalle').locator('summary').click()
    await page.getByRole('button', { name: /Urda – Ciudad Real/ }).click()
    await expect(page.getByTestId('detalle-tramo')).toBeVisible()
    await expect(page.getByTestId('mas-detalle')).not.toHaveAttribute('open')
  })

  test('la línea a la vista y el panel de cobertura tienen su ruta en la URL', async ({ page }) => {
    await page.goto('/')
    await abrirHoja(page)
    await page.getByTestId('selector-linea-manzanares-ciudad-real').click()
    await expect(page).toHaveURL(/#\/linea\/manzanares-ciudad-real$/)
    // el enlace abre esa misma línea
    await page.goto('/#/linea/convencional-madrid-alcazar-cordoba')
    await page.reload()
    await expect(page.getByTestId('selector-linea-convencional-madrid-alcazar-cordoba')).toHaveAttribute('aria-selected', 'true')
    // «Toda la línea» vuelve a la línea del tramo, con su ruta
    await page.goto('/#/tramo/manzanares-ciudad-real:daimiel:almagro')
    await page.reload()
    await page.getByRole('button', { name: '← Toda la línea' }).click()
    await expect(page).toHaveURL(/#\/linea\/manzanares-ciudad-real$/)
    await expect(page.getByTestId('selector-linea-manzanares-ciudad-real')).toHaveAttribute('aria-selected', 'true')
    // la cobertura
    await page.getByTestId('boton-cobertura').click()
    await expect(page).toHaveURL(/#\/cobertura$/)
    await page.reload()
    await expect(page.getByTestId('panel-cobertura')).toBeVisible()
  })
})
