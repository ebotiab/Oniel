import { readFileSync } from 'node:fs'
import { expect, test } from '@playwright/test'

import { composeNetwork } from '../src/data/network.ts'
import type { NetworkIndexOut, NodeServicesOut, Route } from '../src/data/types.ts'
import { buildGraph, findRoutes } from '../src/routing/graph.ts'
import { scenarioFromCode } from '../src/routing/scenario.ts'

const linea = 'medina-del-campo-salamanca'
const enlace = 'enlace-medina-av-salamanca'
const principal = 'salamanca'
const apeadero = 'salamanca-la-alamedilla'
const medina = 'medina-del-campo'
const av = 'medina-del-campo-av'
const pio = 'madrid-principe-pio'
const intermedias = ['campillo', 'el-carpio', 'fresno-el-viejo', 'cantalapiedra', 'el-pedroso-de-la-armuna', 'pitiegua', 'gomecello', 'moriscos']

test('los dos accesos enlazan el mapa y el esquema con las estaciones de Salamanca', async ({ page }) => {
  await page.goto('/linea/' + enlace)
  await expect(page.locator('.maplibregl-canvas')).toBeVisible()
  await expect(page.getByTestId('esquema-nodo-cambiador-medina-av')).toBeAttached()
  await page.getByRole('link', { name: 'línea de Salamanca', exact: true }).click()
  await expect(page).toHaveURL('/linea/' + linea)
  const esquema = page.getByTestId('esquema')
  for (const id of [medina, ...intermedias]) await expect(esquema.getByTestId('esquema-nodo-' + id)).toBeAttached()
  await page.getByRole('button', { name: 'Salamanca-La Alamedilla', exact: true }).click()
  await expect(page).toHaveURL('/nodo/' + apeadero)
  await expect(page.getByTestId('destinos-directos')).toContainText('Ningún tren con viajeros sale de aquí')
})

test('las fichas conservan un solo tren desde cada Medina y desde Ávila hasta su terminal', async ({ page }) => {
  for (const [numero, origen, estaciones] of [
    ['18308', 'Palencia', [medina, 'campillo', principal, apeadero]],
    ['04899', 'Madrid-Chamartín', [av, principal]],
    ['18901', 'Madrid-Príncipe Pío', ['avila', 'penaranda-de-bracamonte', principal, apeadero]],
  ] as const) {
    for (const estacion of estaciones) {
      await page.goto('/nodo/' + estacion)
      const llamada = page.locator('.lista-servicios li').filter({ hasText: numero })
      await expect(llamada).toHaveCount(1)
      await expect(llamada).toContainText(origen)
      await expect(llamada).toContainText(numero === '04899' ? 'Salamanca' : 'Salamanca-La Alamedilla')
      if (estacion === principal && numero !== '04899') await expect(llamada).toContainText('Solo bajada')
    }
  }
})

test('el comparador muestra los servicios que admiten viajeros en cada sentido', async ({ page }) => {
  for (const [inicio, fin, km, servicios] of [
    [medina, principal, '76,4', '7 trenes directos'], [medina, apeadero, '77,2', '5 trenes directos'],
    [principal, medina, '76,4', '7 trenes directos'], [apeadero, medina, '77,2', 'Ningún tren directo'],
    [av, principal, '73,8', '4 trenes directos'], [principal, av, '73,8', '4 trenes directos'],
    [av, apeadero, '74,6', 'Ningún tren directo'],
  ]) {
    await page.goto('/recorridos/' + inicio + '/' + fin)
    const ruta = page.getByTestId('recorrido').filter({ hasText: km + ' km' }).first()
    await expect(ruta).toContainText(km + ' km · tiempo sin estimar')
    await expect(ruta.getByTestId('recorrido-trenes')).toContainText(servicios)
  }
})

