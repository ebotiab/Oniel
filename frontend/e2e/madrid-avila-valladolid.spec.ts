import { readFileSync } from 'node:fs'

import { expect, test } from '@playwright/test'

import { composeNetwork } from '../src/data/network.ts'
import type { NetworkIndexOut } from '../src/data/types.ts'
import { buildGraph, findRoutes } from '../src/routing/graph.ts'

const leer = <T>(ruta: string) => JSON.parse(readFileSync(new URL(ruta, import.meta.url), 'utf-8')) as T
const red = composeNetwork(leer<NetworkIndexOut>('../public/data/index.json'), {})
const grafo = buildGraph(red)

const LINEA = 'madrid-avila-valladolid'
const LAV = 'lav-madrid-valladolid'
const CHAMARTIN = 'madrid-chamartin'
const VALLADOLID = 'valladolid-campo-grande'
const AVILA_AREVALO = `${LINEA}:avila:arevalo`

/** El campo del buscador: en escritorio está a la vista; en el móvil lo despliega la lupa. */
async function abrirBuscador(page: import('@playwright/test').Page) {
  const lupa = page.getByTestId('buscador-abrir')
  if (await lupa.isVisible()) await lupa.click()
  return page.getByRole('combobox', { name: 'Buscar una estación o una línea' })
}

test.describe('Línea convencional de Madrid a Valladolid por Ávila', () => {
  test('va de Madrid-Chamartín a Valladolid-Campo Grande, las cabeceras de la alta velocidad', () => {
    const nodos = red.nodes.filter((n) => n.line_id === LINEA).sort((a, b) => a.km - b.km)
    expect(nodos).toHaveLength(28)
    expect(nodos[0].id).toBe(CHAMARTIN)
    expect(nodos.at(-1)?.id).toBe(VALLADOLID)
    const lineasDe = (id: string) => red.nodes.filter((n) => n.id === id).map((n) => n.line_id)
    expect(lineasDe(CHAMARTIN)).toContain(LINEA)
    expect(lineasDe(CHAMARTIN)).toContain(LAV)
    expect(lineasDe(VALLADOLID)).toContain(LINEA)
    expect(lineasDe('avila')).toEqual([LINEA])
    expect(lineasDe('medina-del-campo')).toEqual([LINEA])
  })

  test('es de vía doble y ancho ibérico en toda su longitud', () => {
    const tramos = red.segments.filter((s) => s.line_id === LINEA)
    expect(tramos).toHaveLength(27)
    expect(tramos.every((s) => s.tracks === 2)).toBe(true)
    expect(red.lines.find((l) => l.id === LINEA)?.gauge_mm).toBe(1668)
  })

  test('el comparador da los dos caminos de Madrid a Valladolid', () => {
    const rutas = findRoutes(grafo, CHAMARTIN, VALLADOLID)
    expect(rutas.slice(0, 2).map((r) => [r.length_km, r.line_ids])).toEqual([
      [178.6, [LAV]],
      [250.2, [LINEA]],
    ])
    expect(findRoutes(grafo, CHAMARTIN, 'avila')[0].length_km).toBe(121.2)
  })

  test('la línea tiene su ficha, con Ávila y Medina del Campo en el esquema', async ({ page }) => {
    await page.goto(`/linea/${LINEA}`)
    await expect(page.getByRole('heading', { name: 'Línea convencional Madrid – Ávila – Medina del Campo – Valladolid' })).toBeVisible()
    await expect(page.locator('body')).toContainText('El camino de siempre de Madrid a Castilla y León')
    const esquema = page.getByTestId('esquema')
    await expect(esquema).toContainText('Madrid-Chamartín')
    await expect(esquema).toContainText('Villalba de Guadarrama')
    await expect(esquema).toContainText('Ávila')
    await expect(esquema).toContainText('Medina del Campo')
    await expect(esquema).toContainText('Valladolid-Campo Grande')
  })

  test('el buscador lleva a Ávila', async ({ page }) => {
    await page.goto('/')
    await expect(page.getByTestId('vista-red')).toBeVisible()
    const campo = await abrirBuscador(page)
    await campo.fill('avila')
    const primero = page.getByRole('option').first()
    await expect(primero).toContainText('Ávila')
    await expect(primero).toContainText('Estación')
    await campo.press('Enter')
    await expect(page).toHaveURL(/\/nodo\/avila$/)
    await expect(page.getByTestId('detalle-nodo').getByRole('heading', { name: 'Ávila' })).toBeVisible()
  })

  test('un tramo dice su vía doble y su bloqueo', async ({ page }) => {
    await page.goto(`/tramo/${AVILA_AREVALO}`)
    await expect(page.getByTestId('detalle-tramo')).toBeVisible()
    const asa = page.getByRole('button', { name: 'Ampliar el panel' })
    if (await asa.isVisible()) await asa.click()
    await expect(page.getByTestId('tramo-vias')).toHaveText('Vía doble')
    await expect(page.getByTestId('tramo-atributo-proteccion_tren')).toHaveText('ASFA')
  })

  test('el comparador enseña el camino por Ávila de Madrid a Valladolid', async ({ page }) => {
    await page.goto(`/recorridos/${CHAMARTIN}/${VALLADOLID}`)
    const recorridos = page.getByTestId('recorrido')
    await expect(recorridos.nth(1)).toBeVisible()
    await expect(recorridos.first()).toContainText('178,6 km')
    await expect(recorridos.nth(1)).toContainText('250,2 km')
    await expect(recorridos.nth(1)).toContainText('Ávila')
  })
})
