import { readFileSync } from 'node:fs'

import { expect, test } from '@playwright/test'

import { composeNetwork } from '../src/data/network.ts'
import type { NetworkIndexOut } from '../src/data/types.ts'
import { buildGraph, findRoutes } from '../src/routing/graph.ts'

const leer = <T>(ruta: string) => JSON.parse(readFileSync(new URL(ruta, import.meta.url), 'utf-8')) as T
const red = composeNetwork(leer<NetworkIndexOut>('../public/data/index.json'), {})
const grafo = buildGraph(red)

const EBRO = 'zaragoza-castejon-logrono'
const NAVARRA = 'castejon-pamplona'
const LAV = 'lav-madrid-barcelona'
const ATOCHA = 'madrid-puerta-de-atocha'
const CASTEJON_ALFARO = `${EBRO}:castejon-de-ebro:alfaro`
const TAFALLA_PAMPLONA = `${NAVARRA}:tafalla:pamplona`

/** El campo del buscador: en escritorio está a la vista; en el móvil lo despliega la lupa. */
async function abrirBuscador(page: import('@playwright/test').Page) {
  const lupa = page.getByTestId('buscador-abrir')
  if (await lupa.isVisible()) await lupa.click()
  return page.getByRole('combobox', { name: 'Buscar una estación o una línea' })
}

const nodosDe = (linea: string) => red.nodes.filter((n) => n.line_id === linea).sort((a, b) => a.km - b.km)
const lineasDe = (id: string) => red.nodes.filter((n) => n.id === id).map((n) => n.line_id)

