import { expect, test, type Page } from '@playwright/test'
import { fraseOtroCamino } from './instantanea.ts'
import { abrirLinea } from './navegar.ts'


const LINEA = 'linares-baeza-moreda-granada'

/** En el móvil la ficha vive en la hoja inferior: hay que ampliarla para verla entera. */
async function abrirHoja(page: Page) {
  const asa = page.getByRole('button', { name: 'Ampliar el panel' })
  if (await asa.isVisible()) await asa.click()
}

test.describe('Línea convencional Linares-Baeza – Moreda – Granada', () => {
  test('la lista lleva a la línea, de vía única y sin electrificar, con sus estaciones', async ({ page }) => {
    await page.goto('/')
    await abrirHoja(page)
    await abrirLinea(page, LINEA)
    await expect(page).toHaveURL(new RegExp(`/linea/${LINEA}$`))
    await expect(page.getByRole('heading', { name: 'Línea convencional Linares-Baeza – Moreda – Granada' })).toBeVisible()
    await expect(page.getByTestId('ficha-linea')).toHaveText(/173,7 km.*hasta 140 km\/h/)
    await page.getByTestId('mas-detalle').locator('summary').click()
    await expect(page.getByTestId('linea-detalle')).toHaveText(/Adif.*410 y 416.*ibérico \(1\.668 mm\).*Sin electrificar/)
    for (const nodo of ['linares-baeza', 'jodar-ubeda', 'cabra-del-santo-cristo', 'moreda', 'bif-almeria', 'iznalloz', 'granada']) {
      await expect(page.getByTestId(`esquema-nodo-${nodo}`)).toBeVisible()
    }
  })

  test('Linares-Baeza es una sola estación para las dos líneas que pasan por ella', async ({ page }) => {
    await page.goto('/nodo/linares-baeza')
    await abrirHoja(page)
    await expect(page.getByTestId('detalle-nodo')).toBeVisible()
    await expect(page.getByTestId('nodo-lineas')).toContainText('2 líneas')
    await expect(page.getByTestId('nodo-lineas')).toContainText(/Madrid – Córdoba por Alcázar de San Juan\s*convencional\s*Linares-Baeza – Granada por Moreda\s*convencional/)
  })

  test('el tramo entre Moreda y la bifurcación dice que no lleva ningún tren', async ({ page }) => {
    await page.goto(`/tramo/${LINEA}:moreda:bif-almeria`)
    await abrirHoja(page)
    const ficha = page.getByTestId('detalle-tramo')
    await expect(ficha).toBeVisible()
    await expect(ficha).toContainText('Moreda – Bifurcación Almería')
    await expect(page.getByTestId('tramo-vias')).toHaveText('Vía única')
    // dice dónde mirar por qué: las fichas de sus dos extremos
    const sinTrenes = page.getByTestId('tramo-sin-trenes')
    await expect(sinTrenes).toHaveText(
      'Ningún tren de los horarios cargados recorre este tramo ese día. Por dónde van los que pasan cerca está en la ficha de Moreda y en la de Bifurcación Almería.',
    )
    // ni un recuento a cero ni la frase de la alternativa
    await expect(page.getByTestId('tramo-hora-de-paso')).toHaveCount(0)
    await expect(page.getByTestId('tramo-alternativa')).toHaveCount(0)
    await sinTrenes.getByRole('button', { name: 'Bifurcación Almería' }).click()
    await expect(page).toHaveURL(/\/nodo\/bif-almeria$/)
  })

  test('los trenes de Granada a Almería recorren la línea hasta la bifurcación', async ({ page }) => {
    await page.goto(`/tramo/${LINEA}:iznalloz:granada`)
    await abrirHoja(page)
    await expect(page.getByTestId('detalle-tramo')).toBeVisible()
    await expect(page.getByTestId('tramo-operadores')).toHaveText('Solo Renfe Viajeros')
    await expect(page.getByTestId('lista-servicios')).toContainText(/Regional \d+ Granada → Almería/)
    // la ficha dice cuántos de sus trenes tendrían otro camino, como lo da el análisis de la red: cambia
    // con las líneas cargadas (con la alta velocidad de Antequera, Granada quedó unida por los dos lados)
    await expect(page.getByTestId('tramo-alternativa')).toContainText(`${fraseOtroCamino(`${LINEA}:iznalloz:granada`)} en las líneas que Oniel tiene cargadas`)
  })

  test('el comparador encuentra Madrid – Granada por Alcázar de San Juan y Linares-Baeza', async ({ page }) => {
    await page.goto('/recorridos/madrid-puerta-de-atocha/granada')
    await abrirHoja(page)
    const recorridos = page.getByTestId('recorrido')
    // cuántos recorridos hay depende de las líneas cargadas: aquí se miran los dos de esta prueba
    await expect(recorridos.nth(0)).toContainText('Por Linares-Baeza')
    await expect(recorridos.nth(0)).toContainText('Recorre dos líneas')
    await expect(recorridos.nth(0)).toContainText('487,3 km')
    await expect(recorridos.nth(0)).toContainText('240,8 km de vía única')
    await expect(recorridos.nth(0)).toContainText(/Pasa por Aranjuez, Alcázar de San Juan, .*Linares-Baeza, .*Moreda/)
    // ningún tren directo va por ahí: los que hay entre Madrid y Granada usan la alta velocidad
    await expect(recorridos.nth(0).getByTestId('recorrido-trenes')).toContainText('Ningún tren directo')
    // el otro camino, por la alta velocidad: más largo y, sin paradas, mucho más rápido
    const alta = recorridos.filter({ hasText: '569,0 km' })
    await expect(alta).toContainText('Por Bifurcación Málaga-Alta Velocidad y Antequera-Santa Ana')
    await expect(alta).toContainText('Recorre tres líneas')
    await expect(alta).toContainText('2 h 17 min sin paradas')
    await expect(alta).toContainText('81,0 km de vía única')
    await expect(alta).toContainText(/Pasa por Ciudad Real, .*Córdoba, .*Antequera-Santa Ana, Antequera AV y Loja/)
    await expect(alta.getByTestId('recorrido-trenes')).toContainText('4 trenes directos')
  })
})
