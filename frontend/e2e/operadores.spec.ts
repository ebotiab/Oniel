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

  test('un tramo de la alta velocidad dice de quién son sus trenes y cuáles salen de una fuente no oficial', async ({ page }, testInfo) => {
    await page.goto('/tramo/lav-madrid-sevilla:ciudad-real:puertollano')
    const asa = page.getByRole('button', { name: 'Ampliar el panel' })
    if (await asa.isVisible()) await asa.click()
    await expect(page.getByTestId('detalle-tramo')).toBeVisible()
    // lo primero, el reparto: los trenes del día de referencia, del operador que más tiene al que menos (6 de Renfe son los de Madrid a Sevilla y a Cádiz que no paran en Córdoba)
    await expect(page.getByTestId('tramo-operadores')).toHaveText('Renfe Viajeros 92 · Iryo 28 · Ouigo España 12')
    // Iryo no publica sus horarios: sus trenes salen de una compilación no oficial y el panel lo dice
    await expect(page.getByTestId('tramo-operadores-no-oficiales')).toHaveText('Los trenes de Iryo salen de una compilación no oficial de sus horarios, que no publica el operador.')
    await expect(page.getByTestId('tramo-operadores-sin-horarios')).toHaveCount(0)
    // la lista va agrupada por operador, cada grupo con su nombre y su cifra
    const lista = page.getByTestId('lista-servicios')
    await expect(lista.getByRole('heading')).toHaveText(['Renfe Viajeros · 92', 'Iryo · 28', 'Ouigo España · 12'])
    await expect(page.getByTestId('trenes-renfe').locator('li')).toHaveCount(92)
    await expect(page.getByTestId('trenes-ouigo').locator('li')).toHaveCount(12)
    await expect(page.getByTestId('trenes-ouigo').locator('li').first()).toContainText('Ouigo 6476')
    await expect(page.getByTestId('trenes-ouigo')).toContainText('Madrid-Puerta de Atocha → Málaga-María Zambrano')
    await expect(page.getByTestId('trenes-iryo').locator('li')).toHaveCount(28)
    // sus trenes llevan el nombre de las estaciones que usa el resto, no el del fichero
    await expect(page.getByTestId('trenes-iryo').locator('li').first()).toContainText(/Iryo 06\d{3}/)
    await expect(page.getByTestId('trenes-iryo')).toContainText('Madrid-Puerta de Atocha')
    await expect(page.getByTestId('trenes-iryo')).not.toContainText('Madrid Atocha')
    // la barra del esquema lleva el total de todos los operadores
    await page.getByRole('button', { name: '← Toda la línea' }).click()
    if (testInfo.project.name !== 'movil') await expect(page.getByTestId('esquema-tramo-7')).toContainText('132')
  })

  test('la nota del esquema dice de quién son los trenes de las barras', async ({ page }, testInfo) => {
    test.skip(testInfo.project.name === 'movil', 'el esquema compacto del móvil no lleva la nota')
    await page.goto('/linea/lav-madrid-sevilla')
    await expect(page.getByTestId('nota-esquema')).toContainText('según los horarios de Iryo, Ouigo España y Renfe Viajeros; los de Iryo, de una compilación no oficial.')
    await page.goto('/linea/manzanares-ciudad-real')
    await expect(page.getByTestId('nota-esquema')).toContainText('según los horarios de Renfe Viajeros. ')
  })

  test('la cobertura enumera los operadores con su fuente y la validez de sus horarios', async ({ page }) => {
    await page.goto('/cobertura')
    const operadores = page.getByTestId('cobertura-operadores')
    // el estado, en una frase; debajo, la ficha de la fuente: quién la publica, la licencia y el día de la descarga
    const renfe = operadores.getByTestId('operador-renfe')
    await expect(renfe).toContainText(/Horarios cargados, válidos del .* de 2026 al .* de 2027\./)
    await expect(renfe).toContainText('Renfe Viajeros (data.renfe.com)')
    await expect(renfe.getByRole('link', { name: 'CC BY 4.0' })).toBeVisible()
    await expect(renfe).toContainText(/Descargado\s*el \d+ de \S+ de 2026/)
    const ouigo = operadores.getByTestId('operador-ouigo')
    await expect(ouigo).toContainText(/Horarios cargados, válidos del .* de junio de 2026 al .* de diciembre de 2026\./)
    await expect(ouigo).toContainText('Punto de Acceso Nacional')
    const sncf = operadores.getByTestId('operador-sncf')
    await expect(sncf).toContainText('SNCF Voyageurs')
    await expect(sncf).toContainText('Horarios cargados, válidos del 25 de noviembre de 2026 al 30 de abril de 2027.')
    await expect(sncf.getByRole('link', { name: 'ODbL 1.0' })).toBeVisible()
    await expect(sncf.getByRole('link', { name: /Horarios de SNCF/ })).toHaveAttribute('href', 'https://transport.data.gouv.fr/datasets/horaires-sncf')
    // los de Iryo salen de una compilación no oficial: lo dice el estado, y la ficha, quién la compila y con qué licencia
    const iryo = operadores.getByTestId('operador-iryo')
    await expect(iryo).toContainText('Horarios cargados de una compilación no oficial, que no publica el operador, válidos del 5 de noviembre de 2026 al 11 de diciembre de 2027.')
    await expect(iryo).toContainText('compilación no oficial y sin vínculo con Iryo')
    await expect(iryo.getByRole('link', { name: /CC BY 4\.0, solo sobre el trabajo de compilación/ })).toBeVisible()
    await expect(page.getByText('Los horarios son los que publica cada operador. Los trenes de Iryo salen de una compilación no oficial', { exact: false })).toBeVisible()
    // primero los que tienen horarios de una fuente oficial
    await expect(operadores.locator('> div').last()).toHaveAttribute('data-testid', 'operador-iryo')
    // el administrador de la infraestructura no es un operador de trenes
    await expect(operadores).not.toContainText('Adif')
  })
})
