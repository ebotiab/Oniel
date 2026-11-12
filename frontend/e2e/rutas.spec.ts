import { readFileSync } from 'node:fs'

import { expect, test } from '@playwright/test'

import { composeNetwork } from '../src/data/network.ts'
import type { NetworkIndexOut, Route } from '../src/data/types.ts'
import { buildGraph, closureDetours, findRoutes, type Detour } from '../src/routing/graph.ts'
import { ScenarioError, closureScenario, scenarioFromCode, scenarioToCode } from '../src/routing/scenario.ts'

const estatico = Boolean(process.env.ONIEL_E2E_STATIC)

// El grafo de rutas se calcula igual en el servidor (`backend/src/oniel/routing`) y en el cliente
// (`src/routing`). Los casos y lo que da el servidor están en `fixtures/rutas-paridad.json`, que
// genera y comprueba `backend/tests/test_routing.py`; aquí el cliente tiene que dar lo mismo sobre
// la instantánea estática: le basta el índice, que lleva todas las líneas, nodos y tramos.
interface Paridad {
  routes: { from: string; to: string; scenario: string; max_changes: number; max_ratio: number | null; expected: Route[] }[]
  detours: { segment_id: string; scenario: string; expected: Detour[] }[]
}
const leer = <T>(ruta: string) => JSON.parse(readFileSync(new URL(ruta, import.meta.url), 'utf-8')) as T
const paridad = leer<Paridad>('./fixtures/rutas-paridad.json')
const red = composeNetwork(leer<NetworkIndexOut>('../public/data/index.json'), {})

const MADRID = 'madrid-puerta-de-atocha'
const URDA_CIUDAD_REAL = 'lav-madrid-sevilla:urda:ciudad-real'

test.describe('Grafo de rutas en el cliente', () => {
  test('da los mismos recorridos que el servidor en los casos compartidos', () => {
    const grafo = buildGraph(red)
    for (const caso of paridad.routes) {
      expect(findRoutes(grafo, caso.from, caso.to, scenarioFromCode(caso.scenario), caso.max_changes, caso.max_ratio), `${caso.from} → ${caso.to}`).toEqual(caso.expected)
    }
    for (const caso of paridad.detours) {
      expect(closureDetours(grafo, caso.segment_id, scenarioFromCode(caso.scenario)), caso.segment_id).toEqual(caso.expected)
    }
  })

  test('Madrid – Córdoba tiene cuatro recorridos y Madrid – Ciudad Real, dos, uno por Manzanares', () => {
    const grafo = buildGraph(red)
    // sin tope útil de líneas entra el de los Alvia desviados (433,3 km por tres líneas)
    expect(findRoutes(grafo, MADRID, 'cordoba').map((r) => r.length_km)).toEqual([343.6, 433.3, 440.7, 479.8])
    const aCiudadReal = findRoutes(grafo, MADRID, 'ciudad-real')
    // la vuelta por Córdoba (613,5 km) pasa del doble del más corto y se descarta
    expect(aCiudadReal.map((r) => r.length_km)).toEqual([170.8, 260.5])
    expect(aCiudadReal[1]?.line_ids).toEqual(['convencional-madrid-alcazar-cordoba', 'manzanares-ciudad-real'])
    expect(findRoutes(grafo, MADRID, 'ciudad-real', undefined, 1, null).map((r) => r.length_km)).toEqual([170.8, 260.5, 613.5])
    // con Urda – Ciudad Real cerrado desaparece el recorrido directo
    expect(findRoutes(grafo, MADRID, 'ciudad-real', closureScenario(URDA_CIUDAD_REAL)).map((r) => r.length_km)).toEqual([260.5])
  })

  test('el escenario va y vuelve de la cadena corta de la URL', () => {
    const cadena = `c~${URDA_CIUDAD_REAL};e~alcazar-de-san-juan~ciudad-real~110.5~200;v~manzanares-ciudad-real:almagro:ciudad-real~95`
    const escenario = scenarioFromCode(cadena)
    expect(escenario.closures).toEqual([URDA_CIUDAD_REAL])
    expect(escenario.links).toEqual([{ from_node_id: 'alcazar-de-san-juan', to_node_id: 'ciudad-real', length_km: 110.5, speed_kmh: 200 }])
    expect(scenarioToCode(escenario)).toBe(cadena)
    expect(scenarioFromCode('')).toEqual({ closures: [], links: [], speeds: [] })
    expect(() => scenarioFromCode('x~nada')).toThrow(ScenarioError)
    expect(() => findRoutes(buildGraph(red), MADRID, 'cordoba', closureScenario('no:existe'))).toThrow(ScenarioError)
  })

  test('la API da lo mismo que el cliente', async ({ request }) => {
    test.skip(estatico, 'compara con la API')
    const caso = paridad.routes[3]!
    const respuesta = await request.get('/api/routes', { params: { from: caso.from, to: caso.to, scenario: caso.scenario, max_changes: caso.max_changes, max_ratio: 100 } })
    expect(respuesta.ok()).toBe(true)
    const cuerpo = (await respuesta.json()) as { routes: (Route & { interruptions?: unknown })[]; scenario_code: string }
    expect(cuerpo.scenario_code).toBe(caso.scenario)
    const delServidor = cuerpo.routes.map((ruta) => {
      const copia = { ...ruta }
      delete copia.interruptions
      return copia
    })
    const redApi = composeNetwork((await (await request.get('/api/lines')).json()) as NetworkIndexOut, {})
    expect(findRoutes(buildGraph(redApi), caso.from, caso.to, scenarioFromCode(caso.scenario), caso.max_changes, 100)).toEqual(delServidor)
  })
})

test.describe('Escenario en la URL', () => {
  test('un escenario que cierra un tramo abre su simulación y la URL lo conserva', async ({ page }) => {
    await page.goto(`/#/escenario/c~${URDA_CIUDAD_REAL}`)
    const panel = page.getByTestId('panel-simulacion')
    await expect(panel).toBeVisible()
    await expect(panel.getByRole('heading', { name: 'Urda – Ciudad Real' })).toBeVisible()
    await expect(page).toHaveURL(new RegExp(`#/escenario/c~${URDA_CIUDAD_REAL}$`))
    // al volver al tramo, la URL deja de ser la del escenario
    await panel.getByRole('button', { name: /Volver al tramo/ }).click()
    await expect(page).toHaveURL(new RegExp(`#/tramo/${URDA_CIUDAD_REAL}$`))
  })

  test('un escenario ilegible no rompe el visor', async ({ page }) => {
    await page.goto('/#/escenario/esto-no-es-un-escenario')
    await expect(page.getByTestId('panel-simulacion')).toHaveCount(0)
    await expect(page.locator('#panel')).toContainText(/Madrid/)
  })
})
