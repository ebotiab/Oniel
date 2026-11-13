import { expect, test, type Page } from '@playwright/test'

import { irA } from './navegar.ts'

/** En el móvil la hoja empieza plegada: se amplía para ver la lista entera. */
async function abrirHoja(page: Page) {
  const asa = page.getByRole('button', { name: 'Ampliar el panel' })
  if (await asa.isVisible()) await asa.click()
}

/** Una red con muchas líneas: a las tres cargadas se les añaden copias con otro nombre, sin trazado. */
async function conMuchasLineas(page: Page, extra: number) {
  await page.route(/\/(data\/index\.json|api\/lines)$/, async (route) => {
    const res = await route.fetch()
    const net = await res.json()
    // las copias heredan la zona de su original: las dos son de Andalucía
    const [lav, conv] = [net.lines[0], net.lines[1]]
    for (let i = 0; i < extra; i++) {
      const base = i % 3 === 0 ? lav : conv
      const tipo = i % 3 === 0 ? 'de alta velocidad' : 'convencional'
      net.lines.push({ ...base, id: `prueba-${i}`, name: `Línea ${tipo} Origen ${i} – Destino ${i}`, length_km: 100 + i })
    }
    await route.fulfill({ response: res, json: net })
  })
}

test.describe('Elegir línea sin pestañas', () => {
  test('sin línea elegida, el panel muestra la vista de la red con sus líneas agrupadas por zonas', async ({ page }) => {
    await page.goto('/')
    await abrirHoja(page)
    const red = page.getByTestId('vista-red')
    await expect(red.getByRole('heading', { name: 'La red ferroviaria española, línea a línea' })).toBeVisible()
    await expect(page.getByTestId('ficha-red')).toHaveText(/^11 líneas · 2\.879 km\s*61 estaciones$/)
    await expect(red).toContainText(/Toca una vía en el mapa o elige una línea de la lista/)
    // las zonas van de norte a sur, y solo las que tienen alguna línea; con once líneas están todas abiertas
    await expect(red.locator('.zona-cabecera')).toHaveText([/^›Cataluña1 línea$/, /^›Comunidad Valenciana y Murcia2 líneas$/, /^›Madrid y Castilla-La Mancha2 líneas$/, /^›Andalucía6 líneas$/])
    for (const cabecera of await red.locator('.zona-cabecera').all()) await expect(cabecera).toHaveAttribute('aria-expanded', 'true')
    await expect(red.getByRole('region', { name: 'Cataluña' }).locator('.fila-linea')).toHaveText([/^Alta velocidad: Madrid – Barcelona por Zaragoza627 km$/])
    await expect(red.getByRole('region', { name: 'Comunidad Valenciana y Murcia' }).locator('.fila-linea')).toHaveText([
      /^Alta velocidad: Madrid – Valencia por Cuenca397 km$/,
      /^Alta velocidad: Albacete – Alicante238 km$/,
    ])
    await expect(red.getByRole('region', { name: 'Madrid y Castilla-La Mancha' }).locator('.fila-linea')).toHaveText([
      /^Línea convencional: Alcázar de San Juan – Albacete131 km$/,
      /^Línea convencional: Manzanares – Ciudad Real64 km$/,
    ])
    // dentro de la zona, primero la alta velocidad y, en cada tipo, de la más larga a la más corta;
    // el tramo sin circulación va bajo el nombre
    await expect(red.getByRole('region', { name: 'Andalucía' }).locator('.fila-linea')).toHaveText([
      /^Alta velocidad: Madrid – Sevilla471 kmun tramo sin circulación$/,
      /^Alta velocidad: Córdoba – Málaga155 km$/,
      /^Alta velocidad: Antequera – Granada114 km$/,
      /^Línea convencional: Madrid – Córdoba por Alcázar de San Juan441 kmun tramo sin circulación$/,
      /^Línea convencional: Linares-Baeza – Granada por Moreda174 km$/,
      /^Línea convencional: Espelúy – Jaén33 kmun tramo sin circulación$/,
    ])
    // el tipo de vía ya no agrupa: lo dice la muestra de cada fila, con su clave sobre las zonas
    await expect(page.getByTestId('clave-lineas')).toHaveText('Alta velocidadLínea convencional')
    // una zona se pliega y dice entonces sus ciudades con estación cargada y la señal de sus líneas
    const andalucia = red.getByRole('region', { name: 'Andalucía' })
    await andalucia.locator('.zona-cabecera').click()
    await expect(andalucia.locator('.fila-linea')).toHaveCount(0)
    await expect(andalucia.locator('.zona-detalle')).toHaveText('Sevilla, Córdoba, Málaga, Granada, Jaén3 líneas con un tramo sin circulación')
    await andalucia.locator('.zona-cabecera').click()
    await expect(andalucia.locator('.fila-linea')).toHaveCount(6)
    // no arranca en ninguna línea: ni esquema ni pestañas, y con ocho líneas aparece ya el filtro de la lista
    await expect(page.getByTestId('esquema')).toHaveCount(0)
    await expect(page.getByRole('tab')).toHaveCount(0)
    await expect(page.getByTestId('filtro-lineas')).toBeVisible()
    await expect(page).toHaveURL(/\/$/)
  })

  test('se cambia de línea desde la lista: «Toda la red» vuelve a ella', async ({ page }) => {
    await page.goto('/')
    await abrirHoja(page)
    await page.getByTestId('linea-lav-madrid-sevilla').click()
    await expect(page).toHaveURL(/\/linea\/lav-madrid-sevilla$/)
    await expect(page.getByRole('heading', { name: 'Línea de alta velocidad Madrid – Sevilla' })).toBeVisible()
    await page.getByRole('button', { name: '← Toda la red' }).click()
    await expect(page).toHaveURL(/\/$/)
    await page.getByTestId('linea-manzanares-ciudad-real').click()
    await expect(page).toHaveURL(/\/linea\/manzanares-ciudad-real$/)
    await expect(page.getByRole('heading', { name: 'Línea convencional Manzanares – Ciudad Real' })).toBeVisible()
    await expect(page.getByTestId('esquema-nodo-almagro')).toBeAttached()
  })

  test('cada línea tiene su URL, y una línea que no existe lleva a la vista de la red', async ({ page }) => {
    await page.goto('/linea/convencional-madrid-alcazar-cordoba')
    await expect(page.getByRole('heading', { name: /Línea convencional Madrid – Alcázar de San Juan – Córdoba/ })).toBeVisible()
    await expect(page.getByTestId('vista-red')).toHaveCount(0)
    await page.goto('/linea/no-existe')
    await page.reload()
    await expect(page.getByTestId('vista-red')).toBeVisible()
  })

  test('«Mapa» y la marca de la cabecera llevan a la vista de la red desde cualquier ficha', async ({ page }) => {
    await page.goto('/tramo/lav-madrid-sevilla:ciudad-real:puertollano')
    await expect(page.getByTestId('detalle-tramo')).toBeVisible()
    await irA(page, 'mapa')
    await expect(page.getByTestId('vista-red')).toBeVisible()
    await expect(page).toHaveURL(/\/$/)
    await page.goto('/nodo/ciudad-real')
    await expect(page.getByTestId('detalle-nodo')).toBeVisible()
    await page.getByTestId('marca').click()
    await expect(page.getByTestId('vista-red')).toBeVisible()
    await expect(page).toHaveURL(/\/$/)
  })

  test('una estación común a dos líneas deja saltar a cada una', async ({ page }) => {
    await page.goto('/nodo/ciudad-real')
    const lineas = page.getByTestId('nodo-lineas')
    await expect(lineas).toContainText('2 líneas')
    await expect(lineas.getByRole('button')).toHaveText(['Madrid – Sevilla', 'Manzanares – Ciudad Real'])
    await page.getByTestId('nodo-linea-manzanares-ciudad-real').click()
    await expect(page).toHaveURL(/\/linea\/manzanares-ciudad-real$/)
    await expect(page.getByRole('heading', { name: 'Línea convencional Manzanares – Ciudad Real' })).toBeVisible()
  })

  test('con muchas líneas las zonas empiezan plegadas, la lista se filtra y la cabecera no crece', async ({ page }) => {
    await page.goto('/')
    await expect(page.getByTestId('vista-red')).toBeVisible()
    const cabecera = page.locator('.cabecera')
    const altoConTres = (await cabecera.boundingBox())!.height

    await conMuchasLineas(page, 60)
    await page.reload()
    await abrirHoja(page)
    await expect(page.getByTestId('ficha-red')).toContainText(/^71 líneas · /)
    // la cabecera no enumera las líneas ni las cuenta: mide lo mismo con once que con setenta y una
    expect((await cabecera.boundingBox())!.height).toBe(altoConTres)
    const lista = page.getByTestId('lista-lineas')
    // con más de doce líneas la lista es un índice de zonas: tres renglones, ninguna línea a la vista
    await expect(lista.locator('.zona-cabecera')).toHaveText([/^›Cataluña1 línea/, /^›Comunidad Valenciana y Murcia2 líneas/, /^›Madrid y Castilla-La Mancha2 líneas/, /^›Andalucía66 líneas/])
    await expect(lista.locator('.fila-linea')).toHaveCount(0)
    // plegar no esconde un corte
    await expect(page.getByTestId('zona-andalucia').locator('.zona-detalle')).toContainText('3 líneas con un tramo sin circulación')
    await page.getByTestId('zona-andalucia').locator('.zona-cabecera').click()
    await expect(lista.locator('.fila-linea')).toHaveCount(66)
    const filtro = page.getByTestId('filtro-lineas')
    await filtro.fill('alcazar')
    // dos líneas llevan Alcázar en el nombre; filtrando, sus zonas están abiertas
    await expect(lista.locator('.fila-linea')).toHaveText([/Alcázar de San Juan – Albacete/, /Madrid – Córdoba por Alcázar de San Juan/])
    // el filtro busca también en las estaciones por las que pasa cada línea, sin acentos
    await filtro.fill('lleida')
    await expect(lista.locator('.fila-linea')).toHaveText([/Madrid – Barcelona por Zaragoza627 kmpasa por Lleida-Pirineus$/])
    await filtro.fill('almagro')
    await expect(lista.locator('.fila-linea')).toHaveText([/Manzanares – Ciudad Real64 kmpasa por Almagro$/])
    await filtro.fill('zzz')
    await expect(lista.locator('.fila-linea')).toHaveCount(0)
    await expect(lista).toContainText('Ninguna línea coincide.')
    await filtro.fill('destino 59')
    await lista.locator('.fila-linea').first().click()
    await expect(page).toHaveURL(/\/linea\/prueba-59$/)
  })

  test('al pasar por una línea o por una zona de la lista, el mapa las resalta', async ({ page, isMobile }) => {
    test.skip(isMobile, 'en el móvil no hay cursor que pase por encima')
    await page.goto('/')
    const mapa = page.getByTestId('mapa')
    await expect(page.locator('.maplibregl-canvas')).toBeVisible()
    await expect(mapa).not.toHaveAttribute('data-lineas-resaltadas')
    // una línea se resalta con sus baipases, que son parte de ella
    await page.getByTestId('linea-lav-madrid-barcelona').hover()
    await expect(mapa).toHaveAttribute('data-lineas-resaltadas', 'lav-madrid-barcelona|baipas-zaragoza|baipas-lleida')
    await page.getByTestId('zona-madrid-castilla-la-mancha').locator('.zona-cabecera').hover()
    await expect(mapa).toHaveAttribute('data-lineas-resaltadas', /^(manzanares-ciudad-real\|alcazar-albacete|alcazar-albacete\|manzanares-ciudad-real)$/)
    await page.getByTestId('ficha-red').hover()
    await expect(mapa).not.toHaveAttribute('data-lineas-resaltadas')
    // al elegir una línea no queda nada resaltado, ni al volver a la red
    await page.getByTestId('linea-espeluy-jaen').click()
    await expect(page).toHaveURL(/\/linea\/espeluy-jaen$/)
    await expect(mapa).not.toHaveAttribute('data-lineas-resaltadas')
    await page.getByTestId('ficha-linea').hover()
    await page.getByRole('button', { name: '← Toda la red' }).click()
    await expect(page.getByTestId('vista-red')).toBeVisible()
    await expect(mapa).not.toHaveAttribute('data-lineas-resaltadas')
  })
})
