import { readFileSync } from 'node:fs'

import { expect, test } from '@playwright/test'

import { composeNetwork } from '../src/data/network.ts'
import type { NetworkIndexOut, NodeServicesOut, Route, SegmentServicesOut } from '../src/data/types.ts'
import { buildGraph, findRoutes } from '../src/routing/graph.ts'
import { scenarioFromCode } from '../src/routing/scenario.ts'

const enlace = 'enlace-conxo:bif-conxo:bif-rio-sar'
const brazos = ['lav-ourense-santiago:bif-conxo:santiago', 'eje-atlantico:santiago:bif-rio-sar']
const diciembre = '2026-12-11'
const estatico = Boolean(process.env.ONIEL_E2E_STATIC)
const sentidos = [
  { origen: 'ourense', destino: 'vigo-urzaiz', numero: '04515', salida: '13:42', llegada: '15:16', otros: ['04475', '04565', '04975', '00622', '37722'] },
  { origen: 'vigo-urzaiz', destino: 'ourense', numero: '04384', salida: '17:25', llegada: '18:52', otros: ['04464', '04494', '04254', '00621', '37621'] },
]
const horariosPorSantiago: Record<string, string> = {
  '04475': '10:54 → 12:34', '04565': '18:03 → 19:44', '04975': '20:45 → 22:29',
  '00622': '21:01 → 22:57', '37722': '21:01 → 22:57',
  '04464': '05:50 → 07:25', '04494': '09:44 → 11:24', '04254': '13:37 → 15:10',
  '00621': '07:32 → 09:18', '37621': '07:32 → 09:18',
}

for (const { origen, destino, numero, salida, llegada, otros } of sentidos) {
  test(`De ${origen} a ${destino} se ven los seis trenes de diciembre y el itinerario pendiente`, async ({ page }) => {
    await page.goto(`/recorridos/${origen}/${destino}`)
    const tarjetas = page.getByTestId('recorrido')
    await expect(tarjetas).toHaveCount(2)
    await expect(page.getByTestId('recorridos-resumen')).toContainText('6 trenes directos')
    const pendiente = page.getByTestId('itinerario-pendiente')
    await expect(pendiente).toHaveText(`AVE ${numero} · ${salida} → ${llegada} · itinerario pendiente de confirmar`)
    await expect(tarjetas.first()).toContainText('Por el enlace de Conxo')
    await expect(tarjetas.first()).toContainText('178,4 km')
    await expect(tarjetas.first()).toContainText('Ningún tren con paso acreditado')
    await expect(tarjetas.nth(1)).toContainText('181,6 km')
    await expect(tarjetas.nth(1).getByTestId('recorrido-inversion')).toContainText('Santiago')
    await expect(tarjetas.nth(1)).toContainText('5 trenes directos')
    for (const n of otros) await expect(tarjetas.nth(1)).toContainText(`${n} · ${horariosPorSantiago[n]}`)
    await expect(tarjetas.nth(1)).not.toContainText(numero)
    await page.goto(`/nodo/${origen}`)
    await expect(page.getByTestId('detalle-nodo').locator('li').filter({ hasText: numero }).filter({ hasText: 'itinerario pendiente de confirmar' })).toHaveCount(1)
  })
}

test('La ficha de la 842 enlaza ambas agujas y distingue un paso sin acreditar', async ({ page }) => {
  await page.goto(`/tramo/${enlace}`)
  const ficha = page.getByTestId('detalle-tramo')
  await expect(ficha.getByTestId('tramo-sin-trenes')).toContainText('Ningún tren tiene un paso acreditado')
  await expect(ficha.getByTestId('lista-servicios').locator('li')).toHaveCount(0)
  await page.goto('/linea/enlace-conxo')
  const esquema = page.getByTestId('esquema')
  for (const [nombre, id] of [['Bif. de Conxo', 'bif-conxo'], ['Bif. Río Sar', 'bif-rio-sar']]) {
    await esquema.getByRole('button', { name: new RegExp(nombre!) }).click()
    await expect(page).toHaveURL(new RegExp('/nodo/' + id + '$'))
    await expect(page.getByTestId('nodo-lineas')).toContainText('Enlace de Conxo')
    await page.goto('/linea/enlace-conxo')
  }
})

