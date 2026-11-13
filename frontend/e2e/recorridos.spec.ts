import { readFileSync } from 'node:fs'

import { expect, test } from '@playwright/test'

import { irA } from './navegar.ts'

import { activeInterruptions, bySegment } from '../src/app/interruptions.ts'
import { compararRecorridos, formatDuracion, minutosEntre, trenesDelRecorrido, trenesDirectos } from '../src/app/recorridos.ts'
import { parseRoute, routePath } from '../src/app/state.ts'
import { composeNetwork } from '../src/data/network.ts'
import type { NetworkIndexOut, NodeCall } from '../src/data/types.ts'
import { buildGraph } from '../src/routing/graph.ts'

const leer = <T>(ruta: string) => JSON.parse(readFileSync(new URL(ruta, import.meta.url), 'utf-8')) as T
const red = composeNetwork(leer<NetworkIndexOut>('../public/data/index.json'), {})
const grafo = buildGraph(red)

const MADRID = 'madrid-puerta-de-atocha'
const URDA_CIUDAD_REAL = 'lav-madrid-sevilla:urda:ciudad-real'
const sinCortes = new Map<string, never[]>()

test.describe('Comparador de recorridos: qué se enseña', () => {
  test('los tiempos se dicen como en un horario', () => {
    expect(formatDuracion(40)).toBe('40 min')
    expect(formatDuracion(81)).toBe('1 h 21 min')
    expect(formatDuracion(120)).toBe('2 h')
    expect(minutosEntre('06:00', '08:35')).toBe(155)
  })

  test('la ruta del comparador va y vuelve de la URL', () => {
    expect(parseRoute('/recorridos').recorridos).toEqual({ from: null, to: null })
    expect(parseRoute('/recorridos/manzanares').recorridos).toEqual({ from: 'manzanares', to: null })
    expect(parseRoute('/recorridos/-/cordoba').recorridos).toEqual({ from: null, to: 'cordoba' })
    const conSupuesto = `/recorridos/${MADRID}/ciudad-real/c~${URDA_CIUDAD_REAL}`
    expect(parseRoute(conSupuesto).recorridos).toEqual({ from: MADRID, to: 'ciudad-real', escenario: `c~${URDA_CIUDAD_REAL}` })
    for (const ruta of ['/recorridos', '/recorridos/manzanares', '/recorridos/-/cordoba', `/recorridos/${MADRID}/cordoba`, conSupuesto]) {
      expect(routePath(parseRoute(ruta))).toBe(ruta)
    }
  })

  test('Madrid – Córdoba enseña tres recorridos y deja fuera el cuarto', () => {
    const c = compararRecorridos(grafo, red, MADRID, 'cordoba', sinCortes)
    expect(c.recorridos.map((r) => r.route.length_km)).toEqual([343.6, 433.3, 440.7])
    expect(c.recorridos.map((r) => r.titulo)).toEqual(['Por la alta velocidad', 'Por Manzanares y Ciudad Real', 'Por la línea convencional'])
    expect(c.recorridos.map((r) => r.lineas)).toEqual([null, 'Recorre tres líneas', null])
    expect(c.ocultos).toBe(1)
    expect(c.recorridos.every((r) => r.cortes.length === 0 && !r.alternativa)).toBe(true)
    // primer y último tramo de cada línea que recorre
    expect(c.recorridos[0]!.tramosClave).toEqual([`lav-madrid-sevilla:${MADRID}:bif-los-gavilanes`, 'lav-madrid-sevilla:adamuz:cordoba'])
    expect(c.recorridos[1]!.tramosClave).toHaveLength(6)
  })

  test('Sevilla – Manzanares: sin la vuelta por Madrid y con nombres que distinguen los dos recorridos', () => {
    const c = compararRecorridos(grafo, red, 'sevilla-santa-justa', 'manzanares', sinCortes)
    // el que sube de Ciudad Real a Madrid para volver (666,4 km) ya no aparece
    expect(c.recorridos.map((r) => r.route.length_km)).toEqual([363.9, 371.2])
    expect(c.ocultos).toBe(0)
    // los dos pasan por Córdoba: el que cambia allí de línea dice además cuál toma
    expect(c.recorridos.map((r) => r.titulo)).toEqual(['Por Ciudad Real', 'Por Córdoba y la línea convencional'])
    const vuelta = compararRecorridos(grafo, red, 'manzanares', 'sevilla-santa-justa', sinCortes)
    expect(vuelta.recorridos.map((r) => r.route.length_km)).toEqual([363.9, 371.2])
    expect(vuelta.recorridos.map((r) => r.titulo)).toEqual(['Por Ciudad Real', 'Por Córdoba y la línea convencional'])
  })

  test('un cierre en la alta velocidad señala el recorrido por Manzanares como alternativa', () => {
    const c = compararRecorridos(grafo, red, MADRID, 'ciudad-real', sinCortes, `c~${URDA_CIUDAD_REAL}`)
    expect(c.recorridos.map((r) => r.route.length_km)).toEqual([170.8, 260.5])
    expect(c.recorridos[0]!.cortes).toEqual([{ id: URDA_CIUDAD_REAL, from_name: 'Urda', to_name: 'Ciudad Real', interruption: null }])
    expect(c.recorridos.map((r) => r.alternativa)).toEqual([false, true])
    expect(c.escenario).toEqual(['cierre de Urda – Ciudad Real'])
    expect(c.sinPaso).toBe(false)
  })

  test('con las interrupciones del 11 de noviembre de 2026, Madrid – Córdoba no tiene paso y Madrid – Ciudad Real sí', () => {
    const cortes = bySegment(activeInterruptions(red, '2026-11-11'))
    const aCordoba = compararRecorridos(grafo, red, MADRID, 'cordoba', cortes)
    expect(aCordoba.recorridos.map((r) => r.cortes.length > 0)).toEqual([true, true, true])
    expect(aCordoba.sinPaso).toBe(true)
    const aCiudadReal = compararRecorridos(grafo, red, MADRID, 'ciudad-real', cortes)
    expect(aCiudadReal.recorridos.map((r) => r.alternativa)).toEqual([false, true])
    // si el único recorrido a la vista está cortado, se añade el más corto que no lo está, mida lo que mida
    const corto = compararRecorridos(grafo, red, 'manzanares', 'ciudad-real', sinCortes, 'c~manzanares-ciudad-real:daimiel:almagro')
    expect(corto.recorridos.map((r) => [r.route.length_km, r.alternativa])).toEqual([
      [64.4, false],
      [366.9, true],
    ])
  })

  test('un supuesto que no encaja con la red se ignora y se dice', () => {
    const c = compararRecorridos(grafo, red, MADRID, 'cordoba', sinCortes, 'c~no:existe')
    expect(c.escenarioIlegible).toBe(true)
    expect(c.recorridos).toHaveLength(3)
    expect(compararRecorridos(grafo, red, MADRID, 'cordoba', sinCortes, 'esto no es').escenarioIlegible).toBe(true)
  })

  test('los trenes directos de la instantánea se reparten entre los recorridos', () => {
    const paradas = (nodo: string) => leer<{ calls: NodeCall[] }>(`../public/data/nodes/${nodo}.json`).calls
    const directos = trenesDirectos(paradas(MADRID), paradas('cordoba'))
    expect(directos.length).toBeGreaterThan(0)
    expect(directos.every((t) => t.minutes > 0)).toBe(true)
    // en sentido contrario son otros trenes
    const vuelta = trenesDirectos(paradas('cordoba'), paradas(MADRID))
    expect(vuelta.some((t) => directos.some((d) => d.service_id === t.service_id))).toBe(false)
    const c = compararRecorridos(grafo, red, MADRID, 'cordoba', sinCortes)
    const pasos = new Map(
      [...new Set(c.recorridos.flatMap((r) => r.tramosClave))].map((id) => [
        id,
        new Set(leer<{ passes: { service: { id: string } }[] }>(`../public/data/segments/${id.replaceAll(':', '--')}.json`).passes.map((p) => p.service.id)),
      ]),
    )
    const porRecorrido = c.recorridos.map((r) => trenesDelRecorrido(r, directos, pasos))
    // ninguno cuenta dos veces, y por la convencional entera no hay directos
    expect(porRecorrido[0]!.length + porRecorrido[1]!.length).toBe(directos.length)
    expect(porRecorrido[0]!.length).toBeGreaterThan(porRecorrido[1]!.length)
    expect(porRecorrido[2]).toHaveLength(0)
  })
})

