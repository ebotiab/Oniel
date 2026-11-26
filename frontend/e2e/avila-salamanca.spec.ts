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
