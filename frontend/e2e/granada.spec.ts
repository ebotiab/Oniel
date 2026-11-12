import { expect, test, type Page } from '@playwright/test'

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
    await page.getByTestId(`linea-${LINEA}`).click()
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
    await expect(page.getByTestId('tramo-sin-trenes')).toHaveText('Ningún tren de los horarios cargados recorre este tramo ese día.')
    // ni un recuento a cero ni la frase de la alternativa
    await expect(ficha).not.toContainText('estimado en 0')
    await expect(page.getByTestId('tramo-alternativa')).toHaveCount(0)
  })

  test('los trenes de Granada a Almería recorren la línea hasta la bifurcación', async ({ page }) => {
    await page.goto(`/tramo/${LINEA}:iznalloz:granada`)
    await abrirHoja(page)
    await expect(page.getByTestId('detalle-tramo')).toBeVisible()
    await expect(page.getByTestId('tramo-operadores')).toHaveText('Solo Renfe Viajeros')
    await expect(page.getByTestId('lista-servicios')).toContainText(/MD \d+ Granada → Almería/)
    await expect(page.getByTestId('tramo-alternativa')).toContainText('no tendrían otro camino')
  })

  test('el comparador encuentra Madrid – Granada por Alcázar de San Juan y Linares-Baeza', async ({ page }) => {
    await page.goto('/recorridos/madrid-puerta-de-atocha/granada')
    await abrirHoja(page)
    const recorridos = page.getByTestId('recorrido')
    await expect(recorridos).toHaveCount(3)
    await expect(recorridos.nth(0)).toContainText('Por Linares-Baeza')
    await expect(recorridos.nth(0)).toContainText('Recorre dos líneas')
    await expect(recorridos.nth(0)).toContainText('487,3 km')
    await expect(recorridos.nth(0)).toContainText('240,8 km de vía única')
    await expect(recorridos.nth(0)).toContainText(/Pasa por Aranjuez, Alcázar de San Juan, .*Linares-Baeza, .*Moreda/)
    // ningún tren directo va por ahí: los que hay entre Madrid y Granada usan la alta velocidad
    await expect(recorridos.nth(0).getByTestId('recorrido-trenes')).toContainText('Ningún tren directo')
  })
})
