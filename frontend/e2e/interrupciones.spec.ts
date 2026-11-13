import { expect, test, type Page } from '@playwright/test'
import type { FeatureCollection } from 'geojson'
import type { GeoJSONSource, Map as MapLibreMap } from 'maplibre-gl'
import { abrirZonas } from './navegar.ts'


// «Hoy» es el 10 de noviembre de 2026, el día en que se comprobaron las dos interrupciones
// iniciales (obras entre Almuradiel y Alcolea de Córdoba; alta velocidad entre La Sagra y Córdoba):
// ambas estaban vigentes. Con el reloj fijo, las pruebas no dependen del día en que se ejecutan ni
// de que más adelante se registre el final de alguna de ellas.
const HOY = new Date('2026-11-10T12:00:00')
const estatico = Boolean(process.env.ONIEL_E2E_STATIC)

const LINEA = 'convencional-madrid-alcazar-cordoba'
const TRAMO_CORTADO = `${LINEA}:venta-de-cardenas:vilches` // tramo 16 de la línea
const TRAMO_ABIERTO = `${LINEA}:valdepenas:santa-cruz-de-mudela` // tramo 13

type ConMapa = { __onielMap?: MapLibreMap }

async function abrirLineaConvencional(page: Page) {
  await page.goto('/')
  const asa = page.getByRole('button', { name: 'Ampliar el panel' })
  if (await asa.isVisible()) await asa.click() // en móvil, la hoja empieza plegada
  await abrirZonas(page)
  await page.getByTestId(`linea-${LINEA}`).click()
  await expect(page.getByTestId('esquema-tramo-16')).toBeAttached()
}

