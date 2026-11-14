import { expect, test, type Page } from '@playwright/test'
import { abrirZonas } from './navegar.ts'

const ENLACE = 'enlace-monforte-del-cid:monforte-del-cid-av:bif-vinalopo'

/** En el móvil la hoja empieza plegada: la despliega para ver la ficha. */
async function abrirPanel(page: Page) {
  const asa = page.getByRole('button', { name: 'Ampliar el panel' })
  if (await asa.isVisible()) await asa.click()
}

// El enlace de Monforte del Cid es una vía corta entre dos líneas: lleva los trenes de Alicante a la
// línea de alta velocidad de Murcia. Para el visitante es parte de la línea de Murcia, de la que
// cuelga (docs/diseno.md, «Enlaces entre líneas»).
test.describe('El enlace de Monforte del Cid', () => {
  test('en la lista cuelga de la línea de Murcia, sangrado, y no cuenta como línea', async ({ page }) => {
    await page.goto('/')
    await abrirPanel(page)
    const red = page.getByTestId('vista-red')
    await expect(page.getByTestId('ficha-red')).toContainText(/^18 líneas · 3\.923 km/)
    const levante = red.getByRole('region', { name: 'Comunidad Valenciana y Murcia' })
    await expect(levante.locator('.zona-cabecera')).toHaveText(/^›Comunidad Valenciana y Murcia4 líneas/)
    await abrirZonas(page)
    await expect(levante.locator('.fila-linea')).toHaveCount(4)
    const enlaces = levante.getByRole('list', { name: 'Enlaces de Monforte del Cid – Murcia' }).getByRole('button')
    await expect(enlaces).toHaveText([/^Enlace de Monforte del Cid2 km$/])
    // el filtro encuentra la línea de Murcia por el nombre de su enlace
    const filtro = page.getByTestId('filtro-lineas')
    await filtro.fill('enlace')
    await expect(red.locator('.fila-linea')).toHaveText([/Monforte del Cid – Murcia68 km$/])
    await filtro.fill('')
    await abrirZonas(page)
    // y el enlace tiene su ficha de línea
    await page.getByTestId('linea-enlace-monforte-del-cid').click()
    await expect(page).toHaveURL(/\/linea\/enlace-monforte-del-cid$/)
    await expect(page.getByRole('heading', { name: 'Enlace de Monforte del Cid' })).toBeVisible()
    await expect(page.getByTestId('ficha-linea')).toContainText('2,1 km')
  })

  test('el buscador lo encuentra por su nombre y no lo ofrece sin escribir', async ({ page }) => {
    await page.goto('/')
    await expect(page.getByTestId('vista-red')).toBeVisible()
    const lupa = page.getByTestId('buscador-abrir')
    if (await lupa.isVisible()) await lupa.click()
    const campo = page.getByRole('combobox', { name: 'Buscar una estación o una línea' })
    await campo.focus()
    await expect(page.getByRole('option').filter({ hasText: 'Enlace de Monforte' })).toHaveCount(0)
    await campo.fill('enlace de monforte')
    const primero = page.getByRole('option').first()
    await expect(primero).toContainText('Enlace de Monforte del Cid')
    await expect(primero).toContainText('Enlace de alta velocidad · 2,1 km')
    await campo.press('Enter')
    await expect(page).toHaveURL(/\/linea\/enlace-monforte-del-cid$/)
  })

  test('su tramo lleva los trenes que pasan por Alicante y dice por qué van por él', async ({ page }) => {
    await page.goto(`/tramo/${ENLACE}`)
    await abrirPanel(page)
    const ficha = page.getByTestId('detalle-tramo')
    await expect(ficha.getByRole('heading', { name: /Monforte del Cid/ })).toBeVisible()
    await expect(ficha).toContainText('Tramo 1 de 1 · Enlace de Monforte del Cid')
    await expect(ficha).toContainText('2,1 km')
    await expect(page.getByTestId('tramo-tipo')).toHaveText('Alta velocidad, vía única')
    await expect(page.getByTestId('tramo-atributo-proteccion_tren')).toHaveText('ERTMS de nivel 2 y ASFA')
    // 30 trenes el día de referencia: los 20 Avant de Alicante a Murcia y 10 de Madrid que paran en Alicante
    await expect(ficha).toContainText('30 el viernes, 13 de noviembre de 2026')
    const lista = page.getByTestId('lista-servicios')
    await expect(lista.locator('li')).toHaveCount(30)
    // todos con paso estimado, y la explicación empieza por el motivo, según el sentido, con el nombre
    // de la parada como lo da el horario de cada operador
    const vienen = lista.locator('[title^="Viene de Alicante"][title*=": por eso va por aquí. Estimado"]')
    const van = lista.locator('[title^="Va a Alicante"][title*=": por eso va por aquí. Estimado"]')
    await expect(vienen).toHaveCount(15)
    await expect(van).toHaveCount(15)
    // los otros dos lados del triángulo no son otro camino: habría que invertir la marcha
    await expect(page.getByTestId('tramo-alternativa')).toHaveText(
      'Si este tramo se cortara, sus 30 trenes no tendrían otro camino en las líneas que Oniel tiene cargadas. No quiere decir que no exista en la red real.',
    )
    // de Monforte del Cid ya no sale ninguna conexión a trazos: el enlace está cargado
    await page.goto('/nodo/monforte-del-cid-av')
    await abrirPanel(page)
    const nodo = page.getByTestId('detalle-nodo')
    await expect(nodo).toContainText('Enlace de Monforte del Cid')
    await expect(nodo.getByRole('button', { name: 'Monforte del Cid – Bifurcación Vinalopó' })).toBeVisible()
    await expect(nodo).not.toContainText('no cargada todavía')
  })

  test('el comparador va de Alicante a Murcia por el enlace, sin retroceder a la bifurcación de Murcia', async ({ page }) => {
    await page.goto('/recorridos/alicante-terminal/murcia-del-carmen')
    const recorridos = page.getByTestId('recorrido')
    await expect(recorridos).toHaveCount(1)
    const unico = recorridos.first()
    // 88,4 km: eran 92,2 cuando el recorrido retrocedía hasta la bifurcación de Murcia
    await expect(unico).toContainText('88,4 km · 26 min sin paradas')
    // el enlace es parte de la línea de Murcia: dos líneas, no tres
    await expect(unico).toContainText('Recorre dos líneas')
    await expect(unico).not.toContainText('Bifurcación Murcia')
    // y los 20 Avant directos de ese sentido siguen ese recorrido
    await expect(page.getByTestId('recorridos-resumen')).toContainText('trenes directos en este sentido')
  })

  test('de Madrid a Murcia sigue habiendo los mismos recorridos: ninguno dobla una esquina del triángulo', async ({ page }) => {
    await page.goto('/recorridos/madrid-chamartin/murcia-del-carmen')
    const recorridos = page.getByTestId('recorrido')
    await expect(recorridos.first()).toContainText('529,5 km · 2 h 3 min sin paradas')
    await expect(recorridos.first()).toContainText('Recorre tres líneas')
    for (const recorrido of await recorridos.all()) await expect(recorrido).not.toContainText('Monforte del Cid')
  })
})
