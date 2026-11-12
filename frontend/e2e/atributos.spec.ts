import { readFileSync } from 'node:fs'

import { expect, test } from '@playwright/test'

import { attributeRows, attributesOf, SEGMENT_ATTRIBUTES, type SegmentAttribute } from '../src/app/segmentAttributes.ts'
import { composeNetwork } from '../src/data/network.ts'
import type { NetworkIndexOut, SegmentOut } from '../src/data/types.ts'

const leer = <T>(ruta: string) => JSON.parse(readFileSync(new URL(ruta, import.meta.url), 'utf-8')) as T
const red = composeNetwork(leer<NetworkIndexOut>('../public/data/index.json'), {})
const tramo = (id: string) => red.segments.find((s) => s.id === id)!
const linea = (s: SegmentOut) => red.lines.find((l) => l.id === s.line_id)

const DOBLE = 'lav-madrid-sevilla:urda:ciudad-real'
const UNICA = 'convencional-madrid-alcazar-cordoba:santa-cruz-de-mudela:almuradiel-viso-del-marques'

test.describe('Atributos de tramo: de las secciones de la línea a la ficha', () => {
  test('cada tramo de la instantánea trae su número de vías como atributo, con fuente donde cambia', () => {
    expect(red.segments.length).toBeGreaterThan(0)
    for (const s of red.segments) expect(s.attributes?.tracks?.value).toBe(s.tracks)
    expect(tramo(UNICA).attributes?.tracks).toEqual({ value: 1, source_id: 'wikipedia-lineas-300-400', checked_on: '2026-11-08' })
    // la vía doble de la alta velocidad es el valor de la línea entera: no tiene fuente propia
    expect(tramo(DOBLE).attributes?.tracks).toEqual({ value: 2, source_id: null, checked_on: null })
  })

  test('la ficha saca las vías de la lista de atributos', () => {
    const filas = attributeRows(tramo(UNICA), linea(tramo(UNICA)), 'esencial')
    expect(filas.map((f) => [f.atributo.etiqueta, f.atributo.formato(f.valor!.value), f.atributo.termino?.(f.valor!.value)])).toEqual([['Vías', 'Vía única', 'via-unica']])
    expect(attributeRows(tramo(UNICA), linea(tramo(UNICA)), 'detalle')).toEqual([])
    expect(SEGMENT_ATTRIBUTES.map((a) => a.clave)).toEqual(['tracks'])
  })

  test('una API anterior a los atributos solo trae `tracks` y se lee igual', () => {
    const { attributes: _sin, ...anterior } = tramo(UNICA)
    expect(attributesOf(anterior)).toEqual({ tracks: { value: 1, source_id: null, checked_on: null } })
    expect(attributeRows(anterior, undefined, 'esencial')[0]?.valor?.value).toBe(1)
    // sin número de vías la fila sigue, y dice que no hay dato
    const filas = attributeRows({ ...anterior, tracks: null }, undefined, 'esencial')
    expect(filas).toHaveLength(1)
    expect(filas[0]?.valor).toBeNull()
    expect(filas[0]?.atributo.sinDato).toBe('sin dato')
  })

  test('un atributo nuevo es una entrada más: el valor del tramo o, si no varía, el de la línea', () => {
    const lista: SegmentAttribute[] = [
      ...SEGMENT_ATTRIBUTES,
      { clave: 'electrificacion', etiqueta: 'Electrificación', formato: String, lugar: 'detalle', deLinea: (l) => l.electrification },
      { clave: 'bloqueo', etiqueta: 'Bloqueo', formato: (v) => (v === 'bca' ? 'Automático' : String(v)), lugar: 'detalle' },
    ]
    const base = tramo(DOBLE)
    // sin secciones, la electrificación es la de la línea y el bloqueo, que no tiene valor, no sale
    const sinSecciones = attributeRows(base, linea(base), 'detalle', lista)
    expect(sinSecciones.map((f) => [f.atributo.clave, f.valor?.value])).toEqual([['electrificacion', '25 kV 50 Hz']])
    // con una sección en el tramo, manda su valor
    const conSecciones: SegmentOut = {
      ...base,
      attributes: {
        ...base.attributes,
        electrificacion: { value: 'sin electrificar', source_id: null, checked_on: null },
        bloqueo: { value: 'bca', source_id: 'una-fuente', checked_on: '2026-11-12' },
      },
    }
    const filas = attributeRows(conSecciones, linea(base), 'detalle', lista)
    expect(filas.map((f) => [f.atributo.etiqueta, f.atributo.formato(f.valor!.value)])).toEqual([
      ['Electrificación', 'sin electrificar'],
      ['Bloqueo', 'Automático'],
    ])
    // y la lista de lo esencial no cambia
    expect(attributeRows(conSecciones, linea(base), 'esencial', lista).map((f) => f.atributo.clave)).toEqual(['tracks'])
  })

  test('la ficha enseña el atributo y no el campo suelto', async ({ page }) => {
    // en el índice y en el detalle de la línea, el atributo dice vía única y el campo `tracks`, doble
    await page.route(/\/(data\/index\.json|api\/lines|data\/lines\/lav-madrid-sevilla\.json|api\/lines\/lav-madrid-sevilla)$/, async (route) => {
      const res = await route.fetch()
      const datos = await res.json()
      for (const f of datos.segment_features.features) if (f.id === DOBLE) f.properties.attributes.tracks.value = 1
      for (const s of datos.segments ?? []) if (s.id === DOBLE) s.attributes.tracks.value = 1
      await route.fulfill({ response: res, json: datos })
    })
    await page.goto(`/#/tramo/${DOBLE}`)
    await expect(page.getByTestId('detalle-tramo')).toBeVisible()
    await expect(page.getByTestId('tramo-vias')).toHaveText('Vía única')
    // el visor sigue pidiendo datos en segundo plano: las peticiones retenidas al acabar no son un fallo
    await page.unrouteAll({ behavior: 'ignoreErrors' })
  })
})