test.describe('Interrupciones del servicio', () => {
  test.beforeEach(async ({ page }) => {
    await page.clock.setFixedTime(HOY)
  })

  test('un tramo interrumpido dice el motivo, las fechas y la fuente', async ({ page }) => {
    await page.goto(`/tramo/${TRAMO_CORTADO}`)
    await expect(page.getByTestId('detalle-tramo')).toBeVisible()
    const bloque = page.getByTestId('interrupcion')
    await expect(bloque).toHaveCount(1)
    await expect(bloque).toContainText('sin circulación')
    await expect(bloque).toContainText('Almuradiel-Viso del Marqués – Alcolea de Córdoba')
    await expect(bloque).toContainText(/autopista ferroviaria/)
    await expect(page.getByTestId('interrupcion-fechas')).toHaveText(/^Desde el 6 de septiembre de 2026\. Reanudación prevista: otoño de 2027\.$/)
    // la fuente principal es el aviso de Adif, con enlace; debajo, la fecha de la comprobación
    const fuentes = page.getByTestId('interrupcion-fuentes')
    await expect(fuentes.getByRole('link').first()).toHaveAttribute('href', /^https:\/\/www\.adif\.es\//)
    await expect(fuentes).toContainText(/Comprobado el \d+ de [a-z]+ de \d{4}\./)
    // los trenes de la lista son los del horario: una línea lo dice (día de referencia de la instantánea)
    await expect(page.getByTestId('nota-horario')).toHaveText(/^Horario publicado; sin circulación real desde el 6 de septiembre de 2026 \(Adif\)\.$/)
    await expect(page.getByTestId('lista-servicios').locator('li').first()).toBeVisible()
  })

  test('un tramo sin interrupción no lleva bloque ni nota', async ({ page }) => {
    await page.goto(`/tramo/${TRAMO_ABIERTO}`)
    await expect(page.getByTestId('lista-servicios').locator('li').first()).toBeVisible()
    await expect(page.getByTestId('interrupcion')).toHaveCount(0)
    await expect(page.getByTestId('nota-horario')).toHaveCount(0)
  })

  test('una interrupción ya terminada queda en el detalle del tramo, sin señal roja', async ({ page }) => {
    await page.goto('/tramo/lav-madrid-sevilla:adamuz:cordoba')
    await expect(page.getByTestId('detalle-tramo')).toBeVisible()
    // la vigente sigue fuera del detalle, y es la única con la señal de «sin circulación»
    await expect(page.getByTestId('interrupcion')).toHaveCount(1)
    const anteriores = page.getByTestId('interrupciones-anteriores')
    await expect(anteriores).toBeHidden()
    await page.getByTestId('mas-detalle').locator('summary').click()
    const anterior = anteriores.getByTestId('interrupcion-anterior')
    await expect(anterior).toHaveCount(1)
    await expect(anterior).toContainText('interrupción terminada')
    await expect(anterior).toContainText('Villanueva de Córdoba-Los Pedroches – Córdoba')
    await expect(anterior.locator('.senal.roja')).toHaveCount(0)
    await expect(page.getByTestId('interrupcion-anterior-fechas')).toHaveText(
      /^Desde el 19 de enero de 2026\. La circulación se reanudó el 17 de febrero de 2026\.$/,
    )
    await expect(page.getByTestId('interrupcion-anterior-fuentes').getByRole('link').first()).toHaveAttribute('href', /^https:\/\/www\.adif\.es\//)

    // un tramo al que no afectó no lleva el apartado
    await page.goto(`/tramo/${TRAMO_ABIERTO}`)
    await expect(page.getByTestId('detalle-tramo')).toBeVisible()
    await expect(page.getByTestId('interrupciones-anteriores')).toHaveCount(0)
  })

  test('el esquema de la línea marca los tramos sin circulación y lleva al primero', async ({ page }) => {
    await abrirLineaConvencional(page)
    await expect(page.getByTestId('esquema-tramo-16')).toHaveAttribute('data-interrumpido', 'true')
    await expect(page.getByTestId('esquema-tramo-16')).toHaveAttribute('aria-label', /sin circulación hoy/)
    await expect(page.getByTestId('esquema-tramo-13')).not.toHaveAttribute('data-interrumpido')
    // una línea de texto sobre el esquema dice qué está cortado, desde cuándo y según quién
    const cortes = page.getByTestId('cortes-linea')
    await expect(cortes.locator('li')).toHaveCount(1)
    await expect(cortes).toContainText('Sin circulación entre Almuradiel-Viso del Marqués y Alcolea de Córdoba desde el 6 de septiembre de 2026 (Adif)')
    await cortes.getByRole('button').click()
    await expect(page.getByTestId('detalle-tramo')).toBeVisible()
    await expect(page).toHaveURL(new RegExp(`/tramo/${LINEA}:almuradiel-viso-del-marques:venta-de-cardenas$`))
    await expect(page.getByTestId('interrupcion')).toBeVisible()
  })

  test('el mapa dibuja en rojo los tramos interrumpidos y la leyenda lo explica', async ({ page }) => {
    await page.goto('/')
    await expect(page.locator('.maplibregl-canvas')).toBeVisible()
    await page.waitForFunction(() => (globalThis as unknown as ConMapa).__onielMap?.getSource('oniel-segments') !== undefined)
    const tramos = await page.evaluate(async () => {
      const map = (globalThis as unknown as ConMapa).__onielMap!
      const data = (await (map.getSource('oniel-segments') as GeoJSONSource).getData()) as FeatureCollection
      const ids = (cortado: boolean) => data.features.filter((f) => Boolean(f.properties?.interrumpido) === cortado).map((f) => String(f.properties?.oniel_id))
      // el color del trazo depende de esa propiedad: rojo si el tramo está interrumpido
      return { cortados: ids(true), abiertos: ids(false), color: JSON.stringify(map.getPaintProperty('oniel-segments', 'line-color')) }
    })
    expect(tramos.cortados).toContain(TRAMO_CORTADO)
    expect(tramos.cortados).toContain('lav-madrid-sevilla:bif-la-sagra:urda')
    expect(tramos.cortados).toContain('lav-madrid-sevilla:adamuz:cordoba')
    expect(tramos.abiertos).toContain(TRAMO_ABIERTO)
    expect(tramos.abiertos).toContain('lav-madrid-sevilla:madrid-puerta-de-atocha:bif-los-gavilanes')
    expect(tramos.abiertos).toContain('lav-madrid-sevilla:cordoba:bif-malaga')
    expect(tramos.color).toContain('"interrumpido"')
    expect(tramos.color).toContain('#B4232A')
    // la leyenda solo existe en escritorio
    if (await page.locator('.leyenda').isVisible()) {
      await expect(page.getByTestId('leyenda-interrupcion')).toBeVisible()
      await expect(page.locator('.leyenda')).toContainText('Sin circulación hoy')
    }
  })

  test('antes de que empiece una interrupción no se marca nada', async ({ page }) => {
    await page.clock.setFixedTime(new Date('2026-08-01T12:00:00'))
    await abrirLineaConvencional(page)
    await expect(page.getByTestId('esquema-tramo-16')).not.toHaveAttribute('data-interrumpido')
    await expect(page.getByTestId('cortes-linea')).toHaveCount(0)
    await expect(page.getByTestId('leyenda-interrupcion')).toHaveCount(0)
    await page.goto(`/tramo/${TRAMO_CORTADO}`)
    await expect(page.getByTestId('detalle-tramo')).toBeVisible()
    await expect(page.getByTestId('interrupcion')).toHaveCount(0)
  })

  test('simular un cierre en un tramo ya interrumpido lo indica', async ({ page }) => {
    await page.goto(`/tramo/${TRAMO_CORTADO}/cierre`)
    await expect(page.getByTestId('panel-simulacion')).toBeVisible()
    await expect(page.getByTestId('sim-interrumpido')).toHaveText(/^Este tramo ya está sin circulación desde el 6 de septiembre de 2026 \(Adif\)\. La simulación se calcula sobre el horario publicado\.$/)
    // en un tramo abierto, el formulario no lleva ninguna nota
    await page.goto(`/tramo/${TRAMO_ABIERTO}/cierre`)
    await expect(page.getByTestId('panel-simulacion')).toBeVisible()
    await expect(page.getByTestId('sim-interrumpido')).toHaveCount(0)
  })

  test('el resultado de la simulación señala el tramo y la alternativa interrumpidos ese día', async ({ page }) => {
    test.skip(estatico, 'la simulación necesita la API')
    await page.goto('/tramo/lav-madrid-sevilla:villanueva-de-cordoba:adamuz/cierre')
    // un día que cubren los horarios cargados (el de las demás pruebas de la simulación), con las dos interrupciones vigentes
    await page.getByTestId('sim-fecha').fill('2026-11-13')
    await page.getByTestId('sim-inicio').fill('08:00')
    await page.getByTestId('sim-fin').fill('09:00')
    await page.getByTestId('sim-calcular').click()
    await expect(page.getByTestId('sim-resultado')).toBeVisible()
    await expect(page.getByTestId('sim-resultado-interrumpido')).toHaveText(/^Ese día el tramo ya está interrumpido\. Horario publicado; sin circulación real desde el 28 de octubre de 2026 \(Adif\)\.$/)
    // la alternativa por Despeñaperros cruza el corte por obras, y el rodeo de Ciudad Real a Córdoba por Manzanares también
    await expect(page.getByTestId('sim-alternativa-interrumpida')).toHaveCount(2)
    await expect(page.getByTestId('sim-alternativa-interrumpida').last()).toContainText('no hay circulación entre Almuradiel-Viso del Marqués y Alcolea de Córdoba desde el 6 de septiembre de 2026 (Adif)')
    await expect(page.getByTestId('sim-interrumpido')).toHaveCount(0)
  })

  test('un nodo del corte y la página de cobertura enumeran la interrupción', async ({ page }) => {
    await page.goto('/nodo/venta-de-cardenas')
    await expect(page.getByTestId('detalle-nodo')).toBeVisible()
    await expect(page.getByTestId('interrupcion')).toHaveCount(1)
    await expect(page.getByTestId('interrupcion')).toContainText(/autopista ferroviaria/)
    // los dos tramos que confluyen en Venta de Cárdenas están sin circulación
    await expect(page.getByTestId('detalle-nodo').locator('.lista-simple .senal.roja')).toHaveCount(2)
    await page.goto('/cobertura')
    const cobertura = page.getByTestId('cobertura-interrupciones')
    await expect(cobertura.getByTestId('interrupcion')).toHaveCount(3)
    await expect(cobertura).toContainText('Bifurcación La Sagra – Córdoba')
    await expect(cobertura).toContainText('Almuradiel-Viso del Marqués – Alcolea de Córdoba')
    await expect(cobertura).toContainText('Espelúy – Jaén')
  })
})
