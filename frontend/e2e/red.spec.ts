import { expect, test, type Page } from '@playwright/test'

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
  test('sin línea elegida, el panel muestra la vista de la red con sus líneas agrupadas por tipo', async ({ page }) => {
    await page.goto('/')
    await abrirHoja(page)
    const red = page.getByTestId('vista-red')
    await expect(red.getByRole('heading', { name: 'La red ferroviaria española, línea a línea' })).toBeVisible()
    await expect(page.getByTestId('ficha-red')).toHaveText(/^10 líneas · 2\.512 km\s*57 estaciones$/)
    await expect(red).toContainText(/Toca una vía en el mapa o elige una línea de la lista/)
    await expect(red.getByRole('region', { name: 'Alta velocidad' }).locator('.fila-linea')).toHaveText([
      /^Madrid – Sevilla470,5 km · hasta 300 km\/h/,
      /^Córdoba – Málaga96,9 km · hasta 300 km\/h/,
      /^Antequera – Granada114,1 km · hasta 300 km\/h/,
      /^Madrid – Barcelona por Zaragoza627,0 km · hasta 300 km\/h/,
      /^Madrid – Valencia por Cuenca361,0 km · hasta 300 km\/h/,
    ])
    await expect(red.getByRole('region', { name: 'Línea convencional' }).locator('.fila-linea')).toHaveCount(5)
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

  test('el recuento de la cabecera lleva a la vista de la red desde cualquier ficha', async ({ page }) => {
    await page.goto('/tramo/lav-madrid-sevilla:ciudad-real:puertollano')
    await expect(page.getByTestId('detalle-tramo')).toBeVisible()
    await page.getByTestId('recuento-red').click()
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

  test('con muchas líneas la lista se filtra por nombre y la cabecera no crece', async ({ page }) => {
    await page.goto('/')
    await expect(page.getByTestId('vista-red')).toBeVisible()
    const cabecera = page.locator('.cabecera')
    const altoConTres = (await cabecera.boundingBox())!.height
    const anchoConTres = (await page.getByTestId('recuento-red').locator('.pill-texto').boundingBox())!.width

    await conMuchasLineas(page, 60)
    await page.reload()
    await abrirHoja(page)
    await expect(page.getByTestId('recuento-red')).toContainText(/^70 líneas · /)
    expect((await cabecera.boundingBox())!.height).toBe(altoConTres)
    // el recuento solo gana las cifras de más: no enumera
    expect((await page.getByTestId('recuento-red').locator('.pill-texto').boundingBox())!.width).toBeLessThan(anchoConTres + 40)
    const lista = page.getByTestId('lista-lineas')
    await expect(lista.locator('.fila-linea')).toHaveCount(70)
    const filtro = page.getByTestId('filtro-lineas')
    await filtro.fill('alcazar')
    // dos líneas pasan por Alcázar: la de Madrid a Córdoba y la que sale de allí hacia Albacete
    await expect(lista.locator('.fila-linea')).toHaveText([
      /^Madrid – Córdoba por Alcázar de San Juan/,
      /^Alcázar de San Juan – Albacete/,
    ])
    await filtro.fill('zzz')
    await expect(lista.locator('.fila-linea')).toHaveCount(0)
    await expect(lista).toContainText('Ninguna línea coincide con ese nombre.')
    await filtro.fill('destino 59')
    await lista.locator('.fila-linea').first().click()
    await expect(page).toHaveURL(/\/linea\/prueba-59$/)
  })
})
