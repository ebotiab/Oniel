import { expect, test } from '@playwright/test'

import { abrirLinea } from './navegar.ts'

const LINEA = 'vitoria-irun'
const NOMBRE = 'Línea convencional Vitoria – Altsasu – San Sebastián – Irún'

test.describe('Vitoria – Altsasu – San Sebastián – Irún', () => {
  test('se abre desde la red y muestra sus estaciones en mapa y esquema', async ({ page }) => {
    await page.goto('/')
    await abrirLinea(page, LINEA)
    await expect(page.getByRole('heading', { name: NOMBRE })).toBeVisible()
    await expect(page.locator('.maplibregl-canvas')).toBeVisible()
    const esquema = page.getByTestId('esquema')
    for (const nombre of ['Vitoria-Gasteiz', 'Altsasu', 'Zumarraga', 'Tolosa', 'San Sebastián-Donostia', 'Irun']) {
      await expect(esquema).toContainText(nombre)
    }
    const lupa = page.getByTestId('buscador-abrir')
    if (await lupa.isVisible()) await lupa.click()
    const campo = page.getByRole('combobox', { name: 'Buscar una estación o una línea' })
    await campo.fill('vitoria')
    await expect(page.getByRole('option').filter({ hasText: 'Vitoria-Gasteiz' })).toHaveCount(1)
  })

  for (const [busqueda, id, nombre] of [
    ['san sebastian', 'san-sebastian-donostia', 'San Sebastián-Donostia'],
    ['irun', 'irun', 'Irun'],
  ]) {
    test(`el buscador abre ${nombre} con sus servicios`, async ({ page }) => {
      await page.goto('/')
      await expect(page.getByTestId('vista-red')).toBeVisible()
      const lupa = page.getByTestId('buscador-abrir')
      if (await lupa.isVisible()) await lupa.click()
      const campo = page.getByRole('combobox', { name: 'Buscar una estación o una línea' })
      await campo.fill(busqueda!)
      await page.getByRole('option').filter({ hasText: nombre! }).first().click()
      await expect(page).toHaveURL(new RegExp(`/nodo/${id}$`))
      const ficha = page.getByTestId('detalle-nodo')
      await expect(ficha.getByRole('heading', { name: nombre, exact: true })).toBeVisible()
      await expect(ficha).toContainText('Madrid-Chamartín')
    })
  }

  for (const destino of ['san-sebastian-donostia', 'irun']) {
    test(`el comparador llega a ${destino} en ambos sentidos`, async ({ page }) => {
      for (const [desde, hasta] of [['madrid-chamartin', destino], [destino, 'madrid-chamartin']]) {
        await page.goto(`/recorridos/${desde}/${hasta}`)
        const ruta = page.getByTestId('recorrido').first()
        await expect(ruta).toBeVisible()
        await expect(ruta).toContainText(destino === 'irun' ? '565,9 km' : '549,0 km')
        await expect(ruta).toContainText('Recorre cinco líneas')
        await expect(ruta).toContainText(destino === 'irun' ? '3 h 13 min' : '3 h 6 min')
        await expect(ruta.getByTestId('recorrido-trenes')).toContainText(/\d+ trenes directos/)
      }
    })
  }

  test('las salidas pendientes y los atributos conservan su significado', async ({ page }) => {
    await page.goto('/nodo/irun')
    await expect(page.getByTestId('detalle-nodo')).toContainText('Hendaya')
    await page.goto('/nodo/bif-altsasu')
    await expect(page.getByTestId('detalle-nodo')).toContainText('Pamplona')
    await page.goto('/nodo/pamplona')
    await expect(page.getByTestId('detalle-nodo')).toContainText('Vitoria por la bifurcación de Altsasu')
    await page.goto('/tramo/vitoria-irun:san-sebastian-donostia:pasaia')
    await expect(page.getByTestId('detalle-tramo')).toBeVisible()
    const asa = page.getByRole('button', { name: 'Ampliar el panel' })
    if (await asa.isVisible()) await asa.click()
    await expect(page.getByTestId('tramo-vias')).toHaveText('Vía doble')
    await expect(page.getByTestId('tramo-atributo-proteccion_tren')).toHaveText('ASFA')
    await page.getByTestId('mas-detalle').locator('summary').click()
    await expect(page.getByTestId('mas-detalle')).toContainText('3 kV CC')
  })
})

test('la API conserva recorridos y servicios de San Sebastián e Irún', { tag: '@api' }, async ({ request }) => {
  test.skip(Boolean(process.env.ONIEL_E2E_STATIC), 'Necesita la API local')
  for (const destino of ['san-sebastian-donostia', 'irun']) {
    const estatico = await (await request.get(`/data/nodes/${destino}.json`)).json() as { date: string; calls: unknown[] }
    const respuesta = await request.get(`/api/nodes/${destino}/services`, { params: { date: estatico.date } })
    expect(respuesta.ok()).toBe(true)
    const servicios = await respuesta.json() as { calls: unknown[] }
    expect(servicios.calls).toEqual(estatico.calls)
    expect(servicios.calls.length).toBeGreaterThan(0)
    for (const [from, to] of [['madrid-chamartin', destino], [destino, 'madrid-chamartin']]) {
      const respuestaRuta = await request.get('/api/routes', { params: { from: from!, to: to! } })
      expect(respuestaRuta.ok()).toBe(true)
      const cuerpo = await respuestaRuta.json() as { routes: { length_km: number; node_ids: string[]; time_min: number | null }[] }
      const ruta = cuerpo.routes[0]!
      expect(ruta.length_km).toBeCloseTo(destino === 'irun' ? 565.9 : 549.0, 1)
      expect(ruta.time_min).toBe(destino === 'irun' ? 193 : 186)
      expect(ruta.node_ids).toContain('vitoria-gasteiz')
      expect(ruta.node_ids).not.toContain('pamplona')
      expect(new Set(ruta.node_ids).size).toBe(ruta.node_ids.length)
    }
  }
})
