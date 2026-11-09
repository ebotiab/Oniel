import { expect, test } from '@playwright/test'

test.describe('Explorar la red', () => {
  test('se abre con el mapa y la línea Madrid–Sevilla', async ({ page }) => {
    await page.goto('/')
    await expect(page).toHaveTitle(/Oniel/)
    await expect(page.getByTestId('mapa')).toBeVisible()
    await expect(page.getByRole('heading', { name: /Línea de alta velocidad Madrid – Sevilla/ })).toBeVisible()
    // el lienzo del mapa se ha creado
    await expect(page.locator('.maplibregl-canvas')).toBeVisible()
    // la cobertura de la versión está a la vista: las dos líneas cargadas
    await expect(page.getByTestId('boton-cobertura')).toContainText('Madrid – Sevilla')
    await expect(page.getByTestId('boton-cobertura')).toContainText('Madrid – Córdoba por Alcázar de San Juan')
  })

  test('seleccionar un tramo en el esquema muestra sus datos y sus trenes', async ({ page }) => {
    await page.goto('/')
    const asa = page.getByRole('button', { name: 'Ampliar el panel' })
    if (await asa.isVisible()) await asa.click() // en móvil, la hoja empieza plegada
    await page.getByTestId('esquema-tramo-5').click() // Ciudad Real – Puertollano
    await expect(page.getByTestId('detalle-tramo')).toBeVisible()
    await expect(page.getByRole('heading', { name: /Ciudad Real/ })).toBeVisible()
    await expect(page.getByRole('heading', { name: /Puertollano/ })).toBeVisible()
    await expect(page.getByText(/Longitud/)).toBeVisible()
    await expect(page.getByTestId('tramo-vias')).toHaveText('Vía doble')
    await expect(page.getByTestId('lista-servicios').locator('li').first()).toBeVisible()
    await expect(page.getByTestId('lista-servicios')).toContainText(/AVE|AVLO|ALVIA|Intercity/)
    await expect(page).toHaveURL(/#\/tramo\/lav-madrid-sevilla:ciudad-real:puertollano/)
  })

  test('el panel permite cambiar a la línea convencional por Alcázar', async ({ page }) => {
    await page.goto('/')
    const asa = page.getByRole('button', { name: 'Ampliar el panel' })
    if (await asa.isVisible()) await asa.click()
    await page.getByTestId('selector-linea-convencional-madrid-alcazar-cordoba').click()
    await expect(page.getByRole('heading', { name: /Línea convencional Madrid – Alcázar de San Juan – Córdoba/ })).toBeVisible()
    await expect(page.getByTestId('esquema-nodo-alcazar-de-san-juan')).toBeVisible()
    await expect(page.getByTestId('esquema-nodo-linares-baeza')).toBeVisible()
    // un tramo de Despeñaperros: vía única y trenes de Media Distancia
    await page.getByTestId('esquema-nodo-santa-cruz-de-mudela').click()
    await expect(page.getByTestId('detalle-nodo')).toBeVisible()
    await page.getByRole('button', { name: 'Santa Cruz de Mudela – Almuradiel-Viso del Marqués' }).click()
    await expect(page.getByTestId('detalle-tramo')).toBeVisible()
    await expect(page.getByTestId('tramo-vias')).toHaveText('Vía única')
    await expect(page.getByTestId('lista-servicios')).toContainText(/MD/)
    await expect(page).toHaveURL(/#\/tramo\/convencional-madrid-alcazar-cordoba:santa-cruz-de-mudela:almuradiel-viso-del-marques/)
  })

  test('seleccionar una estación muestra qué tramos confluyen y qué trenes paran', async ({ page }) => {
    await page.goto('/#/nodo/cordoba')
    await expect(page.getByTestId('detalle-nodo')).toBeVisible()
    await expect(page.getByRole('heading', { name: 'Córdoba' })).toBeVisible()
    await expect(page.getByText(/Tramos que confluyen/)).toBeVisible()
    await expect(page.getByText(/Trenes que paran aquí/)).toBeVisible()
    await expect(page.getByText(/Bifurcación Málaga/).first()).toBeVisible()
    // Córdoba es común a las dos líneas: llega también la convencional desde Rabanales
    await expect(page.getByTestId('nodo-lineas')).toContainText('2 líneas')
    await expect(page.getByRole('button', { name: /Rabanales – Córdoba/ })).toBeVisible()
  })

  test('los puntos de referencia explican qué son con lenguaje neutro', async ({ page }) => {
    await page.goto('/#/nodo/urda')
    await expect(page.getByRole('heading', { name: 'Urda' })).toBeVisible()
    await expect(page.getByText(/Puesto de adelantamiento y estacionamiento/).first()).toBeVisible()
    await expect(page.getByRole('complementary', { name: /Contexto de 2026/ })).toBeVisible()
  })

  test('la cobertura y las fuentes están a un clic', async ({ page }) => {
    await page.goto('/')
    await page.getByTestId('boton-cobertura').click()
    await expect(page.getByTestId('panel-cobertura')).toBeVisible()
    await expect(page.getByText(/Renfe Viajeros/).first()).toBeVisible()
    await expect(page.getByText(/OpenStreetMap/).first()).toBeVisible()
    await expect(page.getByText(/Adif/).first()).toBeVisible()
    await expect(page.getByText(/línea convencional Madrid – Alcázar de San Juan – Córdoba/).first()).toBeVisible()
  })
  test('los rótulos del esquema no se pisan aunque haya nodos muy cercanos', async ({ page }) => {
    await page.goto('/')
    const asa = page.getByRole('button', { name: 'Ampliar el panel' })
    if (await asa.isVisible()) await asa.click()
    for (const [lineId, nodeId] of [
      ['lav-madrid-sevilla', 'majarabique'],
      ['convencional-madrid-alcazar-cordoba', 'rabanales'],
    ] as const) {
      await page.getByTestId(`selector-linea-${lineId}`).click()
      await expect(page.getByTestId(`esquema-nodo-${nodeId}`)).toBeAttached()
      // Cajas de todos los textos de los nodos (nombre y kilómetro); dos no pueden compartir área.
      const boxes = await page
        .getByTestId('esquema')
        .locator('.esquema-nodo text')
        .evaluateAll((els) =>
          els.map((el) => {
            const r = el.getBoundingClientRect()
            return { text: el.textContent ?? '', top: r.top, bottom: r.bottom, left: r.left, right: r.right }
          }),
        )
      expect(boxes.length).toBeGreaterThan(5)
      const overlaps: string[] = []
      for (let i = 0; i < boxes.length; i++) {
        for (let j = i + 1; j < boxes.length; j++) {
          const a = boxes[i]!
          const b = boxes[j]!
          const horizontal = Math.min(a.right, b.right) - Math.max(a.left, b.left)
          const vertical = Math.min(a.bottom, b.bottom) - Math.max(a.top, b.top)
          if (horizontal > 0.5 && vertical > 0.5) overlaps.push(`«${a.text}» y «${b.text}» se pisan ${vertical.toFixed(1)} px`)
        }
      }
      expect(overlaps, `rótulos solapados en ${lineId}`).toEqual([])
    }
  })
})
