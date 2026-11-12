import { expect, test } from '@playwright/test'

/** El campo del buscador: en escritorio está a la vista; en el móvil lo despliega la lupa. */
async function abrirBuscador(page: import('@playwright/test').Page) {
  const lupa = page.getByTestId('buscador-abrir')
  if (await lupa.isVisible()) await lupa.click()
  return page.getByRole('combobox', { name: 'Buscar una estación o una línea' })
}

test.describe('El ramal de Espelúy a Jaén', () => {
  test('el buscador lleva a Jaén y su ficha dice a dónde se llega sin cambiar de tren', async ({ page }) => {
    await page.goto('/')
    await expect(page.getByTestId('vista-red')).toBeVisible()
    const campo = await abrirBuscador(page)
    await campo.fill('jaen')
    const primero = page.getByRole('option').first()
    await expect(primero).toContainText('Jaén')
    await expect(primero).toContainText('Estación')
    await campo.press('Enter')
    await expect(page).toHaveURL(/\/nodo\/jaen$/)
    const ficha = page.getByTestId('detalle-nodo')
    await expect(ficha.getByRole('heading', { name: 'Jaén' })).toBeVisible()
    await expect(ficha).toContainText('Estación término')
    // destinos directos del día de referencia: Córdoba es el que más trenes tiene
    await expect(ficha).toContainText('Córdoba')
    // y la interrupción vigente, con su fuente
    await expect(ficha).toContainText('por carretera')
  })

  test('la línea tiene su ficha, con Espelúy como enlace y dos tramos de vía única', async ({ page }) => {
    await page.goto('/linea/espeluy-jaen')
    await expect(page.getByRole('heading', { name: 'Línea convencional Espelúy – Jaén' })).toBeVisible()
    await expect(page.locator('body')).toContainText('Un ramal de vía única')
    const esquema = page.getByTestId('esquema')
    await expect(esquema).toContainText('Espelúy')
    await expect(esquema).toContainText('Mengíbar-Artichuela')
    await expect(esquema).toContainText('Jaén')
  })

  test('un tramo del ramal dice su vía única y su bloqueo', async ({ page }) => {
    await page.goto('/tramo/espeluy-jaen:mengibar-artichuela:jaen')
    const ficha = page.getByTestId('detalle-tramo')
    await expect(ficha).toBeVisible()
    await expect(page.getByTestId('tramo-vias')).toHaveText('Vía única')
    // la señalización va bajo «Más detalle»: está en la ficha aunque plegada
    await expect(ficha.getByText('De liberación automática en vía única')).toHaveCount(1)
  })

  test('el comparador encuentra el recorrido de Madrid a Jaén', async ({ page }) => {
    await page.goto('/recorridos/madrid-puerta-de-atocha/jaen')
    const recorridos = page.getByTestId('recorrido')
    await expect(recorridos.first()).toBeVisible()
    await expect(recorridos.first()).toContainText('373,0 km')
    await expect(recorridos.first()).toContainText('Por Espelúy')
    await expect(recorridos.first()).toContainText('Recorre dos líneas')
    // el recorrido está cortado hoy, y lo dice
    await expect(recorridos.first()).toContainText('Sin circulación hoy')
  })
})
