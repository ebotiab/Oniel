import { expect, test, type Page } from '@playwright/test'

import { SPAIN_BOUNDS } from '../src/map/bounds.ts'

/** En el móvil la hoja empieza plegada: la despliega para ver la lista o la ficha. */
async function abrirPanel(page: Page) {
  const asa = page.getByRole('button', { name: 'Ampliar el panel' })
  if (await asa.isVisible()) await asa.click()
}

/** El campo del buscador: en escritorio está a la vista; en el móvil lo despliega la lupa. */
async function abrirBuscador(page: Page) {
  const lupa = page.getByTestId('buscador-abrir')
  if (await lupa.isVisible()) await lupa.click()
  return page.getByRole('combobox', { name: 'Buscar una estación o una línea' })
}

// De Madrid a Badajoz se va por cuatro líneas: la convencional hasta las puertas de Plasencia, la de
// alta velocidad de Plasencia a Badajoz por Cáceres, el ramal que entra en Mérida y el trazado antiguo
// de Monfragüe a Cáceres por Cañaveral (docs/datos.md).
test.describe('Las líneas de Extremadura', () => {
  test('la zona «Extremadura» sale en la lista con sus cuatro líneas', async ({ page }) => {
    await page.goto('/')
    await abrirPanel(page)
    const zona = page.getByTestId('vista-red').getByRole('region', { name: 'Extremadura' })
    const cabecera = zona.locator('.zona-cabecera')
    await expect(cabecera).toContainText(/^›Extremadura4 líneas/)
    // con más de doce líneas la lista arranca como un índice de zonas: plegada, dice sus ciudades
    await expect(cabecera).toHaveAttribute('aria-expanded', 'false')
    await expect(zona.locator('.zona-detalle')).toHaveText('Cáceres, Mérida, Badajoz, Plasencia')
    await cabecera.click()
    // primero la alta velocidad y, en cada tipo, de la más larga a la más corta
    await expect(zona.locator('.fila-linea')).toHaveText([
      /^Alta velocidad: Plasencia – Badajoz por Cáceres191 km$/,
      /^Línea convencional: Madrid – Plasencia por Talavera de la Reina260 km$/,
      /^Línea convencional: Monfragüe – Cáceres por Cañaveral71 km$/,
      /^Línea convencional: Ramal de Mérida7 km$/,
    ])
    await page.getByTestId('linea-lav-plasencia-badajoz').click()
    await expect(page).toHaveURL(/\/linea\/lav-plasencia-badajoz$/)
    await expect(page.getByRole('heading', { name: 'Línea de alta velocidad Plasencia – Cáceres – Badajoz' })).toBeVisible()
    const esquema = page.getByTestId('esquema')
    await expect(esquema).toContainText('Plasencia')
    await expect(esquema).toContainText('Cáceres')
    await expect(esquema).toContainText('Badajoz')
  })

  test('el buscador encuentra Cáceres, Mérida y Badajoz', async ({ page }) => {
    await page.goto('/')
    await expect(page.getByTestId('vista-red')).toBeVisible()
    const campo = await abrirBuscador(page)
    for (const [texto, nombre] of [
      ['caceres', 'Cáceres'],
      ['merida', 'Mérida'],
      ['badajoz', 'Badajoz'],
    ] as const) {
      await campo.fill(texto)
      const primero = page.getByRole('option').first()
      await expect(primero).toContainText(nombre)
      await expect(primero).toContainText('Estación')
    }
    await campo.press('Enter')
    await expect(page).toHaveURL(/\/nodo\/badajoz$/)
    await expect(page.getByTestId('detalle-nodo').getByRole('heading', { name: 'Badajoz' })).toBeVisible()
  })

  test('el comparador encuentra los dos recorridos de Madrid a Badajoz', async ({ page }) => {
    await page.goto('/recorridos/madrid-puerta-de-atocha/badajoz')
    const recorridos = page.getByTestId('recorrido')
    await expect(recorridos).toHaveCount(2)
    // por el trazado antiguo de Monfragüe a Cáceres, por Cañaveral: kilómetro y medio menos
    await expect(recorridos.nth(0)).toContainText('444,9 km')
    await expect(recorridos.nth(0)).toContainText('Recorre cuatro líneas')
    // por la bifurcación San Esteban y la línea de alta velocidad, que es por donde van casi todos los trenes
    await expect(recorridos.nth(1)).toContainText('446,4 km')
    await expect(recorridos.nth(1)).toContainText('Bifurcación San Esteban')
    await expect(recorridos.nth(1)).toContainText('Recorre tres líneas')
  })

  test('de Cáceres a Badajoz hay un solo recorrido, por la alta velocidad', async ({ page }) => {
    await page.goto('/recorridos/caceres/badajoz')
    const recorridos = page.getByTestId('recorrido')
    await expect(recorridos).toHaveCount(1)
    await expect(recorridos.first()).toContainText('111,9 km')
    await expect(recorridos.first()).toContainText('Por la alta velocidad')
  })

  test('la línea convencional dice en cada tramo sus vías y si tiene catenaria', async ({ page }) => {
    // casi toda es de vía única y sin electrificar: el tramo no trae electrificación y dice la de su línea
    await page.goto('/tramo/madrid-plasencia:talavera-de-la-reina:oropesa-de-toledo')
    await abrirPanel(page)
    await expect(page.getByTestId('detalle-tramo')).toBeVisible()
    await expect(page.getByTestId('tramo-vias')).toHaveText('Vía única')
    // la electrificación va bajo «Más detalle»: está en la ficha aunque plegada
    await expect(page.getByTestId('tramo-atributo-electrification')).toHaveText('Sin electrificar')
    // de Madrid a Humanes hay vía doble y catenaria: esos tramos traen su propia electrificación
    await page.goto('/tramo/madrid-plasencia:leganes:fuenlabrada')
    await abrirPanel(page)
    await expect(page.getByTestId('detalle-tramo')).toBeVisible()
    await expect(page.getByTestId('tramo-vias')).toHaveText('Vía doble')
    await expect(page.getByTestId('tramo-atributo-electrification')).toHaveText('3 kV CC')
  })

  test('un tramo de la alta velocidad de Plasencia a Badajoz dice la catenaria de su línea', async ({ page }) => {
    await page.goto('/tramo/lav-plasencia-badajoz:bif-la-aldihuela:bif-penas-blancas')
    await abrirPanel(page)
    await expect(page.getByTestId('detalle-tramo')).toBeVisible()
    await expect(page.getByTestId('tramo-vias')).toHaveText('Vía doble')
    await expect(page.getByTestId('tramo-atributo-electrification')).toHaveText('25 kV 50 Hz')
    // a la entrada de Cáceres la vía es única, con la misma catenaria
    await page.goto('/tramo/lav-plasencia-badajoz:caceres:bif-la-aldihuela')
    await abrirPanel(page)
    await expect(page.getByTestId('tramo-vias')).toHaveText('Vía única')
    await expect(page.getByTestId('tramo-atributo-electrification')).toHaveText('25 kV 50 Hz')
  })

  test('Badajoz, la estación más al oeste, cabe en el encuadre de toda la red', async ({ request }) => {
    const indice = (await (await request.get('/data/index.json')).json()) as { nodes: { id: string; lon: number; lat: number }[] }
    const badajoz = indice.nodes.find((n) => n.id === 'badajoz')!
    const [[oeste, sur], [este, norte]] = SPAIN_BOUNDS
    // ningún nodo queda más al oeste, y la caja lo contiene con margen
    expect(Math.min(...indice.nodes.map((n) => n.lon))).toBe(badajoz.lon)
    expect(badajoz.lon - oeste).toBeGreaterThan(0.1)
    for (const n of indice.nodes) {
      expect(n.lon, `${n.id}: longitud`).toBeGreaterThan(oeste)
      expect(n.lon, `${n.id}: longitud`).toBeLessThan(este)
      expect(n.lat, `${n.id}: latitud`).toBeGreaterThan(sur)
      expect(n.lat, `${n.id}: latitud`).toBeLessThan(norte)
    }
  })
})
