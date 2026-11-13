import { expect, test, type Page } from '@playwright/test'

// La red se carga por partes: al arrancar solo el índice; el detalle de cada línea, al abrirla o al
// acercar el mapa. Vale igual con la instantánea estática (/data/…) que con la API (/api/lines…).

const LAV = 'lav-madrid-sevilla'
const CONV = 'convencional-madrid-alcazar-cordoba'
const MZCR = 'manzanares-ciudad-real'

/** Anota qué partes de la red pide la página: el índice, cada línea y la red entera (que ya no debe pedirse). */
function partesPedidas(page: Page) {
  const pedidas = { indice: 0, lineas: [] as string[], redEntera: 0 }
  page.on('request', (req) => {
    const ruta = new URL(req.url()).pathname
    if (/\/(data\/index\.json|api\/lines)$/.test(ruta)) pedidas.indice++
    if (/\/(data\/network\.json|api\/network|data\/segment-counts\.json)$/.test(ruta)) pedidas.redEntera++
    const linea = /\/(?:data\/lines\/([^/]+)\.json|api\/lines\/([^/]+))$/.exec(ruta)
    if (linea) pedidas.lineas.push(decodeURIComponent(linea[1] ?? linea[2]!))
  })
  return pedidas
}

async function abrirHoja(page: Page) {
  const asa = page.getByRole('button', { name: 'Ampliar el panel' })
  if (await asa.isVisible()) await asa.click()
}

test.describe('Carga de la red por partes', () => {
  test('el arranque descarga solo el índice, que es ligero', async ({ page, request }) => {
    const pedidas = partesPedidas(page)
    await page.goto('/')
    await expect(page.getByTestId('vista-red')).toBeVisible()
    await expect(page.getByTestId('recuento-red')).toHaveText(/^9 líneas · 1\.885 km/)
    await expect(page.locator('.maplibregl-canvas')).toBeVisible()
    await page.waitForTimeout(1_500) // margen para una petición que no debe llegar
    expect(pedidas.indice).toBeGreaterThan(0)
    expect(pedidas.lineas).toEqual([])
    expect(pedidas.redEntera).toBe(0)
    // El índice lleva toda la red con la geometría simplificada: pesa mucho menos que una sola línea grande.
    const indice = await (await request.get('/data/index.json')).body()
    const linea = await (await request.get(`/data/lines/${CONV}.json`)).body()
    // Las anotaciones de red (interrupciones, proyectos) van enteras en el índice y no dependen de la
    // geometría: la red mantiene su tope y ellas tienen el suyo. Cuando no quepan, su detalle se pedirá aparte.
    const { annotations, interruptions, ...red } = JSON.parse(indice.toString('utf-8')) as Record<string, unknown>
    const bytes = (parte: unknown) => Buffer.byteLength(JSON.stringify(parte))
    // El tope de la red crece con ella: 20 KB sin comprimir por línea cargada (hoy son 18 KB de media).
    expect(bytes(red)).toBeLessThan(20_000 * (red.lines as unknown[]).length)
    expect(bytes({ annotations, interruptions })).toBeLessThan(40_000)
    // La red del índice sigue pesando menos que el detalle de la línea más grande. El índice entero,
    // con las anotaciones, ya no: con ocho líneas son 150 KB (26 KB comprimido) frente a 148 KB.
    expect(bytes(red)).toBeLessThan(linea.byteLength)
  })

  test('el detalle de una línea se pide al abrirla, y una sola vez', async ({ page }) => {
    const pedidas = partesPedidas(page)
    await page.goto('/')
    await abrirHoja(page)
    const red = page.getByTestId('vista-red')
    await red.getByRole('button', { name: /Madrid – Sevilla/ }).click()
    await expect(page.getByTestId('esquema')).toBeVisible()
    await expect(page.getByTestId('esquema-rotulo-trenes').or(page.getByTestId('esquema-tramo-1')).first()).toBeVisible()
    await expect.poll(() => new Set(pedidas.lineas)).toEqual(new Set([LAV]))

    // una segunda línea pide su detalle; volver a la primera no la pide otra vez
    await page.getByTestId('volver-red').click()
    await red.getByRole('button', { name: /Manzanares – Ciudad Real/ }).click()
    await expect(page.getByRole('heading', { name: /Manzanares – Ciudad Real/ })).toBeVisible()
    // (al encuadrarla, el mapa queda cerca y puede pedir también las vecinas)
    await expect.poll(() => pedidas.lineas).toContain(MZCR)
    const antes = pedidas.lineas.filter((l) => l === LAV).length
    await page.getByTestId('volver-red').click()
    await red.getByRole('button', { name: /Madrid – Sevilla/ }).click()
    await expect(page.getByTestId('esquema')).toBeVisible()
    await page.waitForTimeout(1_500) // margen para una petición que no debe llegar
    expect(pedidas.lineas.filter((l) => l === LAV).length).toBe(antes)
  })

  test('un enlace directo a un tramo de una línea sin cargar muestra el tramo y pide su línea', async ({ page }) => {
    const pedidas = partesPedidas(page)
    await page.goto(`/tramo/${MZCR}:daimiel:almagro`)
    await abrirHoja(page)
    await expect(page.getByTestId('detalle-tramo')).toBeVisible()
    await expect(page.getByRole('heading', { name: /Daimiel/ })).toBeVisible()
    await expect(page.getByTestId('tramo-vias')).toHaveText('Vía única')
    await expect(page.getByTestId('lista-servicios').locator('li').first()).toBeVisible()
    await expect.poll(() => pedidas.lineas).toContain(MZCR)
    expect(pedidas.redEntera).toBe(0)
    // «Toda la línea» lleva a su esquema, ya con el detalle cargado
    await page.getByRole('button', { name: /Toda la línea/ }).click()
    await expect(page.getByTestId('esquema')).toBeVisible()
    await expect(page).toHaveURL(new RegExp(`/linea/${MZCR}$`))
  })

  test('un enlace directo a una estación muestra su descripción, que llega con la línea', async ({ page }) => {
    const pedidas = partesPedidas(page)
    await page.goto('/nodo/puertollano')
    await abrirHoja(page)
    await expect(page.getByTestId('detalle-nodo')).toBeVisible()
    await expect(page.getByRole('heading', { name: 'Puertollano' })).toBeVisible()
    await expect.poll(() => pedidas.lineas).toContain(LAV)
    await expect(page.getByTestId('detalle-nodo')).toContainText(/alta velocidad/i)
  })

  test('al acercar el mapa a una línea se pide su geometría completa', async ({ page }) => {
    const pedidas = partesPedidas(page)
    await page.goto('/')
    await expect(page.locator('.maplibregl-canvas')).toBeVisible()
    await page.waitForTimeout(1_500) // margen para una petición que no debe llegar
    expect(pedidas.lineas).toEqual([])
    // Sin abrir ninguna línea: basta con acercar el mapa a Daimiel, en la línea Manzanares – Ciudad Real.
    await page.evaluate(() => {
      const mapa = (globalThis as unknown as { __onielMap: { jumpTo: (o: { center: [number, number]; zoom: number }) => void } }).__onielMap
      mapa.jumpTo({ center: [-3.615, 39.07], zoom: 11 })
    })
    await expect(page.getByTestId('vista-red')).toBeVisible()
    await expect.poll(() => pedidas.lineas).toContain(MZCR)
  })
})
