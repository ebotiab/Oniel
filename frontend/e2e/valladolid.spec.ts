import { expect, test } from '@playwright/test'

/** El campo del buscador: en escritorio está a la vista; en el móvil lo despliega la lupa. */
async function abrirBuscador(page: import('@playwright/test').Page) {
  const lupa = page.getByTestId('buscador-abrir')
  if (await lupa.isVisible()) await lupa.click()
  return page.getByRole('combobox', { name: 'Buscar una estación o una línea' })
}

test.describe('La línea de alta velocidad Madrid – Segovia – Valladolid', () => {
  test('la línea tiene su ficha, con Segovia y la bifurcación de Galicia en el esquema', async ({ page }) => {
    await page.goto('/linea/lav-madrid-valladolid')
    await expect(page.getByRole('heading', { name: 'Línea de alta velocidad Madrid – Segovia – Valladolid' })).toBeVisible()
    await expect(page.locator('body')).toContainText('cruza la sierra de Guadarrama por un túnel de 28 km')
    const esquema = page.getByTestId('esquema')
    await expect(esquema).toContainText('Madrid-Chamartín')
    await expect(esquema).toContainText('Segovia-Guiomar')
    await expect(esquema).toContainText('Bif. Medina')
    await expect(esquema).toContainText('Valladolid-Campo Grande')
  })

  test('el buscador lleva a Valladolid y su ficha nombra los destinos del norte sin prometer sus líneas', async ({ page }) => {
    await page.goto('/')
    await expect(page.getByTestId('vista-red')).toBeVisible()
    const campo = await abrirBuscador(page)
    await campo.fill('valladolid')
    const primero = page.getByRole('option').first()
    await expect(primero).toContainText('Valladolid-Campo Grande')
    await expect(primero).toContainText('Estación')
    await campo.press('Enter')
    await expect(page).toHaveURL(/\/nodo\/valladolid-campo-grande$/)
    const ficha = page.getByTestId('detalle-nodo')
    await expect(ficha.getByRole('heading', { name: 'Valladolid-Campo Grande' })).toBeVisible()
    // las líneas que siguen hacia el norte no están cargadas, y la ficha lo dice
    await expect(ficha).toContainText('que todavía no están cargadas')
    // destinos directos del día de referencia: los de la red, y León o Palencia, que se nombran sin enlace
    await expect(ficha).toContainText('Madrid-Chamartín')
    await expect(ficha).toContainText('Segovia-Guiomar')
    await expect(ficha).toContainText('León')
    await expect(ficha).toContainText('Palencia')
  })

  test('Madrid-Chamartín une esta línea con la de Valencia', async ({ page }) => {
    await page.goto('/nodo/madrid-chamartin')
    const ficha = page.getByTestId('detalle-nodo')
    await expect(ficha.getByRole('heading', { name: 'Madrid-Chamartín' })).toBeVisible()
    await expect(ficha).toContainText('Segovia-Guiomar')
    await expect(ficha).toContainText('Valladolid-Campo Grande')
    await expect(ficha).toContainText('València-Joaquín Sorolla')
  })

  test('un tramo dice sus trenes de Renfe y de Ouigo y su señalización', async ({ page }) => {
    await page.goto('/tramo/lav-madrid-valladolid:segovia-guiomar:garcillan')
    await expect(page.getByTestId('detalle-tramo')).toBeVisible()
    await expect(page.getByTestId('tramo-vias')).toHaveText('Vía doble')
    await expect(page.getByTestId('tramo-operadores')).toHaveText(/^Renfe Viajeros \d+ · Ouigo España \d+$/)
    // Iryo no circula por esta línea: no hay aviso de trenes que falten
    await expect(page.getByTestId('tramo-operadores-sin-horarios')).toHaveCount(0)
    await expect(page.getByTestId('tramo-atributo-proteccion_tren')).toHaveText('ERTMS de niveles 1 y 2 y ASFA')
    await expect(page.getByTestId('tramo-atributo-bloqueo')).toHaveText('De control automático')
  })

  test('el comparador encuentra Madrid – Valladolid y Madrid – Segovia', async ({ page }) => {
    await page.goto('/recorridos/madrid-chamartin/valladolid-campo-grande')
    const recorridos = page.getByTestId('recorrido')
    await expect(recorridos.first()).toBeVisible()
    await expect(recorridos.first()).toContainText('178,6 km')
    await expect(recorridos.first()).toContainText('Pasa por Segovia-Guiomar')
    await expect(recorridos.first().getByTestId('recorrido-trenes')).toContainText(/\d\d trenes directos en el horario del /)
    await page.goto('/recorridos/madrid-chamartin/segovia-guiomar')
    await expect(recorridos.first()).toBeVisible()
    await expect(recorridos.first()).toContainText('67,7 km')
    await expect(recorridos.first().getByTestId('recorrido-trenes')).toContainText(/\d\d trenes directos en el horario del /)
    // de Segovia a Valencia sin pasar por Atocha: las dos líneas se unen en Chamartín
    await page.goto('/recorridos/segovia-guiomar/valencia-joaquin-sorolla')
    await expect(recorridos.first()).toBeVisible()
    await expect(recorridos.first()).toContainText('Recorre dos líneas')
  })
})
