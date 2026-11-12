import { expect, test, type Page } from '@playwright/test'

const TRAMO = 'lav-madrid-sevilla:ciudad-real:puertollano'

/** En el móvil la ficha vive en la hoja inferior: hay que ampliarla para verla entera. */
async function abrirHoja(page: Page) {
  const asa = page.getByRole('button', { name: 'Ampliar el panel' })
  if (await asa.isVisible()) await asa.click()
}

interface Punto {
  fuente: string
  operador: string
  descargado: string
  dia: string
  trenes: number
  /** Frente al horario anterior del operador, en los mismos días: [antes, ahora]. */
  cambio?: { anterior: string; desde: string; hasta: string; antes: number; ahora: number }
}

const punto = (p: Punto) => ({
  dataset_id: `${p.fuente}-${p.descargado}`,
  source_id: p.fuente,
  operator_id: p.operador,
  retrieved_on: p.descargado,
  date: p.dia,
  trains: p.trenes,
  products: p.trenes ? [{ product: 'AVE', trains: p.trenes }] : [],
  change: p.cambio
    ? {
        previous_dataset_id: `${p.fuente}-${p.cambio.anterior}`,
        previous_retrieved_on: p.cambio.anterior,
        date_from: p.cambio.desde,
        date_to: p.cambio.hasta,
        trains_before: p.cambio.antes,
        trains_after: p.cambio.ahora,
      }
    : null,
})

const RENFE = { fuente: 'renfe-gtfs-av-ld-md', operador: 'renfe' }
const OUIGO = { fuente: 'ouigo-gtfs-nap', operador: 'ouigo' }

/**
 * Sirve un histórico fijo, venga de la API o de la instantánea: las cifras reales cambian con cada
 * fichero de horarios que se añade, y aquí se comprueba cómo se enseñan.
 */
async function conHistorico(page: Page, puntos: Punto[]) {
  await page.route(/\/(api\/(nodes|segments)\/[^/]+\/history|data\/historico\/(nodes|segments)\/[^/]+\.json)$/, (route) =>
    route.fulfill({ json: { id: 'de-prueba', points: puntos.map(punto) } }),
  )
}

