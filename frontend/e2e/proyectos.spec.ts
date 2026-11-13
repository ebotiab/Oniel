import { readFileSync } from 'node:fs'

import { expect, test } from '@playwright/test'
import type { Map as MapLibreMap } from 'maplibre-gl'

import { dibujoDe, leyendaDe } from '../src/app/annotationLayers.ts'
import { activeAnnotations, formatPartialDate, sourceLabels } from '../src/app/annotations.ts'
import { annotationHref, parseRoute, routePath } from '../src/app/state.ts'
import { composeNetwork } from '../src/data/network.ts'
import type { NetworkIndexOut } from '../src/data/types.ts'

// Los proyectos: lo previsto, en obras o parado alrededor de las líneas cargadas. «Hoy» es el 12 de
// noviembre de 2026, el día en que se comprobaron en sus fuentes.
const HOY = new Date('2026-11-12T12:00:00')
const MORA_ALCAZAR = 'proyecto-lav-mora-alcazar'
const LOJA = 'proyecto-variante-de-loja'
const TUNELES = 'proyecto-galibo-tuneles-venta-de-cardenas-montoro'
const TRAMO_CON_OBRAS = 'convencional-madrid-alcazar-cordoba:venta-de-cardenas:vilches'

type ConMapa = { __onielMap?: MapLibreMap }

const leer = <T>(ruta: string) => JSON.parse(readFileSync(new URL(ruta, import.meta.url), 'utf-8')) as T
const red = composeNetwork(leer<NetworkIndexOut>('../public/data/index.json'), {})
const proyectos = activeAnnotations(red, '2026-11-12').filter((a) => a.kind === 'proyecto')
const proyecto = (id: string) => proyectos.find((a) => a.id === id)!

test.describe('Proyectos: datos y registro de capas', () => {
  test('cada proyecto trae estado, hitos fechados con su fuente y fecha de comprobación', () => {
    expect(proyectos.map((a) => a.id).sort()).toEqual([
      'proyecto-conexion-lav-cordoba-jaen',
      'proyecto-duplicacion-antequera-granada',
      TUNELES,
      MORA_ALCAZAR,
      LOJA,
    ])
    for (const a of proyectos) {
      expect(a.title && a.reason, a.id).toBeTruthy()
      expect(a.milestones!.length, a.id).toBeGreaterThan(0)
      // la fuente de cada hito es una de las del proyecto, y tiene dónde consultarse
      for (const h of a.milestones!) expect(a.sources.find((s) => s.id === h.source_id)?.url, `${a.id} ${h.date}`).toBeTruthy()
      expect(a.checked_on, a.id).toBe('2026-11-12')
    }
  })

  test('el dibujo sale del estado: puntos sobre el papel, trazos en obras, nada sobre una vía que ya existe', () => {
    expect(dibujoDe(proyecto(MORA_ALCAZAR))).toBe('puntos')
    // hoy ningún proyecto en obras tiene esbozo: el trazo se comprueba con uno que lo estuviera
    const enObras = { ...proyecto(MORA_ALCAZAR), status: 'en_obras' as const }
    expect(dibujoDe(enObras)).toBe('trazos')
    expect(leyendaDe([enObras]).map((e) => e.texto)).toEqual(['Proyecto en obras'])
    // las obras de los túneles van de nodo a nodo: no tienen geometría propia ni cambian la vía
    expect(dibujoDe(proyecto(TUNELES))).toBeNull()
    expect(proyecto(TUNELES).segment_ids).toHaveLength(8)
    // lo mismo la Variante de Loja y la duplicación de vía, desde que su línea está cargada: cuelgan
    // del paso por Loja y de los tramos de vía única de Antequera – Granada
    expect(dibujoDe(proyecto(LOJA))).toBeNull()
    expect(proyecto(LOJA).segment_ids).toEqual(['lav-antequera-granada:bif-riofrio:loja', 'lav-antequera-granada:loja:bif-tocon'])
    expect(proyecto('proyecto-duplicacion-antequera-granada').segment_ids).toHaveLength(4)
    expect(leyendaDe(proyectos).map((e) => e.texto)).toEqual(['Proyecto'])
    expect(leyendaDe([proyecto(TUNELES)])).toEqual([])
  })

  test('la ficha de un proyecto tiene su ruta, que va y vuelve de la URL', () => {
    const ruta = `/proyecto/${MORA_ALCAZAR}`
    expect(annotationHref(proyecto(MORA_ALCAZAR))).toBe(ruta)
    expect(parseRoute(ruta).selection).toEqual({ type: 'anotacion', kind: 'proyecto', id: MORA_ALCAZAR })
    expect(routePath(parseRoute(ruta))).toBe(ruta)
  })

  test('las fechas a medias se dicen como se conocen, y el BOE se cita por su identificador', () => {
    expect(formatPartialDate('2010')).toBe('2010')
    expect(formatPartialDate('2010-05')).toBe('mayo de 2010')
    expect(formatPartialDate('2008-09-04')).toBe('4 de septiembre de 2008')
    const labels = sourceLabels(proyecto(MORA_ALCAZAR).sources)
    expect(labels[0]).toBe('BOE-B-2008-232070')
    expect(labels.at(-1)).toBe('Colaboradores de OpenStreetMap')
  })
})

