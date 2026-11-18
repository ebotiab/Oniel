import { readFileSync } from 'node:fs'

import { expect, test } from '@playwright/test'

import { compararRecorridos, diferenciaConSupuesto, esViaSupuesta, formatDuracion, lineaRecta, velocidadesHabituales } from '../src/app/recorridos.ts'
import { formatKm } from '../src/app/state.ts'
import { composeNetwork } from '../src/data/network.ts'
import type { NetworkIndexOut, Route } from '../src/data/types.ts'
import { buildGraph } from '../src/routing/graph.ts'

// La vía supuesta del comparador: una vía que no existe entre dos estaciones, con los kilómetros y la
// velocidad que pone el visitante, para comparar lo que se tardaría con los recorridos de hoy. El
// ejemplo es el de la documentación (docs/simulacion.md, «Vía supuesta»): de Madrid a Granada con una
// vía entre Jaén y Granada. Lo que depende de qué otras líneas hay cargadas (cuántos recorridos hay
// hoy, cuánto miden) no se escribe: se compara con el mismo cálculo sin la vía.

const estatico = Boolean(process.env.ONIEL_E2E_STATIC)
const leer = <T>(ruta: string) => JSON.parse(readFileSync(new URL(ruta, import.meta.url), 'utf-8')) as T
const red = composeNetwork(leer<NetworkIndexOut>('../public/data/index.json'), {})
const grafo = buildGraph(red)
const sinCortes = new Map<string, never[]>()

const MADRID = 'madrid-puerta-de-atocha'
const VIA = 'e~jaen~granada~68~160'
const RUTA = `/recorridos/${MADRID}/granada`

test.describe('Vía supuesta: qué se calcula', () => {
  test('los recorridos de hoy no cambian y los que usarían la vía van aparte', () => {
    const hoy = compararRecorridos(grafo, red, MADRID, 'granada', sinCortes)
    const con = compararRecorridos(grafo, red, MADRID, 'granada', sinCortes, VIA)
    expect(hoy.supuestos).toEqual([])
    expect(con.recorridos.map((r) => r.key)).toEqual(hoy.recorridos.map((r) => r.key))
    expect(con.recorridos.every((r) => !r.route.segment_ids.some(esViaSupuesta))).toBe(true)
    expect(con.supuestos.length).toBeGreaterThan(0)
    expect(con.supuestos.length).toBeLessThanOrEqual(2)
    for (const r of con.supuestos) {
      // la vía es un trecho propio, con los kilómetros y la velocidad del supuesto: 68 km a 160 km/h son 26 minutos
      const via = r.route.legs.filter((leg) => leg.line_id === null)
      expect(via.map((leg) => [leg.from_name, leg.to_name, leg.length_km, leg.time_min])).toEqual([['Jaén', 'Granada', 68, 26]])
      // y no cuenta como una línea más
      expect(r.lineas).toMatch(/ y la vía supuesta$/)
    }
    // el escenario en palabras solo dice cierres y velocidades: la vía tiene su propio recuadro
    expect(con.escenario).toEqual([])
  })

  test('la diferencia compara el más rápido y el más corto con los de hoy', () => {
    const con = compararRecorridos(grafo, red, MADRID, 'granada', sinCortes, VIA)
    const frase = diferenciaConSupuesto(con.recorridos, con.supuestos)
    const rapido = Math.min(...con.supuestos.map((r) => r.route.time_min!))
    const rapidoHoy = Math.min(...con.recorridos.map((r) => r.route.time_min!))
    const corto = Math.min(...con.supuestos.map((r) => r.route.length_km))
    expect(frase).toContain(`El más rápido con esta vía tardaría ${formatDuracion(rapido)} sin paradas`)
    expect(frase).toContain(`el más rápido de hoy (${formatDuracion(rapidoHoy)}, por `)
    expect(frase).toContain(`El más corto mediría ${formatKm(corto)} km`)
    expect(diferenciaConSupuesto(con.recorridos, [])).toBeNull()
    // sin ningún recorrido hoy, se dice y se da lo que mediría con la vía
    expect(diferenciaConSupuesto([], con.supuestos)).toContain('Hoy no hay ningún recorrido entre estas dos estaciones')
  })

  test('una vía más rápida acorta el tiempo y no los kilómetros', () => {
    const lenta = compararRecorridos(grafo, red, MADRID, 'granada', sinCortes, VIA).supuestos[0]!
    const rapida = compararRecorridos(grafo, red, MADRID, 'granada', sinCortes, 'e~jaen~granada~68~300').supuestos[0]!
    expect(rapida.route.length_km).toBe(lenta.route.length_km)
    expect(rapida.route.time_min!).toBeLessThan(lenta.route.time_min!)
  })

  test('una vía que ningún recorrido usaría no da recorridos, y una que no encaja con la red se ignora', () => {
    // 2000 km entre Jaén y Granada: cualquier camino por ella es un rodeo de más del doble
    const larga = compararRecorridos(grafo, red, MADRID, 'granada', sinCortes, 'e~jaen~granada~2000~160')
    expect(larga.escenarioIlegible).toBe(false)
    expect(larga.supuestos).toEqual([])
    const rara = compararRecorridos(grafo, red, MADRID, 'granada', sinCortes, 'e~jaen~no-existe~68~160')
    expect(rara.escenarioIlegible).toBe(true)
    expect(rara.supuestos).toEqual([])
  })

  test('los valores de entrada salen de la red: la línea recta y la velocidad habitual', () => {
    const nodo = (id: string) => red.nodes.find((n) => n.id === id)!
    expect(lineaRecta(nodo('jaen'), nodo('granada'))).toBeCloseTo(68.2, 1)
    const { convencional, altaVelocidad } = velocidadesHabituales(red)
    // la mediana de las velocidades habituales de cada tipo de línea, redondeada a la decena
    expect(convencional % 10).toBe(0)
    expect(altaVelocidad % 10).toBe(0)
    expect(convencional).toBeGreaterThanOrEqual(100)
    expect(convencional).toBeLessThan(altaVelocidad)
  })
})