test.describe('Evolución del servicio de un horario al siguiente', () => {
  test('con dos horarios del mismo operador, la ficha de la estación compara los trenes de cada uno', async ({ page }) => {
    await conHistorico(page, [
      { ...RENFE, descargado: '2026-11-08', dia: '2026-11-13', trenes: 21 },
      { ...OUIGO, descargado: '2026-11-12', dia: '2026-07-17', trenes: 6 },
      { ...RENFE, descargado: '2026-12-07', dia: '2026-12-11', trenes: 24 },
    ])
    await page.goto('/#/nodo/ciudad-real')
    await abrirHoja(page)
    // es detalle: plegado de entrada
    await expect(page.getByTestId('evolucion')).toBeHidden()
    await page.getByTestId('mas-detalle').locator('summary').click()
    const evolucion = page.getByTestId('evolucion')
    await expect(evolucion.getByTestId('evolucion-renfe')).toHaveText(
      'Renfe Viajeros. Horario del 8 nov 2026: 21 trenes el 13 nov · horario del 7 dic 2026: 24 trenes el 11 dic',
    )
    // de Ouigo hay un solo horario: nada que comparar
    await expect(evolucion.getByTestId('evolucion-ouigo')).toHaveCount(0)
    await expect(evolucion).toContainText('los trenes que paran aquí en un día laborable')
    // la fuente de los horarios la cita el pie de la ficha, justo debajo
    await expect(page.getByTestId('mas-detalle').getByTestId('pie-fuente').last()).toContainText(/Fuente de los horarios: Renfe/)
  })

  test('la ficha de un tramo también, con una línea por operador y su fuente', async ({ page }) => {
    await conHistorico(page, [
      { ...RENFE, descargado: '2026-11-08', dia: '2026-11-13', trenes: 96 },
      { ...OUIGO, descargado: '2026-07-02', dia: '2026-07-17', trenes: 14 },
      { ...RENFE, descargado: '2026-11-12', dia: '2026-11-13', trenes: 95 },
      { ...OUIGO, descargado: '2026-12-01', dia: '2026-12-11', trenes: 1 },
    ])
    await page.goto(`/#/tramo/${TRAMO}`)
    await abrirHoja(page)
    await page.getByTestId('mas-detalle').locator('summary').click()
    const evolucion = page.getByTestId('evolucion')
    await expect(evolucion.getByTestId('evolucion-renfe')).toHaveText(
      'Renfe Viajeros. Horario del 8 nov 2026: 96 trenes el 13 nov · horario del 12 nov 2026: 95 trenes el 13 nov',
    )
    await expect(evolucion.getByTestId('evolucion-ouigo')).toHaveText(
      'Ouigo España. Horario del 2 jul 2026: 14 trenes el 17 jul · horario del 1 dic 2026: 1 tren el 11 dic',
    )
    await expect(evolucion).toContainText('los trenes que recorren el tramo en un día laborable')
    await expect(evolucion.getByTestId('evolucion-fuente')).toHaveCount(2)
    await expect(evolucion.getByTestId('evolucion-fuente').first()).toContainText(/Fuente de los horarios: Renfe.*renfe-gtfs-av-ld-md/)
  })

  test('con tres o más horarios, una lista por fechas en vez de un renglón', async ({ page }) => {
    await conHistorico(page, [
      { ...RENFE, descargado: '2026-11-08', dia: '2026-11-13', trenes: 21 },
      { ...OUIGO, descargado: '2026-07-02', dia: '2026-07-17', trenes: 6 },
      { ...RENFE, descargado: '2026-12-07', dia: '2026-12-11', trenes: 24 },
      { ...OUIGO, descargado: '2026-12-01', dia: '2026-12-11', trenes: 8 },
      { ...RENFE, descargado: '2027-01-04', dia: '2027-01-08', trenes: 22 },
    ])
    await page.goto('/#/nodo/ciudad-real')
    await abrirHoja(page)
    await page.getByTestId('mas-detalle').locator('summary').click()
    const renfe = page.getByTestId('evolucion-renfe')
    await expect(renfe.locator('p')).toHaveText('Renfe Viajeros')
    // del más antiguo al más reciente, un horario por renglón
    await expect(renfe.getByRole('listitem')).toHaveText([
      'Horario del 8 nov 2026: 21 trenes el 13 nov',
      'Horario del 7 dic 2026: 24 trenes el 11 dic',
      'Horario del 4 ene 2027: 22 trenes el 8 ene',
    ])
    // con dos, el operador de al lado sigue en un renglón
    await expect(page.getByTestId('evolucion-ouigo')).toHaveText('Ouigo España. Horario del 2 jul 2026: 6 trenes el 17 jul · horario del 1 dic 2026: 8 trenes el 11 dic')
  })

  test('lo que cambia de un horario al anterior se cuenta en los mismos días', async ({ page }) => {
    const dias = { anterior: '2026-11-08', desde: '2026-11-11', hasta: '2026-12-08' }
    await conHistorico(page, [
      { ...RENFE, descargado: '2026-11-08', dia: '2026-11-13', trenes: 56 },
      { ...OUIGO, descargado: '2026-07-02', dia: '2026-07-17', trenes: 6 },
      // el día de referencia es el mismo y tiene los mismos trenes: lo que cambia está en otros días
      { ...RENFE, descargado: '2026-11-12', dia: '2026-11-13', trenes: 56, cambio: { ...dias, antes: 1068, ahora: 1083 } },
      { ...OUIGO, descargado: '2026-12-01', dia: '2026-12-11', trenes: 6, cambio: { anterior: '2026-07-02', desde: '2026-11-27', hasta: '2026-12-12', antes: 96, ahora: 96 } },
    ])
    await page.goto('/#/nodo/ciudad-real')
    await abrirHoja(page)
    await page.getByTestId('mas-detalle').locator('summary').click()
    await expect(page.getByTestId('evolucion-renfe')).toHaveText('Renfe Viajeros. Horario del 8 nov 2026: 56 trenes el 13 nov · horario del 12 nov 2026: 56 trenes el 13 nov')
    await expect(page.getByTestId('evolucion-renfe-cambio')).toHaveText(
      'Del 11 nov al 8 dic, 1.083 trenes: 15 más que en el horario del 8 nov 2026 esos mismos días (1.068).',
    )
    await expect(page.getByTestId('evolucion-ouigo-cambio')).toHaveText('Del 27 nov al 12 dic, 96 trenes: los mismos que en el horario del 2 jul 2026 esos mismos días.')
    await expect(page.getByTestId('evolucion')).toContainText('se cuentan los dos en los mismos días, las cuatro primeras semanas del más reciente')

    // con tres horarios, cada renglón de la lista lleva su comparación con el anterior
    await page.unrouteAll()
    await conHistorico(page, [
      { ...RENFE, descargado: '2026-11-08', dia: '2026-11-13', trenes: 56 },
      { ...RENFE, descargado: '2026-11-12', dia: '2026-11-13', trenes: 56, cambio: { ...dias, antes: 1068, ahora: 1083 } },
      { ...RENFE, descargado: '2026-12-07', dia: '2026-12-11', trenes: 54, cambio: { anterior: '2026-11-12', desde: '2026-12-06', hasta: '2027-01-02', antes: 1100, ahora: 1040 } },
    ])
    await page.goto(`/#/tramo/${TRAMO}`)
    await expect(page.getByTestId('evolucion-renfe').getByRole('listitem')).toHaveText([
      'Horario del 8 nov 2026: 56 trenes el 13 nov',
      'Horario del 12 nov 2026: 56 trenes el 13 nov Del 11 nov al 8 dic, 1.083 trenes: 15 más que en el horario anterior esos mismos días (1.068).',
      'Horario del 7 dic 2026: 54 trenes el 11 dic Del 6 dic al 2 ene, 1.040 trenes: 60 menos que en el horario anterior esos mismos días (1.100).',
    ])
  })

  test('con un solo horario por operador, o sin trenes, no se muestra nada', async ({ page }) => {
    await conHistorico(page, [
      { ...RENFE, descargado: '2026-11-08', dia: '2026-11-13', trenes: 21 },
      { ...OUIGO, descargado: '2026-11-12', dia: '2026-07-17', trenes: 0 },
      { ...OUIGO, descargado: '2026-12-01', dia: '2026-12-11', trenes: 0 },
    ])
    await page.goto('/#/nodo/ciudad-real')
    await abrirHoja(page)
    await page.getByTestId('mas-detalle').locator('summary').click()
    await expect(page.getByTestId('nodo-pk').first()).toBeVisible()
    // el resto del detalle está, y la fuente de los horarios también
    await expect(page.getByTestId('mas-detalle').getByTestId('pie-fuente').last()).toContainText(/Fuente de los horarios/)
    await expect(page.getByTestId('evolucion')).toHaveCount(0)
    // el detalle sigue abierto al pasar a otra ficha
    await page.goto(`/#/tramo/${TRAMO}`)
    await expect(page.getByTestId('tramo-pk')).toBeVisible()
    await expect(page.getByTestId('evolucion')).toHaveCount(0)
  })

  test('con los horarios cargados, la estación y el tramo comparan los de Renfe', async ({ page }) => {
    // sin datos de prueba: lo que haya en la instantánea o en la API, que hoy son dos horarios de Renfe
    await page.goto('/#/nodo/ciudad-real')
    await abrirHoja(page)
    await page.getByTestId('mas-detalle').locator('summary').click()
    // dos horarios van en un renglón; con tres o más, en una lista
    const horario = String.raw`[Hh]orario del \d+ \w+ \d{4}: \d+ trenes el \d+ \w+`
    const texto = new RegExp(`^Renfe Viajeros(\\. ${horario} · ${horario}|(\\s*${horario}){3,})$`)
    await expect(page.getByTestId('evolucion-renfe')).toHaveText(texto)
    await page.goto(`/#/tramo/${TRAMO}`)
    await expect(page.getByTestId('evolucion-renfe')).toHaveText(texto)
  })
})