test.describe('Proyectos: la vista', () => {
  test.beforeEach(async ({ page }) => {
    await page.clock.setFixedTime(HOY)
  })

  test('la ficha de un proyecto dice el estado, los hitos con su fuente y cuándo se comprobó', async ({ page }) => {
    await page.goto(`/proyecto/${MORA_ALCAZAR}`)
    const ficha = page.getByTestId('ficha-proyecto')
    await expect(ficha).toBeVisible()
    await expect(page.getByTestId('ficha-proyecto-estado')).toHaveText(/^Proyecto\s*sin ejecutar$/)
    await expect(ficha.getByRole('heading', { level: 2 })).toHaveText('Línea de alta velocidad Madrid – Jaén: tramo Mora – Alcázar de San Juan')
    // el dibujo del mapa es un esbozo, y la ficha lo dice
    await expect(ficha).toContainText('no es el trazado del proyecto')
    const hitos = page.getByTestId('ficha-proyecto-hitos').getByRole('listitem')
    await expect(hitos).toHaveCount(6)
    await expect(hitos.nth(2)).toContainText('4 de septiembre de 2008')
    await expect(hitos.nth(2)).toContainText('Se aprueba definitivamente el estudio informativo.')
    await expect(hitos.nth(2).getByRole('link')).toHaveAttribute('href', 'https://www.boe.es/diario_boe/txt.php?id=BOE-B-2008-232070')
    await expect(page.getByTestId('ficha-proyecto-fuentes')).toContainText('Comprobado el 12 de noviembre de 2026.')
    // la ruta se conserva y «Toda la red» vuelve a la vista de la red
    await expect(page).toHaveURL(new RegExp(`/proyecto/${MORA_ALCAZAR}$`))
    await ficha.getByRole('button', { name: '← Toda la red' }).click()
    await expect(page.getByTestId('ficha-proyecto')).toHaveCount(0)
    await expect(page).toHaveURL(/\/$/)
  })

  test('un proyecto en obras sobre una vía cargada se explica en la ficha de sus tramos', async ({ page }) => {
    await page.goto(`/tramo/${TRAMO_CON_OBRAS}`)
    const bloque = page.getByTestId('proyecto')
    await expect(bloque).toHaveCount(1)
    await expect(bloque).toContainText('en obras')
    await expect(bloque).toContainText('Venta de Cárdenas – Alcolea de Córdoba')
    await expect(bloque).toContainText('Adaptación de 13 túneles para la autopista ferroviaria')
    await expect(page.getByTestId('proyecto-fechas')).toHaveText('Obras desde el 6 de septiembre de 2026. Final previsto: otoño de 2027.')
    // el tramo sigue llevando, aparte, su interrupción
    await expect(page.getByTestId('interrupcion')).toHaveCount(1)
    await page.getByTestId('proyecto-enlace').click()
    await expect(page.getByTestId('ficha-proyecto')).toBeVisible()
    await expect(page).toHaveURL(new RegExp(`/proyecto/${TUNELES}$`))
    await expect(page.getByTestId('ficha-proyecto-fechas')).toContainText('Final previsto: otoño de 2027.')
  })

  test('la página de cobertura enumera los proyectos, con su estado, y lleva a la ficha de cada uno', async ({ page }) => {
    await page.goto('/cobertura')
    const lista = page.getByTestId('cobertura-proyectos')
    await expect(lista.getByRole('listitem')).toHaveCount(5)
    await expect(lista.getByRole('listitem').filter({ hasText: 'Variante de Loja' })).toContainText('en obras')
    await lista.getByTestId('proyecto-enlace').filter({ hasText: 'Variante de Loja' }).click()
    await expect(page).toHaveURL(/\/proyecto\//)
    await expect(page.getByTestId('ficha-proyecto').getByRole('heading', { level: 2 })).toHaveText('Variante de Loja')
    await expect(page.getByTestId('ficha-proyecto-estado')).toContainText('en obras')
  })

  test('el mapa dibuja cada proyecto con su trazo, y tocarlo abre su ficha', async ({ page, isMobile }) => {
    await page.goto('/')
    await page.waitForFunction(() => (globalThis as unknown as ConMapa).__onielMap?.getSource('oniel-annotations') !== undefined)
    const dibujos = await page.evaluate(async () => {
      const map = (globalThis as unknown as ConMapa).__onielMap!
      const data = (await (map.getSource('oniel-annotations') as unknown as { getData: () => Promise<GeoJSON.FeatureCollection> }).getData()).features
      return Object.fromEntries(data.map((f) => [String(f.properties!.oniel_id), String(f.properties!.dibujo)]))
    })
    // solo los dos que no cuelgan de una vía cargada; ninguno está en obras
    expect(dibujos).toEqual({
      'proyecto-conexion-lav-cordoba-jaen': 'puntos',
      [MORA_ALCAZAR]: 'puntos',
    })
    if (!isMobile) {
      await expect(page.getByTestId('leyenda-proyecto')).toBeVisible()
      await expect(page.getByTestId('leyenda-proyecto-en-obras')).toHaveCount(0)
    }
    // un toque en mitad del esbozo, lejos de cualquier vía cargada
    await page.waitForFunction(() => (globalThis as unknown as ConMapa).__onielMap?.loaded() === true)
    const punto = await page.evaluate(() => {
      const map = (globalThis as unknown as ConMapa).__onielMap!
      const p = map.project([-3.5925, 39.489])
      const caja = map.getContainer().getBoundingClientRect()
      return { x: caja.left + p.x, y: caja.top + p.y }
    })
    await page.mouse.click(punto.x, punto.y)
    await expect(page).toHaveURL(new RegExp(`/proyecto/${MORA_ALCAZAR}$`))
    await expect(page.getByTestId('ficha-proyecto')).toBeAttached()
  })
})
