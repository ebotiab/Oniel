import { expect, test } from '@playwright/test'

import type { NodeServicesOut, Route, SegmentServicesOut } from '../src/data/types.ts'
import { abrirLinea } from './navegar.ts'

const acceso = 'enlace-principe-pio-pinar'
const terminal = 'madrid-principe-pio'
const pinar = 'pinar-de-las-rozas'
const principal = 'madrid-avila-valladolid'
const destinos = [
  { id: 'avila', km: 120.6, minutos: 62 },
  { id: 'valladolid-campo-grande', km: 249.5, minutos: 112 },
]

test('el enlace se abre desde la red y el buscador lleva a la ficha de Príncipe Pío', async ({ page }) => {
  await page.goto('/')
  await abrirLinea(page, acceso)
  await expect(page.getByRole('heading', { name: 'Enlace Madrid-Príncipe Pío – Pinar de las Rozas' })).toBeVisible()
  await expect(page.locator('.maplibregl-canvas')).toBeVisible()
  const esquema = page.getByTestId('esquema')
  for (const nombre of ['Madrid-Príncipe Pío', 'Pozuelo', 'Las Rozas', 'Pinar de las Rozas']) await expect(esquema).toContainText(nombre)
  const lupa = page.getByTestId('buscador-abrir')
  if (await lupa.isVisible()) await lupa.click()
  await page.getByRole('combobox', { name: 'Buscar una estación o una línea' }).fill('principe pio')
  await page.getByRole('option').filter({ hasText: 'Madrid-Príncipe Pío' }).filter({ hasText: 'Estación' }).click()
  await expect(page).toHaveURL(new RegExp(`/nodo/${terminal}$`))
  const ficha = page.getByTestId('detalle-nodo')
  await expect(ficha.getByRole('heading', { name: 'Madrid-Príncipe Pío', exact: true })).toBeVisible()
  await ficha.getByTestId('destinos-ver-todos').click()
  const salamanca = ficha.getByTestId('lista-destinos').getByRole('listitem').filter({ hasText: /^SalamancaRegional/ })
  await expect(salamanca).toContainText('7 trenes')
  await expect(salamanca.getByRole('button', { name: 'Salamanca', exact: true })).toBeVisible()
})

for (const destino of destinos) {
  test(`el comparador asigna los regionales en ambos sentidos entre Príncipe Pío y ${destino.id}`, async ({ page }) => {
    for (const [desde, hasta] of [[terminal, destino.id], [destino.id, terminal]]) {
      await page.goto(`/recorridos/${desde}/${hasta}`)
      const ruta = page.getByTestId('recorrido').first()
      await expect(ruta).toContainText(String(destino.km).replace('.', ',') + ' km')
      await expect(page.getByTestId('recorrido-trenes').first()).toContainText(/\d+ trenes? directos?/i)
      await expect(page.getByTestId('recorridos-trenes-fuera')).toHaveCount(0)
    }
  })
}

test('la ficha distingue los atributos documentados de los que faltan', async ({ page }) => {
  await page.goto(`/tramo/${acceso}:madrid-principe-pio:aravaca`)
  await expect(page.getByTestId('tramo-atributo-gauge')).toHaveText('Ibérico (1.668 mm)')
  const ampliar = page.getByRole('button', { name: 'Ampliar el panel' })
  if (await ampliar.isVisible()) await ampliar.click()
  await page.getByTestId('mas-detalle').locator('summary').click()
  await expect(page.getByTestId('tramo-atributo-proteccion_tren')).toHaveText('ASFA')
  await expect(page.getByTestId('tramo-atributo-bloqueo')).toHaveText('Sin dato publicado')
  await expect(page.getByTestId('tramo-atributo-mando')).toHaveText('Sin dato publicado')
  const fuente = page.getByTestId('atributos-fuente')
  await expect(fuente).toContainText('la misma fuente que el trazado')
  await expect(page.getByTestId('mas-detalle').getByText('osm-relation-13489217')).toHaveCount(1)
  await expect(fuente).toContainText('adif-declaracion-red-2026-mapas')
})

test('el cierre entre Las Rozas y Pinar lleva a los horarios de ambas estaciones y al comparador', async ({ page }) => {
  await page.goto(`/tramo/${acceso}:las-rozas:bif-chamartin/cierre`)
  const cierre = page.getByTestId('cierre-estaciones')
  await expect(cierre.getByRole('link', { name: 'Las Rozas', exact: true })).toHaveAttribute('href', '/nodo/las-rozas')
  await expect(cierre.getByRole('link', { name: 'Pinar de las Rozas', exact: true })).toHaveAttribute('href', `/nodo/${pinar}`)
  await cierre.getByRole('link', { name: 'Consultar los recorridos con el cierre' }).click()
  await expect(page.getByTestId('recorridos-escenario')).toContainText('cierre')
})

test('la API y la instantánea comparten horarios, continuidad en Pinar, recorridos y cierres @api', async ({ request }) => {
  test.skip(Boolean(process.env.ONIEL_E2E_STATIC), 'Necesita la API local.')
  const publicado = await (await request.get(`/data/nodes/${terminal}.json`)).json() as NodeServicesOut
  const servicios = await (await request.get(`/api/nodes/${terminal}/services`, { params: { date: publicado.date } })).json() as NodeServicesOut
  expect(servicios.calls).toEqual(publicado.calls)
  expect(servicios.calls.length).toBeGreaterThan(0)
  expect(servicios.calls.every((c) => c.operator_id === 'renfe' && c.product === 'Regional')).toBe(true)
  expect(servicios.destinations).toContainEqual(expect.objectContaining({ name: 'Salamanca', node_id: 'salamanca' }))
  const tramo = `${acceso}:aguja-bif-chamartin:${pinar}`
  const anterior = await (await request.get(`/api/segments/${tramo}/services`, { params: { date: publicado.date } })).json() as SegmentServicesOut
  expect(anterior.segment.station_closure).toMatchObject({ from_id: 'las-rozas', to_id: pinar })
  expect(anterior.passes).toEqual([])
  const ids = servicios.calls.map((c) => c.service_id).sort()
  const villalba = await (await request.get('/api/nodes/villalba-de-guadarrama/services', { params: { date: publicado.date } })).json() as NodeServicesOut
  const porVillalba = new Set(villalba.calls.map((c) => c.service_id))
  expect(ids.every((id) => porVillalba.has(id))).toBe(true)
  const posterior = await (await request.get(`/api/segments/${principal}:${pinar}:las-matas/services`, { params: { date: publicado.date } })).json() as SegmentServicesOut
  const siguientes = posterior.passes.map((p) => p.service.id)
  expect(siguientes.filter((id) => ids.includes(id)).sort()).toEqual(ids)
  for (const destino of destinos) {
    for (const [from, to] of [[terminal, destino.id], [destino.id, terminal]] as const) {
      const resultado = await (await request.get('/api/routes', { params: { from, to } })).json() as { routes: Route[] }
      expect(resultado.routes[0]).toMatchObject({ length_km: destino.km, time_min: destino.minutos })
      expect(resultado.routes[0]?.node_ids).toContain(pinar)
      expect(resultado.routes[0]?.node_ids).not.toContain('madrid-chamartin')
    }
  }
})
