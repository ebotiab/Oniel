import { expect, test, type Page, type Route } from '@playwright/test'

import { cobertura, indice } from './instantanea.ts'

const linea = 'manzanares-ciudad-real'
const tramo = linea + ':daimiel:almagro'

// Entra por la red y espera a que el visor haya recibido el índice y la cobertura de la API.
async function arrancar(page: Page, fecha = cobertura.reference_date) {
  await page.route('**/api/**', (route) => route.fulfill({ status: 503 }))
  await page.route('**/healthz', (route) => route.fulfill({ json: { status: 'ok' } }))
  await page.route('**/api/lines', (route) => route.fulfill({ json: indice }))
  await page.route('**/api/coverage', (route) => route.fulfill({ json: { ...cobertura, reference_date: fecha } }))
  await Promise.all([page.waitForResponse('**/api/lines'), page.waitForResponse('**/api/coverage'), page.goto('/')])
  await expect(page.getByTestId('vista-red')).toBeVisible()
}

// Los enlaces con almohadilla se abren en el visor que ya conectó con la API.
async function abrir(page: Page, ruta: string) {
  await page.goto(new URL('#' + ruta, page.url()).href)
  await expect(page).toHaveURL((url) => url.pathname === ruta && !url.hash)
}

test.describe('Consultas tras la caída de la API', { tag: '@api' }, () => {
  test.skip(Boolean(process.env.ONIEL_E2E_STATIC), 'la API tiene que responder durante el arranque')

  test('recupera la línea y la estación tras un error y el tramo tras una desconexión', async ({ page }) => {
    await arrancar(page)
    await abrir(page, '/linea/' + linea)
    await expect(page.getByTestId('esquema')).toBeVisible()
    await abrir(page, '/nodo/daimiel')
    await expect(page.getByTestId('detalle-nodo')).toContainText('Estación con trenes regionales')
    await expect(page.locator('.lista-servicios li').first()).toBeVisible()
    await page.route('**/api/segments/*/services*', (route) => route.abort('connectionreset'))
    await abrir(page, '/tramo/' + tramo)
    await expect(page.getByTestId('lista-servicios').locator('li').first()).toBeVisible()
    await abrir(page, '/recorridos/daimiel/almagro')
    await expect(page.getByTestId('recorridos-resumen')).toContainText(/Hay \d+ trenes? directos?/)
  })

  test('acota una petición pendiente y vuelve a consultar la API al volver a la estación', async ({ page }) => {
    await arrancar(page)
    let intentos = 0
    let recuperada = false
    await page.route('**/api/nodes/daimiel/services*', (route) => {
      intentos++
      if (recuperada) return route.fulfill({ json: { date: cobertura.reference_date, calls: [], destinations: [] } })
      // Se deja la petición abierta como haría un servidor que ha dejado de responder.
    })
    await abrir(page, '/nodo/daimiel')
    await expect(page.locator('.lista-servicios li').first()).toBeVisible({ timeout: 12_000 })
    expect(intentos).toBe(1)
    recuperada = true
    await abrir(page, '/nodo/almagro')
    await abrir(page, '/nodo/daimiel')
    await expect(page.getByRole('heading', { name: /Trenes que paran aquí · 0 el/ })).toBeVisible()
    expect(intentos).toBe(2)
  })

  test('rechaza horarios de otro día y conserva la ficha y los recorridos', async ({ page }) => {
    await arrancar(page, '2099-01-01')
    // También la API puede contestar con el día equivocado. Ninguno de los dos horarios vale.
    await page.route('**/api/nodes/daimiel/services*', (route) => route.fulfill({ path: 'public/data/nodes/daimiel.json' }))
    await abrir(page, '/nodo/daimiel')
    await expect(page.getByText('Horarios no disponibles para esta consulta.')).toBeVisible()
    await expect(page.locator('.lista-servicios')).toHaveCount(0)
    await abrir(page, '/linea/' + linea)
    await expect(page.getByTestId('esquema')).toBeVisible()
    await expect(page.getByText('Horarios no disponibles para esta consulta.')).toBeVisible()
    await expect(page.locator('.esquema-conteo')).toHaveCount(0)
    await abrir(page, '/tramo/' + tramo)
    await expect(page.getByText('Horarios no disponibles para esta consulta.')).toBeVisible()
    await expect(page.getByTestId('tramo-sin-trenes')).toHaveCount(0)
    await abrir(page, '/recorridos/daimiel/almagro')
    await expect(page.getByText('Horarios no disponibles para esta consulta.')).toBeVisible()
    await expect(page.getByTestId('recorrido').first()).toBeVisible()
    await expect(page.getByTestId('recorrido-trenes')).toHaveCount(0)
  })

  test('si faltan ambas copias, mantiene el esquema y recupera el detalle al volver', async ({ page }) => {
    await arrancar(page)
    await page.route('**/data/lines/' + linea + '.json', (route) => route.abort())
    await page.route('**/data/nodes/daimiel.json', (route) => route.abort())
    await abrir(page, '/linea/' + linea)
    await expect(page.getByText('Detalle de la línea no disponible.')).toBeVisible()
    await expect(page.getByTestId('esquema-nodo-daimiel')).toBeVisible()
    await abrir(page, '/nodo/daimiel')
    await expect(page.getByText('Horarios no disponibles para esta consulta.')).toBeVisible()
    await expect(page.getByTestId('detalle-nodo')).toContainText('Tramos que salen de aquí')
    await abrir(page, '/')
    await page.route('**/api/lines/' + linea + '*', (route) => route.fulfill({ path: 'public/data/lines/' + linea + '.json' }))
    await abrir(page, '/nodo/daimiel')
    await expect(page.getByTestId('detalle-nodo')).toContainText('Estación con trenes regionales')
  })

  test('conserva los trenes visibles si al actualizar la ficha fallan ambos orígenes', async ({ page }) => {
    let despierta = false
    await page.route('**/healthz', (route) => despierta ? route.fulfill({ json: { status: 'ok' } }) : route.abort())
    await page.route('**/api/**', (route) => route.fulfill({ status: 503 }))
    await page.goto('/nodo/daimiel')
    const horarios = page.locator('.lista-servicios li')
    await expect(horarios.first()).toBeVisible()
    const total = await horarios.count()
    await page.route('**/data/nodes/daimiel.json', (route) => route.fulfill({ status: 404 }))
    const respaldo = page.waitForResponse((res) => res.url().endsWith('/data/nodes/daimiel.json') && res.status() === 404)
    despierta = true
    await respaldo
    await expect(horarios).toHaveCount(total)
    await expect(page.getByText('Horarios no disponibles para esta consulta.')).toHaveCount(0)
  })

  test('una respuesta tardía no cambia los horarios de la nueva selección', async ({ page }) => {
    await arrancar(page)
    let retener!: (route: Route) => void
    const retenida = new Promise<Route>((resolve) => { retener = resolve })
    await page.route('**/api/nodes/daimiel/services*', retener)
    await abrir(page, '/recorridos/daimiel/almagro')
    const primera = await retenida
    await abrir(page, '/recorridos/madrid-puerta-de-atocha/cordoba')
    const resumen = page.getByTestId('recorridos-resumen')
    await expect(resumen).toContainText(/Hay \d+ trenes directos/)
    const actual = await resumen.textContent()
    const respuesta = page.waitForResponse(primera.request().url())
    await primera.fulfill({ json: { date: cobertura.reference_date, calls: [], destinations: [] } })
    await respuesta
    await expect(resumen).toHaveText(actual!)
  })
})

test('sin día de referencia, el comparador solo reúne horarios del mismo día', async ({ page }) => {
  await page.route('**/healthz', (route) => route.abort())
  await page.route('**/data/coverage.json', (route) => route.fulfill({ json: { ...cobertura, reference_date: null } }))
  await page.route('**/data/nodes/daimiel.json', (route) => route.fulfill({ json: { date: '2099-01-01', calls: [] } }))
  await page.goto('/recorridos/daimiel/almagro')
  await expect(page.getByText('Horarios no disponibles para esta consulta.')).toBeVisible()
  await expect(page.getByTestId('recorrido-trenes')).toHaveCount(0)
})
