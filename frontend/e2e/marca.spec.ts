import { expect, test } from '@playwright/test'

// La marca de la cabecera es un enlace a la portada: desde una ficha, desde el glosario y desde
// «Cobertura y fuentes» devuelve a la vista de la red sin recargar la página.
const DESDE = [
  { ruta: '/nodo/ciudad-real', que: 'la ficha de una estación', testId: 'detalle-nodo' },
  { ruta: '/glosario/via-unica', que: 'el glosario', testId: 'pagina-glosario' },
  { ruta: '/cobertura', que: 'la página de cobertura', testId: 'pagina-cobertura' },
]

test.describe('La marca de la cabecera lleva a la portada', () => {
  for (const { ruta, que, testId } of DESDE) {
    test(`desde ${que}, tocar la marca lleva a la vista de la red sin recargar`, async ({ page, baseURL }) => {
      let cargas = 0
      page.on('load', () => cargas++)
      await page.goto(ruta)
      await expect(page.getByTestId(testId)).toBeVisible()
      const marca = page.getByRole('link', { name: 'Oniel, ir al inicio' })
      await expect(marca).toBeVisible()
      await expect(marca).toHaveAttribute('href', '/')
      await marca.click()
      await expect(page).toHaveURL(`${baseURL}/`)
      await expect(page.getByTestId('vista-red')).toBeVisible()
      await expect(page.getByTestId(testId)).toBeHidden()
      expect(cargas).toBe(1)
      // «atrás» devuelve a lo que se estaba viendo
      await page.goBack()
      await expect(page).toHaveURL(`${baseURL}${ruta}`)
      await expect(page.getByTestId(testId)).toBeVisible()
    })
  }

  test('la marca no lleva subrayado ni el azul de los enlaces, enseña el foco y la cabecera ya no lleva lema', async ({ page }) => {
    await page.goto('/')
    const marca = page.getByTestId('marca')
    await expect(marca).toBeVisible()
    // si la hoja de estilos pierde la regla de la marca, vuelve a verse como un enlace corriente
    await expect(marca).toHaveCSS('text-decoration-line', 'none')
    await expect(marca).toHaveCSS('color', 'rgb(23, 32, 30)')
    await marca.focus()
    await expect(marca).toHaveCSS('outline-style', 'solid')
    // la O es un círculo dibujado, del alto de la letra, y la vía le llega por la izquierda
    const o = (await marca.locator('svg').boundingBox())!
    expect(o.width).toBeCloseTo(o.height, 0)
    expect(o.height).toBeGreaterThan(14)
    await expect(marca).toHaveCSS('position', 'relative')
    await expect(page.getByText('Cómo está conectada la red ferroviaria')).toHaveCount(0)
    // lo que es Oniel lo siguen diciendo el título de la página y la vista de la red
    await expect(page).toHaveTitle(/Oniel · Cómo está conectada la red ferroviaria/)
    await expect(page.getByTestId('vista-red')).toContainText('La red ferroviaria española, línea a línea')
  })
})
