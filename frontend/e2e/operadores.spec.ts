import { expect, test } from '@playwright/test'

test.describe('Trenes por operador', () => {
  test('un tramo de la convencional dice que todos sus trenes son de Renfe', async ({ page }) => {
    await page.goto('/tramo/convencional-madrid-alcazar-cordoba:alcazar-de-san-juan:cinco-casas')
    const asa = page.getByRole('button', { name: 'Ampliar el panel' })
    if (await asa.isVisible()) await asa.click() // en móvil, la hoja empieza plegada
    await expect(page.getByTestId('detalle-tramo')).toBeVisible()
    await expect(page.getByTestId('tramo-operadores')).toHaveText('Solo Renfe Viajeros')
    await expect(page.getByTestId('tramo-operadores-sin-horarios')).toHaveCount(0)
    // con un solo operador la lista no se parte ni lleva cabeceras
    await expect(page.getByTestId('trenes-renfe').locator('li').first()).toBeVisible()
    await expect(page.getByTestId('lista-servicios').getByRole('heading')).toHaveCount(0)
  })

  test('un tramo de la alta velocidad dice de quién son sus trenes y cuáles faltan', async ({ page }, testInfo) => {
    await page.goto('/tramo/lav-madrid-sevilla:ciudad-real:puertollano')
    const asa = page.getByRole('button', { name: 'Ampliar el panel' })
    if (await asa.isVisible()) await asa.click()
    await expect(page.getByTestId('detalle-tramo')).toBeVisible()
    // lo primero, el reparto: los trenes del día de referencia, del operador que más tiene al que menos
    await expect(page.getByTestId('tramo-operadores')).toHaveText('Renfe Viajeros 102 · Ouigo España 11')
    // Iryo opera en la línea y no publica sus horarios: el panel dice que sus trenes no están
    await expect(page.getByTestId('tramo-operadores-sin-horarios')).toHaveText(
      'No están los trenes de Iryo, que también opera en esta línea: no publica sus horarios en un formato abierto.',
    )
    // la lista va agrupada por operador, cada grupo con su nombre y su cifra
    const lista = page.getByTestId('lista-servicios')
    await expect(lista.getByRole('heading')).toHaveText(['Renfe Viajeros · 102', 'Ouigo España · 11'])
    await expect(page.getByTestId('trenes-renfe').locator('li')).toHaveCount(102)
    await expect(page.getByTestId('trenes-ouigo').locator('li')).toHaveCount(11)
    await expect(page.getByTestId('trenes-ouigo').locator('li').first()).toContainText('Ouigo 6476')
    await expect(page.getByTestId('trenes-ouigo')).toContainText('Madrid-Puerta de Atocha → Málaga')
    await expect(page.getByTestId('trenes-iryo')).toHaveCount(0)
    // la barra del esquema lleva el total de todos los operadores
    await page.getByRole('button', { name: '← Toda la línea' }).click()
    if (testInfo.project.name !== 'movil') await expect(page.getByTestId('esquema-tramo-7')).toContainText('113')
  })

  test('la nota del esquema dice de quién son los trenes de las barras', async ({ page }, testInfo) => {
    test.skip(testInfo.project.name === 'movil', 'el esquema compacto del móvil no lleva la nota')
    await page.goto('/linea/lav-madrid-sevilla')
    await expect(page.getByTestId('nota-esquema')).toContainText('según los horarios de Ouigo España y Renfe Viajeros; no incluyen los de Iryo.')
    await page.goto('/linea/manzanares-ciudad-real')
    await expect(page.getByTestId('nota-esquema')).toContainText('según los horarios de Renfe Viajeros. ')
  })

  test('la cobertura enumera los operadores con su fuente y la validez de sus horarios', async ({ page }) => {
    await page.goto('/cobertura')
    const operadores = page.getByTestId('cobertura-operadores')
    await expect(operadores.getByRole('listitem').filter({ hasText: 'Renfe Viajeros' })).toContainText(/data\.renfe\.com\) · CC BY 4\.0 · válidos del .* de 2026 al .* de 2027/)
    await expect(operadores.getByRole('listitem').filter({ hasText: 'Ouigo España' })).toContainText(/Punto de Acceso Nacional.*válidos del .* de junio de 2026 al .* de diciembre de 2026/)
    await expect(operadores.getByRole('listitem').filter({ hasText: 'Iryo' })).toContainText('No publica sus horarios en un formato abierto')
    // el administrador de la infraestructura no es un operador de trenes
    await expect(operadores).not.toContainText('Adif')
  })
})
