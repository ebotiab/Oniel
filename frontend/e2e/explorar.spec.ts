import { expect, test } from '@playwright/test'

import { irA } from './navegar.ts'

test.describe('Explorar la red', () => {
  test('se abre con el mapa y la vista de la red', async ({ page }) => {
    await page.goto('/')
    await expect(page).toHaveTitle(/Oniel/)
    await expect(page.getByTestId('mapa')).toBeVisible()
    await expect(page.getByTestId('vista-red')).toBeVisible()
    // el lienzo del mapa se ha creado
    await expect(page.locator('.maplibregl-canvas')).toBeVisible()
    // la vista de la red dice cuánta hay cargada con un recuento, sin enumerar las líneas
    await expect(page.getByTestId('ficha-red')).toContainText(/^12 líneas · 2\.949 km/)
  })

  test('seleccionar un tramo en el esquema muestra sus datos y sus trenes', async ({ page }) => {
    await page.goto('/linea/lav-madrid-sevilla')
    const asa = page.getByRole('button', { name: 'Ampliar el panel' })
    if (await asa.isVisible()) await asa.click() // en móvil, la hoja empieza plegada
    await page.getByTestId('esquema-tramo-7').click() // Ciudad Real – Puertollano
    await expect(page.getByTestId('detalle-tramo')).toBeVisible()
    await expect(page.getByRole('heading', { name: /Ciudad Real/ })).toBeVisible()
    await expect(page.getByRole('heading', { name: /Puertollano/ })).toBeVisible()
    await expect(page.getByText(/Longitud/)).toBeVisible()
    await expect(page.getByTestId('tramo-tipo')).toHaveText('Alta velocidad')
    await expect(page.getByTestId('tramo-vias')).toHaveText('Vía doble')
    await expect(page.getByTestId('lista-servicios').locator('li').first()).toBeVisible()
    await expect(page.getByTestId('lista-servicios')).toContainText(/AVE|AVLO|ALVIA|Intercity/)
    await expect(page).toHaveURL(/\/tramo\/lav-madrid-sevilla:ciudad-real:puertollano/)
  })

  test('desde la lista de la red se llega a la línea convencional por Alcázar', async ({ page }) => {
    await page.goto('/')
    const asa = page.getByRole('button', { name: 'Ampliar el panel' })
    if (await asa.isVisible()) await asa.click()
    await page.getByTestId('linea-convencional-madrid-alcazar-cordoba').click()
    await expect(page.getByRole('heading', { name: /Línea convencional Madrid – Alcázar de San Juan – Córdoba/ })).toBeVisible()
    await expect(page.getByTestId('esquema-nodo-alcazar-de-san-juan')).toBeVisible()
    await expect(page.getByTestId('esquema-nodo-linares-baeza')).toBeVisible()
    // un tramo de Despeñaperros: vía única y trenes de Media Distancia
    await page.getByTestId('esquema-nodo-santa-cruz-de-mudela').click()
    await expect(page.getByTestId('detalle-nodo')).toBeVisible()
    await page.getByRole('button', { name: 'Santa Cruz de Mudela – Almuradiel-Viso del Marqués' }).click()
    await expect(page.getByTestId('detalle-tramo')).toBeVisible()
    await expect(page.getByTestId('tramo-tipo')).toHaveText('Línea convencional, vía única')
    await expect(page.getByTestId('tramo-vias')).toHaveText('Vía única')
    await expect(page.getByTestId('lista-servicios')).toContainText(/MD/)
    await expect(page).toHaveURL(/\/tramo\/convencional-madrid-alcazar-cordoba:santa-cruz-de-mudela:almuradiel-viso-del-marques/)
  })

  test('la lista lleva a la línea Manzanares – Ciudad Real, de vía única, con los trenes desviados', async ({ page }) => {
    await page.goto('/')
    const asa = page.getByRole('button', { name: 'Ampliar el panel' })
    const movil = await asa.isVisible()
    if (movil) await asa.click()
    // la lista tiene las doce líneas, también en la hoja del móvil, y ya no hay pestañas
    await expect(page.getByTestId('lista-lineas').locator('.fila-linea')).toHaveCount(12)
    await expect(page.getByRole('tab')).toHaveCount(0)
    await page.getByTestId('linea-manzanares-ciudad-real').click()
    await expect(page).toHaveURL(/\/linea\/manzanares-ciudad-real$/)
    await expect(page.getByRole('heading', { name: 'Línea convencional Manzanares – Ciudad Real' })).toBeVisible()
    await expect(page.getByTestId('ficha-linea')).toHaveText(/64,4 km.*hasta 140 km\/h/)
    // el número de línea, el ancho y la electrificación están en el detalle, plegado
    await page.getByTestId('mas-detalle').locator('summary').click()
    await expect(page.getByTestId('linea-detalle')).toHaveText(/Adif.*522.*ibérico \(1\.668 mm\).*3 kV CC/)
    for (const nodo of ['manzanares', 'daimiel', 'almagro', 'ciudad-real']) await expect(page.getByTestId(`esquema-nodo-${nodo}`)).toBeVisible()
    // Daimiel – Almagro: vía única, con los Media Distancia y los Intercity y Alvia que la cruzan sin parar
    // se toca sobre la vía: el centro del grupo cae entre la barra de trenes y su cifra, que con
    // una barra corta (38 trenes frente a los 140 del tramo con más) deja un hueco sin dibujo
    await page.getByTestId('esquema-tramo-2').click({ position: { x: 14, y: 12 } })
    await expect(page.getByTestId('detalle-tramo')).toBeVisible()
    await expect(page.getByTestId('tramo-vias')).toHaveText('Vía única')
    await expect(page).toHaveURL(/\/tramo\/manzanares-ciudad-real:daimiel:almagro/)
    const lista = page.getByTestId('lista-servicios')
    await expect(lista).toContainText(/MD \d{5}/)
    await expect(lista).toContainText(/ALVIA \d{5}/)
    // el Intercity 10270 se explica con kilómetros por las líneas, no en línea recta
    const intercity = lista.locator('li', { hasText: 'Intercity 10270' }).first()
    await expect(intercity).toContainText('Madrid-Atocha → Sevilla-Santa Justa')
    const porque = intercity.locator('.senal')
    await expect(porque).toHaveText('estimado')
    await expect(porque).toHaveAttribute('title', /entra en esta línea por Manzanares.*64 km por la línea y, desde Manzanares, 196 km por esa línea/)
    await expect(porque).not.toHaveAttribute('title', /línea recta/)
  })

  test('Manzanares y Ciudad Real unen la línea nueva con las otras dos', async ({ page }) => {
    await page.goto('/nodo/ciudad-real')
    await expect(page.getByRole('heading', { name: 'Ciudad Real' })).toBeVisible()
    await expect(page.getByTestId('nodo-lineas')).toContainText('2 líneas')
    await expect(page.getByTestId('nodo-lineas')).toContainText(/Madrid – Sevilla\s*alta velocidad\s*Manzanares – Ciudad Real\s*convencional/)
    await expect(page.getByRole('button', { name: 'Almagro – Ciudad Real' })).toBeVisible()
    await expect(page.getByRole('button', { name: 'Ciudad Real – Puertollano' })).toBeVisible()
    await expect(page.getByText(/Línea convencional Ciudad Real–Badajoz hacia Puertollano/)).toBeVisible()
    await page.goto('/nodo/manzanares')
    await expect(page.getByRole('heading', { name: 'Manzanares' })).toBeVisible()
    await expect(page.getByTestId('nodo-lineas')).toContainText('2 líneas')
    await expect(page.getByRole('button', { name: 'Manzanares – Daimiel' })).toBeVisible()
    await expect(page.getByRole('button', { name: 'Manzanares – Valdepeñas' })).toBeVisible()
    // la línea a Ciudad Real ya no es una conexión pendiente
    await expect(page.getByTestId('detalle-nodo').getByText('no cargada todavía')).toHaveCount(0)
  })

  test('la cabecera de la línea es breve y la descripción se despliega por párrafos', async ({ page }) => {
    await page.goto('/linea/lav-madrid-sevilla')
    const asa = page.getByRole('button', { name: 'Ampliar el panel' })
    const movil = await asa.isVisible()
    if (movil) await asa.click()
    // a la vista, lo que entiende cualquiera: cuánto mide y a qué velocidad se circula
    await expect(page.getByTestId('ficha-linea')).toHaveText(/^470,5 km\s*hasta 300 km\/h$/)
    if (movil) return // la hoja compacta no lleva frase de entrada ni notas
    // una frase de entrada a la vista; el resto, plegado por párrafos
    await expect(page.getByTestId('linea-entrada')).toContainText(/^Primera línea de alta velocidad de España/)
    const resto = page.getByText(/Es de vía doble en todo su recorrido/)
    await expect(resto).toBeHidden()
    await page.getByTestId('mas-detalle').locator('summary').click()
    await expect(resto).toBeVisible()
    // una sola nota bajo el esquema, y el rótulo de la columna de barras
    await expect(page.getByTestId('nota-esquema')).toContainText(/Toca una estación o un tramo/)
    await expect(page.getByTestId('esquema-rotulo-trenes')).toHaveText(/^trenes el \d+ [a-z]+$/)
    await expect(page.getByText(/Las barras cuentan los trenes/)).toHaveCount(1)
  })

  test('seleccionar una estación muestra qué tramos salen de ella y qué trenes paran', async ({ page }) => {
    await page.goto('/nodo/cordoba')
    await expect(page.getByTestId('detalle-nodo')).toBeVisible()
    await expect(page.getByRole('heading', { name: 'Córdoba' })).toBeVisible()
    await expect(page.getByText(/Tramos que salen de aquí/)).toBeVisible()
    await expect(page.getByText(/Trenes que paran aquí/)).toBeVisible()
    await expect(page.getByText(/Bifurcación Málaga/).first()).toBeVisible()
    // Córdoba es común a las dos líneas: llega también la convencional desde Rabanales
    await expect(page.getByTestId('nodo-lineas')).toContainText('2 líneas')
    await expect(page.getByRole('button', { name: /Rabanales – Córdoba/ })).toBeVisible()
  })

  test('los puntos de referencia explican qué son con lenguaje neutro', async ({ page }) => {
    await page.goto('/nodo/urda')
    await expect(page.getByRole('heading', { name: 'Urda' })).toBeVisible()
    await expect(page.getByText(/Puesto de adelantamiento y estacionamiento/).first()).toBeVisible()
    await expect(page.getByRole('complementary', { name: /Contexto de 2026/ })).toBeVisible()
  })

  test('la cobertura y las fuentes están a un clic', async ({ page }) => {
    await page.goto('/')
    await irA(page, 'cobertura')
    // Se busca dentro de la página: «OpenStreetMap» está también en la atribución del mapa.
    const cobertura = page.getByTestId('pagina-cobertura')
    await expect(cobertura).toBeVisible()
    await expect(cobertura.getByText(/Renfe Viajeros/).first()).toBeVisible()
    await expect(cobertura.getByText(/Adif/).first()).toBeVisible()
    await expect(cobertura.getByTestId('cobertura-lineas')).toContainText('Madrid – Alcázar de San Juan – Córdoba')
    await expect(cobertura.getByTestId('cobertura-lineas')).toContainText('Manzanares – Ciudad Real')
    // las fuentes van plegadas por lo que aportan
    await cobertura.getByTestId('fuentes-trazado').locator('summary').click()
    await expect(cobertura.getByText(/OpenStreetMap/).first()).toBeVisible()
  })

  test('los rótulos del esquema no se pisan aunque haya nodos muy cercanos', async ({ page }) => {
    await page.goto('/')
    const asa = page.getByRole('button', { name: 'Ampliar el panel' })
    if (await asa.isVisible()) await asa.click()
    for (const [lineId, nodeId] of [
      ['lav-madrid-sevilla', 'majarabique'],
      ['convencional-madrid-alcazar-cordoba', 'rabanales'],
      ['manzanares-ciudad-real', 'almagro'],
    ] as const) {
      await page.goto(`/linea/${lineId}`)
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
      expect(boxes.length).toBeGreaterThan(3) // la línea más corta tiene cuatro nodos
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
