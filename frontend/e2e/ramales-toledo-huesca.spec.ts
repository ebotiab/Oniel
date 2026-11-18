import { expect, test } from '@playwright/test'

/** El campo del buscador: en escritorio está a la vista; en el móvil lo despliega la lupa. */
async function abrirBuscador(page: import('@playwright/test').Page) {
  const lupa = page.getByTestId('buscador-abrir')
  if (await lupa.isVisible()) await lupa.click()
  return page.getByRole('combobox', { name: 'Buscar una estación o una línea' })
}

test.describe('Los ramales de alta velocidad a Toledo y a Huesca', () => {
  test('el ramal de Toledo tiene su ficha, desde la bifurcación La Sagra', async ({ page }) => {
    await page.goto('/linea/lav-la-sagra-toledo')
    await expect(page.getByRole('heading', { name: 'Línea de alta velocidad La Sagra – Toledo' })).toBeVisible()
    await expect(page.locator('body')).toContainText('Es la única vía de tren que llega hoy a la ciudad')
    const esquema = page.getByTestId('esquema')
    await expect(esquema).toContainText('La Sagra')
    await expect(esquema).toContainText('Toledo')
  })

  test('el buscador lleva a Toledo y a Huesca', async ({ page }) => {
    await page.goto('/')
    await expect(page.getByTestId('vista-red')).toBeVisible()
    const campo = await abrirBuscador(page)
    await campo.fill('toledo')
    const primero = page.getByRole('option').first()
    await expect(primero).toContainText('Toledo')
    await expect(primero).toContainText('Estación')
    await campo.press('Enter')
    await expect(page).toHaveURL(/\/nodo\/toledo$/)
    const ficha = page.getByTestId('detalle-nodo')
    await expect(ficha.getByRole('heading', { name: 'Toledo', exact: true })).toBeVisible()
    await expect(ficha).toContainText('Madrid-Puerta de Atocha')

    const otra = await abrirBuscador(page)
    await otra.fill('huesca')
    const estacion = page.getByRole('option').filter({ hasText: 'Estación' }).first()
    await expect(estacion).toContainText('Huesca')
    await estacion.click()
    await expect(page).toHaveURL(/\/nodo\/huesca$/)
  })

  test('de Tardienta a Huesca la vía es de ancho mixto, de una sola vía', async ({ page }) => {
    await page.goto('/tramo/lav-zaragoza-huesca:tardienta:huesca')
    await expect(page.getByTestId('detalle-tramo')).toBeVisible()
    const asa = page.getByRole('button', { name: 'Ampliar el panel' })
    if (await asa.isVisible()) await asa.click()
    await expect(page.getByTestId('tramo-vias')).toHaveText('Vía única')
    await expect(page.getByTestId('tramo-atributo-gauge')).toContainText('Mixto')
    await expect(page.getByTestId('tramo-atributo-proteccion_tren')).toHaveText('ASFA')
  })

  test('el comparador encuentra Madrid – Toledo y Madrid – Huesca', async ({ page }) => {
    await page.goto('/recorridos/madrid-puerta-de-atocha/toledo')
    const recorridos = page.getByTestId('recorrido')
    await expect(recorridos.first()).toBeVisible()
    await expect(recorridos.first()).toContainText('74,9 km')
    await expect(recorridos.first().getByTestId('recorrido-trenes')).toContainText(/\d+ trenes directos en el horario del /)
    await page.goto('/recorridos/madrid-puerta-de-atocha/huesca')
    await expect(recorridos.first()).toBeVisible()
    await expect(recorridos.first()).toContainText('390,7 km')
  })
})