test('La API y el visor estático coinciden en ambos sentidos y en cada cierre de Conxo @api', async ({ request }) => {
  test.skip(estatico, 'Necesita la API local.')
  const indice = JSON.parse(readFileSync('public/data/index.json', 'utf8')) as NetworkIndexOut
  const grafo = buildGraph(composeNetwork(indice, {}))
  for (const { origen, destino } of sentidos) {
    for (const tramo of ['', enlace, ...brazos]) {
      const scenario = tramo ? `c~${tramo}` : ''
      const respuesta = await request.get('/api/routes', { params: { from: origen, to: destino, date: diciembre, scenario } })
      expect(respuesta.ok()).toBeTruthy()
      const cuerpo = await respuesta.json() as { routes: (Route & { interruptions: unknown })[]; max_ratio: number }
      expect(cuerpo.max_ratio).toBe(2)
      const local = findRoutes(grafo, origen, destino, scenarioFromCode(scenario))
      expect(cuerpo.routes.map(({ interruptions: _avisos, ...r }) => r)).toEqual(local)
      expect(local.map((r) => r.length_km)).toEqual(!tramo ? [178.4, 181.6] : tramo === enlace ? [181.6] : [178.4])
      for (const r of local) {
        const directo = r.segment_ids.includes(enlace)
        expect(r.reverse_node_ids).toEqual(directo ? [] : ['santiago'])
        for (const brazo of brazos) expect(r.segment_ids.includes(brazo)).toBe(!directo)
      }
    }
  }
})

test('Solo el día observado acredita el paso aunque el 04384 conserve su identidad @api', async ({ request }) => {
  test.skip(estatico, 'Contrasta dos días de la API con las fichas de la instantánea de diciembre.')
  for (const date of ['2026-11-17', diciembre]) {
    const confirmado = date !== diciembre
    const fichas = await Promise.all([enlace, ...brazos].map(async (id) => {
      const respuesta = await request.get(`/api/segments/${id}/services`, { params: { date } })
      expect(respuesta.ok()).toBeTruthy()
      const ficha = await respuesta.json() as SegmentServicesOut
      if (!confirmado) expect(ficha.passes).toEqual((JSON.parse(readFileSync(`public/data/segments/${id.replaceAll(':', '--')}.json`, 'utf8')) as SegmentServicesOut).passes)
      return new Set(ficha.passes.map((p) => p.service.id))
    }))
    expect(fichas[0]!.size).toBe(confirmado ? 2 : 0)
    for (const { origen, destino, numero, salida, llegada, otros } of sentidos) {
      const llamadas = await Promise.all([origen, destino].map(async (id) => {
        const respuesta = await request.get(`/api/nodes/${id}/services`, { params: { date } })
        expect(respuesta.ok()).toBeTruthy()
        const ficha = await respuesta.json() as NodeServicesOut
        if (!confirmado) expect(ficha.calls).toEqual((JSON.parse(readFileSync(`public/data/nodes/${id}.json`, 'utf8')) as NodeServicesOut).calls)
        return ficha.calls
      }))
      const destinos = new Map(llamadas[1]!.filter((c) => c.alights).map((c) => [c.service_id, c.arrival]))
      const directos = llamadas[0]!.filter((c) => c.boards && c.departure && c.departure < (destinos.get(c.service_id) ?? ''))
      expect(directos.map((c) => c.train_number).sort()).toEqual([numero, ...otros].sort())
      for (const c of directos) {
        const candidato = c.train_number === numero
        expect(fichas[0]!.has(c.service_id)).toBe(candidato && confirmado)
        for (const brazo of fichas.slice(1)) expect(brazo.has(c.service_id)).toBe(!candidato)
        if (!candidato) {
          if (!confirmado) expect(`${c.departure} → ${destinos.get(c.service_id)}`).toBe(horariosPorSantiago[c.train_number])
          continue
        }
        const id = numero === '04384' ? '0438412026-11-16' : confirmado ? '0451512026-11-16' : '0451512026-12-09'
        expect([c.service_id, c.departure, destinos.get(id)]).toEqual([id, salida, llegada])
        expect(c.itinerary).toEqual({ line_id: 'enlace-conxo', source_id: confirmado ? `renfe-conxo-${numero}` : null })
        const detalle = await request.get(`/api/services/${id}`, { params: { date } })
        expect((await detalle.json()).itinerary).toEqual(c.itinerary)
      }
    }
  }
})
