import { readFileSync } from 'node:fs'

import { expect, test } from '@playwright/test'

import { composeNetwork } from '../src/data/network.ts'
import type { NetworkIndexOut } from '../src/data/types.ts'
import { buildGraph, findRoutes } from '../src/routing/graph.ts'

const leer = <T>(ruta: string) => JSON.parse(readFileSync(new URL(ruta, import.meta.url), 'utf-8')) as T
const red = composeNetwork(leer<NetworkIndexOut>('../public/data/index.json'), {})
const grafo = buildGraph(red)

const LINEA = 'palencia-santander'
const LAV_LEON = 'lav-valladolid-leon'
const CHAMARTIN = 'madrid-chamartin'
const REINOSA_BARCENA = `${LINEA}:reinosa:barcena`

/** El campo del buscador: en escritorio está a la vista; en el móvil lo despliega la lupa. */
async function abrirBuscador(page: import('@playwright/test').Page) {
  const lupa = page.getByTestId('buscador-abrir')
  if (await lupa.isVisible()) await lupa.click()
  return page.getByRole('combobox', { name: 'Buscar una estación o una línea' })
}

test.describe('Línea convencional de Palencia a Santander', () => {
  test('sale de Palencia, la estación de la alta velocidad de León, y acaba en Santander', () => {
    const nodos = red.nodes.filter((n) => n.line_id === LINEA).sort((a, b) => a.km - b.km)
    expect(nodos).toHaveLength(22)
    expect(nodos[0].id).toBe('palencia')
    expect(nodos.at(-1)?.id).toBe('santander')
    const lineasDe = (id: string) => red.nodes.filter((n) => n.id === id).map((n) => n.line_id)
    expect(lineasDe('palencia')).toContain(LINEA)
    expect(lineasDe('palencia')).toContain(LAV_LEON)
    expect(lineasDe('reinosa')).toEqual([LINEA])
    expect(lineasDe('santander')).toEqual([LINEA])
  })

  test('es de vía única y ancho ibérico en toda su longitud', () => {
    const tramos = red.segments.filter((s) => s.line_id === LINEA)
    expect(tramos).toHaveLength(21)
    expect(tramos.every((s) => s.tracks === 1)).toBe(true)
    expect(red.lines.find((l) => l.id === LINEA)?.gauge_mm).toBe(1668)
  })

  test('Palencia ya no sale a trazos hacia Santander', () => {
    const conexiones = red.connections.filter((c) => c.node_id === 'palencia')
    expect(conexiones.map((c) => c.id)).not.toContain('conv-palencia-santander')
  })

  test('el comparador lleva de Madrid a Santander por Valladolid y Palencia', () => {
    const [primera] = findRoutes(grafo, CHAMARTIN, 'santander')
    expect(primera.length_km).toBe(446.8)
    expect(primera.line_ids).toEqual(['lav-madrid-valladolid', LAV_LEON, LINEA])
  })

  test('la línea tiene su ficha, con Aguilar de Campoo y Reinosa en el esquema', async ({ page }) => {
    await page.goto(`/linea/${LINEA}`)
    await expect(page.getByRole('heading', { name: 'Línea convencional Palencia – Santander' })).toBeVisible()
    await expect(page.locator('body')).toContainText('Une la meseta con la costa de Cantabria')
    const esquema = page.getByTestId('esquema')
    await expect(esquema).toContainText('Palencia')
    await expect(esquema).toContainText('Aguilar de Campoo')
    await expect(esquema).toContainText('Reinosa')
    await expect(esquema).toContainText('Torrelavega')
    await expect(esquema).toContainText('Santander')
  })

  test('el buscador lleva a Santander', async ({ page }) => {
    await page.goto('/')
    await expect(page.getByTestId('vista-red')).toBeVisible()
    const campo = await abrirBuscador(page)
    await campo.fill('santander')
    const primero = page.getByRole('option').first()
    await expect(primero).toContainText('Santander')
    await expect(primero).toContainText('Estación')
    await campo.press('Enter')
    await expect(page).toHaveURL(/\/nodo\/santander$/)
    await expect(page.getByTestId('detalle-nodo').getByRole('heading', { name: 'Santander' })).toBeVisible()
  })

  test('un tramo de la montaña dice su vía única y su bloqueo', async ({ page }) => {
    await page.goto(`/tramo/${REINOSA_BARCENA}`)
    await expect(page.getByTestId('detalle-tramo')).toBeVisible()
    const asa = page.getByRole('button', { name: 'Ampliar el panel' })
    if (await asa.isVisible()) await asa.click()
    await expect(page.getByTestId('tramo-vias')).toHaveText('Vía única')
    await expect(page.getByTestId('tramo-atributo-proteccion_tren')).toHaveText('ASFA')
  })

  test('el comparador enseña el recorrido de Madrid a Santander', async ({ page }) => {
    await page.goto(`/recorridos/${CHAMARTIN}/santander`)
    const recorrido = page.getByTestId('recorrido').first()
    await expect(recorrido).toBeVisible()
    await expect(recorrido).toContainText('446,8 km')
    await expect(recorrido).toContainText('Palencia')
  })
})
