import { expect, test, type Page } from '@playwright/test'

/** El campo del buscador: en escritorio está a la vista; en el móvil lo despliega la lupa. */
async function abrirBuscador(page: Page) {
  const lupa = page.getByTestId('buscador-abrir')
  if (await lupa.isVisible()) await lupa.click()
  const campo = page.getByRole('combobox', { name: 'Buscar una estación o una línea' })
  await expect(campo).toBeVisible()
  return campo
}

test.describe('Buscar una estación o una línea', () => {
  test('«alcazar», sin acento ni mayúscula, lleva a Alcázar de San Juan', async ({ page }) => {
    await page.goto('/')
    await expect(page.getByTestId('vista-red')).toBeVisible()
    const campo = await abrirBuscador(page)
    await campo.fill('alcazar')
    const primero = page.getByRole('option').first()
    await expect(primero).toContainText('Alcázar de San Juan')
    await expect(primero).toContainText('Estación')
    await expect(primero).toHaveAttribute('aria-selected', 'true')
    await campo.press('Enter')
    await expect(page).toHaveURL(/#\/nodo\/alcazar-de-san-juan$/)
    await expect(page.getByTestId('detalle-nodo')).toBeVisible()
    await expect(page.getByRole('heading', { name: 'Alcázar de San Juan' })).toBeVisible()
    // el buscador queda recogido y vacío
    await expect(page.getByRole('option')).toHaveCount(0)
  })

  test('«Urda» lleva al PAET, y el resultado dice qué es', async ({ page }) => {
    await page.goto('/')
    await expect(page.getByTestId('vista-red')).toBeVisible()
    const campo = await abrirBuscador(page)
    await campo.fill('Urda')
    const resultado = page.getByRole('option', { name: /Urda/ })
    await expect(resultado).toContainText('Puesto de adelantamiento (PAET) · Madrid – Sevilla')
    await resultado.click()
    await expect(page).toHaveURL(/#\/nodo\/urda$/)
    await expect(page.getByTestId('detalle-nodo')).toBeVisible()
    await expect(page.getByRole('heading', { name: 'Urda' })).toBeVisible()
  })

  test('sin escribir ofrece las líneas y el glosario, y con las flechas se llega a una que queda en la URL', async ({ page }) => {
    await page.goto('/')
    await expect(page.getByTestId('vista-red')).toBeVisible()
    const campo = await abrirBuscador(page)
    await campo.focus()
    await expect(page.getByRole('option')).toHaveCount(5)
    await expect(page.getByRole('option').last()).toContainText('Glosario')
    await campo.press('ArrowDown')
    await campo.press('ArrowDown')
    await expect(page.getByRole('option').nth(2)).toHaveAttribute('aria-selected', 'true')
    await campo.press('Enter')
    await expect(page).toHaveURL(/#\/linea\/manzanares-ciudad-real$/)
    await expect(page.getByRole('heading', { name: 'Línea convencional Manzanares – Ciudad Real' })).toBeVisible()
    // la dirección sirve para volver: al recargar sigue en esa línea
    await page.reload()
    await expect(page.getByRole('heading', { name: 'Línea convencional Manzanares – Ciudad Real' })).toBeVisible()
  })

  test('admite el código de Adif y avisa cuando nada coincide', async ({ page }) => {
    await page.goto('/')
    await expect(page.getByTestId('vista-red')).toBeVisible()
    const campo = await abrirBuscador(page)
    await campo.fill('60400')
    await expect(page.getByRole('option')).toHaveCount(1)
    await expect(page.getByRole('option').first()).toContainText('Alcázar de San Juan')
    await expect(page.getByRole('option').first()).toContainText('código de Adif 60400')
    await campo.fill('zzz')
    await expect(page.getByRole('option')).toHaveCount(0)
    await expect(page.getByText('Ninguna estación, línea ni término coincide con ese nombre.')).toBeVisible()
    await campo.press('Escape')
    await expect(page.getByText('Ninguna estación, línea ni término coincide con ese nombre.')).toBeHidden()
  })

  test('la tecla «/» enfoca el buscador', async ({ page, isMobile }) => {
    test.skip(isMobile, 'El atajo es de teclado físico')
    await page.goto('/')
    await expect(page.getByTestId('vista-red')).toBeVisible()
    await page.keyboard.press('/')
    await expect(page.getByRole('combobox', { name: 'Buscar una estación o una línea' })).toBeFocused()
    await page.keyboard.type('anover')
    await expect(page.getByRole('option').first()).toContainText('Castillejo-Añover')
  })
})
