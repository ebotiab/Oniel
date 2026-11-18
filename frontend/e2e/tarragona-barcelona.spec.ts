import { expect, test } from '@playwright/test'

/** El campo del buscador: en escritorio está a la vista; en el móvil lo despliega la lupa. */
async function abrirBuscador(page: import('@playwright/test').Page) {
  const lupa = page.getByTestId('buscador-abrir')
  if (await lupa.isVisible()) await lupa.click()
  return page.getByRole('combobox', { name: 'Buscar una estación o una línea' })
}

const LINEA = 'tarragona-barcelona'

test.describe('La línea Tarragona – Vilanova i la Geltrú – Barcelona', () => {
  test('la línea tiene su ficha, con Tarragona, Sant Vicenç y Barcelona-Sants en el esquema', async ({ page }) => {
    await page.goto(`/linea/${LINEA}`)
    await expect(page.getByRole('heading', { name: 'Línea convencional Tarragona – Vilanova i la Geltrú – Barcelona' })).toBeVisible()
    await expect(page.locator('body')).toContainText('Une Tarragona con Barcelona por la costa')
    const esquema = page.getByTestId('esquema')
    for (const estacion of ['Bif. La Feredat', 'Tarragona', 'Sant Vicenç de Calders', 'Vilanova i la Geltrú', 'Barcelona-Sants']) {
      await expect(esquema).toContainText(estacion)
    }
  })

  for (const [texto, nombre, id] of [
    ['tarragona', 'Tarragona', 'tarragona'],
    ['vilanova', 'Vilanova i la Geltrú', 'vilanova-i-la-geltru'],
  ]) {
    test(`el buscador lleva a ${nombre}`, async ({ page }) => {
      await page.goto('/')
      await expect(page.getByTestId('vista-red')).toBeVisible()
      const campo = await abrirBuscador(page)
      await campo.fill(texto)
      const opcion = page.getByRole('option').filter({ hasText: new RegExp(`^${nombre}`) }).filter({ hasText: 'Estación' }).first()
      await expect(opcion).toBeVisible()
      await opcion.click()
      await expect(page).toHaveURL(new RegExp(`/nodo/${id}$`))
      const ficha = page.getByTestId('detalle-nodo')
      await expect(ficha.getByRole('heading', { name: nombre, exact: true })).toBeVisible()
      // destinos directos del día de referencia, hacia los dos lados
      await expect(ficha).toContainText('Barcelona-Sants')
      await expect(ficha).toContainText('Tortosa')
    })
  }

  test('de La Feredat ya no sale una conexión a trazos hacia la costa: sale esta línea', async ({ page }) => {
    await page.goto('/nodo/bif-la-feredat')
    const ficha = page.getByTestId('detalle-nodo')
    await expect(ficha.getByRole('heading', { name: 'Bifurcación La Feredat' })).toBeVisible()
    await expect(ficha).not.toContainText('Línea convencional por Tarragona y la costa')
    await expect(ficha).toContainText('Tarragona – Vilanova i la Geltrú – Barcelona')
  })

  test('de Sant Vicenç de Calders salen a trazos las líneas de Valls y de Vilafranca', async ({ page }) => {
    await page.goto('/nodo/sant-vicenc-de-calders')
    const ficha = page.getByTestId('detalle-nodo')
    await expect(ficha.getByRole('heading', { name: 'Sant Vicenç de Calders' })).toBeVisible()
    await expect(ficha).toContainText('Valls')
    await expect(ficha).toContainText('Vilafranca del Penedès')
  })

  test('el enlace de La Feredat es de vía única; el resto, de vía doble con ASFA', async ({ page }) => {
    const asa = page.getByRole('button', { name: 'Ampliar el panel' })
    await page.goto(`/tramo/${LINEA}:bif-la-feredat:bif-vila-seca`)
    await expect(page.getByTestId('detalle-tramo')).toBeVisible()
    if (await asa.isVisible()) await asa.click()
    await expect(page.getByTestId('tramo-vias')).toHaveText('Vía única')
    await page.goto(`/tramo/${LINEA}:sant-vicenc-de-calders:vilanova-i-la-geltru`)
    await expect(page.getByTestId('detalle-tramo')).toBeVisible()
    if (await asa.isVisible()) await asa.click()
    await expect(page.getByTestId('tramo-vias')).toHaveText('Vía doble')
    await expect(page.getByTestId('tramo-atributo-proteccion_tren')).toHaveText('ASFA')
  })

  test('el comparador da València – Barcelona por la costa hasta Sants', async ({ page }) => {
    await page.goto('/recorridos/valencia-estacio-del-nord/barcelona-sants')
    const recorridos = page.getByTestId('recorrido')
    await expect(recorridos.first()).toBeVisible()
    await expect(recorridos.first()).toContainText('345,9 km')
    await expect(recorridos.first()).toContainText('Recorre dos líneas')
    await expect(recorridos.first()).toContainText('Vilanova i la Geltrú')
    await expect(recorridos.first().getByTestId('recorrido-trenes')).toContainText(/\d+ (tren directo|trenes directos) en el horario del /)

    await page.goto('/recorridos/tarragona/barcelona-sants')
    await expect(recorridos.first()).toContainText('84,3 km')
    await expect(recorridos.first().getByTestId('recorrido-trenes')).toContainText(/\d+ (tren directo|trenes directos) en el horario del /)
  })
})
