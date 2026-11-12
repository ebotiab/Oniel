import { expect, test } from '@playwright/test'

/** El campo del buscador: en escritorio está a la vista; en el móvil lo despliega la lupa. */
async function abrirBuscador(page: import('@playwright/test').Page) {
  const lupa = page.getByTestId('buscador-abrir')
  if (await lupa.isVisible()) await lupa.click()
  return page.getByRole('combobox', { name: 'Buscar una estación o una línea' })
}

test.describe('La línea de Alcázar de San Juan a Albacete', () => {
  test('el buscador lleva a Albacete y su ficha dice a dónde se llega sin cambiar de tren', async ({ page }) => {
    await page.goto('/')
    await expect(page.getByTestId('vista-red')).toBeVisible()
    const campo = await abrirBuscador(page)
    await campo.fill('albacete')
    const primero = page.getByRole('option').first()
    await expect(primero).toContainText('Albacete-Los Llanos')
    await expect(primero).toContainText('Estación')
    await campo.press('Enter')
    await expect(page).toHaveURL(/\/nodo\/albacete-los-llanos$/)
    const ficha = page.getByTestId('detalle-nodo')
    await expect(ficha.getByRole('heading', { name: 'Albacete-Los Llanos' })).toBeVisible()
    await expect(ficha).toContainText('vías de dos anchos')
    // destinos directos del día de referencia, por la línea convencional
    await expect(ficha).toContainText('Alcázar de San Juan')
    await expect(ficha).toContainText('Socuéllamos')
  })

  test('la ficha de Alcázar de San Juan enseña destinos directos hacia Levante', async ({ page }) => {
    await page.goto('/nodo/alcazar-de-san-juan')
    const ficha = page.getByTestId('detalle-nodo')
    await expect(ficha.getByRole('heading', { name: 'Alcázar de San Juan' })).toBeVisible()
    await expect(ficha).toContainText('hacia Andalucía y hacia Levante')
    // el jueves de referencia Albacete es el séptimo destino por número de trenes: se ve al
    // desplegar la lista, que de entrada enseña los seis más frecuentes
    await page.getByTestId('destinos-ver-todos').click()
    await expect(ficha).toContainText('Albacete-Los Llanos')
    await expect(ficha).toContainText('MD, ALVIA y Regional Exprés')
  })

  test('la línea tiene su ficha, con Alcázar como enlace y sus estaciones en el esquema', async ({ page }) => {
    await page.goto('/linea/alcazar-albacete')
    await expect(page.getByRole('heading', { name: 'Línea convencional Alcázar de San Juan – Albacete' })).toBeVisible()
    await expect(page.locator('body')).toContainText('La rama de Levante')
    const esquema = page.getByTestId('esquema')
    await expect(esquema).toContainText('Alcázar de San Juan')
    await expect(esquema).toContainText('Villarrobledo')
    await expect(esquema).toContainText('Albacete-Los Llanos')
  })

  test('un tramo dice su vía doble y su bloqueo, y que el mando no está publicado', async ({ page }) => {
    await page.goto('/tramo/alcazar-albacete:villarrobledo:minaya')
    const ficha = page.getByTestId('detalle-tramo')
    await expect(ficha).toBeVisible()
    await expect(page.getByTestId('tramo-vias')).toHaveText('Vía doble')
    // la señalización va bajo «Más detalle»: está en la ficha aunque plegada
    await expect(ficha.getByText('Automático de vía doble')).toHaveCount(1)
    await expect(ficha.getByText('Sin dato publicado')).toHaveCount(1)
  })

  test('el comparador encuentra el recorrido de Madrid a Albacete por Alcázar', async ({ page }) => {
    await page.goto('/recorridos/madrid-puerta-de-atocha/albacete-los-llanos')
    const recorridos = page.getByTestId('recorrido')
    await expect(recorridos.first()).toBeVisible()
    await expect(recorridos.first()).toContainText('277,6 km')
    await expect(recorridos.first()).toContainText('Por Alcázar de San Juan')
    await expect(recorridos.first()).toContainText('Recorre dos líneas')
  })
})
