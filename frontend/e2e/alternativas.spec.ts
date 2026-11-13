import { expect, test, type Page } from '@playwright/test'

// Trenes por tramo y si tienen otro camino en las líneas cargadas (día de referencia: 13 de
// noviembre de 2026). El cálculo es del servidor y viaja en `alternatives.json`, así que estas
// pruebas valen igual con la API y en modo estático.

async function abrirPanel(page: Page) {
  const asa = page.getByRole('button', { name: 'Ampliar el panel' })
  if (await asa.isVisible()) await asa.click() // en móvil, la hoja empieza plegada
}

const estatico = Boolean(process.env.ONIEL_E2E_STATIC)

test.describe('Tramos sin otro camino', () => {
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
    await expect(page.locator('.cabecera')).toHaveAttribute('data-estado', 'disponible')
    await page.goto('/sin-otro-camino')
    await expect(page.getByTestId('lista-sin-alternativa').locator('> li')).toHaveCount(6)
    await expect(page.getByTestId('vista-sin-otro-camino')).not.toContainText('No se ha podido cargar esta vista')
    await page.goto('/tramo/lav-madrid-sevilla:bif-malaga:majarabique')
    await expect(page.getByTestId('tramo-alternativa')).toContainText('sus 83 trenes no tendrían otro camino')
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
      'Si este tramo se cortara, sus 118 trenes tendrían otro camino en las líneas que Oniel tiene cargadas. Para los más numerosos (41, entre Madrid-Puerta de Atocha y Sevilla-Santa Justa), 97 km y 1 h 46 min más.',
    )
    const detalle = page.getByTestId('tramo-alternativa-detalle')
    await expect(detalle).toBeHidden()
    await page.getByTestId('mas-detalle').locator('summary').click()
    await expect(detalle).toBeVisible()
    const grupos = detalle.locator('li')
    // los de Málaga, los de Algeciras, los de Granada y los de Almería son grupos distintos: unos
    // llegan a Málaga, otros dejan la red cargada en Antequera-Santa Ana y los demás llegan a
    // Granada o siguen hacia Moreda
    await expect(grupos).toHaveCount(13)
    await expect(grupos.first()).toHaveText(
      '41 trenes entre Madrid-Puerta de Atocha y Sevilla-Santa Justa: otro camino por la línea convencional Madrid – Alcázar de San Juan – Córdoba y la línea de alta velocidad Madrid – Sevilla, 97 km y 1 h 46 min más (567,3 km en vez de 470,3).',
    )
    // los desviados por Manzanares ya dan un rodeo: para ellos el otro camino añade poco
    await expect(grupos.nth(2)).toContainText('10 trenes entre Madrid-Puerta de Atocha y Málaga-María Zambrano')
    await expect(grupos.nth(2)).toContainText('7 km y 38 min más')
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
      'Si este tramo se cortara, sus 83 trenes no tendrían otro camino en las líneas que Oniel tiene cargadas. No quiere decir que no exista en la red real.',
    )
    // Iryo también pasa por aquí y sus trenes no están: la ficha lo dice junto al recuento
    await expect(page.getByTestId('tramo-operadores-sin-horarios')).toContainText('Iryo')
    await page.getByTestId('mas-detalle').locator('summary').click()
    const grupos = page.getByTestId('tramo-alternativa-detalle').locator('li')
    await expect(grupos).toHaveCount(8)
    for (const grupo of await grupos.all()) await expect(grupo).toContainText('sin otro camino en las líneas cargadas.')
  })

  test('para un tren desviado, el otro camino puede ser más corto', async ({ page }) => {
    await page.goto('/tramo/manzanares-ciudad-real:almagro:ciudad-real')
    await abrirPanel(page)
    await expect(page.getByTestId('tramo-alternativa')).toHaveText(
      'Si este tramo se cortara, sus 32 trenes tendrían otro camino en las líneas que Oniel tiene cargadas. Para los más numerosos (10, entre Madrid-Puerta de Atocha y Málaga-María Zambrano), 90 km y 1 h 7 min menos.',
    )
  })

  test('«Tramos sin otro camino» tiene su vista: un renglón por línea y los demás tramos, plegados', async ({ page }) => {
    await page.goto('/sin-otro-camino')
    const vista = page.getByTestId('vista-sin-otro-camino')
    await expect(vista.getByRole('heading', { name: 'Tramos sin otro camino' })).toBeVisible()
    // el alcance, siempre delante: las líneas cargadas, no la red real
    await expect(page.getByTestId('alternativa-alcance')).toHaveText(
      'Si uno de estos tramos se cortara, sus trenes no tendrían por dónde ir en las líneas que Oniel tiene cargadas. No quiere decir que no exista otro camino en la red real.',
    )
    await expect(page.getByTestId('sin-camino-resumen')).toHaveText('Son 41 de los 121 tramos con trenes, en 7 líneas. En el mapa, lo demás va atenuado.')
    // y sin los trenes de Iryo
    await expect(page.getByTestId('sin-camino-faltan')).toHaveText('Faltan los trenes de Iryo, que no publica sus horarios en un formato abierto.')
    // una línea por renglón, de la que deja a más trenes sin otro camino a la que menos
    const lineas = page.getByTestId('lista-sin-alternativa').locator('> li')
    await expect(lineas).toHaveCount(7)
    const linea = (nombre: string) => lineas.filter({ hasText: nombre })
    // quince de los veinte de la alta velocidad de Barcelona, que solo comparte con las demás la cabecera de
    // Madrid: son los que más trenes llevan. Los cinco de Zaragoza-Delicias y Lleida-Pirineus tienen el baipás
    await expect(lineas.nth(0)).toContainText('Madrid – Barcelona por Zaragoza')
    await expect(lineas.nth(0)).toContainText('15 de sus 20 tramos')
    await expect(lineas.nth(0)).toContainText('de 73 a 108 trenes')
    // de la alta velocidad de Madrid a Valencia, los dos primeros, de Madrid-Chamartín a la bifurcación de Torrejón
    // de Velasco (a Chamartín solo llega esta línea), y los cuatro últimos, de la bifurcación de Albacete a
    // Valencia: entre las dos bifurcaciones el otro camino es el de Alcázar de San Juan y Albacete
    await expect(linea('Madrid – Valencia por Cuenca')).toContainText('6 de sus 14 tramos')
    await expect(linea('Madrid – Valencia por Cuenca')).toContainText('de 42 a 74 trenes')
    // y los siete de la de Albacete a Alicante que quedan al sur de Albacete
    await expect(linea('Albacete – Alicante')).toContainText('7 de sus 9 tramos')
    await expect(linea('Albacete – Alicante')).toContainText('de 36 a 56 trenes')
    // la de Madrid a Valladolid entera: es la única cargada al norte de Madrid
    await expect(linea('Madrid – Valladolid por Segovia')).toContainText('Toda la línea, 5 tramos')
    await expect(linea('Madrid – Valladolid por Segovia')).toContainText('de 81 a 122 trenes')
    // los dos que llevan a Sevilla desde la bifurcación de Málaga
    await expect(linea('Madrid – Sevilla')).toContainText('2 de sus 13 tramos')
    await expect(linea('Madrid – Sevilla')).toContainText('de 81 a 83 trenes')
    // los cuatro de Antequera-Santa Ana a Málaga: a Málaga solo llega esa línea
    await expect(linea('Córdoba – Málaga')).toContainText('4 de sus 8 tramos')
    await expect(linea('Córdoba – Málaga')).toContainText('de 57 a 63 trenes')
    // el ramal de Jaén, que acaba en una estación término
    await expect(linea('Espelúy – Jaén')).toContainText('Toda la línea, 2 tramos')
    await expect(linea('Espelúy – Jaén')).toContainText('26 trenes')
    // de Alcázar de San Juan a Albacete ya no figura: desde que está cargada la alta velocidad por Cuenca,
    // Albacete tiene dos caminos
    await expect(page.getByTestId('lista-sin-alternativa')).not.toContainText('Alcázar de San Juan – Albacete')
    // Granada está unida por los dos lados (la convencional de Moreda y la alta velocidad de Antequera):
    // sus líneas no figuran
    await expect(page.getByTestId('lista-sin-alternativa')).not.toContainText('Granada')
    await expect(vista).toContainText('Trenes del viernes, 13 de noviembre de 2026')
    await expect(vista).not.toContainText(/criticidad/i)
    // el mapa atenúa el resto de la red; mientras no se mira nada, no hay nada en azul
    await expect(page.getByTestId('mapa')).not.toHaveAttribute('data-recorrido-elegido')

    // los demás, plegados: 80 tramos con lo que añade su otro camino, los dos baipases entre ellos
    const resto = page.getByTestId('tramos-con-alternativa')
    await expect(resto.locator('summary')).toHaveText('Los otros 80 tramos tienen otro camino')
    await expect(page.getByTestId('lista-con-alternativa')).toBeHidden()
    await resto.locator('summary').click()
    const otros = page.getByTestId('lista-con-alternativa').locator('li')
    await expect(otros).toHaveCount(80)
    // el que más trenes lleva: por él pasan también los que no paran en Madrid
    await expect(otros.first()).toContainText('Córdoba – Bifurcación Málaga-Alta Velocidad')
    await expect(otros.first()).toContainText('140 trenes')
    await expect(otros.first()).toContainText('+340 km · +3 h 2 min')
    await expect(resto).toContainText('no mira si el tren cabe por él')
    // entre la estación de Moreda y la bifurcación no pasa ningún tren: no está en ninguna lista
    await expect(vista).not.toContainText('Moreda – Bifurcación Almería')
    // cada fila lleva a la ficha de su tramo
    await otros.first().getByRole('button').click()
    await expect(page).toHaveURL(/\/tramo\/lav-madrid-sevilla:cordoba:bif-malaga$/)
    await expect(page.getByTestId('detalle-tramo')).toBeVisible()
  })

  test('al abrir una línea salen sus tramos en orden, y un tramo lleva a su ficha o a simular su cierre', async ({ page }) => {
    await page.goto('/sin-otro-camino')
    const linea = page.getByTestId('sin-camino-linea-lav-madrid-sevilla')
    const boton = linea.getByRole('button', { name: /Madrid – Sevilla/ })
    await expect(boton).toHaveAttribute('aria-expanded', 'false')
    await boton.click()
    await expect(boton).toHaveAttribute('aria-expanded', 'true')
    // en el orden en que se recorre la línea, no por trenes
    const tramos = linea.locator('ol > li')
    await expect(tramos).toHaveCount(2)
    await expect(tramos.nth(0)).toContainText('Bifurcación Málaga-Alta Velocidad – Cambiador de Majarabique')
    await expect(tramos.nth(0)).toContainText('83 trenes')
    await expect(tramos.nth(1)).toContainText('Cambiador de Majarabique – Sevilla-Santa Justa')
    await expect(tramos.nth(1)).toContainText('81 trenes')
    // al elegir un tramo se pinta en azul en el mapa y se despliega en el sitio
    const tramo = page.getByTestId('tramo-lav-madrid-sevilla:bif-malaga:majarabique')
    await tramo.click()
    await expect(tramo).toHaveAttribute('aria-pressed', 'true')
    await expect(page.getByTestId('mapa')).toHaveAttribute('data-recorrido-elegido', '1')
    const detalle = page.getByTestId('sin-camino-detalle')
    await expect(detalle).toContainText(/Los más numerosos \(\d+\) van entre .+ y Sevilla-Santa Justa\./)
    await expect(page.getByTestId('sin-camino-ficha')).toHaveAttribute('href', '/tramo/lav-madrid-sevilla:bif-malaga:majarabique')
    const simular = page.getByTestId('sin-camino-simular')
    await expect(simular).toHaveText('Simular su cierre')
    await expect(simular).toHaveAttribute('href', '/tramo/lav-madrid-sevilla:bif-malaga:majarabique/cierre')
    // la simulación del cierre de ese tramo, a un toque
    await simular.click()
    await expect(page).toHaveURL(/\/tramo\/lav-madrid-sevilla:bif-malaga:majarabique\/cierre$/)
    await expect(page.getByTestId('panel-simulacion')).toBeVisible()

    // y su ficha
    await page.goto('/sin-otro-camino')
    await page.getByTestId('sin-camino-linea-espeluy-jaen').getByRole('button').first().click()
    await page.getByTestId('tramo-espeluy-jaen:mengibar-artichuela:jaen').click()
    await page.getByTestId('sin-camino-ficha').click()
    await expect(page).toHaveURL(/\/tramo\/espeluy-jaen:mengibar-artichuela:jaen$/)
    await expect(page.getByTestId('detalle-tramo')).toBeVisible()
  })

  test('«Cobertura y fuentes» ya no lleva la lista: enlaza con la vista', async ({ page }) => {
    await page.goto('/cobertura')
    await expect(page.getByTestId('pagina-cobertura')).toBeVisible()
    await expect(page.getByTestId('tramos-sin-alternativa')).toHaveCount(0)
    const enlace = page.getByTestId('cobertura-sin-otro-camino').getByRole('link', { name: 'Tramos sin otro camino' })
    await expect(enlace).toHaveAttribute('href', '/sin-otro-camino')
    await enlace.click()
    await expect(page).toHaveURL(/\/sin-otro-camino$/)
    await expect(page.getByTestId('vista-sin-otro-camino')).toBeVisible()
  })
})