test.describe('Líneas convencionales de Zaragoza a Logroño y de Castejón a Pamplona', () => {
  test('la del Ebro sale de Zaragoza-Delicias, la estación de la alta velocidad, y acaba en Logroño', () => {
    const nodos = nodosDe(EBRO)
    expect(nodos).toHaveLength(19)
    expect(nodos[0].id).toBe('zaragoza-delicias')
    expect(nodos.at(-1)?.id).toBe('logrono')
    expect(lineasDe('zaragoza-delicias')).toContain(EBRO)
    expect(lineasDe('zaragoza-delicias')).toContain(LAV)
    expect(lineasDe('logrono')).toEqual([EBRO])
  })

  test('la de Pamplona sale de Castejón de Ebro, que comparten las dos', () => {
    const nodos = nodosDe(NAVARRA)
    expect(nodos.map((n) => n.id)).toEqual([
      'castejon-de-ebro',
      'villafranca-de-navarra',
      'marcilla-de-navarra',
      'olite',
      'tafalla',
      'pamplona',
    ])
    expect([...lineasDe('castejon-de-ebro')].sort()).toEqual([NAVARRA, EBRO].sort())
    expect(lineasDe('pamplona')).toEqual([NAVARRA])
  })

  test('hay dos vías hasta Castejón y una sola de ahí a Logroño y a Pamplona', () => {
    const tramos = red.segments.filter((s) => s.line_id === EBRO)
    expect(tramos).toHaveLength(18)
    const castejon = nodosDe(EBRO).find((n) => n.id === 'castejon-de-ebro')?.km ?? 0
    for (const tramo of tramos) expect(tramo.tracks).toBe(tramo.km_to <= castejon + 0.01 ? 2 : 1)
    const aPamplona = red.segments.filter((s) => s.line_id === NAVARRA)
    expect(aPamplona).toHaveLength(5)
    expect(aPamplona.every((s) => s.tracks === 1)).toBe(true)
  })

  test('Zaragoza ya no sale a trazos hacia Tudela; quedan a trazos Casetas, Pamplona y el cambiador', () => {
    const ids = red.connections.map((c) => c.id)
    expect(ids).not.toContain('convencional-zaragoza-norte')
    const de = (nodo: string) => red.connections.filter((c) => c.node_id === nodo).map((c) => c.id)
    expect(de('casetas')).toEqual(['conv-casetas-calatayud'])
    expect(de('pamplona')).toEqual(['conv-pamplona-altsasu'])
    expect(de('cambiador-plasencia-de-jalon')).toEqual(['convencional-plasencia-de-jalon-tudela'])
  })

  test('el comparador lleva de Madrid a Pamplona y a Logroño por Zaragoza', () => {
    const [aPamplona] = findRoutes(grafo, ATOCHA, 'pamplona')
    expect(aPamplona.length_km).toBe(483.6)
    expect(aPamplona.line_ids).toEqual([LAV, EBRO, NAVARRA])
    const [aLogrono] = findRoutes(grafo, ATOCHA, 'logrono')
    expect(aLogrono.length_km).toBe(472.1)
    expect(aLogrono.line_ids).toEqual([LAV, EBRO])
    const [desdeZaragoza] = findRoutes(grafo, 'zaragoza-delicias', 'pamplona')
    expect(desdeZaragoza.length_km).toBe(177.1)
  })

  test('cada línea tiene su ficha, con sus estaciones principales en el esquema', async ({ page }) => {
    await page.goto(`/linea/${EBRO}`)
    await expect(
      page.getByRole('heading', { name: 'Línea convencional Zaragoza – Castejón – Logroño' }),
    ).toBeVisible()
    await expect(page.locator('body')).toContainText('Sigue el valle del Ebro aguas arriba')
    const esquema = page.getByTestId('esquema')
    for (const nombre of ['Zaragoza-Delicias', 'Tudela de Navarra', 'Castejón de Ebro', 'Calahorra', 'Logroño'])
      await expect(esquema).toContainText(nombre)

    await page.goto(`/linea/${NAVARRA}`)
    await expect(page.getByRole('heading', { name: 'Línea convencional Castejón – Pamplona' })).toBeVisible()
    for (const nombre of ['Castejón de Ebro', 'Tafalla', 'Pamplona/Iruña'])
      await expect(page.getByTestId('esquema')).toContainText(nombre)
  })

  test('el buscador lleva a Pamplona y a Logroño', async ({ page }) => {
    for (const [texto, nombre, id] of [
      ['pamplona', 'Pamplona/Iruña', 'pamplona'],
      ['logroño', 'Logroño', 'logrono'],
    ]) {
      await page.goto('/')
      await expect(page.getByTestId('vista-red')).toBeVisible()
      const campo = await abrirBuscador(page)
      await campo.fill(texto)
      const primero = page.getByRole('option').first()
      await expect(primero).toContainText(nombre)
      await expect(primero).toContainText('Estación')
      await campo.press('Enter')
      await expect(page).toHaveURL(new RegExp(`/nodo/${id}$`))
      await expect(page.getByTestId('detalle-nodo').getByRole('heading', { name: nombre })).toBeVisible()
    }
  })

  test('un tramo de vía única dice su vía y su protección', async ({ page }) => {
    for (const tramo of [CASTEJON_ALFARO, TAFALLA_PAMPLONA]) {
      await page.goto(`/tramo/${tramo}`)
      await expect(page.getByTestId('detalle-tramo')).toBeVisible()
      const asa = page.getByRole('button', { name: 'Ampliar el panel' })
      if (await asa.isVisible()) await asa.click()
      await expect(page.getByTestId('tramo-vias')).toHaveText('Vía única')
      await expect(page.getByTestId('tramo-atributo-proteccion_tren')).toHaveText('ASFA')
    }
  })

  test('el comparador enseña el recorrido de Madrid a Pamplona', async ({ page }) => {
    await page.goto(`/recorridos/${ATOCHA}/pamplona`)
    const recorrido = page.getByTestId('recorrido').first()
    await expect(recorrido).toBeVisible()
    await expect(recorrido).toContainText('483,6 km')
    await expect(recorrido).toContainText('Castejón de Ebro')
  })
})
