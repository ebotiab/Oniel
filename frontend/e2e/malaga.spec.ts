import { expect, test } from '@playwright/test'

/** El campo del buscador: en escritorio está a la vista; en el móvil lo despliega la lupa. */
async function abrirBuscador(page: import('@playwright/test').Page) {
  const lupa = page.getByTestId('buscador-abrir')
  if (await lupa.isVisible()) await lupa.click()
  return page.getByRole('combobox', { name: 'Buscar una estación o una línea' })
}

test.describe('La alta velocidad Córdoba – Málaga, entera', () => {
  test('el buscador lleva a Málaga-María Zambrano, que es una estación de la red', async ({ page }) => {
    await page.goto('/')
    await expect(page.getByTestId('vista-red')).toBeVisible()
    const campo = await abrirBuscador(page)
    await campo.fill('malaga')
    const primero = page.getByRole('option').first()
    await expect(primero).toContainText('Málaga-María Zambrano')
    await expect(primero).toContainText('Estación')
    await campo.press('Enter')
    await expect(page).toHaveURL(/\/nodo\/malaga-maria-zambrano$/)
    const ficha = page.getByTestId('detalle-nodo')
    await expect(ficha.getByRole('heading', { name: 'Málaga-María Zambrano' })).toBeVisible()
    await expect(ficha).toContainText('final de la línea')
    // destinos directos del día de referencia: Madrid, Córdoba y, por el enlace directo, Granada
    await expect(ficha).toContainText('Madrid-Puerta de Atocha')
    await expect(ficha).toContainText('Córdoba')
  })

  test('la línea llega a Málaga, con la bifurcación Gobantes y sin continuación a trazos', async ({ page }) => {
    await page.goto('/linea/lav-cordoba-malaga')
    await expect(page.getByRole('heading', { name: 'Línea de alta velocidad Córdoba – Málaga' })).toBeVisible()
    await expect(page.locator('body')).toContainText('baja hasta Málaga-María Zambrano')
    const esquema = page.getByTestId('esquema')
    await expect(esquema).toContainText('Antequera-Santa Ana')
    await expect(esquema).toContainText('Málaga-María Zambrano')
  })

  test('el último tramo dice su señalización y recuerda la interrupción de 2026, ya terminada', async ({ page }) => {
    await page.goto('/tramo/lav-cordoba-malaga:paet-los-prados:malaga-maria-zambrano')
    const ficha = page.getByTestId('detalle-tramo')
    await expect(ficha).toBeVisible()
    await expect(page.getByTestId('tramo-vias')).toHaveText('Vía doble')
    await expect(ficha.getByText('ERTMS de niveles 1 y 2 y ASFA')).toHaveCount(1)
    // a Málaga solo llega esta línea: sus trenes no tienen otro camino en las líneas cargadas
    await expect(page.getByTestId('tramo-alternativa')).toContainText('sus 63 trenes no tendrían otro camino')
    // el corte por el desprendimiento de Álora terminó: no se dibuja, pero queda en el detalle
    await expect(ficha).toContainText('Interrupciones anteriores en este tramo')
    await expect(ficha).toContainText('desprendimiento de tierras a la altura de Álora')
  })

  test('el comparador da el recorrido de Madrid a Málaga por la alta velocidad', async ({ page }) => {
    await page.goto('/recorridos/madrid-puerta-de-atocha/malaga-maria-zambrano')
    const recorridos = page.getByTestId('recorrido')
    await expect(recorridos.first()).toBeVisible()
    await expect(recorridos.first()).toContainText('512,7 km')
    await expect(recorridos.first()).toContainText('Recorre dos líneas')
  })
})
