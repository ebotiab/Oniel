import { expect, test } from '@playwright/test'

/** El campo del buscador: en escritorio está a la vista; en el móvil lo despliega la lupa. */
async function abrirBuscador(page: import('@playwright/test').Page) {
  const lupa = page.getByTestId('buscador-abrir')
  if (await lupa.isVisible()) await lupa.click()
  return page.getByRole('combobox', { name: 'Buscar una estación o una línea' })
}

test.describe('La línea de alta velocidad Monforte del Cid – Murcia', () => {
  test('el buscador lleva a Murcia y su ficha dice a dónde se llega sin cambiar de tren', async ({ page }) => {
    await page.goto('/')
    await expect(page.getByTestId('vista-red')).toBeVisible()
    const campo = await abrirBuscador(page)
    await campo.fill('murcia')
    const estacion = page.getByRole('option').filter({ hasText: 'Murcia del Carmen' })
    await expect(estacion).toContainText('Estación')
    await estacion.click()
    await expect(page).toHaveURL(/\/nodo\/murcia-del-carmen$/)
    const ficha = page.getByTestId('detalle-nodo')
    await expect(ficha.getByRole('heading', { name: 'Murcia del Carmen' })).toBeVisible()
    await expect(ficha).toContainText('La estación de Murcia, donde acaba la línea')
    await expect(ficha).toContainText('Alicante-Terminal')
    await expect(ficha).toContainText('Madrid-Chamartín')
  })

  test('la línea tiene su ficha, con sus bifurcaciones y sus cinco estaciones en el esquema', async ({ page }) => {
    await page.goto('/linea/lav-monforte-murcia')
    await expect(page.getByRole('heading', { name: 'Línea de alta velocidad Monforte del Cid – Murcia' })).toBeVisible()
    await expect(page.locator('body')).toContainText('El camino por el que la alta velocidad llega a Elche, a Orihuela y a Murcia')
    const esquema = page.getByTestId('esquema')
    await expect(esquema).toContainText('Bif. Murcia')
    await expect(esquema).toContainText('Bif. Vinalopó')
    await expect(esquema).toContainText('Elche Alta Velocidad')
    await expect(esquema).toContainText('Callosa de Segura-Cox')
    await expect(esquema).toContainText('Orihuela-Miguel Hernández')
    await expect(esquema).toContainText('Beniel')
    await expect(esquema).toContainText('Murcia del Carmen')
  })

  test('la entrada a Murcia es de vía única y de ancho mixto, y en esta línea no falta ningún operador', async ({ page }) => {
    await page.goto('/tramo/lav-monforte-murcia:bif-el-regueron:murcia-del-carmen')
    const ficha = page.getByTestId('detalle-tramo')
    await expect(ficha).toBeVisible()
    await expect(page.getByTestId('tramo-atributo-gauge')).toContainText('Mixto')
    await expect(page.getByTestId('tramo-atributo-proteccion_tren')).toHaveText('ERTMS de nivel 2 y ASFA')
    await expect(page.getByTestId('tramo-atributo-bloqueo')).toHaveText('De control automático')
    // Iryo no llega a Murcia: aquí no hay aviso de trenes que falten
    await expect(page.getByTestId('tramo-operadores-sin-horarios')).toHaveCount(0)
  })

  test('el comparador encuentra Madrid – Murcia por Cuenca, sin entrar en Alicante', async ({ page }) => {
    await page.goto('/recorridos/madrid-puerta-de-atocha/murcia-del-carmen')
    const recorridos = page.getByTestId('recorrido')
    await expect(recorridos.first()).toBeVisible()
    // el primero, más corto, junta la línea convencional hasta Albacete con la alta velocidad
    // desde allí; el segundo es el de alta velocidad entero, por Cuenca
    const porCuenca = recorridos.nth(1)
    await expect(porCuenca).toContainText('Por Bifurcación Torrejón de Velasco, Bifurcación Albacete y Bifurcación Murcia')
    await expect(porCuenca).toContainText('521,7 km · 1 h 58 min sin paradas')
    await expect(porCuenca).toContainText('Recorre cuatro líneas')
    await expect(porCuenca).not.toContainText('Alicante-Terminal')
  })
})
