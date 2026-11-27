import { expect, test } from '@playwright/test'

import type { NodeServicesOut } from '../src/data/types.ts'

test('el detalle del regional conserva el producto de su edición, las terminales y los permisos @api', async ({ request }) => {
  test.skip(Boolean(process.env.ONIEL_E2E_STATIC), 'Necesita la API local.')
  for (const [date, product] of [
    ['2026-11-10', 'Media Distancia'],
    ['2026-11-13', 'Media Distancia'],
    ['2026-11-26', 'Regional'],
  ] as const) {
    const params = { date }
    const respuesta = await request.get('/api/nodes/madrid-principe-pio/services', { params })
    expect(respuesta.ok()).toBeTruthy()
    const estacion = await respuesta.json() as NodeServicesOut
    if (date === '2026-11-26') {
      const terminales = estacion.destinations?.filter((d) => ['30100', '30110'].includes(d.stop_id))
      expect(terminales).toHaveLength(2)
      expect(terminales).toEqual(expect.arrayContaining(['30100', '30110'].map((stop_id) =>
        expect.objectContaining({ stop_id, trains: 7, products: ['Regional'] }),
      )))
    }
    for (const numero of ['18901', '18904']) {
      const paradas = estacion.calls.filter((c) => c.train_number === numero)
      expect(paradas).toHaveLength(1)
      const url = `/api/services/${encodeURIComponent(paradas[0]!.service_id)}`
      const detalle = await request.get(url, { params })
      expect(detalle.ok()).toBeTruthy()
      const viaje = await detalle.json()
      expect(viaje).toMatchObject({ train_number: numero, product, id: paradas[0]!.service_id })
      if (numero === '18901') {
        expect(viaje.stops.slice(-2)).toMatchObject([
          { stop_id: '30100', arrival: '10:40', departure: '10:42', pickup_type: 1, drop_off_type: 0 },
          { stop_id: '30110', arrival: '10:45', pickup_type: 1, drop_off_type: 0 },
        ])
        if (date === '2026-11-26') {
          expect((await request.get(url, { params: { date: '2026-11-28' } })).status()).toBe(404)
        }
      } else {
        expect(viaje.stops[0]).toMatchObject({ stop_id: '30100', departure: '16:42', pickup_type: 0, drop_off_type: 1 })
        expect(viaje.stops.at(-1)).toMatchObject({ stop_id: '10000', pickup_type: 1, drop_off_type: 0 })
      }
    }
  }
})

test('la línea lleva al mapa, al esquema y a las fichas de ambas terminales', async ({ page }) => {
  await page.goto('/linea/avila-salamanca')
  await expect(page.getByRole('heading', { name: 'Línea convencional Ávila – Salamanca' })).toBeVisible()
  await expect(page.locator('.maplibregl-canvas')).toBeVisible()
  const esquema = page.getByTestId('esquema')
  for (const id of ['penaranda-de-bracamonte', 'salamanca', 'salamanca-la-alamedilla']) {
    await expect(esquema.getByTestId(`esquema-nodo-${id}`)).toBeAttached()
  }
  await page.getByRole('button', { name: 'estación de Ávila', exact: true }).click()
  await expect(page).toHaveURL(/\/nodo\/avila$/)
  for (const [id, numero] of [['salamanca', '18904'], ['salamanca-la-alamedilla', '18901']]) {
    await page.goto('/nodo/' + id)
    const ficha = page.getByTestId('detalle-nodo')
    await expect(ficha.locator('.lista-servicios li').filter({ hasText: `Regional ${numero}` })).toHaveCount(1)
    if (id === 'salamanca') {
      await expect(ficha.locator('.lista-servicios li').filter({ hasText: 'Regional 18901' })).toContainText('Solo bajada')
    } else {
      await expect(ficha.getByTestId('destinos-directos')).toContainText('Ningún tren con viajeros sale de aquí')
    }
  }
})

