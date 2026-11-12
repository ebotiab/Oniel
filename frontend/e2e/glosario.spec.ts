import { expect, test, type Page } from '@playwright/test'

/** En el móvil la ficha vive en la hoja inferior: hay que ampliarla para verla entera. */
async function abrirHoja(page: Page) {
  const asa = page.getByRole('button', { name: 'Ampliar el panel' })
  if (await asa.isVisible()) await asa.click()
}

test.describe('Glosario: cada término a un toque y el glosario como página propia, por URL', () => {
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
    // la página tapa el visor: ni el mapa ni el panel quedan a la vista
    await expect(page.getByTestId('pagina-glosario')).toBeVisible()
    await expect(page.locator('#panel')).toBeHidden()
    // «Volver al mapa» devuelve a la ficha de la que salió el término
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

  test('#/glosario/via-unica abre la palabra, y de ella se llega a su concepto, con su dibujo y su referencia', async ({ page }) => {
    await page.goto('/#/glosario/via-unica')
    const pagina = page.getByTestId('pagina-glosario')
    await expect(pagina).toBeVisible()
    const entrada = page.getByTestId('glosario-via-unica')
    await expect(entrada).toHaveAttribute('aria-current', 'true')
    await expect(entrada).toBeInViewport()
    await expect(entrada).toContainText('Una sola vía para los dos sentidos')
    // de un término a su concepto, con su ruta
    await entrada.getByRole('link', { name: 'Vía única: cómo se cruzan los trenes' }).click()
    await expect(page).toHaveURL(/#\/glosario\/cruces-en-via-unica$/)
    const concepto = page.getByTestId('glosario-cruces-en-via-unica')
    await expect(concepto).toHaveAttribute('aria-current', 'true')
    await expect(concepto).toBeInViewport()
    // el dibujo va por pasos: una viñeta por frase, y cada viñeta se ve
    const pasos = concepto.locator('.glosario-pasos > li')
    await expect(pasos).toHaveCount(3)
    await expect(pasos.nth(1)).toContainText('se detiene y espera')
    for (const dibujo of await pasos.locator('svg').all()) {
      const caja = (await dibujo.boundingBox())!
      expect(caja.width).toBeGreaterThan(200)
      expect(caja.height).toBeGreaterThan(40)
    }
    // la referencia sigue citada, discreta, y su fuente y su fecha están en el detalle
    await expect(concepto).toContainText('Referencia: Reglamento de Circulación Ferroviaria')
    await page.getByTestId('mas-detalle').locator('summary').click()
    await expect(page.getByTestId('pie-fuente')).toContainText('boe-reglamento-circulacion-ferroviaria')
    // la dirección sirve para volver
    await page.reload()
    await expect(page.getByTestId('glosario-cruces-en-via-unica')).toHaveAttribute('aria-current', 'true')
  })

  test('la página abre con el índice de los conceptos, todos con dibujo, y cabe en la pantalla', async ({ page }) => {
    await page.goto('/#/glosario')
    const pagina = page.getByTestId('pagina-glosario')
    await expect(page.getByRole('heading', { level: 1, name: 'Glosario' })).toBeVisible()
    // si la hoja de estilos se rompe, la página deja de tapar el visor
    await expect(pagina).toHaveCSS('position', 'absolute')
    const indice = page.getByTestId('glosario-indice')
    await expect(indice.getByRole('link')).toHaveText([
      'Cómo se separan los trenes',
      'Vía única',
      'Marcha a la vista',
      'Quién dirige la circulación',
      'Sistemas que vigilan al tren',
      'Palabras, de la A a la Z',
    ])
    // cada concepto lleva al menos una viñeta, y cada frase la suya
    for (const concepto of await pagina.locator('.glosario-concepto').all()) {
      const pasos = concepto.locator('.glosario-pasos > li')
      expect(await pasos.count()).toBeGreaterThan(0)
      await expect(pasos.locator('svg')).toHaveCount(await pasos.count())
    }
    // nada se sale por los lados, tampoco en el móvil
    const ancho = await pagina.evaluate((el) => [el.scrollWidth, el.clientWidth])
    expect(ancho[0]).toBeLessThanOrEqual(ancho[1]!)
    // del índice a un concepto, que queda en la URL
    await indice.getByRole('link', { name: 'Marcha a la vista' }).click()
    await expect(page).toHaveURL(/#\/glosario\/marcha-a-la-vista$/)
    await expect(page.getByTestId('glosario-marcha-a-la-vista')).toBeInViewport()
    await indice.getByRole('link', { name: 'Palabras, de la A a la Z' }).click()
    await expect(page.getByRole('heading', { name: 'Palabras' })).toBeInViewport()
  })

  test('las palabras se filtran sin acentos, por el nombre o por la definición', async ({ page }) => {
    await page.goto('/#/glosario')
    const palabras = page.locator('.glosario-palabra')
    const todas = await palabras.count()
    expect(todas).toBeGreaterThan(20)
    const filtro = page.getByRole('searchbox', { name: 'Filtrar palabras' })
    await filtro.fill('via unica')
    await expect(page.getByTestId('glosario-via-unica')).toBeVisible()
    expect(await palabras.count()).toBeLessThan(todas)
    // «ibérico» no está en ningún nombre: lo encuentra en las definiciones
    await filtro.fill('iberico')
    await expect(page.getByTestId('glosario-ancho-de-via')).toBeVisible()
    await expect(page.getByTestId('glosario-via-unica')).toHaveCount(0)
    await filtro.fill('zzz')
    await expect(page.getByTestId('glosario-sin-palabras')).toContainText('Ninguna palabra coincide')
    await filtro.fill('')
    await expect(palabras).toHaveCount(todas)
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
    await expect(page.getByRole('heading', { level: 1, name: 'Glosario' })).toBeVisible()
    await page.getByTestId('glosario-volver').click()
    await expect(page.getByTestId('vista-red')).toBeVisible()
    // el renglón al pie de la vista de la red
    await abrirHoja(page)
    await page.getByTestId('boton-glosario-red').click()
    await expect(page).toHaveURL(/#\/glosario$/)
    await page.getByTestId('glosario-volver').click()
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
