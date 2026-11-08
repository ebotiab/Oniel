import { expect, test } from '@playwright/test'

test.describe('Explorar la red', () => {
  test('se abre con el mapa y la línea Madrid–Sevilla', async ({ page }) => {
    await page.goto('/')
    await expect(page).toHaveTitle(/Oniel/)
    await expect(page.getByTestId('mapa')).toBeVisible()
    await expect(page.getByRole('heading', { name: /Línea de alta velocidad Madrid – Sevilla/ })).toBeVisible()
    // el lienzo del mapa se ha creado
    await expect(page.locator('.maplibregl-canvas')).toBeVisible()
    // la cobertura de la versión está a la vista
    await expect(page.getByTestId('boton-cobertura')).toContainText('Madrid – Sevilla')
  })

  test('seleccionar un tramo en el esquema muestra sus datos y sus trenes', async ({ page }) => {
    await page.goto('/')
    const asa = page.getByRole('button', { name: 'Ampliar el panel' })
    if (await asa.isVisible()) await asa.click() // en móvil, la hoja empieza plegada
    await page.getByTestId('esquema-tramo-5').click() // Ciudad Real – Puertollano
    await expect(page.getByTestId('detalle-tramo')).toBeVisible()
    await expect(page.getByRole('heading', { name: /Ciudad Real/ })).toBeVisible()
    await expect(page.getByRole('heading', { name: /Puertollano/ })).toBeVisible()
    await expect(page.getByText(/Longitud/)).toBeVisible()
    await expect(page.getByTestId('lista-servicios').locator('li').first()).toBeVisible()
    await expect(page.getByTestId('lista-servicios')).toContainText(/AVE|AVLO|ALVIA|Intercity/)
    await expect(page).toHaveURL(/#\/tramo\/lav-madrid-sevilla:ciudad-real:puertollano/)
  })

  test('seleccionar una estación muestra qué tramos confluyen y qué trenes paran', async ({ page }) => {
    await page.goto('/#/nodo/cordoba')
    await expect(page.getByTestId('detalle-nodo')).toBeVisible()
    await expect(page.getByRole('heading', { name: 'Córdoba' })).toBeVisible()
    await expect(page.getByText(/Tramos que confluyen/)).toBeVisible()
    await expect(page.getByText(/Trenes que paran aquí/)).toBeVisible()
    await expect(page.getByText(/Bifurcación Málaga/).first()).toBeVisible()
  })

  test('los puntos de referencia explican qué son con lenguaje neutro', async ({ page }) => {
    await page.goto('/#/nodo/urda')
    await expect(page.getByRole('heading', { name: 'Urda' })).toBeVisible()
    await expect(page.getByText(/Puesto de adelantamiento y estacionamiento/).first()).toBeVisible()
    await expect(page.getByRole('complementary', { name: /Contexto de 2026/ })).toBeVisible()
  })

  test('la cobertura y las fuentes están a un clic', async ({ page }) => {
    await page.goto('/')
    await page.getByTestId('boton-cobertura').click()
    await expect(page.getByTestId('panel-cobertura')).toBeVisible()
    await expect(page.getByText(/Renfe Viajeros/).first()).toBeVisible()
    await expect(page.getByText(/OpenStreetMap/).first()).toBeVisible()
    await expect(page.getByText(/Adif/).first()).toBeVisible()
  })
})