test('el cierre de Campillo se consulta entre estaciones de viajeros', async ({ page }) => {
  await page.goto('/tramo/' + linea + ':campillo:el-carpio/cierre')
  const cierre = page.getByTestId('cierre-estaciones')
  await expect(cierre.locator('a[href="/nodo/campillo"]')).toBeVisible()
  await expect(cierre.locator('a[href="/nodo/el-carpio"]')).toBeVisible()
  await cierre.getByRole('link', { name: 'Consultar los recorridos con el cierre' }).click()
  await expect(page.getByTestId('recorridos-escenario')).toBeVisible()
})

test('la API y la instantánea coinciden en ambos sentidos y con un acceso cerrado @api', async ({ request }) => {
  test.skip(Boolean(process.env.ONIEL_E2E_STATIC), 'Necesita la API local.')
  const index = JSON.parse(readFileSync(new URL('../public/data/index.json', import.meta.url), 'utf8')) as NetworkIndexOut
  const graph = buildGraph(composeNetwork(index, {}))
  for (const origen of [medina, av, pio]) {
    for (const terminal of [principal, apeadero]) {
      for (const [from, to] of [[origen, terminal], [terminal, origen]] as const) {
        for (const scenario of ['', 'c~' + linea + ':campillo:el-carpio']) {
          const response = await request.get('/api/routes', { params: { from, to, scenario } })
          expect(response.ok()).toBeTruthy()
          const body = await response.json() as { routes: Route[] }
          const cliente = findRoutes(graph, from, to, scenarioFromCode(scenario))
          expect(body.routes).toHaveLength(cliente.length)
          for (const ruta of cliente) {
            expect(body.routes).toContainEqual(expect.objectContaining({
              node_ids: ruta.node_ids, segment_ids: ruta.segment_ids, line_ids: ruta.line_ids, length_km: ruta.length_km, time_min: ruta.time_min,
            }))
          }
        }
      }
    }
  }
})

test('la API conserva el viaje completo, paradas y permisos en ida y vuelta @api', async ({ request }) => {
  test.skip(Boolean(process.env.ONIEL_E2E_STATIC), 'Necesita la API local.')
  const params = { date: '2026-11-26' }
  for (const [numero, estaciones, paradas] of [
    ['18308', [medina, principal, apeadero], ['14100', '11000', '10605', '10610', '10600', '10500', '32001', '32002', '32003', '32004', '32006', '32008', '30100', '30110']],
    ['18312', [principal, medina], ['30100', '32008', '32007', '32006', '32004', '32003', '32002', '32001', '10500', '10501', '10502', '10503', '10504', '10600']],
    ['04899', ['madrid-chamartin', av, principal], ['17000', '08004', '08240', '30100']],
    ['04868', [principal, av, 'madrid-chamartin'], ['30100', '08240', '08004', '17000']],
  ] as const) {
    const ids = new Set<string>()
    for (const estacion of estaciones) {
      const resp = await request.get('/api/nodes/' + estacion + '/services', { params })
      expect(resp.ok()).toBeTruthy()
      const llamadas = ((await resp.json()) as NodeServicesOut).calls.filter((c) => c.train_number === numero)
      expect(llamadas).toHaveLength(1)
      ids.add(llamadas[0]!.service_id)
    }
    expect(ids.size).toBe(1)
    const resp = await request.get('/api/services/' + encodeURIComponent([...ids][0]!), { params })
    expect(resp.ok()).toBeTruthy()
    const detalle = await resp.json()
    expect(detalle.stops.map((s: { stop_id: string }) => s.stop_id)).toEqual(paradas)
    expect(detalle.stops[0]).toMatchObject({ pickup_type: 0, drop_off_type: 1 })
    expect(detalle.stops.at(-1)).toMatchObject({ pickup_type: 1, drop_off_type: 0 })
    if (numero === '18308') expect(detalle.stops.at(-2)).toMatchObject({ arrival: '15:42', departure: '15:44', pickup_type: 1, drop_off_type: 0 })
  }
})
