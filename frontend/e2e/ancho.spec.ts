import { readFileSync } from 'node:fs'

import { expect, test } from '@playwright/test'

import { composeNetwork } from '../src/data/network.ts'
import type { NetworkIndexOut } from '../src/data/types.ts'

const leer = <T>(ruta: string) => JSON.parse(readFileSync(new URL(ruta, import.meta.url), 'utf-8')) as T
const red = composeNetwork(leer<NetworkIndexOut>('../public/data/index.json'), {})

const RIOFRIO_LOJA = 'lav-antequera-granada:bif-riofrio:loja'
const ANTEQUERA_ARCHIDONA = 'lav-antequera-granada:antequera-av:bif-archidona'
const MIXTOS = [
  RIOFRIO_LOJA,
  'lav-antequera-granada:loja:bif-tocon',
  'lav-antequera-granada:bif-la-chana:granada',
  'lav-monforte-murcia:bif-el-regueron:murcia-del-carmen',
]

test.describe('Ancho de vía: el tramo de ancho mixto lo dice', () => {
  test('solo el paso por Loja, la entrada a Granada y la de Murcia traen el ancho mixto', () => {
    const conAncho = red.segments.filter((s) => s.attributes?.gauge).map((s) => s.id)
    expect(conAncho.sort()).toEqual([...MIXTOS].sort())
    for (const id of MIXTOS) expect(red.segments.find((s) => s.id === id)?.attributes?.gauge?.value).toBe('mixto')
  })

  test('la ficha de un tramo de ancho mixto lo dice a la vista, con su término y su fuente', async ({ page }) => {
    await page.goto(`/tramo/${RIOFRIO_LOJA}`)
    const ficha = page.getByTestId('detalle-tramo')
    await expect(ficha).toBeVisible()
    const asa = page.getByRole('button', { name: 'Ampliar el panel' })
    if (await asa.isVisible()) await asa.click()
    // con lo esencial, sin abrir «Más detalle»
    await expect(page.getByTestId('tramo-atributo-gauge')).toBeVisible()
    await expect(page.getByTestId('tramo-atributo-gauge')).toHaveText('Mixto: caben trenes de los dos anchos')
    // la etiqueta y el valor son términos del glosario
    const nota = page.getByTestId('termino-nota').filter({ visible: true })
    await ficha.getByRole('button', { name: 'Ancho de vía', exact: true }).click()
    await expect(nota).toContainText('La distancia entre los dos carriles')
    await page.keyboard.press('Escape')
    await ficha.getByRole('button', { name: 'Mixto: caben trenes de los dos anchos' }).click()
    await expect(nota).toContainText('tercer carril')
    await nota.getByRole('link', { name: 'Ver en el glosario' }).click()
    await expect(page).toHaveURL(/\/glosario\/ancho-mixto$/)
    await expect(page.getByTestId('glosario-ancho-mixto')).toHaveAttribute('aria-current', 'true')
    // la fuente, al pie de «Más detalle», antes que la de la señalización
    await page.goto(`/tramo/${RIOFRIO_LOJA}`)
    await expect(ficha).toBeVisible()
    if (await asa.isVisible()) await asa.click()
    await page.getByTestId('mas-detalle').locator('summary').click()
    const fuente = page.getByTestId('atributos-fuente')
    await expect(fuente).toContainText(/Ancho de vía: Colaboradores de OpenStreetMap, comprobado el 12 de noviembre de 2026/)
    await expect(fuente).toContainText('osm-relation-2869549')
    await expect(fuente.locator('p').first()).toContainText('Ancho de vía')
  })

  test('un tramo de ancho normal no enseña la fila ni cita su fuente', async ({ page }) => {
    await page.goto(`/tramo/${ANTEQUERA_ARCHIDONA}`)
    await expect(page.getByTestId('detalle-tramo')).toBeVisible()
    await expect(page.getByTestId('tramo-vias')).toBeVisible()
    await expect(page.getByTestId('tramo-atributo-gauge')).toHaveCount(0)
    const asa = page.getByRole('button', { name: 'Ampliar el panel' })
    if (await asa.isVisible()) await asa.click()
    await page.getByTestId('mas-detalle').locator('summary').click()
    await expect(page.getByTestId('atributos-fuente')).not.toContainText('Ancho de vía')
  })
})
