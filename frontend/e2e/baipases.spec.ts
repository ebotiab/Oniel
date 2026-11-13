import { expect, test, type Page } from '@playwright/test'

const estatico = Boolean(process.env.ONIEL_E2E_STATIC)

const BAIPAS_ZARAGOZA = 'baipas-zaragoza:bif-moncasi:bif-canal-imperial'
const ENTRADA_ZARAGOZA = 'lav-madrid-barcelona:bif-moncasi:zaragoza-delicias'

/** En el móvil la hoja empieza plegada: la despliega para ver la ficha. */
async function abrirPanel(page: Page) {
  const asa = page.getByRole('button', { name: 'Ampliar el panel' })
  if (await asa.isVisible()) await asa.click()
}

// Los baipases de Zaragoza y de Lleida son dos líneas cortas que cuelgan de la alta velocidad de
// Barcelona: llevan los trenes que no paran en la estación que rodean, y para el visitante son parte
// de su línea (docs/diseno.md, «Baipases»).
test.describe('Los baipases de Zaragoza y de Lleida', () => {
  test('en la lista cuelgan de su línea, sangrados, y no cuentan como líneas', async ({ page }) => {
    await page.goto('/')
    await abrirPanel(page)
    const red = page.getByTestId('vista-red')
    // diez líneas, con los kilómetros de los dos baipases sumados
    await expect(page.getByTestId('ficha-red')).toContainText(/^11 líneas · 2\.872 km/)
    const cataluna = red.getByRole('region', { name: 'Cataluña' })
    await expect(cataluna.locator('.zona-cabecera')).toHaveText(/^›Cataluña1 línea$/)
    await expect(cataluna.locator('.fila-linea')).toHaveText([/Madrid – Barcelona por Zaragoza627 km$/])
    const baipases = cataluna.getByRole('list', { name: 'Baipases de Madrid – Barcelona por Zaragoza' }).getByRole('button')
    await expect(baipases).toHaveText([/^Baipás de Zaragoza21 km$/, /^Baipás de Lleida14 km$/])
    // el filtro encuentra la línea por el nombre de su baipás, y el baipás sigue colgado de ella
    const filtro = page.getByTestId('filtro-lineas')
    await filtro.fill('baipas')
    await expect(red.locator('.fila-linea')).toHaveText([/Madrid – Barcelona por Zaragoza627 km$/])
    await expect(baipases).toHaveCount(2)
    await filtro.fill('')
    // cada baipás tiene su ficha de línea
    await page.getByTestId('linea-baipas-zaragoza').click()
    await expect(page).toHaveURL(/\/linea\/baipas-zaragoza$/)
    await expect(page.getByRole('heading', { name: 'Baipás de Zaragoza' })).toBeVisible()
    await expect(page.getByTestId('ficha-linea')).toContainText('20,7 km')
  })

  test('el buscador los encuentra por su nombre y no los ofrece sin escribir', async ({ page }) => {
    await page.goto('/')
    await expect(page.getByTestId('vista-red')).toBeVisible()
    const lupa = page.getByTestId('buscador-abrir')
    if (await lupa.isVisible()) await lupa.click()
    const campo = page.getByRole('combobox', { name: 'Buscar una estación o una línea' })
    await campo.focus()
    await expect(page.getByRole('option').filter({ hasText: 'Baipás' })).toHaveCount(0)
    await campo.fill('baipas de lleida')
    const primero = page.getByRole('option').first()
    await expect(primero).toContainText('Baipás de Lleida')
    await expect(primero).toContainText('Baipás de alta velocidad · 14,3 km')
    await campo.press('Enter')
    await expect(page).toHaveURL(/\/linea\/baipas-lleida$/)
  })

  test('el tramo del baipás lleva los trenes que no paran en Zaragoza y dice por qué van por él', async ({ page }) => {
    await page.goto(`/tramo/${BAIPAS_ZARAGOZA}`)
    await abrirPanel(page)
    const ficha = page.getByTestId('detalle-tramo')
    await expect(ficha.getByRole('heading', { name: /Bifurcación Moncasi/ })).toBeVisible()
    await expect(ficha).toContainText('Tramo 1 de 1 · Baipás de Zaragoza')
    await expect(ficha).toContainText('20,7 km')
    await expect(page.getByTestId('tramo-tipo')).toHaveText('Alta velocidad')
    // 22 trenes el día de referencia: los que van de Madrid a Barcelona sin parar en Zaragoza
    await expect(ficha).toContainText('22 el viernes, 13 de noviembre de 2026')
    const trenes = page.getByTestId('lista-servicios').locator('li')
    await expect(trenes).toHaveCount(22)
    // todos con paso estimado, y la explicación empieza por el motivo
    await expect(page.getByTestId('lista-servicios').locator('[title^="No para en Zaragoza-Delicias: por eso va por aquí. Estimado"]')).toHaveCount(22)
    // si se cortara, sus trenes entrarían en la estación
    await expect(page.getByTestId('tramo-alternativa')).toHaveText(
      'Si este tramo se cortara, sus 22 trenes tendrían otro camino en las líneas que Oniel tiene cargadas. Ese camino tiene 5 km y 6 min más.',
    )
  })

  test('la entrada a Zaragoza-Delicias solo lleva los trenes que paran allí, y su otro camino es el baipás', async ({ page }) => {
    await page.goto(`/tramo/${ENTRADA_ZARAGOZA}`)
    await abrirPanel(page)
    const ficha = page.getByTestId('detalle-tramo')
    // eran 78 cuando el tren que no para figuraba por la estación; lo que llega a la bifurcación sale
    // por aquí (56) o por el baipás (22)
    await expect(ficha).toContainText('56 el viernes, 13 de noviembre de 2026')
    await expect(page.getByTestId('lista-servicios').locator('li')).toHaveCount(56)
    await expect(page.getByTestId('tramo-alternativa')).toContainText('sus 56 trenes tendrían otro camino en las líneas que Oniel tiene cargadas')
    // la ficha de la bifurcación enseña los dos caminos que salen de ella
    await page.goto('/nodo/bif-moncasi')
    await abrirPanel(page)
    const nodo = page.getByTestId('detalle-nodo')
    await expect(nodo).toContainText('Baipás de Zaragoza')
    await expect(nodo.getByRole('button', { name: 'Bifurcación Moncasi – Bifurcación Canal Imperial' })).toBeVisible()
    await expect(nodo.getByRole('button', { name: 'Bifurcación Moncasi – Zaragoza-Delicias' })).toBeVisible()
    // ya no hay conexión a trazos: el baipás está cargado
    await expect(nodo).not.toContainText('no cargada todavía')
  })

  test('el comparador da un solo recorrido de Madrid a Barcelona por su línea, medido por los baipases', async ({ page }) => {
    await page.goto('/recorridos/madrid-puerta-de-atocha/barcelona-sants')
    const recorridos = page.getByTestId('recorrido')
    // el de la línea, uno solo aunque haya cuatro maneras de pasar por Zaragoza y Lleida, y el que baja por València y la costa
    await expect(recorridos).toHaveCount(2)
    await expect(recorridos.nth(1)).toContainText('755,1 km')
    await expect(page.getByTestId('recorridos-resumen')).toHaveText(/^Dos recorridos, del más corto al más largo\. Hay 29 trenes directos en este sentido/)
    const unico = recorridos.first()
    await expect(unico.getByRole('button', { name: 'Por la alta velocidad' })).toBeVisible()
    await expect(unico).toContainText('620,1 km · 2 h 5 min sin paradas')
    // una sola línea: pasar a un baipás no es cambiar de línea
    await expect(unico).not.toContainText('Recorre')
    await expect(unico).toContainText('Pasa por Guadalajara-Yebes, Calatayud y Camp de Tarragona.')
    await expect(unico.getByTestId('recorrido-baipases')).toHaveText(
      'Rodea Zaragoza y Lleida por sus baipases; el tren que para en Zaragoza-Delicias y en Lleida-Pirineus recorre 6,9 km más.',
    )
    // todos los directos son de este recorrido, paren o no en las dos estaciones
    await expect(unico.getByTestId('recorrido-trenes')).toContainText('29 trenes directos')
    // el mapa lo dibuja por los dos baipases: quince tramos de la línea y los dos de los baipases, no los veinte
    await expect(page.getByTestId('mapa')).toHaveAttribute('data-recorrido-elegido', '17')

    // a Lleida se llega rodeando Zaragoza y entrando por su ramal
    await page.goto('/recorridos/madrid-puerta-de-atocha/lleida-pirineus')
    // también a Lleida hay un segundo recorrido, que sube desde València por Camp de Tarragona
    await expect(recorridos).toHaveCount(2)
    await expect(recorridos.first()).toContainText('441,6 km')
    await expect(recorridos.first().getByTestId('recorrido-baipases')).toHaveText(
      'Rodea Zaragoza por su baipás; el tren que para en Zaragoza-Delicias recorre 4,9 km más.',
    )
    // y a Zaragoza, por el suyo: ningún baipás que contar
    await page.goto('/recorridos/madrid-puerta-de-atocha/zaragoza-delicias')
    await expect(recorridos).toHaveCount(1)
    await expect(recorridos.first()).toContainText('306,5 km')
    await expect(page.getByTestId('recorrido-baipases')).toHaveCount(0)
  })

  test('con el baipás de Zaragoza cerrado, el recorrido entra en la estación', async ({ page }) => {
    await page.goto(`/recorridos/madrid-puerta-de-atocha/barcelona-sants/c~${BAIPAS_ZARAGOZA}`)
    const recorridos = page.getByTestId('recorrido')
    // el de siempre, cortado; el más corto que no lo está, por Zaragoza-Delicias, 4,9 km más, y el de València
    await expect(recorridos).toHaveCount(3)
    await expect(recorridos.nth(1)).toContainText('El más corto que no está cortado')
    await expect(recorridos.nth(2)).toContainText('755,1 km')
    await expect(recorridos.nth(0)).toContainText('620,1 km')
    await expect(recorridos.nth(0).getByTestId('recorrido-corte')).toHaveText('Cerrado en este supuesto entre Bifurcación Moncasi y Bifurcación Canal Imperial.')
    await expect(recorridos.nth(1)).toContainText('625,0 km')
    await expect(recorridos.nth(1)).toContainText('Zaragoza-Delicias')
    await expect(recorridos.nth(1).getByTestId('recorrido-baipases')).toHaveText(
      'Rodea Lleida por su baipás; el tren que para en Lleida-Pirineus recorre 2,0 km más.',
    )
  })

  test('simular el cierre de la entrada a Zaragoza señala el baipás como alternativa', async ({ page }) => {
    test.skip(estatico, 'la simulación necesita la API')
    await page.goto(`/tramo/${ENTRADA_ZARAGOZA}`)
    await abrirPanel(page)
    await page.getByTestId('boton-simular').click()
    await expect(page.getByTestId('panel-simulacion')).toBeVisible()
    await page.getByTestId('sim-fecha').fill('2026-11-13')
    await page.getByTestId('sim-inicio').fill('08:00')
    await page.getByTestId('sim-fin').fill('10:00')
    await page.getByTestId('sim-calcular').click()
    await expect(page.getByTestId('sim-resultado')).toBeVisible()
    const alternativa = page.getByTestId('sim-alternativa')
    await expect(alternativa).toContainText(/[Bb]aipás de Zaragoza/)
    await expect(alternativa).toContainText('20,7 km frente a 25,6 km')
  })
})
