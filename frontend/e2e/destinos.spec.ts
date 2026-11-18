import { expect, test, type Page } from '@playwright/test'

/** En el móvil la ficha vive en la hoja inferior: hay que ampliarla para verla entera. */
async function abrirHoja(page: Page) {
  const asa = page.getByRole('button', { name: 'Ampliar el panel' })
  if (await asa.isVisible()) await asa.click()
}

test.describe('Destinos directos de una estación', () => {
  test('Ciudad Real: a dónde se llega sin cambiar de tren, del destino con más trenes al que menos', async ({ page }) => {
    await page.goto('/nodo/ciudad-real')
    await abrirHoja(page)
    const destinos = page.getByTestId('destinos-directos')
    await expect(destinos.getByRole('heading')).toHaveText('Destinos directos · 57 el viernes, 20 de noviembre de 2026')
    // a la vista, los seis más frecuentes: nombre, tipos de servicio, entre qué horas salen y cuántos trenes
    const filas = page.getByTestId('lista-destinos').getByRole('listitem')
    await expect(filas).toHaveCount(6)
    await expect(filas.nth(0)).toHaveText('CórdobaAVE, AVLO, Intercity e Iryo · de 07:55 a 22:01 · Renfe Viajeros 17, Iryo 118 trenes')
    // hacia Madrid pasan más trenes, pero una parte solo deja viajeros en Ciudad Real: se puede ir en 14 (12 de Renfe y 2 de Iryo)
    await expect(filas.nth(2)).toContainText('Madrid-Puerta de Atocha')
    await expect(filas.nth(2)).toContainText('14 trenes')
    // los horarios son los publicados, y los de Iryo salen de una compilación no oficial
    await expect(page.getByTestId('destinos-nota-horario')).toBeVisible()
    await expect(page.getByTestId('destinos-no-oficiales')).toHaveText('Los trenes de Iryo salen de una compilación no oficial de sus horarios, que no publica el operador.')
    await expect(page.getByTestId('destinos-sin-horarios')).toHaveCount(0)
    // el resto, a un toque
    await page.getByTestId('destinos-ver-todos').click()
    await expect(filas).toHaveCount(57)
    // Málaga es ya una estación de la red: lleva a su ficha. Ya no está entre los seis primeros
    const malaga = filas.filter({ hasText: 'Málaga' })
    await expect(malaga).toContainText('5 trenes')
    // en una estación con trenes de dos operadores, cada destino dice de quién son los suyos, aunque sean de uno solo
    await expect(malaga).toContainText('· Renfe Viajeros')
    await expect(malaga.getByRole('button')).toHaveCount(1)
    // a Badajoz van dos: desde que las líneas de Extremadura están cargadas cuenta también el
    // tren de las 11:58, además del de las 16:48; el horario rotula «Regional» los dos
    await expect(filas.filter({ hasText: 'Badajoz' })).toHaveText('BadajozRegional · de 11:58 a 16:48 · Renfe Viajeros2 trenes')
    await expect(page.getByTestId('destinos-ver-todos')).toHaveText('Ver solo los más frecuentes')
    // un destino de la red lleva a su ficha
    await page.getByTestId('destino-puertollano').click()
    await expect(page).toHaveURL(/\/nodo\/puertollano$/)
    await expect(page.getByTestId('detalle-nodo').getByRole('heading', { level: 2 })).toHaveText('Puertollano')
    await expect(page.getByTestId('destinos-directos').getByRole('heading')).toContainText('Destinos directos · 44 el')
  })

  test('Madrid: con varios operadores, cada destino dice de quién son sus trenes', async ({ page }) => {
    await page.goto('/nodo/madrid-puerta-de-atocha')
    await abrirHoja(page)
    const filas = page.getByTestId('lista-destinos').getByRole('listitem')
    await expect(filas.nth(0)).toContainText('Córdoba')
    await expect(filas.nth(0)).toContainText('de 06:50 a 21:20 · Renfe Viajeros 39, Iryo 14, Ouigo España 6')
    await expect(filas.nth(0)).toContainText('59 trenes')
    await expect(filas.nth(1)).toContainText('Barcelona-Sants')
    await expect(filas.nth(1)).toContainText('Renfe Viajeros 24, Iryo 15, Ouigo España 6')
    // un destino con trenes de un solo operador también lo nombra
    await page.getByTestId('destinos-ver-todos').click()
    await expect(filas.filter({ hasText: 'Badajoz' })).toContainText('· Renfe Viajeros')
    // y los de Toledo, solo de Renfe, desde que está cargado su ramal
    await expect(filas.filter({ hasText: /^Toledo/ })).toContainText('15 trenes')
    await expect(filas.filter({ hasText: /^Toledo/ })).toContainText('· Renfe Viajeros')
  })

  test('el comparador de recorridos cuenta los mismos trenes directos que la ficha', async ({ page }) => {
    await page.goto('/recorridos/ciudad-real/madrid-puerta-de-atocha')
    await abrirHoja(page)
    await expect(page.getByTestId('recorridos-resumen')).toContainText('Hay 14 trenes directos en este sentido')
    await page.goto('/recorridos/madrid-puerta-de-atocha/cordoba')
    await expect(page.getByTestId('recorridos-resumen')).toContainText('Hay 59 trenes directos en este sentido')
  })

  test('un nodo que no es estación no tiene destinos; el detalle de una estación dice cómo se cuentan', async ({ page }) => {
    await page.goto('/nodo/urda')
    await abrirHoja(page)
    await expect(page.getByTestId('detalle-nodo')).toBeVisible()
    await expect(page.getByTestId('destinos-directos')).toHaveCount(0)
    await page.goto('/nodo/daimiel')
    await expect(page.getByTestId('destinos-directos')).toBeVisible()
    // en una línea solo de Renfe no falta ningún operador ni hay trenes de una fuente no oficial
    await expect(page.getByTestId('destinos-sin-horarios')).toHaveCount(0)
    await expect(page.getByTestId('destinos-no-oficiales')).toHaveCount(0)
    const detalle = page.getByTestId('mas-detalle')
    await detalle.locator('summary').click()
    await expect(detalle).toContainText('Un destino directo es una estación en la que para, después de esta, un tren al que se puede subir aquí.')
    await expect(detalle.getByTestId('pie-fuente').last()).toContainText(/Fuente de los horarios: Renfe/)
  })
})
