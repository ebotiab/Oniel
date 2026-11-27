import { expect, test } from '@playwright/test'

import type { SegmentServicesOut } from '../src/data/types.ts'
import { fraseOtroCamino } from './instantanea.ts'

/** El campo del buscador: en escritorio está a la vista; en el móvil lo despliega la lupa. */
async function abrirBuscador(page: import('@playwright/test').Page) {
  const lupa = page.getByTestId('buscador-abrir')
  if (await lupa.isVisible()) await lupa.click()
  return page.getByRole('combobox', { name: 'Buscar una estación o una línea' })
}

test.describe('La alta velocidad Córdoba – Málaga, entera', () => {
  test('el buscador lleva a Málaga-María Zambrano, que es una estación de la red', async ({ page }) => {
    await page.goto('/')
    await expect(page.getByTestId('vista-red')).toBeVisible()
    const campo = await abrirBuscador(page)
    await campo.fill('malaga')
    const primero = page.getByRole('option').first()
    await expect(primero).toContainText('Málaga-María Zambrano')
    await expect(primero).toContainText('Estación')
    await campo.press('Enter')
    await expect(page).toHaveURL(/\/nodo\/malaga-maria-zambrano$/)
    const ficha = page.getByTestId('detalle-nodo')
    await expect(ficha.getByRole('heading', { name: 'Málaga-María Zambrano' })).toBeVisible()
    await expect(ficha).toContainText('final de la línea')
    // destinos directos del día de referencia: Madrid, Córdoba y, por el enlace directo, Granada
    await expect(ficha).toContainText('Madrid-Puerta de Atocha')
    await expect(ficha).toContainText('Córdoba')
  })

  test('la línea llega a Málaga, con la bifurcación Gobantes y sin continuación a trazos', async ({ page }) => {
    await page.goto('/linea/lav-cordoba-malaga')
    await expect(page.getByRole('heading', { name: 'Línea de alta velocidad Córdoba – Málaga' })).toBeVisible()
    await expect(page.locator('body')).toContainText('baja hasta Málaga-María Zambrano')
    const esquema = page.getByTestId('esquema')
    await expect(esquema).toContainText('Antequera-Santa Ana')
    await expect(esquema).toContainText('Málaga-María Zambrano')
  })

  test('el último tramo dice su señalización y recuerda la interrupción de 2026, ya terminada', async ({ page }) => {
    await page.goto('/tramo/lav-cordoba-malaga:paet-los-prados:malaga-maria-zambrano')
    const ficha = page.getByTestId('detalle-tramo')
    await expect(ficha).toBeVisible()
    await expect(page.getByTestId('tramo-vias')).toHaveText('Vía doble')
    await expect(ficha.getByText('ERTMS de niveles 1 y 2 y ASFA')).toHaveCount(1)
    // la ficha dice si sus trenes tendrían otro camino, como lo da el análisis de la red (hoy a Málaga
    // solo llega esta línea, y no lo tienen)
    await expect(page.getByTestId('tramo-alternativa')).toContainText(fraseOtroCamino('lav-cordoba-malaga:paet-los-prados:malaga-maria-zambrano'))
    // el corte por el desprendimiento de Álora terminó: no se dibuja, pero queda en el detalle
    await expect(ficha).toContainText('Interrupciones anteriores en este tramo')
    await expect(ficha).toContainText('desprendimiento de tierras a la altura de Álora')
  })

  test('el comparador da el recorrido de Madrid a Málaga por la alta velocidad', async ({ page }) => {
    await page.goto('/recorridos/madrid-puerta-de-atocha/malaga-maria-zambrano')
    const recorridos = page.getByTestId('recorrido')
    await expect(recorridos.first()).toBeVisible()
    await expect(recorridos.first()).toContainText('512,7 km')
    await expect(recorridos.first()).toContainText('Recorre dos líneas')
  })
})

const malaga = 'malaga-maria-zambrano'
const enlace = 'enlace-gobantes-bobadilla'
const segmento = enlace + ':bif-gobantes:bif-bobadilla'
const ida = ['08815', '08835', '08855']
const vuelta = ['08915', '08935', '08955']

