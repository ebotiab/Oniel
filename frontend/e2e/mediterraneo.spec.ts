import { readFileSync } from 'node:fs'

import { expect, test } from '@playwright/test'

import { composeNetwork } from '../src/data/network.ts'
import type { NetworkIndexOut } from '../src/data/types.ts'
import { buildGraph, findRoutes } from '../src/routing/graph.ts'

const leer = <T>(ruta: string) => JSON.parse(readFileSync(new URL(ruta, import.meta.url), 'utf-8')) as T
const red = composeNetwork(leer<NetworkIndexOut>('../public/data/index.json'), {})
const grafo = buildGraph(red)

const LINEA = 'valencia-castello-tarragona'
const NORD = 'valencia-estacio-del-nord'
const SOROLLA = 'valencia-joaquin-sorolla'
const CAMP = 'camp-de-tarragona'
const BOELLA_CAMP = `${LINEA}:cambiador-la-boella:${CAMP}`
const SAGUNT_LES_VALLS = `${LINEA}:sagunt:les-valls`
const CASTELLO_BENICASSIM = `${LINEA}:castello-de-la-plana:benicassim`

test.describe('Línea de València a Camp de Tarragona: une la alta velocidad de Valencia y la de Barcelona', () => {
  test('va de la Estació del Nord a Camp de Tarragona y comparte un nodo con cada una de las dos líneas', () => {
    const nodos = red.nodes.filter((n) => n.line_id === LINEA).sort((a, b) => a.km - b.km)
    expect(nodos).toHaveLength(36)
    expect(nodos.slice(0, 2).map((n) => n.id)).toEqual([NORD, SOROLLA])
    expect(nodos.at(-1)?.id).toBe(CAMP)
    const lineasDe = (id: string) => red.nodes.filter((n) => n.id === id).map((n) => n.line_id).sort()
    expect(lineasDe(SOROLLA)).toEqual(['lav-madrid-valencia', LINEA])
    expect(lineasDe(CAMP)).toEqual(['lav-madrid-barcelona', LINEA])
    expect(lineasDe(NORD)).toEqual([LINEA])
  })

  test('el ancho cambia por tramos: mixto hasta Castelló, ibérico hasta La Boella y estándar hasta Camp de Tarragona', () => {
    const anchos = red.segments.filter((s) => s.line_id === LINEA && s.attributes?.gauge).map((s) => [s.id, s.attributes?.gauge?.value])
    expect(anchos.filter(([, v]) => v === 'mixto')).toHaveLength(18)
    expect(anchos.filter(([, v]) => v === 'estandar')).toEqual([[BOELLA_CAMP, 'estandar']])
    expect(anchos.map(([id]) => id)).toContain(SAGUNT_LES_VALLS)
    expect(anchos.map(([id]) => id)).not.toContain(CASTELLO_BENICASSIM)
    expect(anchos.map(([id]) => id)).not.toContain(`${LINEA}:${NORD}:${SOROLLA}`)
    expect(red.lines.find((l) => l.id === LINEA)?.gauge_mm).toBe(1668)
  })

  test('de València a Barcelona hay un recorrido, por la costa; la vuelta por Madrid se descarta por larga', () => {
    const costa = findRoutes(grafo, SOROLLA, 'barcelona-sants')
    expect(costa.map((r) => r.length_km)).toEqual([365.4])
    expect(costa[0].line_ids).toEqual([LINEA, 'lav-madrid-barcelona'])
    // sin el tope de los rodeos aparece: mide 2,8 veces lo que el camino de la costa
    const todos = findRoutes(grafo, SOROLLA, 'barcelona-sants', undefined, null, null)
    expect(todos[1].length_km).toBe(1009.7)
    expect(findRoutes(grafo, NORD, 'castello-de-la-plana').map((r) => r.length_km)).toEqual([73.7])
    // y de Madrid a Barcelona hay ya otros dos caminos por València y la costa: por Cuenca y por Albacete
    const aBarcelona = findRoutes(grafo, 'madrid-puerta-de-atocha', 'barcelona-sants')
    expect(aBarcelona.map((r) => r.length_km)).toEqual([620.1, 755.1, 864.8])
  })

  test('la ficha del último tramo dice que es de ancho estándar; la de un tramo de ancho ibérico no dice nada', async ({ page }) => {
    await page.goto(`/tramo/${BOELLA_CAMP}`)
    await expect(page.getByTestId('detalle-tramo')).toBeVisible()
    await expect(page.getByTestId('tramo-atributo-gauge')).toHaveText('Estándar: el de la alta velocidad')
    await page.goto(`/tramo/${SAGUNT_LES_VALLS}`)
    await expect(page.getByTestId('detalle-tramo')).toBeVisible()
    await expect(page.getByTestId('tramo-atributo-gauge')).toHaveText('Mixto: caben trenes de los dos anchos')
    await page.goto(`/tramo/${CASTELLO_BENICASSIM}`)
    await expect(page.getByTestId('detalle-tramo')).toBeVisible()
    await expect(page.getByTestId('tramo-vias')).toBeVisible()
    await expect(page.getByTestId('tramo-atributo-gauge')).toHaveCount(0)
  })
})
