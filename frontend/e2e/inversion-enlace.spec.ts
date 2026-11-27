import { execFileSync } from 'node:child_process'
import { fileURLToPath } from 'node:url'

import { expect, test } from '@playwright/test'

import { compararRecorridos } from '../src/app/recorridos.ts'
import type { Route } from '../src/data/types.ts'
import { buildGraph, findRoutes } from '../src/routing/graph.ts'
import { scenarioFromCode } from '../src/routing/scenario.ts'

interface Ensayo {
  variante: string
  red: Parameters<typeof buildGraph>[0]
  casos: { desde: string; hasta: string; escenario: string; rutas: Route[] }[]
}

test('el comparador y la API coinciden en el enlace, la inversión y los giros de las agujas', () => {
  const backend = fileURLToPath(new URL('../../backend/', import.meta.url))
  const ensayos = JSON.parse(execFileSync('uv', ['run', '--locked', 'python', 'tests/test_ensayo_inversion.py'], { cwd: backend, encoding: 'utf8' })) as Ensayo[]
  for (const { variante, red, casos } of ensayos) {
    const grafo = buildGraph(red)
    for (const { desde, hasta, escenario, rutas } of casos) {
      const caso = `${variante} · ${desde} → ${hasta} · ${escenario || 'abierto'}`
      expect(findRoutes(grafo, desde, hasta, scenarioFromCode(escenario)), caso).toEqual(rutas)
      const vista = compararRecorridos(grafo, red, desde, hasta, new Map(), escenario)
      const libres = escenario.startsWith('e~') ? vista.supuestos : vista.recorridos.filter((r) => !r.cortes.length)
      expect(libres.map((r) => r.route), caso).toEqual(rutas)
      expect(libres.map((r) => r.inversion), caso).toEqual(rutas.map((r) => r.reverse_node_ids.length ? 'Invierte la marcha en Parada.' : null))
    }
  }
})