test('el comparador asigna tres Avant al enlace en cada sentido y conserva la ruta de Sevilla por Santa Ana', async ({ page }) => {
  await page.goto('/recorridos/' + malaga + '/granada')
  const rutas = page.getByTestId('recorrido')
  for (const [desde, hasta, paradas] of [[malaga, 'granada', 'Antequera AV y Loja'], ['granada', malaga, 'Loja y Antequera AV']]) {
    await expect(page).toHaveURL('/recorridos/' + desde + '/' + hasta)
    await expect(rutas).toHaveCount(1)
    await expect(rutas).toContainText('165,0 km · 49 min sin paradas')
    await expect(rutas).toContainText('Pasa por ' + paradas)
    await expect(rutas.getByTestId('recorrido-inversion')).toHaveCount(0)
    await expect(rutas.getByTestId('recorrido-trenes')).toContainText('3 trenes directos')
    await expect(page.getByTestId('recorridos-trenes-fuera')).toHaveCount(0)
    if (desde === malaga) await page.getByTestId('recorridos-invertir').click()
  }
  await rutas.getByRole('link', { name: 'Enlace de Gobantes a Bobadilla' }).click()
  await expect(page).toHaveURL('/linea/' + enlace)

  await page.goto('/recorridos/sevilla-santa-justa/granada')
  await expect(rutas).toHaveCount(2)
  await expect(rutas.first()).toContainText('352,1 km')
  await expect(rutas.first()).toContainText('Antequera-Santa Ana, Antequera AV y Loja')
  await expect(rutas.first().getByTestId('recorrido-inversion')).toHaveText('Invierte la marcha en Córdoba.')
  await expect(rutas.first().getByTestId('recorrido-trenes')).toContainText('4 trenes directos')
  await expect(rutas.last()).toContainText('427,3 km')
})

test('los seis Avant y el de Sevilla se distinguen en las fichas de las dos estaciones de Antequera', async ({ page }) => {
  for (const [estacion, horaControl] of [['antequera-av', '09:30'], ['antequera-santa-ana', '09:20']]) {
    await page.goto('/nodo/' + estacion)
    const llamadas = page.getByTestId('detalle-nodo').locator('.lista-servicios li')
    await expect(llamadas.filter({ hasText: 'Avant 08275' })).toContainText(horaControl)
    for (const tren of [...ida, ...vuelta]) {
      await expect(llamadas.filter({ hasText: 'Avant ' + tren })).toHaveCount(estacion === 'antequera-av' ? 1 : 0)
    }
  }
  await page.goto('/tramo/' + segmento)
  const ficha = page.getByTestId('detalle-tramo')
  for (const tren of [...ida, ...vuelta]) await expect(ficha).toContainText('Avant ' + tren)
  await expect(ficha).not.toContainText('Avant 08275')
})

test('el 20 de noviembre las horas y permisos se conservan hasta las terminales y cada directo pasa una vez por la 014 @api', async ({ request }) => {
  test.skip(Boolean(process.env.ONIEL_E2E_STATIC), 'Necesita la API para consultar el 20 de noviembre.')
  const params = { date: '2026-11-20' }
  const porTramo = async (id: string) => {
    const resp = await request.get('/api/segments/' + id + '/services', { params })
    expect(resp.ok()).toBe(true)
    const datos = await resp.json() as SegmentServicesOut
    return datos.passes.filter((p) => p.service.operator_id === 'renfe')
  }
  const directos = await porTramo(segmento)
  expect(directos.map((p) => p.service.train_number).sort()).toEqual([...ida, ...vuelta])
  for (const p of directos) {
    expect(p.kind).toBe('estimado')
    expect(p.km_increasing).toBe(ida.includes(p.service.train_number))
  }
  for (const [trozo, total, control] of [
    ['lav-cordoba-malaga:antequera-santa-ana:bif-gobantes', 43, false],
    ['lav-cordoba-malaga:bif-gobantes:pb-alora', 49, false],
    ['lav-antequera-granada:antequera-santa-ana:bif-bobadilla', 18, true],
    ['lav-antequera-granada:bif-bobadilla:antequera-av', 24, true],
  ] as const) {
    const numeros = (await porTramo(trozo)).map((p) => p.service.train_number)
    expect(numeros).toHaveLength(total)
    expect(numeros.includes('08275')).toBe(control)
    expect(numeros.filter((n) => [...ida, ...vuelta].includes(n)).sort()).toEqual(trozo.includes('antequera-santa-ana') ? [] : [...ida, ...vuelta])
  }
  for (const [numero, paradas] of [
    ['08815', ['54413 09:20 09:20', '02030 09:46 09:48', '05012 10:14 10:16', '05000 10:43 10:43']],
    ['08915', ['05000 07:36 07:36', '05012 07:56 07:58', '02030 08:25 08:27', '54413 09:05 09:05']],
    ['08275', ['51003 07:40 07:40', '50500 08:24 08:29', '02002 08:57 08:58', '02003 09:16 09:20', '02030 09:28 09:30', '05012 09:56 09:58', '05000 10:25 10:25']],
  ] as const) {
    const respuesta = await request.get('/api/services/' + numero + '12026-11-16', { params })
    expect(respuesta.ok()).toBe(true)
    const detalle = await respuesta.json() as { stops: { stop_id: string; arrival: string; departure: string; pickup_type: number; drop_off_type: number }[] }
    expect(detalle.stops.map((s) => [s.stop_id, s.arrival, s.departure, s.pickup_type, s.drop_off_type])).toEqual(
      paradas.map((p, i) => [...p.split(' '), Number(i === paradas.length - 1), Number(i === 0)]),
    )
  }
})