test('el comparador distingue la distancia, el horario comercial y el tiempo sin estimar', async ({ page }) => {
  for (const [salida, llegada, km, trenes] of [
    ['madrid-principe-pio', 'salamanca', '231,4', '7 trenes directos'],
    ['madrid-principe-pio', 'salamanca-la-alamedilla', '232,2', '7 trenes directos'],
    ['salamanca', 'madrid-principe-pio', '231,4', '7 trenes directos'],
    ['salamanca-la-alamedilla', 'madrid-principe-pio', '232,2', 'Ningún tren directo'],
  ]) {
    await page.goto(`/recorridos/${salida}/${llegada}`)
    const ruta = page.getByTestId('recorrido').first()
    await expect(ruta).toContainText(`${km} km · tiempo sin estimar`)
    await expect(ruta.getByTestId('recorrido-trenes')).toContainText(trenes)
    await expect(page.getByTestId('recorridos-trenes-fuera')).toHaveCount(0)
  }
})

test('los cierres del interior y del apeadero se consultan entre estaciones de viajeros', async ({ page }) => {
  for (const [origen, destino] of [['san-pedro-del-arroyo', 'crespos'], ['salamanca', 'salamanca-la-alamedilla']]) {
    await page.goto(`/tramo/avila-salamanca:${origen}:${destino}/cierre`)
    const cierre = page.getByTestId('cierre-estaciones')
    await expect(cierre.locator(`a[href="/nodo/${origen}"]`)).toBeVisible()
    await expect(cierre.locator(`a[href="/nodo/${destino}"]`)).toBeVisible()
    await cierre.getByRole('link', { name: 'Consultar los recorridos con el cierre' }).click()
    await expect(page.getByTestId('recorridos-escenario')).toBeVisible()
  }
})

test('la API conserva la identidad entre estaciones y los recuentos del 26 de noviembre @api', async ({ request }) => {
  test.skip(Boolean(process.env.ONIEL_E2E_STATIC), 'Necesita la API local.')
  const params = { date: '2026-11-26' }
  for (const [numero, estaciones] of [
    ['18901', ['madrid-principe-pio', 'avila', 'penaranda-de-bracamonte', 'salamanca', 'salamanca-la-alamedilla']],
    ['18904', ['salamanca', 'penaranda-de-bracamonte', 'avila', 'madrid-principe-pio']],
  ] as const) {
    const ids = new Set<string>()
    for (const estacion of estaciones) {
      const resp = await request.get(`/api/nodes/${estacion}/services`, { params })
      expect(resp.ok()).toBeTruthy()
      const ficha = await resp.json() as NodeServicesOut
      const llamadas = ficha.calls.filter((c) => c.train_number === numero)
      expect(llamadas).toHaveLength(1)
      ids.add(llamadas[0]!.service_id)
    }
    expect(ids.size).toBe(1)
  }
  for (const [origen, destino, total] of [
    ['san-pedro-del-arroyo', 'crespos', 14],
    ['salamanca', 'salamanca-la-alamedilla', 12],
  ] as const) {
    const servicio = await request.get(`/api/segments/avila-salamanca:${origen}:${destino}/services`, { params })
    expect(servicio.ok()).toBeTruthy()
    const ficha = await servicio.json()
    expect(ficha.segment.station_closure).toMatchObject({ from_id: origen, to_id: destino })
    expect(ficha.counts.publicado + ficha.counts.estimado).toBe(total)
    expect(ficha.passes).toEqual([])
  }
  for (const [estacion, km] of [['salamanca', 231.4], ['salamanca-la-alamedilla', 232.2]] as const) {
    for (const [from, to] of [['madrid-principe-pio', estacion], [estacion, 'madrid-principe-pio']]) {
      const resp = await request.get('/api/routes', { params: { from, to } })
      expect(resp.ok()).toBeTruthy()
      const ruta = (await resp.json()).routes[0]
      expect(ruta).toMatchObject({ length_km: km, time_min: null })
      expect(ruta.node_ids).toEqual(expect.arrayContaining(['pinar-de-las-rozas', 'avila', 'penaranda-de-bracamonte']))
    }
  }
})
