import { expect, test } from '@playwright/test'

/** El campo del buscador: en escritorio está a la vista; en el móvil lo despliega la lupa. */
async function abrirBuscador(page: import('@playwright/test').Page) {
  const lupa = page.getByTestId('buscador-abrir')
  if (await lupa.isVisible()) await lupa.click()
  return page.getByRole('combobox', { name: 'Buscar una estación o una línea' })
}

test.describe('La línea de alta velocidad Valladolid – Palencia – León', () => {
  test('la línea tiene su ficha, con Palencia y la bifurcación de Burgos en el esquema', async ({ page }) => {
    await page.goto('/linea/lav-valladolid-leon')
    await expect(page.getByRole('heading', { name: 'Línea de alta velocidad Valladolid – Palencia – León' })).toBeVisible()
    await expect(page.locator('body')).toContainText('sale de Valladolid, pasa por Palencia y acaba en León')
    const esquema = page.getByTestId('esquema')
    await expect(esquema).toContainText('Valladolid-Campo Grande')
    await expect(esquema).toContainText('Bif. Venta de Baños')
    await expect(esquema).toContainText('Palencia')
    await expect(esquema).toContainText('León')
  })

  test('el buscador lleva a León y su ficha nombra los destinos de la red y los de fuera', async ({ page }) => {
    await page.goto('/')
    await expect(page.getByTestId('vista-red')).toBeVisible()
    const campo = await abrirBuscador(page)
    await campo.fill('león')
    const primero = page.getByRole('option').first()
    await expect(primero).toContainText('León')
    await expect(primero).toContainText('Estación')
    await campo.press('Enter')
    await expect(page).toHaveURL(/\/nodo\/leon$/)
    const ficha = page.getByTestId('detalle-nodo')
    await expect(ficha.getByRole('heading', { name: 'León' })).toBeVisible()
    // de León sigue la línea de Oviedo y Gijón; la de Galicia no está cargada, y la ficha lo dice
    await expect(ficha).toContainText('empieza la de Oviedo y Gijón')
    await expect(ficha).toContainText('por una línea convencional que no está cargada')
    await expect(ficha).toContainText('Palencia')
    await expect(ficha).toContainText('Valladolid-Campo Grande')
    await expect(ficha).toContainText('Madrid-Chamartín')
    await expect(ficha).toContainText('Oviedo')
  })

  test('un tramo de vía única lo dice, con sus trenes y su señalización', async ({ page }) => {
    await page.goto('/tramo/lav-valladolid-leon:palencia:bif-las-barreras')
    await expect(page.getByTestId('detalle-tramo')).toBeVisible()
    await expect(page.getByTestId('tramo-vias')).toHaveText('Vía única')
    await expect(page.getByTestId('tramo-operadores')).toHaveText('Solo Renfe Viajeros')
    await expect(page.getByTestId('tramo-operadores-sin-horarios')).toHaveCount(0)
    await expect(page.getByTestId('tramo-atributo-proteccion_tren')).toHaveText('ERTMS de nivel 2 y ASFA')
    await expect(page.getByTestId('tramo-atributo-bloqueo')).toHaveText('De control automático')
    await page.goto('/tramo/lav-valladolid-leon:bif-las-barreras:bif-las-arenas')
    await expect(page.getByTestId('tramo-vias')).toHaveText('Vía doble')
  })

  test('el comparador encuentra Madrid – León y Madrid – Palencia', async ({ page }) => {
    await page.goto('/recorridos/madrid-chamartin/leon')
    const recorridos = page.getByTestId('recorrido')
    await expect(recorridos.first()).toBeVisible()
    await expect(recorridos.first()).toContainText('344,6 km')
    await expect(recorridos.first()).toContainText('Recorre dos líneas')
    await expect(recorridos.first().getByTestId('recorrido-trenes')).toContainText(/\d+ trenes directos en el horario del /)
    await page.goto('/recorridos/madrid-chamartin/palencia')
    await expect(recorridos.first()).toBeVisible()
    await expect(recorridos.first()).toContainText('229,8 km')
    await expect(recorridos.first().getByTestId('recorrido-trenes')).toContainText(/\d+ trenes directos en el horario del /)
  })
})
