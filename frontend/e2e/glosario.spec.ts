import { expect, test, type Page } from '@playwright/test'

/** En el móvil la ficha vive en la hoja inferior: hay que ampliarla para verla entera. */
async function abrirHoja(page: Page) {
  const asa = page.getByRole('button', { name: 'Ampliar el panel' })
  if (await asa.isVisible()) await asa.click()
}

test.describe('Glosario: cada término a un toque y el glosario completo por URL', () => {
  test('tocar el tipo de punto en la ficha de Urda muestra la definición de PAET y lleva a su entrada', async ({ page }) => {
    await page.goto('/#/nodo/urda')
    const ficha = page.getByTestId('detalle-nodo')
    await expect(ficha).toBeVisible()
    await abrirHoja(page)
    const termino = ficha.getByRole('button', { name: 'Puesto de adelantamiento y estacionamiento' })
    await expect(termino).toHaveAttribute('aria-expanded', 'false')
    // el término se distingue por su subrayado de puntos: si la hoja de estilos se rompe, deja de verse
    await expect(termino).toHaveCSS('text-decoration-style', 'dotted')
    await termino.click()
    const nota = page.getByTestId('termino-nota')
    await expect(nota).toBeVisible()
    await expect(nota).toContainText('PAET')
    await expect(nota).toHaveCSS('position', 'fixed')
    await expect(nota).toContainText('donde un tren puede detenerse para que otro lo adelante')
    await expect(termino).toHaveAttribute('aria-expanded', 'true')
    // la nota cabe entera en la pantalla, también en el móvil
    const caja = (await nota.boundingBox())!
    const pantalla = page.viewportSize()!
    expect(caja.x).toBeGreaterThanOrEqual(0)
    expect(caja.x + caja.width).toBeLessThanOrEqual(pantalla.width)
    expect(caja.y + caja.height).toBeLessThanOrEqual(pantalla.height)
    // de la nota a la entrada completa, que queda en la URL
    await nota.getByRole('link', { name: 'Ver en el glosario' }).click()
    await expect(page).toHaveURL(/#\/glosario\/paet$/)
    await expect(page.getByTestId('glosario-paet')).toHaveAttribute('aria-current', 'true')
    await expect(page.getByTestId('glosario-paet')).toBeInViewport()
    // «Volver» devuelve a la ficha de la que salió el término
    await page.getByTestId('glosario-volver').click()
    await expect(page).toHaveURL(/#\/nodo\/urda$/)
    await expect(page.getByTestId('detalle-nodo')).toBeVisible()
  })

  test('la nota se abre y se cierra con el teclado', async ({ page }) => {
    await page.goto('/#/nodo/urda')
    await expect(page.getByTestId('detalle-nodo')).toBeVisible()
    await abrirHoja(page)
    const termino = page.getByTestId('detalle-nodo').getByRole('button', { name: 'Puesto de adelantamiento y estacionamiento' })
    await termino.focus()
    await page.keyboard.press('Enter')
    await expect(page.getByTestId('termino-nota')).toBeVisible()
    await page.keyboard.press('Escape')
    await expect(page.getByTestId('termino-nota')).toBeHidden()
    await expect(termino).toHaveAttribute('aria-expanded', 'false')
  })

  test('#/glosario/via-unica abre la entrada, y el glosario empieza por los conceptos', async ({ page }) => {
    await page.goto('/#/glosario/via-unica')
    const panel = page.getByTestId('panel-glosario')
    await expect(panel).toBeVisible()
    const entrada = page.getByTestId('glosario-via-unica')
    await expect(entrada).toHaveAttribute('aria-current', 'true')
    await expect(entrada).toBeInViewport()
    await expect(entrada).toContainText('Una sola vía para los dos sentidos')
    // de un término a su concepto, con su ruta y su referencia
    await entrada.getByRole('link', { name: 'Vía única: cómo se cruzan los trenes' }).click()
    await expect(page).toHaveURL(/#\/glosario\/cruces-en-via-unica$/)
    const concepto = page.getByTestId('glosario-cruces-en-via-unica')
    await expect(concepto).toHaveAttribute('aria-current', 'true')
    await expect(concepto).toContainText('Referencia: Reglamento de Circulación Ferroviaria')
    // los conceptos van antes que los términos
    const titulos = await panel.locator('h3').allTextContents()
    expect(titulos.slice(0, 2)).toEqual(['Cómo funciona', 'Términos'])
    // la referencia, con su fuente y su fecha, en el detalle
    await page.getByTestId('mas-detalle').locator('summary').click()
    await expect(page.getByTestId('pie-fuente')).toContainText('boe-reglamento-circulacion-ferroviaria')
    // la dirección sirve para volver
    await page.reload()
    await expect(page.getByTestId('glosario-cruces-en-via-unica')).toHaveAttribute('aria-current', 'true')
  })

  test('se entra desde la cabecera, desde el buscador y desde la vista de la red', async ({ page, isMobile }) => {
    await page.goto('/')
    await expect(page.getByTestId('vista-red')).toBeVisible()
    if (isMobile) {
      // en el móvil la cabecera no lleva botón: el buscador ofrece el glosario sin escribir
      await expect(page.getByTestId('boton-glosario')).toHaveCount(0)
      await page.getByTestId('buscador-abrir').click()
      await page.getByRole('option', { name: /^Glosario/ }).click()
    } else {
      await page.getByTestId('boton-glosario').click()
    }
    await expect(page).toHaveURL(/#\/glosario$/)
    await expect(page.getByRole('heading', { name: 'Glosario' })).toBeVisible()
    await page.getByTestId('glosario-volver').click()
    await expect(page.getByTestId('vista-red')).toBeVisible()
    // el renglón al pie de la vista de la red
    await abrirHoja(page)
    await page.getByTestId('boton-glosario-red').click()
    await expect(page).toHaveURL(/#\/glosario$/)
    // y el buscador encuentra un término por su nombre, sin acentos
    const lupa = page.getByTestId('buscador-abrir')
    if (await lupa.isVisible()) await lupa.click()
    const campo = page.getByRole('combobox', { name: 'Buscar una estación o una línea' })
    await campo.fill('via unica')
    const resultado = page.getByRole('option').first()
    await expect(resultado).toContainText('Vía única')
    await expect(resultado).toContainText('Glosario')
    await campo.press('Enter')
    await expect(page).toHaveURL(/#\/glosario\/via-unica$/)
  })

  test('en un tramo, la etiqueta de cada tren y los datos técnicos son términos', async ({ page }) => {
    await page.goto('/#/tramo/manzanares-ciudad-real:daimiel:almagro')
    const ficha = page.getByTestId('detalle-tramo')
    await expect(ficha).toBeVisible()
    await abrirHoja(page)
    await ficha.getByRole('button', { name: 'Vía única' }).first().click()
    await expect(page.getByTestId('termino-nota')).toContainText('uno espera al otro')
    // abrir otra nota cierra la anterior: solo hay una a la vez
    await page.getByTestId('lista-servicios').getByRole('button', { name: 'estimado' }).first().click()
    const abiertas = page.locator('[data-testid="termino-nota"]:popover-open')
    await expect(abiertas).toHaveCount(1)
    await expect(abiertas).toContainText('Paso estimado')
  })
})
