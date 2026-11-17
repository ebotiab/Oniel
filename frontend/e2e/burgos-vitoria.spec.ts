import { expect, test } from '@playwright/test'

/** El campo del buscador: en escritorio está a la vista; en el móvil lo despliega la lupa. */
async function abrirBuscador(page: import('@playwright/test').Page) {
  const lupa = page.getByTestId('buscador-abrir')
  if (await lupa.isVisible()) await lupa.click()
  return page.getByRole('combobox', { name: 'Buscar una estación o una línea' })
}

test.describe('La línea Burgos – Miranda de Ebro – Vitoria', () => {
  test('la línea tiene su ficha, con Miranda de Ebro y Vitoria en el esquema', async ({ page }) => {
    await page.goto('/linea/burgos-miranda-vitoria')
    await expect(page.getByRole('heading', { name: 'Línea convencional Burgos – Miranda de Ebro – Vitoria' })).toBeVisible()
    await expect(page.locator('body')).toContainText('Es el camino de los trenes de Madrid al País Vasco')
    const esquema = page.getByTestId('esquema')
    await expect(esquema).toContainText('Burgos-Rosa Manzano')
    await expect(esquema).toContainText('Miranda de Ebro')
    await expect(esquema).toContainText('Vitoria-Gasteiz')
  })

  test('el buscador lleva a Vitoria', async ({ page }) => {
    await page.goto('/')
    await expect(page.getByTestId('vista-red')).toBeVisible()
    const campo = await abrirBuscador(page)
    await campo.fill('vitoria')
    const primero = page.getByRole('option').first()
    await expect(primero).toContainText('Vitoria-Gasteiz')
    await expect(primero).toContainText('Estación')
    await campo.press('Enter')
    await expect(page).toHaveURL(/\/nodo\/vitoria-gasteiz$/)
    const ficha = page.getByTestId('detalle-nodo')
    await expect(ficha.getByRole('heading', { name: 'Vitoria-Gasteiz' })).toBeVisible()
    await expect(ficha).toContainText('Madrid-Chamartín')
  })

  test('los tramos son de vía doble, a 3 kV, con ASFA y bloqueo automático banalizado', async ({ page }) => {
    await page.goto('/tramo/burgos-miranda-vitoria:pancorbo:miranda-de-ebro')
    await expect(page.getByTestId('detalle-tramo')).toBeVisible()
    const asa = page.getByRole('button', { name: 'Ampliar el panel' })
    if (await asa.isVisible()) await asa.click()
    await expect(page.getByTestId('tramo-vias')).toHaveText('Vía doble')
    await expect(page.getByTestId('tramo-atributo-gauge')).toHaveCount(0)
    await expect(page.getByTestId('tramo-atributo-proteccion_tren')).toHaveText('ASFA')
    await page.getByTestId('mas-detalle').locator('summary').click()
    await expect(page.getByTestId('mas-detalle')).toContainText('3 kV CC')
  })

  test('el comparador encuentra Madrid – Vitoria por Burgos', async ({ page }) => {
    await page.goto('/recorridos/madrid-chamartin/vitoria-gasteiz')
    const recorridos = page.getByTestId('recorrido')
    await expect(recorridos.first()).toBeVisible()
    await expect(recorridos.first()).toContainText('420,5 km')
    await expect(recorridos.first()).toContainText('Recorre cuatro líneas')
    await expect(recorridos.first().getByTestId('recorrido-trenes')).toContainText(/\d+ trenes directos en el horario del /)
  })
})
