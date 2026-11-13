import { expect, test } from '@playwright/test'

const estatico = Boolean(process.env.ONIEL_E2E_STATIC)

test.describe('Simular un cierre', () => {
  test.skip(estatico, 'la simulación necesita la API')

  test('el caso calculado a mano: AVE 02070, Villanueva–Adamuz, 13/11/2026 de 8:00 a 9:00', async ({ page }) => {
    await page.goto('/tramo/lav-madrid-sevilla:villanueva-de-cordoba:adamuz')
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
    // la línea convencional por Alcázar une Madrid y Córdoba a ambos lados del tramo cerrado
    const alternativa = page.getByTestId('sim-alternativa')
    await expect(alternativa).toBeVisible()
    await expect(alternativa).toContainText('Madrid-Puerta de Atocha')
    await expect(alternativa).toContainText('Córdoba')
    await expect(alternativa).toContainText('Alcázar de San Juan')
    await expect(alternativa).toContainText(/vía única/)
    // la explicación del método está disponible
    await page.getByRole('button', { name: 'Cómo se calcula' }).click()
    await expect(page.getByText(/margen del 15 %/)).toBeVisible()
    await expect(page).toHaveURL(/\/cierre$/)
  })

  test('un cierre en Despeñaperros señala la alta velocidad como alternativa', async ({ page }) => {
    await page.goto('/tramo/convencional-madrid-alcazar-cordoba:venta-de-cardenas:vilches/cierre')
    await page.getByTestId('sim-fecha').fill('2026-11-13')
    await page.getByTestId('sim-inicio').fill('07:00')
    await page.getByTestId('sim-fin').fill('10:00')
    await page.getByTestId('sim-calcular').click()
    const resultado = page.getByTestId('sim-resultado')
    await expect(resultado).toBeVisible()
    await expect(resultado).toContainText(/MD \d{5}/)
    await expect(page.getByTestId('sim-alternativa')).toContainText(/alta velocidad Madrid – Sevilla/)
  })

  test('un cierre entre Almagro y Ciudad Real afecta a los Intercity desviados por Manzanares', async ({ page }) => {
    await page.goto('/tramo/manzanares-ciudad-real:almagro:ciudad-real/cierre')
    await page.getByTestId('sim-fecha').fill('2026-11-13')
    await page.getByTestId('sim-inicio').fill('08:00')
    await page.getByTestId('sim-fin').fill('09:00')
    await page.getByTestId('sim-calcular').click()
    const resultado = page.getByTestId('sim-resultado')
    await expect(resultado).toBeVisible()
    await expect(resultado).toContainText(/trenes afectados/)
    // el Intercity 10270 llega a Ciudad Real a las 8:35 publicadas; su entrada en el tramo es estimada
    const fila = resultado.locator('li', { hasText: 'Intercity 10270' }).first()
    await expect(fila).toBeVisible()
    await expect(fila).toContainText('08:22–08:35')
    await fila.getByText('Por qué').click()
    await expect(fila).toContainText(/dentro de la ventana/)
    await expect(fila).toContainText(/entra en esta línea por Manzanares/)
    await expect(fila).toContainText(/196 km por esa línea hasta Madrid-Atocha Cercanías/)
    await expect(fila).not.toContainText(/línea recta/)
    await expect(resultado).toContainText(/MD \d{5}/)
    // ninguna línea sola une los dos lados de este tramo; el rodeo encadena dos
    const alternativa = page.getByTestId('sim-alternativa')
    await expect(alternativa).toContainText(/encadena 2 líneas/)
    await expect(alternativa).toContainText(/hasta Madrid-Puerta de Atocha y línea de alta velocidad Madrid – Sevilla hasta Ciudad Real/)
    await expect(alternativa).toContainText(/366,9 km frente a 64,4 km/)
    // el de Córdoba (417,4 km) también se enseña; la vuelta por Granada y Córdoba, de más del doble, no
    await expect(alternativa.locator('p.texto:not(.suave)')).toHaveCount(2)
    await expect(page.getByTestId('sim-alternativa-omitidas')).toHaveText(/^Existe otro recorrido más largo, que no se enseña/)
  })

  test('un cierre entre Urda y Ciudad Real señala el desvío por Manzanares, que usa dos líneas', async ({ page }) => {
    await page.goto('/tramo/lav-madrid-sevilla:urda:ciudad-real/cierre')
    await page.getByTestId('sim-fecha').fill('2026-11-13')
    await page.getByTestId('sim-inicio').fill('08:00')
    await page.getByTestId('sim-fin').fill('09:00')
    await page.getByTestId('sim-calcular').click()
    const alternativa = page.getByTestId('sim-alternativa')
    await expect(alternativa).toBeVisible()
    const desvio = alternativa.locator('p.texto').first()
    await expect(desvio).toContainText('Madrid-Puerta de Atocha')
    await expect(desvio).toContainText(/encadena 2 líneas: línea convencional Madrid – Alcázar de San Juan – Córdoba hasta Manzanares y línea convencional Manzanares – Ciudad Real hasta Ciudad Real/)
    await expect(desvio).toContainText(/260,5 km frente a 170,8 km por la línea cerrada, con 64,4 km de vía única/)
    // la convencional entera, de Madrid a Córdoba, sigue apareciendo como antes
    await expect(alternativa.locator('p.texto:not(.suave)')).toHaveCount(2)
    await expect(alternativa.locator('p.texto').nth(1)).toContainText(/existe otra línea: línea convencional Madrid – Alcázar de San Juan – Córdoba, por Aranjuez/)
    // la vuelta por Granada hasta la bifurcación de Málaga (698 km frente a 358) existe, pero no se lista
    await expect(alternativa).not.toContainText('Granada')
    await expect(page.getByTestId('sim-alternativa-omitidas')).toHaveText(/^Existe otro recorrido más largo, que no se enseña: da un rodeo de más del doble/)
  })

  test('una ventana sin trenes devuelve cero afectados', async ({ page }) => {
    await page.goto('/tramo/lav-madrid-sevilla:ciudad-real:puertollano/cierre')
    await page.getByTestId('sim-fecha').fill('2026-11-13')
    await page.getByTestId('sim-inicio').fill('02:00')
    await page.getByTestId('sim-fin').fill('04:00')
    await page.getByTestId('sim-calcular').click()
    const resultado = page.getByTestId('sim-resultado')
    await expect(resultado).toContainText(/^0 trenes afectados/)
  })
})
