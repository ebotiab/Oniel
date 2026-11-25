import { readFileSync } from 'node:fs'

import { expect, test } from '@playwright/test'

import { activeAnnotations } from '../src/app/annotations.ts'
import { composeNetwork } from '../src/data/network.ts'
import type { NetworkIndexOut } from '../src/data/types.ts'
import { buildGraph, findRoutes } from '../src/routing/graph.ts'

const leer = <T>(ruta: string) => JSON.parse(readFileSync(new URL(ruta, import.meta.url), 'utf-8')) as T
const red = composeNetwork(leer<NetworkIndexOut>('../public/data/index.json'), {})
const grafo = buildGraph(red)

const LINEA = 'valencia-xativa-alicante'
const NORD = 'valencia-estacio-del-nord'
const ALICANTE = 'alicante-terminal'
const XATIVA_BIF = `${LINEA}:xativa:bif-la-encina`
const ALZIRA_CARCAIXENT = `${LINEA}:alzira:carcaixent`

/** El campo del buscador: en escritorio está a la vista; en el móvil lo despliega la lupa. */
async function abrirBuscador(page: import('@playwright/test').Page) {
  const lupa = page.getByTestId('buscador-abrir')
  if (await lupa.isVisible()) await lupa.click()
  return page.getByRole('combobox', { name: 'Buscar una estación o una línea' })
}

test.describe('Línea de València a Alicante por Xàtiva', () => {
  test('va de la Estació del Nord a Alicante/Alacant-Terminal, dos estaciones que ya definían otras líneas', () => {
    const nodos = red.nodes.filter((n) => n.line_id === LINEA).sort((a, b) => a.km - b.km)
    expect(nodos).toHaveLength(21)
    expect(nodos[0].id).toBe(NORD)
    expect(nodos.at(-1)?.id).toBe(ALICANTE)
    const lineasDe = (id: string) => red.nodes.filter((n) => n.id === id).map((n) => n.line_id).sort()
    expect(lineasDe(NORD)).toEqual(['valencia-castello-tarragona', LINEA])
    expect(lineasDe(ALICANTE)).toEqual(['lav-albacete-alicante', LINEA])
    expect(lineasDe('xativa')).toEqual([LINEA])
  })

  test('toda la línea es de ancho ibérico: dos vías hasta Xàtiva y una desde allí', () => {
    const tramos = red.segments.filter((s) => s.line_id === LINEA).sort((a, b) => a.km_from - b.km_from)
    expect(tramos).toHaveLength(20)
    expect(tramos.map((s) => s.tracks)).toEqual([...Array(11).fill(2), ...Array(9).fill(1)])
    expect(tramos.filter((s) => s.attributes?.gauge)).toEqual([])
    expect(red.lines.find((l) => l.id === LINEA)?.gauge_mm).toBe(1668)
  })

  test('el comparador da València – Alicante por Xàtiva', () => {
    const rutas = findRoutes(grafo, NORD, ALICANTE)
    expect(rutas[0].length_km).toBe(183.1)
    expect(rutas[0].line_ids).toEqual([LINEA])
    expect(findRoutes(grafo, NORD, 'xativa').map((r) => r.length_km)).toEqual([55.9])
    // la vuelta por la alta velocidad mide más del doble y no sale; de Madrid a Alicante hay un tercer camino, por València y Xàtiva
    expect(rutas).toHaveLength(1)
    // el primero baja a Atocha por el túnel de Recoletos y sigue por la convencional hasta Albacete; eran 507,6 km
    // cuando ese camino doblaba en la bifurcación de Torrejón de Velasco
    expect(findRoutes(grafo, 'madrid-chamartin', ALICANTE).map((r) => r.length_km)).toEqual([450.1, 486.2, 581.3, 587.8])
  })

  test('la alta velocidad en obras y el tercer carril figuran como proyectos, no como línea', () => {
    const proyectos = activeAnnotations(red, '2026-11-18').filter((a) => a.kind === 'proyecto')
    const av = proyectos.find((a) => a.id === 'proyecto-alta-velocidad-valencia-xativa-la-encina')!
    expect(av.status).toBe('en_obras')
    expect(av.line_id ?? null).toBeNull()
    expect((av.milestones ?? []).map((m) => m.date)).toEqual(['2023-09-09', '2025-03-03', '2026-04-22'])
    const carril = proyectos.find((a) => a.id === 'proyecto-ancho-mixto-la-encina-alicante')!
    expect(carril.status).toBe('licitado')
    expect([carril.line_id, carril.from_node_id, carril.to_node_id]).toEqual([LINEA, 'bif-la-encina', ALICANTE])
  })

  test('la línea tiene su ficha, con Xàtiva y Villena en el esquema', async ({ page }) => {
    await page.goto(`/linea/${LINEA}`)
    await expect(page.getByRole('heading', { name: 'Línea convencional Valencia – Xàtiva – Alicante' })).toBeVisible()
    await expect(page.locator('body')).toContainText('Une Valencia con Alicante por el interior')
    const esquema = page.getByTestId('esquema')
    await expect(esquema).toContainText('València-Estació del Nord')
    await expect(esquema).toContainText('Xàtiva')
    await expect(esquema).toContainText('La Encina')
    await expect(esquema).toContainText('Villena')
    await expect(esquema).toContainText('Alicante/Alacant-Terminal')
  })

  test('el buscador lleva a Xàtiva', async ({ page }) => {
    await page.goto('/')
    await expect(page.getByTestId('vista-red')).toBeVisible()
    const campo = await abrirBuscador(page)
    await campo.fill('xativa')
    const primero = page.getByRole('option').first()
    await expect(primero).toContainText('Xàtiva')
    await expect(primero).toContainText('Estación')
    await campo.press('Enter')
    await expect(page).toHaveURL(/\/nodo\/xativa$/)
    await expect(page.getByTestId('detalle-nodo').getByRole('heading', { name: 'Xàtiva' })).toBeVisible()
  })

  test('un tramo de vía única lo dice, con su bloqueo; uno de vía doble, también', async ({ page }) => {
    await page.goto(`/tramo/${XATIVA_BIF}`)
    await expect(page.getByTestId('detalle-tramo')).toBeVisible()
    const asa = page.getByRole('button', { name: 'Ampliar el panel' })
    if (await asa.isVisible()) await asa.click()
    await expect(page.getByTestId('tramo-vias')).toHaveText('Vía única')
    await expect(page.getByTestId('tramo-atributo-proteccion_tren')).toHaveText('ASFA')
    await expect(page.getByTestId('tramo-atributo-gauge')).toHaveCount(0)
    await page.goto(`/tramo/${ALZIRA_CARCAIXENT}`)
    await expect(page.getByTestId('detalle-tramo')).toBeVisible()
    await expect(page.getByTestId('tramo-vias')).toHaveText('Vía doble')
  })

  test('el comparador enseña el recorrido de València a Alicante', async ({ page }) => {
    await page.goto(`/recorridos/${NORD}/${ALICANTE}`)
    const recorridos = page.getByTestId('recorrido')
    await expect(recorridos.first()).toBeVisible()
    await expect(recorridos.first()).toContainText('183,1 km')
    await expect(recorridos.first().getByTestId('recorrido-trenes')).toContainText(/\d+ trenes directos en el horario del /)
  })
})
