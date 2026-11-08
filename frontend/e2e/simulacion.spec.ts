import { expect, test } from '@playwright/test'

const estatico = Boolean(process.env.ONIEL_E2E_STATIC)

test.describe('Simular un cierre', () => {
  test.skip(estatico, 'la simulación necesita la API')

  test('el caso calculado a mano: AVE 02070, Villanueva–Adamuz, 13/11/2026 de 8:00 a 9:00', async ({ page }) => {
    await page.goto('/#/tramo/lav-madrid-sevilla:villanueva-de-cordoba:adamuz')
    await page.getByTestId('boton-simular').click()
    await expect(page.getByTestId('panel-simulacion')).toBeVisible()
    await page.getByTestId('sim-fecha').fill('2026-11-13')
    await page.getByTestId('sim-inicio').fill('08:00')
    await page.getByTestId('sim-fin').fill('09:00')
    await page.getByTestId('sim-calcular').click()
    const resultado = page.getByTestId('sim-resultado')
    await expect(resultado).toBeVisible()
    await expect(resultado).toContainText(/trenes afectados/)
    await expect(resultado).toContainText(/afectados con paso estimado/i)
    // el AVE 02070 aparece como afectado con paso estimado entre las 8:34 y las 8:44
    const fila = resultado.locator('li', { hasText: 'AVE 02070' }).first()
    await expect(fila).toBeVisible()
    await expect(fila).toContainText('08:34')
    await expect(fila).toContainText('08:44')
    await fila.getByText('Por qué').click()
    await expect(fila).toContainText(/en proporción a la distancia/)
    // la explicación del método está disponible
    await page.getByRole('button', { name: 'Cómo se calcula' }).click()
    await expect(page.getByText(/margen del 15 %/)).toBeVisible()
    await expect(page).toHaveURL(/\/cierre$/)
  })

  test('una ventana sin trenes devuelve cero afectados', async ({ page }) => {
    await page.goto('/#/tramo/lav-madrid-sevilla:ciudad-real:puertollano/cierre')
    await page.getByTestId('sim-fecha').fill('2026-11-13')
    await page.getByTestId('sim-inicio').fill('02:00')
    await page.getByTestId('sim-fin').fill('04:00')
    await page.getByTestId('sim-calcular').click()
    const resultado = page.getByTestId('sim-resultado')
    await expect(resultado).toContainText(/^0 trenes afectados/)
  })
})
