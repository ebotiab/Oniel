import { readFileSync } from 'node:fs'

import { expect, test } from '@playwright/test'

import { ANNOTATION_LAYERS, CAPAS_CON_TRAZO, annotationLayer, capasDe, trazoDe } from '../src/app/annotationLayers.ts'
import { activeAnnotations, activeInterruptions, bySegment, isActive } from '../src/app/annotations.ts'
import { composeNetwork } from '../src/data/network.ts'
import type { AnnotationOut, NetworkIndexOut } from '../src/data/types.ts'

// Las anotaciones de red sin navegador: qué trae la instantánea, cómo se leen las de una API
// anterior y qué dice el registro de capas. Lo que se ve está en interrupciones.spec.ts.

const leer = <T>(ruta: string) => JSON.parse(readFileSync(new URL(ruta, import.meta.url), 'utf-8')) as T
const indice = leer<NetworkIndexOut>('../public/data/index.json')
const red = composeNetwork(indice, {})
const HOY = '2026-11-10'

test.describe('Anotaciones de red: datos y registro de capas', () => {
  test('la instantánea trae las anotaciones, y las interrupciones como alias de las de su tipo', () => {
    expect(indice.annotations!.length).toBeGreaterThanOrEqual(2)
    expect(indice.interruptions).toEqual(indice.annotations!.filter((a) => a.kind === 'interrupcion'))
    for (const a of indice.annotations!) {
      expect(a.status, a.id).toBeTruthy()
      expect(a.sources.length, a.id).toBeGreaterThan(0)
      expect(a.checked_on, a.id).toMatch(/^\d{4}-\d{2}-\d{2}$/)
    }
  })

  test('cada tipo que trae la instantánea tiene su capa en el registro', () => {
    for (const a of red.annotations) expect(annotationLayer(a.kind), a.kind).toBeDefined()
    // sin tipos repetidos ni propiedades de trazo repetidas: cada capa marca sus tramos con la suya
    expect(new Set(ANNOTATION_LAYERS.map((l) => l.kind)).size).toBe(ANNOTATION_LAYERS.length)
    expect(new Set(CAPAS_CON_TRAZO.map((c) => c.propiedad)).size).toBe(CAPAS_CON_TRAZO.length)
  })

  test('un índice de una API anterior, que solo trae interruptions, se lee igual', () => {
    const anterior: NetworkIndexOut = { ...indice, annotations: undefined }
    const leida = composeNetwork(anterior, {})
    expect(leida.annotations).toEqual(red.annotations.filter((a) => a.kind === 'interrupcion'))
    expect(activeInterruptions(leida, HOY)).toEqual(activeInterruptions(red, HOY))
  })

  test('una anotación sin fecha de inicio está vigente hasta que termina', () => {
    const base = red.annotations[0]!
    const sinInicio: AnnotationOut = { ...base, start_date: null, ended_on: '2026-03-08' }
    expect(isActive(sinInicio, '2020-01-01')).toBe(true)
    expect(isActive(sinInicio, '2026-03-08')).toBe(false)
  })

  test('un tipo sin capa se sirve pero no cambia el dibujo ni la leyenda', () => {
    const base = activeAnnotations(red, HOY)[0]!
    const otra: AnnotationOut = { ...base, id: 'otra', kind: 'tipo-sin-capa' }
    expect(capasDe([otra])).toEqual([])
    expect(trazoDe([otra])).toBeNull()
    // junto a una interrupción, manda la capa que sí tiene trazo
    const tramo = base.segment_ids[0]!
    const marcas = bySegment([otra, base])
    expect(marcas.get(tramo)!.map((a) => a.id)).toEqual(['otra', base.id])
    expect(trazoDe(marcas.get(tramo))?.propiedad).toBe('interrumpido')
    expect(capasDe(marcas.get(tramo)).map((l) => l.kind)).toEqual(['interrupcion'])
  })

  test('la capa de las interrupciones dice las fechas como antes', () => {
    const ficha = annotationLayer('interrupcion')!.ficha
    const obras = red.annotations.find((a) => a.id === 'convencional-obras-autopista-ferroviaria-2026-09-06')!
    expect(ficha.fechas(obras)).toBe('Desde el 6 de septiembre de 2026. Reanudación prevista: otoño de 2027.')
    expect(ficha.fechas({ ...obras, expected_end_text: null })).toBe('Desde el 6 de septiembre de 2026. Sin fecha prevista de reanudación.')
    expect(ficha.fechas({ ...obras, ended_on: '2027-10-01' })).toBe('Desde el 6 de septiembre de 2026. La circulación se reanudó el 1 de octubre de 2027.')
  })
})
