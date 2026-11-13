import { expect, test } from '@playwright/test'

/** El campo del buscador: en escritorio está a la vista; en el móvil lo despliega la lupa. */
async function abrirBuscador(page: import('@playwright/test').Page) {
  const lupa = page.getByTestId('buscador-abrir')
  if (await lupa.isVisible()) await lupa.click()
  return page.getByRole('combobox', { name: 'Buscar una estación o una línea' })
}

test.describe('La línea de alta velocidad Madrid – Cuenca – Valencia', () => {
  test('el buscador lleva a Cuenca y su ficha dice a dónde se llega sin cambiar de tren', async ({ page }) => {
    await page.goto('/')
    await expect(page.getByTestId('vista-red')).toBeVisible()
    const campo = await abrirBuscador(page)
    await campo.fill('cuenca')
    const primero = page.getByRole('option').first()
    await expect(primero).toContainText('Cuenca-Fernando Zóbel')
    await expect(primero).toContainText('Estación')
    await campo.press('Enter')
    await expect(page).toHaveURL(/\/nodo\/cuenca-fernando-zobel$/)
    const ficha = page.getByTestId('detalle-nodo')
    await expect(ficha.getByRole('heading', { name: 'Cuenca-Fernando Zóbel' })).toBeVisible()
    await expect(ficha).toContainText('La estación de alta velocidad de Cuenca')
    // destinos directos del día de referencia: los dos caminos de Levante
    await expect(ficha).toContainText('València-Joaquín Sorolla')
    await expect(ficha).toContainText('Albacete-Los Llanos')
  })

  test('la línea tiene su ficha, con la bifurcación de Albacete y sus estaciones en el esquema', async ({ page }, testInfo) => {
    await page.goto('/linea/lav-madrid-valencia')
    await expect(page.getByRole('heading', { name: 'Línea de alta velocidad Madrid – Cuenca – Valencia' })).toBeVisible()
    await expect(page.locator('body')).toContainText('Sale de la línea Madrid – Sevilla en Torrejón de Velasco')
    const esquema = page.getByTestId('esquema')
    await expect(esquema).toContainText('Bif. Torrejón de Velasco')
    await expect(esquema).toContainText('Cuenca-Fernando Zóbel')
    await expect(esquema).toContainText('Bif. Albacete')
    await expect(esquema).toContainText('Requena-Utiel')
    await expect(esquema).toContainText('València-Joaquín Sorolla')
    // los recuentos del esquema son de Renfe y de Ouigo; faltan los de Iryo (el esquema compacto del móvil no lleva la nota)
    if (testInfo.project.name !== 'movil') await expect(page.getByTestId('nota-esquema')).toContainText('no incluyen los de Iryo')
  })

  test('un tramo dice sus trenes por operador, que faltan los de Iryo y su señalización', async ({ page }) => {
    await page.goto('/tramo/lav-madrid-valencia:horcajada:cuenca-fernando-zobel')
    const ficha = page.getByTestId('detalle-tramo')
    await expect(ficha).toBeVisible()
    await expect(page.getByTestId('tramo-vias')).toHaveText('Vía doble')
    await expect(page.getByTestId('tramo-operadores')).toHaveText(/^Renfe Viajeros \d+ · Ouigo España \d+$/)
    await expect(page.getByTestId('tramo-operadores-sin-horarios')).toContainText('No están los trenes de Iryo')
    // la señalización va bajo «Más detalle»: está en la ficha aunque plegada
    await expect(page.getByTestId('tramo-atributo-proteccion_tren')).toHaveText('ERTMS de nivel 1 y ASFA')
    await expect(page.getByTestId('tramo-atributo-bloqueo')).toHaveText('De control automático')
  })

  test('el último tramo dice que el bloqueo cambia a la entrada de Valencia', async ({ page }) => {
    await page.goto('/tramo/lav-madrid-valencia:siete-aguas-av:valencia-joaquin-sorolla')
    await expect(page.getByTestId('detalle-tramo')).toBeVisible()
    await expect(page.getByTestId('tramo-atributo-bloqueo')).toHaveText(
      'De control automático en una parte y de señalización lateral en otra',
    )
  })

  test('el comparador encuentra Madrid – Valencia y Madrid – Cuenca por la bifurcación de Torrejón de Velasco', async ({ page }) => {
    await page.goto('/recorridos/madrid-puerta-de-atocha/valencia-joaquin-sorolla')
    const recorridos = page.getByTestId('recorrido')
    await expect(recorridos.first()).toBeVisible()
    await expect(recorridos.first()).toContainText('389,7 km')
    await expect(recorridos.first()).toContainText('Pasa por Cuenca y Requena-Utiel')
    await expect(recorridos.first()).toContainText('Recorre dos líneas')
    await page.goto('/recorridos/madrid-puerta-de-atocha/cuenca-fernando-zobel')
    await expect(recorridos.first()).toBeVisible()
    await expect(recorridos.first()).toContainText('187,7 km')
    await expect(recorridos.first()).toContainText('Recorre dos líneas')
  })
})
