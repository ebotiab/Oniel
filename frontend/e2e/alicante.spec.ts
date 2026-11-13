import { expect, test } from '@playwright/test'

/** El campo del buscador: en escritorio está a la vista; en el móvil lo despliega la lupa. */
async function abrirBuscador(page: import('@playwright/test').Page) {
  const lupa = page.getByTestId('buscador-abrir')
  if (await lupa.isVisible()) await lupa.click()
  return page.getByRole('combobox', { name: 'Buscar una estación o una línea' })
}

test.describe('La línea de alta velocidad Albacete – Alicante', () => {
  test('el buscador lleva a Alicante y su ficha dice a dónde se llega sin cambiar de tren', async ({ page }) => {
    await page.goto('/')
    await expect(page.getByTestId('vista-red')).toBeVisible()
    const campo = await abrirBuscador(page)
    await campo.fill('alicante')
    const primero = page.getByRole('option').first()
    await expect(primero).toContainText('Alicante-Terminal')
    await expect(primero).toContainText('Estación')
    await campo.press('Enter')
    await expect(page).toHaveURL(/\/nodo\/alicante-terminal$/)
    const ficha = page.getByTestId('detalle-nodo')
    await expect(ficha.getByRole('heading', { name: 'Alicante-Terminal' })).toBeVisible()
    await expect(ficha).toContainText('Es una estación término')
    await expect(ficha).toContainText('Albacete-Los Llanos')
    await expect(ficha).toContainText('Madrid-Chamartín')
  })

  test('la línea tiene su ficha, con las dos bifurcaciones y sus estaciones en el esquema', async ({ page }) => {
    await page.goto('/linea/lav-albacete-alicante')
    await expect(page.getByRole('heading', { name: 'Línea de alta velocidad Albacete – Alicante' })).toBeVisible()
    await expect(page.locator('body')).toContainText('El ramal por el que la alta velocidad llega a Albacete y a Alicante')
    const esquema = page.getByTestId('esquema')
    await expect(esquema).toContainText('Bif. Albacete')
    await expect(esquema).toContainText('Albacete-Los Llanos')
    await expect(esquema).toContainText('Villena Alta Velocidad')
    await expect(esquema).toContainText('Bif. Murcia')
    await expect(esquema).toContainText('Alicante-Terminal')
  })

  test('al sur de Albacete la ficha dice que la protección del tren no está publicada', async ({ page }) => {
    await page.goto('/tramo/lav-albacete-alicante:albacete-los-llanos:chinchilla-av')
    const ficha = page.getByTestId('detalle-tramo')
    await expect(ficha).toBeVisible()
    await expect(page.getByTestId('tramo-operadores-sin-horarios')).toContainText('No están los trenes de Iryo')
    await expect(page.getByTestId('tramo-atributo-proteccion_tren')).toHaveText('Sin dato publicado')
    await expect(page.getByTestId('tramo-atributo-bloqueo')).toHaveText('De control automático')
  })

  test('el comparador enseña los dos caminos de Madrid a Albacete', async ({ page }) => {
    await page.goto('/recorridos/madrid-puerta-de-atocha/albacete-los-llanos')
    const recorridos = page.getByTestId('recorrido')
    await expect(recorridos.first()).toBeVisible()
    // el convencional es más corto; el de alta velocidad, por Cuenca, más rápido
    await expect(recorridos.nth(0)).toContainText('Por Alcázar de San Juan')
    await expect(recorridos.nth(0)).toContainText('277,6 km · 1 h 46 min sin paradas')
    await expect(recorridos.nth(1)).toContainText('Por Bifurcación Torrejón de Velasco y Bifurcación Albacete')
    await expect(recorridos.nth(1)).toContainText('313,6 km · 1 h 5 min sin paradas')
    await expect(recorridos.nth(1)).toContainText('Pasa por Cuenca.')
  })

  test('el comparador encuentra Madrid – Alicante por Cuenca y Albacete', async ({ page }) => {
    await page.goto('/recorridos/madrid-puerta-de-atocha/alicante-terminal')
    const recorridos = page.getByTestId('recorrido')
    await expect(recorridos.first()).toBeVisible()
    // el primero, más corto, junta la línea convencional hasta Albacete con la alta velocidad
    // desde allí; el segundo es el de alta velocidad entero, por Cuenca
    const porCuenca = recorridos.nth(1)
    await expect(porCuenca).toContainText('Por Bifurcación Torrejón de Velasco y Bifurcación Albacete')
    await expect(porCuenca).toContainText('478,4 km · 1 h 42 min sin paradas')
    await expect(porCuenca).toContainText('Pasa por Cuenca, Albacete y Villena Alta Velocidad.')
    await expect(porCuenca).toContainText('Recorre tres líneas')
  })
})