test.describe('Comparador de recorridos: la vista', () => {
  test('desde la cabecera se abre el comparador, se eligen dos estaciones y se comparan Madrid y Córdoba', async ({ page }) => {
    await page.goto('/')
    await irA(page, 'recorridos')
    await expect(page).toHaveURL(/\/recorridos$/)
    const panel = page.getByTestId('comparador')
    await expect(panel.getByRole('heading', { name: 'Comparar recorridos' })).toBeVisible()
    await expect(page.getByTestId('recorridos-ayuda')).toBeVisible()

    const desde = page.getByRole('combobox', { name: 'Desde: buscar una estación' })
    await desde.fill('atocha')
    await desde.press('Enter')
    await expect(page).toHaveURL(/\/recorridos\/madrid-puerta-de-atocha$/)
    const hasta = page.getByRole('combobox', { name: 'Hasta: buscar una estación' })
    await hasta.fill('cordoba')
    await page.getByRole('option', { name: /^Córdoba/ }).click()
    await expect(page).toHaveURL(/\/recorridos\/madrid-puerta-de-atocha\/cordoba$/)

    const recorridos = page.getByTestId('recorrido')
    await expect(recorridos).toHaveCount(3)
    await expect(page.getByTestId('recorridos-resumen')).toContainText('Tres recorridos, del más corto al más largo.')
    await expect(recorridos.nth(0)).toContainText('Por la alta velocidad')
    await expect(recorridos.nth(0)).toContainText('343,6 km · 1 h 20 min sin paradas · sin vía única')
    await expect(recorridos.nth(0)).toContainText('Pasa por Ciudad Real, Puertollano y Villanueva de Córdoba.')
    await expect(recorridos.nth(1)).toContainText('Por Manzanares y Ciudad Real')
    await expect(recorridos.nth(1)).toContainText('Recorre tres líneas')
    await expect(recorridos.nth(1)).toContainText('433,3 km')
    await expect(recorridos.nth(2)).toContainText('Por la línea convencional')
    await expect(recorridos.nth(2)).toContainText('440,7 km · 3 h 6 min sin paradas · 194,1 km de vía única')
    await expect(recorridos.nth(2)).toContainText('Alcázar de San Juan')
    // trenes directos del día de referencia, por recorrido
    await expect(page.getByTestId('recorridos-resumen')).toContainText(/Hay \d+ trenes directos en este sentido/)
    await expect(recorridos.nth(0).getByTestId('recorrido-trenes')).toContainText(/\d+ trenes directos en el horario del .*; el más rápido tarda \d h/)
    await expect(recorridos.nth(2).getByTestId('recorrido-trenes')).toContainText('Ningún tren directo')
    // los dos límites del cálculo, a la vista
    const limites = page.getByTestId('recorridos-limites')
    await expect(limites).toContainText('no es un horario')
    await expect(limites).toContainText('sin mirar el ancho de vía')

    // el primero es el elegido; al tocar otro, cambia el resaltado del mapa
    await expect(recorridos.nth(0).getByRole('button', { name: 'Por la alta velocidad' })).toHaveAttribute('aria-pressed', 'true')
    await expect(page.getByTestId('mapa')).toHaveAttribute('data-recorrido-elegido', '10')
    await recorridos.nth(2).getByRole('button', { name: 'Por la línea convencional' }).click()
    await expect(recorridos.nth(2).locator('.recorrido-titulo')).toHaveAttribute('aria-pressed', 'true')
    await expect(page.getByTestId('mapa')).toHaveAttribute('data-recorrido-elegido', '25')

    // el detalle dice las líneas de cada recorrido y el método
    await page.getByTestId('mas-detalle').locator('summary').click()
    await expect(page.getByTestId('recorrido-detalle').nth(1)).toContainText('Línea convencional Manzanares – Ciudad Real, de Manzanares a Ciudad Real: 64,4 km')
    await expect(page.getByTestId('mas-detalle')).toContainText('uno más, más largo, que no se enseña')

    await page.getByTestId('recorridos-invertir').click()
    await expect(page).toHaveURL(/\/recorridos\/cordoba\/madrid-puerta-de-atocha$/)
    await page.getByTestId('volver-red').click()
    await expect(page.getByTestId('vista-red')).toBeVisible()
  })

  test('la lista de sugerencias de «Desde» queda por delante del campo «Hasta» y se puede pulsar', async ({ page }) => {
    await page.goto('/recorridos')
    const desde = page.getByRole('combobox', { name: 'Desde: buscar una estación' })
    await desde.fill('m')
    const primera = page.getByTestId('recorridos-desde').getByRole('option').first()
    await expect(primera).toBeVisible()
    // Lo que hay bajo el centro de la primera sugerencia es la propia sugerencia, no la fila «Hasta» que tiene debajo.
    const encima = await primera.evaluate((li) => {
      const r = li.getBoundingClientRect()
      const el = document.elementFromPoint(r.left + r.width / 2, r.top + r.height / 2)
      return el !== null && li.contains(el)
    })
    expect(encima).toBe(true)
    // Y la lista sale alineada con el campo en el que se escribe.
    const campo = await page.getByTestId('recorridos-desde-buscador').boundingBox()
    const lista = await page.getByTestId('recorridos-desde').locator('.buscador-lista').boundingBox()
    expect(Math.abs(lista!.x - campo!.x)).toBeLessThan(2)
    await primera.click()
    await expect(page).toHaveURL(/\/recorridos\/[a-z0-9-]+$/)
  })

  test('Madrid – Ciudad Real con la alta velocidad cerrada señala el recorrido por Manzanares', async ({ page }) => {
    await page.goto(`/recorridos/${MADRID}/ciudad-real/c~${URDA_CIUDAD_REAL}`)
    const recorridos = page.getByTestId('recorrido')
    await expect(recorridos).toHaveCount(2)
    await expect(page.getByTestId('recorridos-escenario')).toContainText('cierre de Urda – Ciudad Real')
    await expect(recorridos.nth(0)).toContainText('170,8 km')
    await expect(recorridos.nth(0).getByTestId('recorrido-corte').first()).toBeVisible()
    await expect(recorridos.nth(0)).toContainText('Cerrado en este supuesto entre Urda y Ciudad Real.')
    await expect(recorridos.nth(1)).toContainText('Por Manzanares')
    await expect(recorridos.nth(1)).toContainText('Recorre dos líneas · el más corto que no está cortado')
    await expect(recorridos.nth(1)).toContainText('260,5 km · 1 h 47 min sin paradas · 64,4 km de vía única')
    // sin el supuesto, la URL vuelve a ser la de las dos estaciones
    await page.getByRole('button', { name: 'Quitar el supuesto' }).click()
    await expect(page).toHaveURL(/\/recorridos\/madrid-puerta-de-atocha\/ciudad-real$/)
    await expect(recorridos).toHaveCount(2)
  })

  test('Sevilla – Manzanares: dos recorridos con nombres distintos y ningún tren directo', async ({ page }) => {
    await page.goto('/recorridos/sevilla-santa-justa/manzanares')
    const recorridos = page.getByTestId('recorrido')
    await expect(recorridos).toHaveCount(2)
    await expect(recorridos.nth(0)).toContainText('Por Ciudad Real')
    await expect(recorridos.nth(0)).toContainText('363,9 km')
    await expect(recorridos.nth(1)).toContainText('Por Córdoba y la línea convencional')
    await expect(recorridos.nth(1)).toContainText('371,2 km')
    // la vuelta por Madrid, de 666,4 km, no se enseña
    await expect(page.getByTestId('comparador')).not.toContainText('666,4')
    await expect(page.getByTestId('recorridos-resumen')).toHaveText(/^Dos recorridos, del más corto al más largo\. No hay trenes directos en este sentido en el horario del .+\.$/)
  })

  test('la ficha de una estación abre el comparador con ella como salida', async ({ page }) => {
    await page.goto('/nodo/manzanares')
    await page.getByTestId('recorridos-desde-aqui').click()
    await expect(page).toHaveURL(/\/recorridos\/manzanares$/)
    await expect(page.getByTestId('recorridos-desde')).toContainText('Manzanares')
    await page.getByTestId('recorridos-desde').getByRole('button', { name: /Cambiar/ }).click()
    await expect(page).toHaveURL(/\/recorridos$/)
  })

  test('una estación que no existe en la URL queda sin elegir', async ({ page }) => {
    await page.goto('/recorridos/atlantida/cordoba')
    await expect(page.getByRole('combobox', { name: 'Desde: buscar una estación' })).toBeVisible()
    await expect(page.getByTestId('recorridos-hasta')).toContainText('Córdoba')
    await expect(page.getByTestId('recorrido')).toHaveCount(0)
  })
})
