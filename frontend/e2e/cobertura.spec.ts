import { expect, test } from '@playwright/test'

import { irA } from './navegar.ts'

// «Cobertura y fuentes» es una página propia, sin mapa: lo esencial arriba, las líneas como lista
// enlazada, los operadores con su estado y, al final, todas las fuentes agrupadas por lo que aportan.

test.describe('Cobertura y fuentes, como página', () => {
  test('se abre desde la cabecera, tapa el visor y «Mapa» devuelve a lo que se veía', async ({ page }) => {
    await page.goto('/linea/manzanares-ciudad-real')
    await expect(page.getByTestId('ficha-linea')).toBeVisible()
    await irA(page, 'cobertura')
    await expect(page).toHaveURL(/\/cobertura$/)
    const pagina = page.getByTestId('pagina-cobertura')
    await expect(pagina.getByRole('heading', { level: 1 })).toHaveText('Cobertura y fuentes')
    // el visor queda debajo, fuera de la vista; la cabecera sigue, con el buscador
    await expect(page.locator('#panel')).toBeHidden()
    await expect(page.getByTestId('buscador')).toBeVisible()
    // «Mapa» devuelve a la línea que se estaba viendo
    await irA(page, 'mapa')
    await expect(page).toHaveURL(/\/linea\/manzanares-ciudad-real$/)
    await expect(page.getByTestId('ficha-linea')).toBeVisible()
    await expect(pagina).toHaveCount(0)
  })

  test('lo esencial va arriba: las cuatro cifras, las fechas de los horarios y el índice', async ({ page }) => {
    await page.goto('/cobertura')
    const cifras = page.getByTestId('cobertura-cifras').locator('div')
    await expect(cifras).toHaveCount(4)
    await expect(cifras.nth(0)).toContainText('Líneas cargadas')
    // la primera cifra es el número de líneas de la lista
    await expect(page.getByTestId('cobertura-lineas').getByRole('listitem')).toHaveCount(Number(await cifras.nth(0).locator('dd').innerText()))
    await expect(cifras.nth(1)).toContainText('Kilómetros')
    await expect(cifras.nth(2)).toContainText('Estaciones')
    await expect(cifras.nth(3)).toContainText('Trenes distintos')
    await expect(page.getByTestId('cobertura-validez')).toContainText(/Horarios válidos del \S+, \d+ de \S+ de \d{4} al \S+, \d+ de \S+ de \d{4}\./)
    const indice = page.getByTestId('cobertura-indice').getByRole('link')
    await expect(indice).toHaveText([
      'Líneas cargadas',
      'Operadores de trenes',
      'Interrupciones del servicio',
      'Proyectos',
      'Tramos sin alternativa',
      'Pendiente de cargar',
      'Fuentes y licencias',
    ])
    // cada entrada lleva a su apartado
    await indice.last().click()
    await expect(page.getByRole('heading', { name: 'Fuentes y licencias' })).toBeInViewport()
  })

  test('las líneas van en una lista por tipo y cada una lleva a su línea', async ({ page }) => {
    await page.goto('/cobertura')
    const lineas = page.getByTestId('cobertura-lineas')
    await expect(lineas.getByRole('heading', { level: 3 })).toHaveText([/Alta velocidad/, /Línea convencional/])
    const fila = lineas.getByRole('listitem').filter({ hasText: 'Manzanares – Ciudad Real' })
    await expect(fila).toContainText('64,4 km')
    const enlace = page.getByTestId('cobertura-linea-manzanares-ciudad-real')
    await expect(enlace).toHaveAttribute('href', '/linea/manzanares-ciudad-real')
    await enlace.click()
    await expect(page).toHaveURL(/\/linea\/manzanares-ciudad-real$/)
    await expect(page.getByTestId('pagina-cobertura')).toHaveCount(0)
    await expect(page.getByRole('heading', { name: 'Línea convencional Manzanares – Ciudad Real' })).toBeVisible()
  })

  test('todas las fuentes siguen citadas, agrupadas y plegadas, con su enlace, su licencia y su fecha', async ({ page }) => {
    await page.goto('/cobertura')
    const fuentes = page.getByTestId('cobertura-fuentes')
    const grupos = fuentes.locator('details')
    await expect(grupos.locator('.fuentes-titulo')).toHaveText([
      /^Horarios \d+$/,
      /^Trazado y mapa \d+$/,
      /^Características de las líneas \d+$/,
      /^Interrupciones y proyectos \d+$/,
      /^Glosario \d+$/,
    ])
    // ninguna se queda fuera: las de los grupos suman las registradas
    const registradas = await page.evaluate(async () => ((await (await fetch('/data/coverage.json')).json()) as { sources: unknown[] }).sources.length)
    await expect(fuentes.locator('li')).toHaveCount(registradas) // plegadas no cuentan como elementos de lista accesibles
    await expect(page.getByTestId('pagina-cobertura')).toContainText(`una de estas ${registradas} fuentes`)
    // plegadas de entrada; al abrir un grupo, cada fuente con quién la publica, la licencia y el día de la consulta
    const renfe = page.getByTestId('fuente-renfe-gtfs-av-ld-md')
    await expect(renfe).toBeHidden()
    await page.getByTestId('fuentes-horarios').locator('summary').click()
    await expect(renfe.getByRole('link', { name: /Horarios de alta velocidad, larga distancia y media distancia/ })).toHaveAttribute('href', /^https:\/\/data\.renfe\.com\//)
    await expect(renfe).toContainText('Renfe Viajeros (data.renfe.com)')
    await expect(renfe.getByRole('link', { name: 'CC BY 4.0' })).toBeVisible()
    await expect(renfe).toContainText(/consultada el \d+ de \S+ de \d{4}/)
    await expect(renfe).toContainText('Identificador de la fuente: renfe-gtfs-av-ld-md')
    // cada fuente, en su grupo
    await expect(page.getByTestId('fuentes-trazado').getByTestId('fuente-osm-relation-1254828')).toHaveCount(1)
    await expect(page.getByTestId('fuentes-trazado').getByTestId('fuente-openfreemap')).toHaveCount(1)
    await expect(page.getByTestId('fuentes-anotaciones').getByTestId('fuente-adif-estado-de-la-red')).toHaveCount(1)
    await expect(page.getByTestId('fuentes-glosario').getByTestId('fuente-boe-reglamento-circulacion-ferroviaria')).toHaveCount(1)
    await expect(page.getByTestId('fuentes-lineas').getByTestId('fuente-adif-declaracion-red-2026-mapas')).toHaveCount(1)
  })

  test('un término de la página abre el glosario, y la cabecera devuelve a la página', async ({ page }) => {
    await page.goto('/cobertura')
    await page.getByTestId('pagina-cobertura').getByRole('button', { name: 'Operadores' }).click()
    await page.getByRole('link', { name: 'Ver en el glosario' }).click()
    await expect(page).toHaveURL(/\/glosario\/operador$/)
    await irA(page, 'cobertura')
    await expect(page).toHaveURL(/\/cobertura$/)
    await expect(page.getByTestId('pagina-cobertura')).toBeVisible()
  })
})
