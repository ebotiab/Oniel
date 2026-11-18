import { expect, test } from '@playwright/test'
import { fraseOtroCamino } from './instantanea.ts'

/** El campo del buscador: en escritorio está a la vista; en el móvil lo despliega la lupa. */
async function abrirBuscador(page: import('@playwright/test').Page) {
  const lupa = page.getByTestId('buscador-abrir')
  if (await lupa.isVisible()) await lupa.click()
  return page.getByRole('combobox', { name: 'Buscar una estación o una línea' })
}

test.describe('La línea Barcelona – Girona – Portbou', () => {
  test('la línea tiene su ficha, con Granollers, Girona, Figueres y Portbou en el esquema', async ({ page }) => {
    await page.goto('/linea/barcelona-girona-portbou')
    await expect(page.getByRole('heading', { name: 'Línea convencional Barcelona – Girona – Portbou' })).toBeVisible()
    await expect(page.locator('body')).toContainText('Une Barcelona con Girona, Figueres y Portbou')
    const esquema = page.getByTestId('esquema')
    for (const estacion of ['Barcelona-Sants', 'Granollers Centre', 'Maçanet-Massanes', 'Girona', 'Figueres', 'Portbou']) {
      await expect(esquema).toContainText(estacion)
    }
  })

  test('el buscador distingue Figueres de Figueres-Vilafant', async ({ page }) => {
    await page.goto('/')
    await expect(page.getByTestId('vista-red')).toBeVisible()
    const campo = await abrirBuscador(page)
    await campo.fill('figueres')
    const opcion = page.getByRole('option').filter({ hasText: /^Figueres(?!-)/ }).filter({ hasText: 'Estación' }).first()
    await expect(opcion).toBeVisible()
    await opcion.click()
    await expect(page).toHaveURL(/\/nodo\/figueres$/)
    const ficha = page.getByTestId('detalle-nodo')
    await expect(ficha.getByRole('heading', { name: 'Figueres', exact: true })).toBeVisible()
    await expect(ficha).toContainText('Figueres-Vilafant')
    // destinos directos del día de referencia
    await expect(ficha).toContainText('Portbou')
  })

  test('Girona es una estación de las dos líneas', async ({ page }) => {
    await page.goto('/nodo/girona')
    const ficha = page.getByTestId('detalle-nodo')
    await expect(ficha.getByRole('heading', { name: 'Girona', exact: true })).toBeVisible()
    await expect(ficha).toContainText('Figueres-Vilafant')
    await expect(ficha).toContainText('Flaçà')
    await expect(ficha).not.toContainText('Línea convencional Girona – Portbou')
  })

  test('Portbou dice que la continuación a Cerbère no está cargada', async ({ page }) => {
    await page.goto('/nodo/portbou')
    const ficha = page.getByTestId('detalle-nodo')
    await expect(ficha.getByRole('heading', { name: 'Portbou' })).toBeVisible()
    await expect(ficha).toContainText('Línea Portbou – Cerbère')
    await expect(ficha).toContainText('no cargada todavía')
  })

  test('de Vilamalla a Figueres hay bloqueo de vía doble sin control centralizado', async ({ page }) => {
    await page.goto('/tramo/barcelona-girona-portbou:vilamalla:figueres')
    await expect(page.getByTestId('detalle-tramo')).toBeVisible()
    const asa = page.getByRole('button', { name: 'Ampliar el panel' })
    if (await asa.isVisible()) await asa.click()
    await expect(page.getByTestId('tramo-vias')).toHaveText('Vía doble')
    await expect(page.getByTestId('tramo-atributo-proteccion_tren')).toHaveText('ASFA')
    await expect(page.getByTestId('tramo-atributo-mando')).toHaveText('Sin control centralizado')
  })

  test('el tramo de Granollers dice si sus trenes tendrían otro camino', async ({ page }) => {
    const id = 'barcelona-girona-portbou:granollers-centre:sant-celoni'
    await page.goto(`/tramo/${id}`)
    await expect(page.getByTestId('tramo-alternativa')).toContainText(fraseOtroCamino(id))
  })

  test('el comparador enseña los dos caminos de Barcelona a Girona y a Figueres', async ({ page }) => {
    const recorridos = page.getByTestId('recorrido')
    await page.goto('/recorridos/barcelona-sants/girona')
    await expect(recorridos).toHaveCount(2)
    await expect(recorridos.nth(0)).toContainText('94,1 km')
    await expect(recorridos.nth(1)).toContainText('100,7 km')
    await expect(recorridos.nth(1).getByTestId('recorrido-trenes')).toContainText(/\d+ trenes directos en el horario del /)

    await page.goto('/recorridos/barcelona-sants/figueres')
    await expect(recorridos).toHaveCount(2)
    await expect(recorridos.nth(0)).toContainText('135,7 km')
    await expect(recorridos.nth(0)).toContainText('Recorre dos líneas')
    await expect(recorridos.nth(1)).toContainText('142,3 km')
  })
})
