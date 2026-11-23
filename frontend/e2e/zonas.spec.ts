import { expect, test } from '@playwright/test'

import { lineasDeLista, paraEn, renglonDe, zona, zonas } from './instantanea.ts'
import { abrirZona } from './navegar.ts'

// La lista de zonas de la portada: una línea sale en la zona a la que lleva y en cada zona en la que para
// en una de sus ciudades, para que quien busca «las líneas de Madrid» las encuentre en la zona de Madrid
// (docs/diseno.md, «Elegir línea»).

async function abrirHoja(page: import('@playwright/test').Page) {
  const asa = page.getByRole('button', { name: 'Ampliar el panel' })
  if (await asa.isVisible()) await asa.click()
}

test.describe('La lista de zonas', () => {
  test('quien abre la zona de Madrid llega a las líneas que salen de Madrid', async ({ page }) => {
    await page.goto('/')
    await abrirHoja(page)
    const madrid = zona('madrid-castilla-la-mancha')
    const seccion = page.getByTestId('zona-madrid-castilla-la-mancha')
    // plegada, la zona nombra Madrid entre sus ciudades
    await expect(seccion.locator('.zona-detalle')).toContainText(/^Madrid, /)
    await abrirZona(page, 'madrid-castilla-la-mancha')
    // están las que llevan a otra zona y salen de Madrid, cada una con el renglón de esta zona
    for (const id of ['lav-madrid-sevilla', 'lav-madrid-barcelona', 'lav-madrid-valencia', 'lav-madrid-valladolid', 'madrid-avila-valladolid', 'madrid-plasencia'])
      await expect(seccion.getByTestId(`linea-${id}--madrid-castilla-la-mancha`)).toBeVisible()
    // y la regla: toda línea con estación en Madrid está en la zona
    const deMadrid = lineasDeLista.filter((l) => paraEn(l.id, 'Madrid'))
    expect(deMadrid.length).toBeGreaterThan(6)
    for (const l of deMadrid) await expect(seccion.getByTestId(renglonDe(l, 'madrid-castilla-la-mancha'))).toBeVisible()
    await expect(seccion.locator('.fila-linea')).toHaveCount(madrid.lineas.length)
    // el renglón abre la línea, como el de su zona
    await seccion.getByTestId('linea-lav-madrid-barcelona--madrid-castilla-la-mancha').click()
    await expect(page).toHaveURL(/\/linea\/lav-madrid-barcelona$/)
  })

  test('cada zona nombra las ciudades por las que pasa alguna de sus líneas, y Castelló figura en la suya', async ({ page }) => {
    await page.goto('/')
    await abrirHoja(page)
    await expect(page.getByTestId('zona-levante').locator('.zona-detalle')).toContainText('Castelló')
    // las que la regla anterior dejaba fuera, porque su estación está en una línea que lleva a otra zona
    await expect(page.getByTestId('zona-madrid-castilla-la-mancha').locator('.zona-detalle')).toContainText('Cuenca, Guadalajara')
    await expect(page.getByTestId('zona-castilla-y-leon').locator('.zona-detalle')).toContainText('Zamora')
    await expect(page.getByTestId('zona-aragon-navarra-rioja').locator('.zona-detalle')).toContainText('Calatayud')
    // y, de todas, la regla: la ciudad se nombra si alguna línea de la zona para en ella
    for (const z of zonas) for (const c of z.ciudades) await expect(page.getByTestId(`zona-${z.zona.id}`).locator('.zona-detalle')).toContainText(c)
  })

  test('filtrando, una línea que está en varias zonas sale una sola vez', async ({ page }) => {
    await page.goto('/')
    await abrirHoja(page)
    await page.getByTestId('filtro-lineas').fill('lleida')
    await expect(page.getByTestId('lista-lineas').locator('.fila-linea')).toHaveCount(1)
    await expect(page.getByTestId('linea-lav-madrid-barcelona')).toBeVisible()
  })
})
