import { readFileSync } from 'node:fs'

import { expect, test } from '@playwright/test'

import { composeNetwork } from '../src/data/network.ts'
import type { NetworkIndexOut } from '../src/data/types.ts'
import { formatKm } from '../src/app/state.ts'
import { buildGraph, findRoutes } from '../src/routing/graph.ts'

const leer = <T>(ruta: string) => JSON.parse(readFileSync(new URL(ruta, import.meta.url), 'utf-8')) as T
const red = composeNetwork(leer<NetworkIndexOut>('../public/data/index.json'), {})
const grafo = buildGraph(red)

const LINEA = 'miranda-bilbao'
const BURGOS_VITORIA = 'burgos-miranda-vitoria'
const CHAMARTIN = 'madrid-chamartin'
const BILBAO = 'bilbao-abando'
const MIRANDA_ORDUNA = `${LINEA}:miranda-de-ebro:orduna`
const ORDUNA_LLODIO = `${LINEA}:orduna:llodio`

/** El campo del buscador: en escritorio está a la vista; en el móvil lo despliega la lupa. */
async function abrirBuscador(page: import('@playwright/test').Page) {
  const lupa = page.getByTestId('buscador-abrir')
  if (await lupa.isVisible()) await lupa.click()
  return page.getByRole('combobox', { name: 'Buscar una estación o una línea' })
}

test.describe('Línea convencional de Miranda de Ebro a Bilbao', () => {
  test('sale de Miranda de Ebro, la estación de la línea de Burgos a Vitoria, y acaba en Bilbao', () => {
    const nodos = red.nodes.filter((n) => n.line_id === LINEA).sort((a, b) => a.km - b.km)
    expect(nodos.map((n) => n.id)).toEqual(['miranda-de-ebro', 'orduna', 'llodio', BILBAO])
    const lineasDe = (id: string) => red.nodes.filter((n) => n.id === id).map((n) => n.line_id)
    expect(lineasDe('miranda-de-ebro')).toContain(LINEA)
    expect(lineasDe('miranda-de-ebro')).toContain(BURGOS_VITORIA)
    expect(lineasDe(BILBAO)).toEqual([LINEA])
  })

  test('es de vía única hasta Orduña y de vía doble de ahí a Bilbao', () => {
    const tramos = red.segments.filter((s) => s.line_id === LINEA)
    expect(tramos.map((s) => s.tracks)).toEqual([1, 2, 2])
    expect(red.lines.find((l) => l.id === LINEA)?.gauge_mm).toBe(1668)
  })

  test('Miranda de Ebro ya no sale a trazos hacia Bilbao, y sí hacia Logroño', () => {
    const conexiones = red.connections.filter((c) => c.node_id === 'miranda-de-ebro').map((c) => c.id)
    expect(conexiones).not.toContain('conv-miranda-bilbao')
    expect(conexiones).toContain('conv-miranda-logrono')
  })

  test('el comparador lleva de Madrid a Bilbao por Burgos y Miranda de Ebro', () => {
    const [primera] = findRoutes(grafo, CHAMARTIN, BILBAO)
    expect(primera.line_ids.at(-2)).toBe(BURGOS_VITORIA)
    expect(primera.line_ids.at(-1)).toBe(LINEA)
  })

  test('la línea tiene su ficha, con Orduña y Llodio en el esquema', async ({ page }) => {
    await page.goto(`/linea/${LINEA}`)
    await expect(page.getByRole('heading', { name: 'Línea convencional Miranda de Ebro – Orduña – Bilbao' })).toBeVisible()
    await expect(page.locator('body')).toContainText('Une Miranda de Ebro con Bilbao')
    const esquema = page.getByTestId('esquema')
    await expect(esquema).toContainText('Miranda de Ebro')
    // Orduña es secundaria: en el móvil el esquema no la rotula, pero el tramo la nombra
    await expect(esquema.getByRole('button', { name: /^Tramo Miranda de Ebro – Orduña/ })).toBeVisible()
    await expect(esquema).toContainText('Llodio')
    await expect(esquema).toContainText('Bilbao-Abando')
  })

  test('el buscador lleva a la estación de Bilbao', async ({ page }) => {
    await page.goto('/')
    await expect(page.getByTestId('vista-red')).toBeVisible()
    const campo = await abrirBuscador(page)
    await campo.fill('abando')
    const primero = page.getByRole('option').first()
    await expect(primero).toContainText('Bilbao-Abando')
    await expect(primero).toContainText('Estación')
    await campo.press('Enter')
    await expect(page).toHaveURL(new RegExp(`/nodo/${BILBAO}$`))
    await expect(page.getByTestId('detalle-nodo').getByRole('heading', { name: 'Bilbao-Abando Indalecio Prieto' })).toBeVisible()
  })

  test('los tramos dicen su vía y su bloqueo', async ({ page }) => {
    const asa = page.getByRole('button', { name: 'Ampliar el panel' })
    await page.goto(`/tramo/${MIRANDA_ORDUNA}`)
    await expect(page.getByTestId('detalle-tramo')).toBeVisible()
    if (await asa.isVisible()) await asa.click()
    await expect(page.getByTestId('tramo-vias')).toHaveText('Vía única')
    await expect(page.getByTestId('tramo-atributo-proteccion_tren')).toHaveText('ASFA')
    await page.goto(`/tramo/${ORDUNA_LLODIO}`)
    await expect(page.getByTestId('detalle-tramo')).toBeVisible()
    if (await asa.isVisible()) await asa.click()
    await expect(page.getByTestId('tramo-vias')).toHaveText('Vía doble')
  })

  test('el comparador enseña el recorrido de Madrid a Bilbao', async ({ page }) => {
    const [primera] = findRoutes(grafo, CHAMARTIN, BILBAO)
    await page.goto(`/recorridos/${CHAMARTIN}/${BILBAO}`)
    const recorrido = page.getByTestId('recorrido').first()
    await expect(recorrido).toBeVisible()
    await expect(recorrido).toContainText(`${formatKm(primera.length_km)} km`)
    await expect(recorrido).toContainText('Miranda de Ebro')
  })
})