test.describe('Vía supuesta: en el visor', () => {
  test('se plantea desde el panel, queda en la dirección y se distingue de lo que existe', async ({ page }) => {
    await page.goto(RUTA)
    await expect(page.getByTestId('recorrido').first()).toBeVisible()
    const hoy = await page.getByTestId('recorrido').count()
    await expect(page.getByTestId('recorridos-hoy')).toHaveCount(0)
    await page.getByTestId('via-ir').click()
    const caja = page.getByTestId('via-caja')
    await caja.getByRole('combobox', { name: 'Vía supuesta, primera estación: buscar una estación' }).fill('jaen')
    await caja.getByRole('option', { name: /^Jaén/ }).click()
    await caja.getByRole('combobox', { name: 'Vía supuesta, segunda estación: buscar una estación' }).fill('granada')
    await caja.getByRole('option', { name: /^Granada/ }).click()

    // los valores de entrada: la línea recta entre las dos estaciones y la velocidad de las líneas convencionales
    const { convencional, altaVelocidad } = velocidadesHabituales(red)
    await expect(page).toHaveURL(new RegExp(`/recorridos/${MADRID}/granada/e~jaen~granada~68~${convencional}$`))
    await expect(caja.getByTestId('via-km')).toHaveValue('68')
    await expect(caja.getByTestId('via-kmh')).toHaveValue(String(convencional))
    await expect(caja.getByTestId('via-cifras-origen')).toContainText('68 km, la distancia en línea recta entre las dos estaciones')
    await expect(caja.getByTestId('via-kmh-alta-velocidad')).toHaveText(`${altaVelocidad} km/h, como la alta velocidad`)

    // lo de hoy sigue igual, bajo su rótulo; lo supuesto va dentro del recuadro y lo dice en cada recorrido
    await expect(page.getByTestId('recorridos-hoy')).toHaveText('Hoy')
    await expect(page.getByTestId('recorrido')).toHaveCount(hoy)
    const supuestos = caja.getByTestId('recorrido-supuesto')
    await expect(supuestos.first()).toContainText('Supuesto: esta vía no existe')
    await expect(supuestos.first().getByTestId('recorrido-via')).toContainText('68,0 km por la vía supuesta entre Jaén y Granada')
    await expect(page.getByTestId('recorrido-supuesto')).toHaveCount(await supuestos.count())
    await expect(supuestos.first().getByTestId('recorrido-trenes')).toHaveCount(0)
    await expect(caja.getByTestId('via-diferencia')).toContainText('El más rápido con esta vía tardaría')
    await expect(caja.getByTestId('via-aviso')).toContainText('Esta vía no existe y Oniel no la toma de ningún proyecto')
    await expect(caja.getByTestId('via-aviso')).toContainText('estimación sin paradas')
    await expect(page.getByTestId('via-entrada')).toContainText('una vía supuesta entre Jaén y Granada, que no existe')

    // el mapa la dibuja y, en escritorio, la leyenda dice qué es
    await expect(page.getByTestId('mapa')).toHaveAttribute('data-vias-supuestas', '1')
    if (await page.locator('.leyenda').isVisible()) await expect(page.getByTestId('leyenda-via-supuesta')).toBeVisible()
  })

  test('las cifras las pone quien mira, y quitar la vía deja la comparación como estaba', async ({ page }) => {
    await page.goto(`${RUTA}/${VIA}`)
    const caja = page.getByTestId('via-caja')
    const supuesto = caja.getByTestId('recorrido-supuesto').first()
    await expect(supuesto.getByTestId('recorrido-via')).toContainText('68,0 km por la vía supuesta entre Jaén y Granada, 26 min')

    await caja.getByTestId('via-km').fill('100')
    await expect(page).toHaveURL(/e~jaen~granada~100~160$/)
    await expect(supuesto.getByTestId('recorrido-via')).toContainText('100,0 km por la vía supuesta')
    // la propuesta de entrada sigue diciendo de dónde sale, aunque la cifra ya sea otra
    await expect(caja.getByTestId('via-cifras-origen')).toContainText('68 km, la distancia en línea recta')

    await caja.getByTestId('via-kmh-alta-velocidad').click()
    await expect(page).toHaveURL(/e~jaen~granada~100~300$/)
    await expect(supuesto.getByTestId('recorrido-via')).toContainText('100,0 km por la vía supuesta entre Jaén y Granada, 20 min')

    // un campo vacío o a medias no cambia nada, y al salir vuelve a enseñar el valor en vigor
    await caja.getByTestId('via-kmh').fill('')
    await expect(page).toHaveURL(/e~jaen~granada~100~300$/)
    await caja.getByTestId('via-km').focus()
    await expect(caja.getByTestId('via-kmh')).toHaveValue('300')

    // elegir el recorrido supuesto lo pone en azul en el mapa, como cualquier otro
    await supuesto.getByRole('button').first().click()
    await expect(supuesto).toHaveClass(/activo/)

    await caja.getByTestId('via-quitar').click()
    await expect(page).toHaveURL(new RegExp(`/recorridos/${MADRID}/granada$`))
    await expect(page.getByTestId('recorrido-supuesto')).toHaveCount(0)
    await expect(page.getByTestId('recorridos-hoy')).toHaveCount(0)
    await expect(page.getByTestId('mapa')).not.toHaveAttribute('data-vias-supuestas')
    await expect(caja.getByTestId('via-abrir')).toBeVisible()
  })

  test('una vía que no encaja con la red se dice y no se aplica', async ({ page }) => {
    await page.goto(`${RUTA}/e~jaen~no-existe~68~160`)
    await expect(page.getByText('El supuesto de la dirección no encaja con la red cargada y no se ha aplicado.')).toBeVisible()
    await expect(page.getByTestId('recorrido-supuesto')).toHaveCount(0)
    await expect(page.getByTestId('recorrido').first()).toBeVisible()
  })

  test('el servidor da el mismo recorrido por la vía supuesta', async ({ request }) => {
    test.skip(estatico, 'compara con la API')
    const respuesta = await request.get('/api/routes', { params: { from: MADRID, to: 'granada', scenario: VIA } })
    expect(respuesta.ok()).toBe(true)
    const { routes } = (await respuesta.json()) as { routes: Route[] }
    const porLaVia = routes.filter((r) => r.segment_ids.some(esViaSupuesta))
    const cliente = compararRecorridos(grafo, red, MADRID, 'granada', sinCortes, VIA).supuestos
    expect(porLaVia.slice(0, cliente.length).map((r) => [r.segment_ids, r.length_km, r.time_min])).toEqual(cliente.map((r) => [r.route.segment_ids, r.route.length_km, r.route.time_min]))
  })
})
