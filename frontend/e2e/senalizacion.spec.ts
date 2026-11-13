import { readFileSync } from 'node:fs'

import { expect, test, type Page } from '@playwright/test'

import { attributeRows, attributeSources } from '../src/app/segmentAttributes.ts'
import { composeNetwork } from '../src/data/network.ts'
import type { NetworkIndexOut } from '../src/data/types.ts'

const leer = <T>(ruta: string) => JSON.parse(readFileSync(new URL(ruta, import.meta.url), 'utf-8')) as T
const red = composeNetwork(leer<NetworkIndexOut>('../public/data/index.json'), {})

const FUENTE = 'adif-declaracion-red-2026-mapas'
const ALTA_VELOCIDAD = 'lav-madrid-sevilla:urda:ciudad-real'
const VIA_UNICA = 'convencional-madrid-alcazar-cordoba:santa-cruz-de-mudela:almuradiel-viso-del-marques'
const MIXTO = 'convencional-madrid-alcazar-cordoba:cinco-casas:manzanares'
const MANZANARES_CIUDAD_REAL = 'manzanares-ciudad-real:manzanares:daimiel'

/** En el móvil la ficha vive en la hoja inferior: hay que ampliarla para verla entera. */
async function abrirDetalle(page: Page, tramo: string) {
  await page.goto(`/tramo/${tramo}`)
  await expect(page.getByTestId('detalle-tramo')).toBeVisible()
  const asa = page.getByRole('button', { name: 'Ampliar el panel' })
  if (await asa.isVisible()) await asa.click()
  await page.getByTestId('mas-detalle').locator('summary').click()
}

test.describe('Señalización: protección del tren, bloqueo y mando de cada tramo', () => {
  test('todos los tramos de la instantánea traen los tres, con la fuente y la fecha', () => {
    expect(red.segments).toHaveLength(130)
    for (const s of red.segments) {
      for (const clave of ['proteccion_tren', 'bloqueo', 'mando']) {
        expect(s.attributes?.[clave], `${clave} de ${s.id}`).toMatchObject({ source_id: FUENTE })
        // la prolongación a Málaga se leyó en el mapa un día después que el resto
        expect(['2026-11-12', '2026-11-13']).toContain(s.attributes?.[clave]?.checked_on)
      }
      const filas = attributeRows(s, red.lines.find((l) => l.id === s.line_id), 'detalle')
      // cada valor tiene su texto en la ficha: ninguno sale con la clave cruda
      for (const f of filas) expect(f.atributo.formato(f.valor!.value)).not.toMatch(/_|^[a-z]/)
      const comprobado = s.attributes?.bloqueo?.checked_on
      expect(attributeSources(filas)).toEqual([{ sourceId: FUENTE, checkedOn: comprobado, etiquetas: ['Protección del tren', 'Bloqueo', 'Mando'] }])
    }
  })

  test('van plegados bajo «Más detalle», con su fuente y la fecha en que se comprobaron', async ({ page }) => {
    await page.goto(`/tramo/${VIA_UNICA}`)
    await expect(page.getByTestId('detalle-tramo')).toBeVisible()
    await expect(page.getByTestId('tramo-atributo-bloqueo')).toBeHidden()
    await abrirDetalle(page, VIA_UNICA)
    await expect(page.getByTestId('tramo-atributo-proteccion_tren')).toHaveText('ASFA')
    await expect(page.getByTestId('tramo-atributo-bloqueo')).toHaveText('Automático de vía única')
    await expect(page.getByTestId('tramo-atributo-mando')).toHaveText('Control de tráfico centralizado')
    const fuente = page.getByTestId('atributos-fuente')
    await expect(fuente).toContainText(/Protección del tren, bloqueo y mando: Adif Alta Velocidad; Adif, comprobado el 12 de noviembre de 2026/)
    await expect(fuente).toContainText('Declaración sobre la Red 2026')
    await expect(fuente).toContainText(FUENTE)
  })

  test('la alta velocidad dice su sistema y su bloqueo, y que el mando no está publicado', async ({ page }) => {
    await abrirDetalle(page, ALTA_VELOCIDAD)
    await expect(page.getByTestId('tramo-atributo-proteccion_tren')).toHaveText('LZB y ASFA')
    await expect(page.getByTestId('tramo-atributo-bloqueo')).toHaveText('De control automático')
    await expect(page.getByTestId('tramo-atributo-mando')).toHaveText('Sin dato publicado')
  })

  test('las líneas de alta velocidad de Córdoba a Granada dicen su ERTMS, con el ASFA de respaldo', async ({ page }) => {
    await abrirDetalle(page, 'lav-cordoba-malaga:bif-malaga:la-marota')
    await expect(page.getByTestId('tramo-atributo-proteccion_tren')).toHaveText('ERTMS de niveles 1 y 2 y ASFA')
    await expect(page.getByTestId('tramo-atributo-bloqueo')).toHaveText('De control automático')
    await abrirDetalle(page, 'lav-antequera-granada:bif-riofrio:loja')
    await expect(page.getByTestId('tramo-atributo-proteccion_tren')).toHaveText('ERTMS de nivel 2 y ASFA')
    await expect(page.getByTestId('tramo-atributo-mando')).toHaveText('Sin dato publicado')
  })

  test('el tramo que cambia de bloqueo donde no hay nodo lo dice, y Manzanares – Ciudad Real es de vía única', async ({ page }) => {
    await abrirDetalle(page, MIXTO)
    await expect(page.getByTestId('tramo-atributo-bloqueo')).toHaveText('Automático: banalizado en una parte y de vía doble en otra')
    await abrirDetalle(page, MANZANARES_CIUDAD_REAL)
    await expect(page.getByTestId('tramo-atributo-bloqueo')).toHaveText('Automático de vía única')
    await expect(page.getByTestId('tramo-atributo-mando')).toHaveText('Control de tráfico centralizado')
  })

  test('cada término abre su nota y lleva a su entrada del glosario', async ({ page }) => {
    await abrirDetalle(page, ALTA_VELOCIDAD)
    const ficha = page.getByTestId('detalle-tramo')
    await ficha.getByRole('button', { name: 'LZB y ASFA' }).click()
    const nota = page.getByTestId('termino-nota').filter({ visible: true })
    await expect(nota).toContainText('LZB')
    await expect(nota).toContainText('Supervisa de forma continua la velocidad')
    await page.keyboard.press('Escape')
    await ficha.getByRole('button', { name: 'Bloqueo', exact: true }).click()
    await expect(nota).toContainText('solo haya un tren a la vez')
    await page.keyboard.press('Escape')
    await ficha.getByRole('button', { name: 'De control automático' }).click()
    await expect(nota).toContainText('Bloqueo de control automático')
    await nota.getByRole('link', { name: 'Ver en el glosario' }).click()
    await expect(page).toHaveURL(/\/glosario\/bloqueo-de-control-automatico$/)
    await expect(page.getByTestId('pagina-glosario')).toContainText('Bloqueo de control automático')
    // los términos nuevos están en la página, cada uno con su ruta
    for (const id of ['asfa', 'lzb', 'ertms', 'bloqueo-automatico', 'control-de-trafico-centralizado', 'puesto-de-mando', 'proteccion-del-tren']) {
      await page.goto(`/glosario/${id}`)
      await expect(page.getByTestId(`glosario-${id}`)).toHaveAttribute('aria-current', 'true')
    }
  })
})
