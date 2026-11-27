import { expect, test } from '@playwright/test'

/** El campo del buscador: en escritorio está a la vista; en el móvil lo despliega la lupa. */
async function abrirBuscador(page: import('@playwright/test').Page) {
  const lupa = page.getByTestId('buscador-abrir')
  if (await lupa.isVisible()) await lupa.click()
  return page.getByRole('combobox', { name: 'Buscar una estación o una línea' })
}

test.describe('Las líneas de Ourense a Santiago y de A Coruña a Vigo', () => {
  test('la línea de Ourense a Santiago tiene su ficha, con sus bifurcaciones en el esquema', async ({ page }) => {
    await page.goto('/linea/lav-ourense-santiago')
    await expect(page.getByRole('heading', { name: 'Línea de alta velocidad Ourense – Santiago de Compostela' })).toBeVisible()
    await expect(page.locator('body')).toContainText('Une Ourense con Santiago de Compostela en poco más de media hora')
    const esquema = page.getByTestId('esquema')
    await expect(esquema).toContainText('Ourense')
    await expect(esquema).toContainText('Santiago de Compostela')
  })

  test('la línea de A Coruña a Vigo tiene su ficha y dice que es el Eje Atlántico', async ({ page }) => {
    await page.goto('/linea/eje-atlantico')
    await expect(page.getByRole('heading', { name: 'Línea de alta velocidad A Coruña – Santiago – Vigo' })).toBeVisible()
    await expect(page.locator('body')).toContainText('Es el Eje Atlántico')
    const esquema = page.getByTestId('esquema')
    for (const estacion of ['A Coruña', 'Santiago de Compostela', 'Vilagarcía de Arousa', 'Pontevedra', 'Vigo-Urzáiz']) {
      await expect(esquema).toContainText(estacion)
    }
  })

  for (const [texto, nombre, id] of [
    ['santiago', 'Santiago de Compostela', 'santiago'],
    ['coruña', 'A Coruña', 'a-coruna'],
    ['pontevedra', 'Pontevedra', 'pontevedra'],
    ['vigo', 'Vigo-Urzáiz', 'vigo-urzaiz'],
  ]) {
    test(`el buscador lleva a ${nombre}`, async ({ page }) => {
      await page.goto('/')
      await expect(page.getByTestId('vista-red')).toBeVisible()
      const campo = await abrirBuscador(page)
      await campo.fill(texto)
      const opcion = page.getByRole('option').filter({ hasText: nombre }).filter({ hasText: 'Estación' }).first()
      await expect(opcion).toBeVisible()
      await opcion.click()
      await expect(page).toHaveURL(new RegExp(`/nodo/${id}$`))
      const ficha = page.getByTestId('detalle-nodo')
      await expect(ficha.getByRole('heading', { name: nombre })).toBeVisible()
      await expect(ficha).toContainText('Madrid-Chamartín')
    })
  }

  test('la salida de Ourense es de vía única y a 3 kV; el resto de la línea, de vía doble', async ({ page }) => {
    await page.goto('/tramo/lav-ourense-santiago:ourense:bif-coto-da-torre')
    await expect(page.getByTestId('detalle-tramo')).toBeVisible()
    const asa = page.getByRole('button', { name: 'Ampliar el panel' })
    if (await asa.isVisible()) await asa.click()
    await expect(page.getByTestId('tramo-vias')).toHaveText('Vía única')
    await expect(page.getByTestId('tramo-atributo-proteccion_tren')).toHaveText('ERTMS de nivel 1 y ASFA')
    await page.getByTestId('mas-detalle').locator('summary').click()
    await expect(page.getByTestId('mas-detalle')).toContainText('3 kV CC')
    await page.goto('/tramo/lav-ourense-santiago:bif-coto-da-torre:bif-a-grandeira')
    await expect(page.getByTestId('tramo-vias')).toHaveText('Vía doble')
  })

  test('los tramos de A Coruña a Vigo son de vía doble, con ERTMS y bloqueo automático banalizado', async ({ page }) => {
    await page.goto('/tramo/eje-atlantico:vilagarcia-de-arousa:portela')
    await expect(page.getByTestId('detalle-tramo')).toBeVisible()
    const asa = page.getByRole('button', { name: 'Ampliar el panel' })
    if (await asa.isVisible()) await asa.click()
    await expect(page.getByTestId('tramo-vias')).toHaveText('Vía doble')
    await expect(page.getByTestId('tramo-atributo-gauge')).toHaveCount(0)
    await expect(page.getByTestId('tramo-atributo-proteccion_tren')).toHaveText('ERTMS de nivel 1 y ASFA')
  })

  test('el comparador encuentra Madrid – A Coruña y Madrid – Vigo por Ourense y Santiago', async ({ page }) => {
    await page.goto('/recorridos/madrid-chamartin/a-coruna')
    const recorridos = page.getByTestId('recorrido')
    await expect(recorridos.first()).toBeVisible()
    await expect(recorridos.first()).toContainText('610,6 km')
    await expect(recorridos.first()).toContainText('Recorre cuatro líneas')
    await expect(recorridos.first().getByTestId('recorrido-trenes')).toContainText(/\d+ trenes directos en el horario del /)
    await page.goto('/recorridos/madrid-chamartin/vigo-urzaiz')
    await expect(recorridos.first()).toBeVisible()
    await expect(recorridos.first()).toContainText('639,8 km')
    await expect(recorridos.nth(1)).toContainText('643,0 km')
  })
})
