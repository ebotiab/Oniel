import { expect, test, type Page } from '@playwright/test'

import { SPAIN_BOUNDS } from '../src/map/bounds.ts'
import { cabeceraDeZona, zona as zonaDeLista } from './instantanea.ts'

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
// alta velocidad de Plasencia a Badajoz por Cáceres, la línea que entra en Mérida desde Aljucén y el trazado antiguo
// de Monfragüe a Cáceres por Cañaveral (docs/datos.md).
test.describe('Las líneas de Extremadura', () => {
  test('la zona «Extremadura» sale en la lista con sus cuatro líneas', async ({ page }) => {
    await page.goto('/')
    await abrirPanel(page)
    const zona = page.getByTestId('vista-red').getByRole('region', { name: 'Extremadura' })
    const cabecera = zona.locator('.zona-cabecera')
    // cuántas líneas tiene la zona lo dice la instantánea: aquí se miran las cuatro de esta prueba
    const extremadura = zonaDeLista('extremadura')
    await expect(cabecera).toContainText(cabeceraDeZona(extremadura))
    // con más de doce líneas la lista arranca como un índice de zonas: plegada, dice sus ciudades
    await expect(cabecera).toHaveAttribute('aria-expanded', 'false')
    for (const ciudad of ['Cáceres', 'Mérida', 'Badajoz', 'Plasencia']) await expect(zona.locator('.zona-detalle')).toContainText(ciudad)
    await cabecera.click()
    await expect(zona.locator('.fila-linea')).toHaveCount(extremadura.lineas.length)
    await expect(page.getByTestId('linea-lav-plasencia-badajoz')).toHaveText(/^Alta velocidad: Plasencia – Badajoz por Cáceres191 km$/)
    await expect(page.getByTestId('linea-madrid-plasencia')).toHaveText(/^Línea convencional: Madrid – Plasencia por Talavera de la Reina260 km$/)
    await expect(page.getByTestId('linea-monfrague-caceres')).toHaveText(/^Línea convencional: Monfragüe – Cáceres por Cañaveral71 km$/)
    await expect(page.getByTestId('linea-ramal-merida')).toHaveText(/^Línea convencional: Aljucén – Mérida7 km$/)
    // primero la alta velocidad y, en cada tipo, de la más larga a la más corta
    const cuatro = ['linea-lav-plasencia-badajoz', 'linea-madrid-plasencia', 'linea-monfrague-caceres', 'linea-ramal-merida']
    const orden = await zona.locator('.fila-linea').evaluateAll((filas) => filas.map((f) => f.getAttribute('data-testid') ?? ''))
    expect(orden.filter((id) => cuatro.includes(id))).toEqual(cuatro)
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
    // los dos más cortos son los de Extremadura
    // por el trazado antiguo de Monfragüe a Cáceres, por Cañaveral: kilómetro y medio menos
    await expect(recorridos.nth(0)).toContainText('444,9 km')
    await expect(recorridos.nth(0)).toContainText('Recorre cuatro líneas')
    // por la línea de alta velocidad, entrando en Plasencia: en la bifurcación San Esteban las vías no dejan
    // pasar de la línea de Madrid a la de Cáceres, y el recorrido llega a Plasencia e invierte la marcha, como
    // los trenes que paran allí (461,3 km; girando en la bifurcación eran 446,4). Los que no paran van por el
    // enlace de El Chaparral a Arroyo de la Herrera, que no está cargado
    await expect(recorridos.nth(1)).toContainText('461,3 km')
    await expect(recorridos.nth(1).locator('.recorrido-titulo')).toHaveText('Por Plasencia')
    await expect(recorridos.nth(1).getByTestId('recorrido-inversion')).toHaveText('Invierte la marcha en Plasencia.')
    await expect(recorridos.nth(1)).toContainText('Recorre cuatro líneas')
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

  test('Badajoz, la estación más al oeste de Extremadura, cabe en el encuadre de toda la red', async ({ request }) => {
    const indice = (await (await request.get('/data/index.json')).json()) as { nodes: { id: string; lon: number; lat: number }[] }
    const badajoz = indice.nodes.find((n) => n.id === 'badajoz')!
    const [[oeste, sur], [este, norte]] = SPAIN_BOUNDS
    // la caja la contiene con margen, y a todos los demás nodos de la red, estén más al oeste o no
    expect(badajoz.lon - oeste).toBeGreaterThan(0.1)
    for (const n of indice.nodes) {
      expect(n.lon, `${n.id}: longitud`).toBeGreaterThan(oeste)
      expect(n.lon, `${n.id}: longitud`).toBeLessThan(este)
      expect(n.lat, `${n.id}: latitud`).toBeGreaterThan(sur)
      expect(n.lat, `${n.id}: latitud`).toBeLessThan(norte)
    }
  })
})
