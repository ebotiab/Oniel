import { expect, test, type Page } from '@playwright/test'

import type { NodeServicesOut, SegmentServicesOut } from '../src/data/types.ts'
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

const enlace = 'enlace-el-chaparral-arroyo-de-la-herrera'
const nombreEnlace = 'Enlace de El Chaparral a Arroyo de la Herrera'
const chaparral = 'bif-el-chaparral'
const arroyo = 'arroyo-de-la-herrera'
const segmento = [enlace, chaparral, arroyo].join(':')

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

  test('Madrid – Badajoz conserva los recorridos por el enlace, Cañaveral y Plasencia', async ({ page }) => {
    await page.goto('/recorridos/madrid-puerta-de-atocha/badajoz')
    const recorridos = page.getByTestId('recorrido')
    await expect(recorridos.nth(0)).toContainText('444,2 km')
    await expect(recorridos.nth(0).getByRole('link', { name: nombreEnlace })).toBeVisible()
    await expect(recorridos.nth(1)).toContainText('444,9 km')
    await page.getByRole('button', { name: 'Incluir recorridos más largos' }).click()
    await expect(recorridos.nth(2)).toContainText('461,3 km')
    await expect(recorridos.nth(2).getByTestId('recorrido-inversion')).toHaveText('Invierte la marcha en Plasencia.')
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

test('Navalmoral ↔ Cáceres permite elegir los tres recorridos y seguir el enlace directo', async ({ page }) => {
  await page.goto('/recorridos/navalmoral-de-la-mata/caceres')
  const rutas = page.getByTestId('recorrido')
  await expect(rutas).toHaveCount(2)
  await page.getByRole('button', { name: 'Incluir recorridos más largos' }).click()
  for (const [desde, hasta] of [['navalmoral-de-la-mata', 'caceres'], ['caceres', 'navalmoral-de-la-mata']]) {
    await expect(page).toHaveURL('/recorridos/' + desde + '/' + hasta + '?max_ratio=100')
    await expect(rutas).toHaveCount(3)
    for (const [i, km] of ['129,3', '130,0', '146,4'].entries()) {
      const ruta = rutas.nth(i)
      await expect(ruta).toContainText(km + ' km')
      await ruta.locator('.recorrido-titulo').click()
      await expect(ruta.locator('.recorrido-titulo')).toHaveAttribute('aria-pressed', 'true')
      if (i === 2) await expect(ruta.getByTestId('recorrido-inversion')).toHaveText('Invierte la marcha en Plasencia.')
      else await expect(ruta.getByTestId('recorrido-inversion')).toHaveCount(0)
    }
    if (desde === 'navalmoral-de-la-mata') await page.getByTestId('recorridos-invertir').click()
  }
  await page.reload()
  await expect(rutas).toHaveCount(3)
  await page.getByRole('button', { name: 'Volver al límite habitual' }).click()
  await expect(rutas).toHaveCount(2)
  await expect(page).toHaveURL('/recorridos/caceres/navalmoral-de-la-mata')
  await rutas.first().getByRole('link', { name: nombreEnlace }).click()
  await expect(page.getByRole('heading', { name: nombreEnlace })).toBeVisible()
  const esquema = page.getByTestId('esquema')
  for (const nodo of [chaparral, arroyo]) await expect(esquema.getByTestId('esquema-nodo-' + nodo)).toBeAttached()
  await esquema.getByTestId('esquema-tramo-1').click()
  await expect(page).toHaveURL('/tramo/' + segmento)
  await expect(page.getByTestId('tramo-vias')).toHaveText('Vía única')
  await expect(page.getByTestId('lista-servicios')).toContainText('00190')
  await expect(page.getByTestId('lista-servicios')).not.toContainText('00194')
})

test('las fichas de El Chaparral, Arroyo, Monfragüe y Plasencia distinguen el enlace y las paradas', async ({ page }) => {
  for (const [nodo, otra] of [[chaparral, 'madrid-plasencia'], [arroyo, 'lav-plasencia-badajoz']]) {
    await page.goto('/nodo/' + nodo)
    await abrirPanel(page)
    for (const linea of [enlace, otra]) await expect(page.getByTestId('nodo-linea-' + linea)).toBeVisible()
    await page.getByTestId('nodo-linea-' + enlace).click()
    await expect(page.getByRole('heading', { name: nombreEnlace })).toBeVisible()
  }
  for (const [nodo, presente, ausente, hora] of [['monfrague', '00190', '00194', '11:40'], ['plasencia', '00194', '00190', '21:47']] as const) {
    await page.goto('/nodo/' + nodo)
    await abrirPanel(page)
    const lista = page.locator('.lista-servicios li')
    await expect(lista.filter({ hasText: presente })).toHaveCount(1)
    await expect(lista.filter({ hasText: presente })).toContainText(hora)
    await expect(lista.filter({ hasText: ausente })).toHaveCount(0)
  }
})

test('el 20 de noviembre la API conserva las paradas, permisos y pasos en ambos sentidos @api', async ({ request }) => {
  test.skip(Boolean(process.env.ONIEL_E2E_STATIC), 'Necesita la API.')
  const params = { date: '2026-11-20' }
  const pasos = await request.get('/api/segments/' + segmento + '/services', { params })
  expect(pasos.ok()).toBeTruthy()
  const ficha = (await pasos.json()) as SegmentServicesOut
  expect(ficha.date).toBe(params.date)
  for (const [ida, numeros] of [[true, ['00190', '00192', '37090', '37492']], [false, ['00293', '00295', '37093', '37095']]] as const) {
    expect(ficha.passes.filter((p) => p.km_increasing === ida && p.kind === 'estimado').map((p) => p.service.train_number).sort()).toEqual(numeros)
  }
  expect(ficha.passes).toHaveLength(8)
  const [madrid, lav] = await Promise.all([
    'madrid-plasencia:monfrague:bif-el-chaparral',
    'lav-plasencia-badajoz:arroyo-de-la-herrera:bif-el-palmeral',
  ].map(async (id) => {
    const respuesta = await request.get('/api/segments/' + id + '/services', { params })
    expect(respuesta.ok()).toBeTruthy()
    return (await respuesta.json()) as SegmentServicesOut
  }))
  for (const p of ficha.passes) {
    const [antes, despues] = p.km_increasing ? [madrid, lav] : [lav, madrid]
    expect(antes!.passes.find((v) => v.service.id === p.service.id)?.exit).toBe(p.enter)
    expect(despues!.passes.find((v) => v.service.id === p.service.id)?.enter).toBe(p.exit)
  }
  const entrada = ['00194', '00291', '17012', '17018', '17021', '17026', '17902', '17907', '35807', '35902', '37091', '37094']
  const enPlasencia = [...entrada, '18773', '18779'].sort()
  const regionales = ['17018', '17021']
  for (const [id, numeros] of [
    ['madrid-plasencia:bif-el-chaparral:bif-san-esteban', entrada],
    ['lav-plasencia-badajoz:plasencia:bif-san-esteban', enPlasencia],
    ['lav-plasencia-badajoz:bif-san-esteban:arroyo-de-la-herrera', enPlasencia.filter((n) => !regionales.includes(n))],
    ['monfrague-caceres:casas-de-millan:canaveral', regionales],
  ] as const) {
    const respuesta = await request.get('/api/segments/' + id + '/services', { params })
    expect(respuesta.ok()).toBeTruthy()
    const vecinos = (await respuesta.json()) as SegmentServicesOut
    expect(vecinos.passes.map((p) => p.service.train_number).sort()).toEqual(numeros)
    expect(new Set(vecinos.passes.map((p) => p.service.id)).size).toBe(numeros.length)
  }
  const navalmoral = await request.get('/api/nodes/navalmoral-de-la-mata/services', { params })
  expect(navalmoral.ok()).toBeTruthy()
  const llamadas = ((await navalmoral.json()) as NodeServicesOut).calls
  for (const [numero, orden, parada, llegada, salida] of [
    ['00190', '17000 18000 35001 35105 35200 35203 35206 30000 35400 37500 37603 37606', '30000', '11:39', '11:40'],
    ['00194', '17000 18000 35001 35200 35206 30002 35400 37606', '30002', '21:42', '21:47'],
    ['00293', '37606 37500 35400 30000 35206 35203 35200 35105 35001 18000 17000', '30000', '09:13', '09:14'],
    ['00291', '37606 35400 30002 35206 35200 35001 18000 17000', '30002', '07:51', '07:56'],
    ['17012', '18000 35001 35002 35005 35105 35200 35203 35206 35207 30000 30002 35400 37500', '30002', '17:51', '17:56'],
  ] as const) {
    const tren = llamadas.filter((c) => c.train_number === numero)
    expect(tren).toHaveLength(1)
    const resp = await request.get('/api/services/' + encodeURIComponent(tren[0]!.service_id), { params })
    expect(resp.ok()).toBeTruthy()
    const detalle = await resp.json() as { stops: { stop_id: string; arrival: string; departure: string; pickup_type: number; drop_off_type: number }[] }
    expect(detalle.stops.map((s) => s.stop_id)).toEqual(orden.split(' '))
    expect(detalle.stops.find((s) => s.stop_id === parada)).toMatchObject({ arrival: llegada, departure: salida, pickup_type: 0, drop_off_type: 0 })
    expect(detalle.stops[0]).toMatchObject({ pickup_type: 0, drop_off_type: 1 })
    expect(detalle.stops.at(-1)).toMatchObject({ pickup_type: 1, drop_off_type: 0 })
    const delEnlace = ficha.passes.filter((p) => p.service.id === tren[0]!.service_id)
    expect(delEnlace).toHaveLength(numero === '00190' || numero === '00293' ? 1 : 0)
  }
})
