import { expect, test, type Page } from '@playwright/test'

// Trenes por tramo y si tienen otro camino en las líneas cargadas (día de referencia: 13 de
// noviembre de 2026). El cálculo es del servidor y viaja en `alternatives.json`, así que estas
// pruebas valen igual con la API y en modo estático.

async function abrirPanel(page: Page) {
  const asa = page.getByRole('button', { name: 'Ampliar el panel' })
  if (await asa.isVisible()) await asa.click() // en móvil, la hoja empieza plegada
}

const estatico = Boolean(process.env.ONIEL_E2E_STATIC)

test.describe('Tramos sin alternativa', () => {
  test('si la API todavía no tiene el análisis, el visor usa la instantánea', async ({ page }) => {
    test.skip(estatico, 'sin API el visor ya lee la instantánea')
    // una API anterior a este apartado: el visor se publica antes de que el servidor se despliegue
    let pedidas = 0
    await page.route('**/api/alternatives*', (route) => {
      pedidas++
      return route.fulfill({ status: 404, contentType: 'application/json', body: '{"detail":"Not Found"}' })
    })
    // se espera a que el visor hable ya con la API: antes de eso leería la instantánea de todos modos
    await page.goto('/')
    await expect(page.getByTestId('recuento-red')).not.toContainText('despertando el servidor')
    await expect(page.getByTestId('recuento-red')).not.toContainText('vista estática')
    await page.goto('/cobertura')
    await abrirPanel(page)
    await expect(page.getByTestId('lista-sin-alternativa').locator('li')).toHaveCount(11 + 20)
    await expect(page.getByTestId('panel-cobertura')).not.toContainText('No se ha podido cargar este apartado')
    await page.goto('/tramo/lav-madrid-sevilla:bif-malaga:majarabique')
    await expect(page.getByTestId('tramo-alternativa')).toContainText('sus 84 trenes no tendrían otro camino')
    expect(pedidas).toBeGreaterThan(0)
  })

  test('el arranque no pide el análisis: llega al abrir un tramo', async ({ page }) => {
    const pedidos: string[] = []
    page.on('request', (r) => {
      if (/alternatives/.test(r.url())) pedidos.push(r.url())
    })
    await page.goto('/')
    await expect(page.locator('.maplibregl-canvas')).toBeVisible()
    await page.waitForTimeout(1_500) // margen para una petición que no debe llegar
    expect(pedidos).toEqual([])
    await page.goto('/tramo/lav-madrid-sevilla:adamuz:cordoba')
    await abrirPanel(page)
    await expect(page.getByTestId('tramo-alternativa')).toBeVisible()
    expect(pedidos.length).toBeGreaterThan(0)
  })

  test('un tramo con otro camino dice cuánto añade, y el desglose va en «Más detalle»', async ({ page }) => {
    await page.goto('/tramo/lav-madrid-sevilla:adamuz:cordoba')
    await abrirPanel(page)
    // lo esencial, a la vista: cuántos trenes, si tienen otro camino y dónde se ha buscado
    await expect(page.getByTestId('tramo-alternativa')).toHaveText(
      'Si este tramo se cortara, sus 113 trenes tendrían otro camino en las líneas que Oniel tiene cargadas. Para los más numerosos (44, entre Madrid-Puerta de Atocha y Sevilla-Santa Justa), 97 km y 1 h 46 min más.',
    )
    const detalle = page.getByTestId('tramo-alternativa-detalle')
    await expect(detalle).toBeHidden()
    await page.getByTestId('mas-detalle').locator('summary').click()
    await expect(detalle).toBeVisible()
    const grupos = detalle.locator('li')
    // los de Málaga, los de Granada y los de Almería son grupos distintos: unos dejan la red
    // cargada en Antequera-Santa Ana y los otros llegan a Granada o siguen hacia Moreda
    await expect(grupos).toHaveCount(11)
    await expect(grupos.first()).toHaveText(
      '44 trenes entre Madrid-Puerta de Atocha y Sevilla-Santa Justa: otro camino por la línea convencional Madrid – Alcázar de San Juan – Córdoba y la línea de alta velocidad Madrid – Sevilla, 97 km y 1 h 46 min más (567,3 km en vez de 470,3).',
    )
    // los desviados por Manzanares ya dan un rodeo: para ellos el otro camino añade poco
    await expect(grupos.nth(2)).toContainText('12 trenes entre Madrid-Puerta de Atocha y Antequera-Santa Ana')
    await expect(grupos.nth(2)).toContainText('7 km y 37 min más')
    // para los de Granada el otro camino, por Moreda, es más corto
    await expect(grupos.nth(4)).toContainText('6 trenes entre Madrid-Puerta de Atocha y Granada')
    await expect(grupos.nth(4)).toContainText('82 km')
    // el detalle dice qué significa y qué no mira el cálculo
    await expect(detalle).toContainText('no hay otro camino en las líneas que Oniel tiene cargadas, no que no exista en la red real')
    await expect(detalle).toContainText('no mira si el tren cabe por él')
    await expect(page.getByTestId('detalle-tramo')).not.toContainText(/criticidad/i)
  })

  test('hacia Sevilla, el tramo dice que sus trenes no tienen otro camino en las líneas cargadas', async ({ page }) => {
    await page.goto('/tramo/lav-madrid-sevilla:bif-malaga:majarabique')
    await abrirPanel(page)
    await expect(page.getByTestId('tramo-alternativa')).toHaveText(
      'Si este tramo se cortara, sus 84 trenes no tendrían otro camino en las líneas que Oniel tiene cargadas. No quiere decir que no exista en la red real.',
    )
    // Iryo también pasa por aquí y sus trenes no están: la ficha lo dice junto al recuento
    await expect(page.getByTestId('tramo-operadores-sin-horarios')).toContainText('Iryo')
    await page.getByTestId('mas-detalle').locator('summary').click()
    const grupos = page.getByTestId('tramo-alternativa-detalle').locator('li')
    await expect(grupos).toHaveCount(7)
    for (const grupo of await grupos.all()) await expect(grupo).toContainText('sin otro camino en las líneas cargadas.')
  })

  test('para un tren desviado, el otro camino puede ser más corto', async ({ page }) => {
    await page.goto('/tramo/manzanares-ciudad-real:almagro:ciudad-real')
    await abrirPanel(page)
    await expect(page.getByTestId('tramo-alternativa')).toHaveText(
      'Si este tramo se cortara, sus 32 trenes tendrían otro camino en las líneas que Oniel tiene cargadas. Para los más numerosos (12, entre Madrid-Puerta de Atocha y Antequera-Santa Ana), 90 km y 1 h 8 min menos.',
    )
  })

  test('la cobertura lista los tramos sin alternativa y pliega los demás', async ({ page }) => {
    await page.goto('/cobertura')
    await abrirPanel(page)
    const apartado = page.getByTestId('tramos-sin-alternativa')
    await expect(page.getByRole('heading', { name: 'Tramos con más trenes y sin alternativa' })).toBeVisible()
    // el alcance, siempre delante: las líneas cargadas, no la red real, y sin los trenes de Iryo
    await expect(page.getByTestId('alternativa-alcance')).toHaveText(
      'Si uno de estos tramos se cortara, sus trenes no tendrían otro camino en las líneas que Oniel tiene cargadas. No quiere decir que no exista en la red real. Faltan los trenes de Iryo, que no publica sus horarios en un formato abierto.',
    )
    // del que más trenes lleva al que menos
    const filas = page.getByTestId('lista-sin-alternativa').locator('li')
    // los dos que llevan a Sevilla, los dos del ramal de Jaén y los siete de Alcázar de San Juan a
    // Albacete, una rama unida al resto por un solo extremo. Granada está unida por los dos lados
    // (la convencional de Moreda y la alta velocidad de Antequera), así que ni sus líneas ni
    // Córdoba – Bifurcación Málaga figuran ya: sus trenes tienen otro camino
    // Con ellos, los veinte de la alta velocidad de Barcelona, que solo comparte con las demás la
    // cabecera de Madrid y cuyos baipases no están cargados: son los que más trenes llevan
    await expect(filas).toHaveCount(11 + 20)
    await expect(filas.nth(0)).toContainText('111 trenes')
    await expect(filas.nth(0)).toContainText('Alta velocidad Madrid – Zaragoza – Barcelona')
    // los dos de Sevilla, con los trenes que no paran en Madrid, quedan entre los de Barcelona
    await expect(filas.nth(11)).toContainText('Bifurcación Málaga-Alta Velocidad – Cambiador de Majarabique')
    await expect(filas.nth(11)).toContainText('84 trenes')
    await expect(filas.nth(14)).toContainText('Cambiador de Majarabique – Sevilla-Santa Justa')
    await expect(filas.nth(14)).toContainText('82 trenes')
    await expect(filas.nth(21)).toContainText('Lleida-Pirineus')
    await expect(filas.nth(21)).toContainText('77 trenes')
    // y los dos del ramal de Jaén, que acaba en una estación término
    await expect(filas.nth(22)).toContainText('Espelúy – Mengíbar-Artichuela')
    await expect(filas.nth(22)).toContainText('26 trenes')
    await expect(filas.nth(23)).toContainText('Mengíbar-Artichuela – Jaén')
    await expect(filas.nth(23)).toContainText('26 trenes')
    // de Alcázar de San Juan a Albacete, hasta que se cargue otra línea que llegue a Albacete
    await expect(filas.nth(24)).toContainText('12 trenes')
    await expect(filas.nth(24)).toContainText('Línea convencional Alcázar de San Juan – Albacete')
    await expect(filas.nth(30)).toContainText('12 trenes')
    await expect(page.getByTestId('lista-sin-alternativa')).not.toContainText('Córdoba – Bifurcación Málaga-Alta Velocidad')
    await expect(page.getByTestId('lista-sin-alternativa')).not.toContainText('Linares-Baeza – Moreda – Granada')
    // entre la estación de Moreda y la bifurcación no pasa ningún tren: no está en ninguna lista
    await expect(apartado).not.toContainText('Moreda – Bifurcación Almería')
    await expect(apartado).toContainText('Trenes del jueves, 12 de noviembre de 2026')
    await expect(apartado).not.toContainText(/criticidad/i)
    // los demás, plegados: 56 tramos con lo que añade su otro camino
    const resto = page.getByTestId('tramos-con-alternativa')
    await expect(resto.locator('summary')).toHaveText('Los otros 56 tramos tienen otro camino')
    await expect(page.getByTestId('lista-con-alternativa')).toBeHidden()
    await resto.locator('summary').click()
    const otros = page.getByTestId('lista-con-alternativa').locator('li')
    await expect(otros).toHaveCount(56)
    // el que más trenes lleva: por él pasan también los que no paran en Madrid
    await expect(otros.first()).toContainText('Córdoba – Bifurcación Málaga-Alta Velocidad')
    await expect(otros.first()).toContainText('135 trenes')
    await expect(otros.first()).toContainText('+340 km · +3 h 2 min')
    await expect(resto).toContainText('no mira si el tren cabe por él')
    // cada fila lleva a la ficha de su tramo
    await filas.nth(0).getByRole('button').click()
    await expect(page).toHaveURL(/\/tramo\/lav-madrid-barcelona:camp-de-tarragona:l-arboc$/)
    await expect(page.getByTestId('detalle-tramo')).toBeVisible()
  })
})
