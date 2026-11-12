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
    await expect(destinos.getByRole('heading')).toHaveText('Destinos directos · 55 el viernes, 13 de noviembre de 2026')
    // a la vista, los seis más frecuentes: nombre, tipos de servicio, entre qué horas salen y cuántos trenes
    const filas = page.getByTestId('lista-destinos').getByRole('listitem')
    await expect(filas).toHaveCount(6)
    await expect(filas.nth(0)).toHaveText('CórdobaIntercity, AVE, AVLO y ALVIA · de 07:55 a 22:0122 trenes')
    // hacia Madrid pasan 23 trenes, pero 11 solo dejan viajeros en Ciudad Real: se puede ir en 12
    await expect(filas.nth(1)).toContainText('Madrid-Puerta de Atocha')
    await expect(filas.nth(1)).toContainText('12 trenes')
    // con un solo operador no se nombra
    await expect(filas.nth(0)).not.toContainText('Renfe')
    // un destino fuera de la red cargada se nombra, sin enlace
    const malaga = filas.filter({ hasText: 'Málaga' })
    await expect(malaga).toContainText('9 trenes')
    await expect(malaga.getByRole('button')).toHaveCount(0)
    // los horarios son los publicados y faltan los de quien no los publica
    await expect(page.getByTestId('destinos-nota-horario')).toBeVisible()
    await expect(page.getByTestId('destinos-sin-horarios')).toHaveText('No están los trenes de Iryo: no publica sus horarios en un formato abierto.')
    // el resto, a un toque
    await page.getByTestId('destinos-ver-todos').click()
    await expect(filas).toHaveCount(55)
    await expect(filas.filter({ hasText: 'Badajoz' })).toContainText('MD · a las 16:48')
    await expect(page.getByTestId('destinos-ver-todos')).toHaveText('Ver solo los más frecuentes')
    // un destino de la red lleva a su ficha
    await page.getByTestId('destino-puertollano').click()
    await expect(page).toHaveURL(/\/nodo\/puertollano$/)
    await expect(page.getByTestId('detalle-nodo').getByRole('heading', { level: 2 })).toHaveText('Puertollano')
    await expect(page.getByTestId('destinos-directos').getByRole('heading')).toContainText('Destinos directos · 36 el')
  })

  test('Madrid: con dos operadores, cada destino dice de quién son sus trenes', async ({ page }) => {
    await page.goto('/nodo/madrid-puerta-de-atocha')
    await abrirHoja(page)
    const filas = page.getByTestId('lista-destinos').getByRole('listitem')
    await expect(filas.nth(0)).toContainText('Córdoba')
    await expect(filas.nth(0)).toContainText('de 06:00 a 21:20 · Renfe Viajeros 47, Ouigo España 6')
    await expect(filas.nth(0)).toContainText('53 trenes')
    await expect(filas.filter({ hasText: 'Antequera' })).toContainText('· Renfe Viajeros')
  })

  test('el comparador de recorridos cuenta los mismos trenes directos que la ficha', async ({ page }) => {
    await page.goto('/recorridos/ciudad-real/madrid-puerta-de-atocha')
    await abrirHoja(page)
    await expect(page.getByTestId('recorridos-resumen')).toContainText('Hay 12 trenes directos en este sentido')
    await page.goto('/recorridos/madrid-puerta-de-atocha/cordoba')
    await expect(page.getByTestId('recorridos-resumen')).toContainText('Hay 53 trenes directos en este sentido')
  })

  test('un nodo que no es estación no tiene destinos; el detalle de una estación dice cómo se cuentan', async ({ page }) => {
    await page.goto('/nodo/urda')
    await abrirHoja(page)
    await expect(page.getByTestId('detalle-nodo')).toBeVisible()
    await expect(page.getByTestId('destinos-directos')).toHaveCount(0)
    await page.goto('/nodo/daimiel')
    await expect(page.getByTestId('destinos-directos')).toBeVisible()
    // en una línea solo de Renfe no falta ningún operador
    await expect(page.getByTestId('destinos-sin-horarios')).toHaveCount(0)
    const detalle = page.getByTestId('mas-detalle')
    await detalle.locator('summary').click()
    await expect(detalle).toContainText('Un destino directo es una estación en la que para, después de esta, un tren al que se puede subir aquí.')
    await expect(detalle.getByTestId('pie-fuente').last()).toContainText(/Fuente de los horarios: Renfe/)
  })
})
