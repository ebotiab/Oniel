import { readFileSync } from 'node:fs'

import { expect, test, type Page } from '@playwright/test'
import type { LineDetailOut, SegmentServicesOut } from '../src/data/types.ts'
import { alternativas } from './instantanea.ts'

// Un tren es del día en que sale. El AVE 02210 entra en este tramo a las 23:09 y su margen de
// estimación pasa de la medianoche: antes salía dos veces en la lista, la de hoy y la de la víspera,
// y la lista tenía un tren más que el esquema y que «Tramos sin otro camino».
const LINEA = 'lav-madrid-sevilla'
const TRAMO = `${LINEA}:bif-malaga:majarabique`

const leer = <T>(ruta: string) => JSON.parse(readFileSync(new URL(`../public/data/${ruta}`, import.meta.url), 'utf-8')) as T
const servicios = leer<SegmentServicesOut>(`segments/${TRAMO.replaceAll(':', '--')}.json`)
const linea = leer<LineDetailOut>(`lines/${LINEA}.json`)
const analisis = alternativas.segments.find((s) => s.segment_id === TRAMO)!

/** En el móvil la ficha vive en la hoja inferior: hay que ampliarla para verla entera. */
async function abrirHoja(page: Page) {
  const asa = page.getByRole('button', { name: 'Ampliar el panel' })
  if (await asa.isVisible()) await asa.click()
}

test.describe('Trenes al filo de la medianoche', () => {
  test('la lista, el esquema y el análisis de la instantánea cuentan los mismos trenes en todos los tramos', () => {
    for (const s of alternativas.segments) {
      const tramo = leer<SegmentServicesOut>(`segments/${s.segment_id.replaceAll(':', '--')}.json`)
      const ids = tramo.passes.map((p) => p.service.id)
      expect(new Set(ids).size, s.segment_id).toBe(ids.length)
      expect(s.trains, s.segment_id).toBe(ids.length)
    }
    expect(linea.counts[TRAMO]).toBe(servicios.passes.length)
  })

  test('la ficha del tramo enseña cada tren una vez y la misma cifra en el título y en la frase del otro camino', async ({ page }) => {
    const avisos: string[] = []
    page.on('console', (m) => {
      if (m.type() === 'error' || m.type() === 'warning') avisos.push(m.text())
    })
    await page.goto(`/tramo/${TRAMO}`)
    await abrirHoja(page)
    const ficha = page.getByTestId('detalle-tramo')
    await expect(ficha).toBeVisible()
    const n = servicios.passes.length
    expect(n).toBe(analisis.trains)
    await expect(ficha.getByRole('heading', { name: /Trenes que lo recorren/ })).toContainText(`· ${n} el `)
    await expect(page.getByTestId('lista-servicios').locator('li')).toHaveCount(n)
    await expect(page.getByTestId('lista-servicios').locator('li').filter({ hasText: 'AVE 02210' })).toHaveCount(1)
    // ningún tren para en los dos extremos: todas las horas son calculadas, y la frase lo dice sin ceros
    await expect(page.getByTestId('tramo-hora-de-paso')).toHaveText('Ninguno para en los dos extremos del tramo: la hora a la que pasan está calculada.')
    await expect(page.getByTestId('tramo-alternativa')).toContainText(`${analisis.without_alternative} trenes no tendrían otro camino`)
    expect(analisis.without_alternative).toBe(n)
    // React avisa en la consola cuando dos renglones de una lista llevan la misma clave
    expect(avisos.filter((a) => /same key/i.test(a))).toEqual([])
  })
})
