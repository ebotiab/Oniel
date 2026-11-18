import { expect, test } from '@playwright/test'

/** El campo del buscador: en escritorio está a la vista; en el móvil lo despliega la lupa. */
async function abrirBuscador(page: import('@playwright/test').Page) {
  const lupa = page.getByTestId('buscador-abrir')
  if (await lupa.isVisible()) await lupa.click()
  return page.getByRole('combobox', { name: 'Buscar una estación o una línea' })
}

test.describe('La línea Sevilla – Cádiz', () => {
  test('la línea tiene su ficha, con Jerez y Cádiz en el esquema', async ({ page }) => {
    await page.goto('/linea/sevilla-cadiz')
    await expect(page.getByRole('heading', { name: 'Línea convencional Sevilla – Cádiz' })).toBeVisible()
    await expect(page.locator('body')).toContainText('Une Sevilla con Jerez de la Frontera y Cádiz')
    const esquema = page.getByTestId('esquema')
    await expect(esquema).toContainText('Sevilla-Santa Justa')
    await expect(esquema).toContainText('Jerez de la Frontera')
    await expect(esquema).toContainText('Cádiz')
  })

  test('el buscador lleva a Jerez de la Frontera y a Cádiz', async ({ page }) => {
    await page.goto('/')
    await expect(page.getByTestId('vista-red')).toBeVisible()
    const campo = await abrirBuscador(page)
    await campo.fill('jerez')
    const primero = page.getByRole('option').first()
    await expect(primero).toContainText('Jerez de la Frontera')
    await expect(primero).toContainText('Estación')
    await campo.press('Enter')
    await expect(page).toHaveURL(/\/nodo\/jerez-de-la-frontera$/)
    await expect(page.getByTestId('detalle-nodo').getByRole('heading', { name: 'Jerez de la Frontera' })).toBeVisible()

    const otra = await abrirBuscador(page)
    await otra.fill('cadiz')
    await expect(page.getByRole('option').first()).toContainText('Cádiz')
    await otra.press('Enter')
    await expect(page).toHaveURL(/\/nodo\/cadiz$/)
    const ficha = page.getByTestId('detalle-nodo')
    await expect(ficha.getByRole('heading', { name: 'Cádiz', exact: true })).toBeVisible()
    await expect(ficha).toContainText('Sevilla-Santa Justa')
  })

  test('los tramos son de vía doble, a 3 kV, con ERTMS y bloqueo automático banalizado', async ({ page }) => {
    await page.goto('/tramo/sevilla-cadiz:jerez-de-la-frontera:el-puerto-de-santa-maria')
    await expect(page.getByTestId('detalle-tramo')).toBeVisible()
    const asa = page.getByRole('button', { name: 'Ampliar el panel' })
    if (await asa.isVisible()) await asa.click()
    await expect(page.getByTestId('tramo-vias')).toHaveText('Vía doble')
    await expect(page.getByTestId('tramo-atributo-proteccion_tren')).toHaveText('ERTMS de nivel 1 y ASFA')
    await page.getByTestId('mas-detalle').locator('summary').click()
    await expect(page.getByTestId('mas-detalle')).toContainText('3 kV CC')
  })

  test('el comparador encuentra Madrid – Cádiz y Sevilla – Cádiz', async ({ page }) => {
    await page.goto('/recorridos/madrid-puerta-de-atocha/cadiz')
    const recorridos = page.getByTestId('recorrido')
    await expect(recorridos.first()).toBeVisible()
    await expect(recorridos.first()).toContainText('622,7 km')
    await expect(recorridos.first()).toContainText('Recorre dos líneas')
    await expect(recorridos.first().getByTestId('recorrido-trenes')).toContainText(/\d+ trenes directos en el horario del /)

    await page.goto('/recorridos/sevilla-santa-justa/cadiz')
    await expect(recorridos.first()).toContainText('152,5 km')
    await expect(recorridos.first().getByTestId('recorrido-trenes')).toContainText(/\d+ trenes directos en el horario del /)
  })
})
