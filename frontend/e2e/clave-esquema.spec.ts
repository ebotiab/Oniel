import { expect, test } from '@playwright/test'

test.describe('Clave del esquema: cada símbolo dice qué es', () => {
  test('la alta velocidad enseña estación, puestos técnicos, bifurcación y conexión, y cada nombre abre su nota', async ({ page }) => {
    await page.goto('/linea/lav-madrid-sevilla')
    await expect(page.getByTestId('esquema')).toBeVisible()
    const asa = page.getByRole('button', { name: 'Ampliar el panel' })
    if (await asa.isVisible()) await asa.click()
    const clave = page.getByTestId('clave-esquema')
    await clave.scrollIntoViewIfNeeded()
    await expect(clave).toBeVisible()
    await expect(clave.getByRole('listitem')).toHaveText(['Estación', 'Puesto técnico: PAET, puesto de banalización o cambiador de ancho', 'Bifurcación', 'Conexión con otra línea'])
    // cada símbolo va dibujado junto a su nombre, en renglón: si la hoja de estilos se rompe, deja de serlo
    await expect(clave).toHaveCSS('display', 'flex')
    await expect(clave.locator('svg')).toHaveCount(4)
    // la clave cabe en el panel, también en el móvil
    const caja = (await clave.boundingBox())!
    expect(caja.x).toBeGreaterThanOrEqual(0)
    expect(caja.x + caja.width).toBeLessThanOrEqual(page.viewportSize()!.width)
    // el nombre es un término del glosario: un toque abre su definición
    await clave.getByRole('button', { name: 'PAET' }).click()
    const nota = page.getByTestId('termino-nota')
    await expect(nota).toBeVisible()
    await expect(nota).toContainText('donde un tren puede detenerse para que otro lo adelante')
  })

  test('solo salen los símbolos que tiene la línea', async ({ page }) => {
    await page.goto('/linea/manzanares-ciudad-real')
    await expect(page.getByTestId('esquema')).toBeVisible()
    await expect(page.getByTestId('clave-esquema').getByRole('listitem')).toHaveText(['Estación', 'Conexión con otra línea'])
    await page.goto('/linea/convencional-madrid-alcazar-cordoba')
    await expect(page.getByTestId('clave-esquema').getByRole('listitem')).toHaveText(['Estación', 'Punto de referencia', 'Bifurcación', 'Conexión con otra línea'])
  })
})
