import { readFileSync } from 'node:fs'

import { expect, test } from '@playwright/test'

import { composeNetwork } from '../src/data/network.ts'
import type { NetworkIndexOut } from '../src/data/types.ts'
import { buildGraph, findRoutes } from '../src/routing/graph.ts'

const leer = <T>(ruta: string) => JSON.parse(readFileSync(new URL(ruta, import.meta.url), 'utf-8')) as T
const red = composeNetwork(leer<NetworkIndexOut>('../public/data/index.json'), {})
const grafo = buildGraph(red)

const LINEA = 'sevilla-huelva'
const LAV_SEVILLA = 'lav-madrid-sevilla'
const ATOCHA = 'madrid-puerta-de-atocha'
const SANTA_JUSTA = 'sevilla-santa-justa'
const NIEBLA_SAN_JUAN = `${LINEA}:niebla-puerta-del-buey:san-juan-del-puerto`

/** El campo del buscador: en escritorio está a la vista; en el móvil lo despliega la lupa. */
async function abrirBuscador(page: import('@playwright/test').Page) {
  const lupa = page.getByTestId('buscador-abrir')
  if (await lupa.isVisible()) await lupa.click()
  return page.getByRole('combobox', { name: 'Buscar una estación o una línea' })
}

test.describe('Línea convencional de Sevilla a Huelva', () => {
  test('sale de Santa Justa, pasa por la bifurcación Los Naranjos y acaba en Huelva', () => {
    const nodos = red.nodes.filter((n) => n.line_id === LINEA).sort((a, b) => a.km - b.km)
    expect(nodos).toHaveLength(12)
    expect(nodos.map((n) => n.id).slice(0, 2)).toEqual([SANTA_JUSTA, 'bif-los-naranjos'])
    expect(nodos.at(-1)?.id).toBe('huelva')
    const lineasDe = (id: string) => red.nodes.filter((n) => n.id === id).map((n) => n.line_id)
    expect(lineasDe(SANTA_JUSTA)).toContain(LINEA)
    expect(lineasDe(SANTA_JUSTA)).toContain(LAV_SEVILLA)
    expect(lineasDe('huelva')).toEqual([LINEA])
  })

  test('es de vía doble hasta la bifurcación de Cartuja y de vía única desde allí', () => {
    const tramos = red.segments.filter((s) => s.line_id === LINEA)
    expect(tramos).toHaveLength(11)
    expect(tramos.filter((s) => s.tracks === 2).map((s) => s.id)).toEqual([
      `${LINEA}:${SANTA_JUSTA}:bif-los-naranjos`,
      `${LINEA}:bif-los-naranjos:bif-cartuja`,
    ])
    expect(red.lines.find((l) => l.id === LINEA)?.gauge_mm).toBe(1668)
  })

  test('Santa Justa ya no sale a trazos hacia Huelva; el enlace de Majarabique sí', () => {
    const conexiones = red.connections.filter((c) => c.node_id === SANTA_JUSTA)
    expect(conexiones.map((c) => c.id)).not.toContain('sevilla-huelva')
    const enlace = red.connections.find((c) => c.id === 'majarabique-los-naranjos')
    expect(enlace?.node_id).toBe('majarabique')
  })

  test('el comparador lleva de Madrid a Huelva por la alta velocidad y Santa Justa', () => {
    const [primera] = findRoutes(grafo, ATOCHA, 'huelva')
    expect(primera.length_km).toBe(587.2)
    expect(primera.line_ids).toEqual([LAV_SEVILLA, LINEA])
    const [deSevilla] = findRoutes(grafo, SANTA_JUSTA, 'huelva')
    expect(deSevilla.length_km).toBe(117)
    expect(deSevilla.line_ids).toEqual([LINEA])
  })

  test('la línea tiene su ficha, con La Palma del Condado y Niebla en el esquema', async ({ page }) => {
    await page.goto(`/linea/${LINEA}`)
    await expect(page.getByRole('heading', { name: 'Línea convencional Sevilla – Huelva' })).toBeVisible()
    await expect(page.locator('body')).toContainText('Une Sevilla con Huelva')
    const esquema = page.getByTestId('esquema')
    await expect(esquema).toContainText('Sevilla-Santa Justa')
    await expect(esquema).toContainText('Los Naranjos')
    await expect(esquema).toContainText('La Palma del Condado')
    await expect(esquema).toContainText('Huelva')
  })

  test('el buscador lleva a Huelva', async ({ page }) => {
    await page.goto('/')
    await expect(page.getByTestId('vista-red')).toBeVisible()
    const campo = await abrirBuscador(page)
    await campo.fill('huelva')
    const primero = page.getByRole('option').first()
    await expect(primero).toContainText('Huelva')
    await expect(primero).toContainText('Estación')
    await campo.press('Enter')
    await expect(page).toHaveURL(/\/nodo\/huelva$/)
    await expect(page.getByTestId('detalle-nodo').getByRole('heading', { name: 'Huelva' })).toBeVisible()
  })

  test('un tramo del Condado dice su vía única y su protección', async ({ page }) => {
    await page.goto(`/tramo/${NIEBLA_SAN_JUAN}`)
    await expect(page.getByTestId('detalle-tramo')).toBeVisible()
    const asa = page.getByRole('button', { name: 'Ampliar el panel' })
    if (await asa.isVisible()) await asa.click()
    await expect(page.getByTestId('tramo-vias')).toHaveText('Vía única')
    await expect(page.getByTestId('tramo-atributo-proteccion_tren')).toHaveText('ASFA')
  })

  test('el comparador enseña el recorrido de Madrid a Huelva', async ({ page }) => {
    await page.goto(`/recorridos/${ATOCHA}/huelva`)
    const recorrido = page.getByTestId('recorrido').first()
    await expect(recorrido).toBeVisible()
    await expect(recorrido).toContainText('587,2 km')
    await expect(recorrido).toContainText('Sevilla-Santa Justa')
  })
})
