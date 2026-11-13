import { expect, test } from '@playwright/test'

/** El campo del buscador: en escritorio está a la vista; en el móvil lo despliega la lupa. */
async function abrirBuscador(page: import('@playwright/test').Page) {
  const lupa = page.getByTestId('buscador-abrir')
  if (await lupa.isVisible()) await lupa.click()
  return page.getByRole('combobox', { name: 'Buscar una estación o una línea' })
}

test.describe('La línea de alta velocidad Madrid – Zaragoza – Barcelona', () => {
  test('el buscador lleva a Barcelona-Sants y su ficha dice a dónde se llega sin cambiar de tren', async ({ page }) => {
    await page.goto('/')
    await expect(page.getByTestId('vista-red')).toBeVisible()
    const campo = await abrirBuscador(page)
    await campo.fill('barcelona')
    const primero = page.getByRole('option').first()
    await expect(primero).toContainText('Barcelona-Sants')
    await expect(primero).toContainText('Estación')
    await campo.press('Enter')
    await expect(page).toHaveURL(/\/nodo\/barcelona-sants$/)
    const ficha = page.getByTestId('detalle-nodo')
    await expect(ficha.getByRole('heading', { name: 'Barcelona-Sants' })).toBeVisible()
    await expect(ficha).toContainText('Girona, Figueres y Francia')
    // destinos directos del día de referencia, entre los que más trenes tienen
    await expect(ficha).toContainText('Camp de Tarragona')
    await expect(ficha).toContainText('Zaragoza-Delicias')
    await expect(ficha).toContainText('Madrid-Puerta de Atocha')
  })

  test('la línea tiene su ficha, con sus siete estaciones en el esquema', async ({ page }) => {
    await page.goto('/linea/lav-madrid-barcelona')
    await expect(page.getByRole('heading', { name: 'Línea de alta velocidad Madrid – Zaragoza – Barcelona' })).toBeVisible()
    await expect(page.locator('body')).toContainText('Une Madrid-Puerta de Atocha con Barcelona-Sants')
    const esquema = page.getByTestId('esquema')
    for (const estacion of ['Madrid-Puerta de Atocha', 'Zaragoza-Delicias', 'Barcelona-Sants']) {
      await expect(esquema).toContainText(estacion)
    }
  })

  test('la nota del esquema dice que faltan los trenes de Iryo', async ({ page }, testInfo) => {
    test.skip(testInfo.project.name === 'movil', 'el esquema compacto del móvil no lleva la nota')
    await page.goto('/linea/lav-madrid-barcelona')
    await expect(page.getByTestId('nota-esquema')).toContainText('según los horarios de Ouigo España y Renfe Viajeros; no incluyen los de Iryo.')
  })

  test('un tramo dice sus trenes por operador, los que faltan y su señalización', async ({ page }) => {
    await page.goto('/tramo/lav-madrid-barcelona:calatayud:cambiador-plasencia-de-jalon')
    const asa = page.getByRole('button', { name: 'Ampliar el panel' })
    if (await asa.isVisible()) await asa.click() // en móvil, la hoja empieza plegada
    const ficha = page.getByTestId('detalle-tramo')
    await expect(ficha).toBeVisible()
    await expect(page.getByTestId('tramo-vias')).toHaveText('Vía doble')
    await expect(page.getByTestId('tramo-operadores')).toHaveText('Renfe Viajeros 79 · Ouigo España 11')
    await expect(page.getByTestId('tramo-operadores-sin-horarios')).toHaveText(
      'No están los trenes de Iryo, que también opera en esta línea: no publica sus horarios en un formato abierto.',
    )
    await expect(page.getByTestId('trenes-ouigo').locator('li')).toHaveCount(11)
    await expect(page.getByTestId('trenes-iryo')).toHaveCount(0)
    // la señalización va bajo «Más detalle»: está en la ficha aunque plegada
    await expect(ficha.getByText('ERTMS de nivel 1 y ASFA')).toHaveCount(1)
    await expect(ficha.getByText('De control automático')).toHaveCount(1)
  })

  test('el comparador encuentra Madrid – Barcelona y Madrid – Zaragoza, con su tiempo', async ({ page }) => {
    await page.goto('/recorridos/madrid-puerta-de-atocha/barcelona-sants')
    const recorridos = page.getByTestId('recorrido')
    await expect(recorridos.first()).toBeVisible()
    // el primero, medido por los dos baipases (e2e/baipases.spec.ts): 620,1 km. Los otros dos bajan a València y
    // suben por la costa (e2e/mediterraneo.spec.ts)
    await expect(recorridos).toHaveCount(3)
    await expect(recorridos.first()).toContainText('620,1 km')
    await expect(recorridos.first()).toContainText('Zaragoza-Delicias')
    // hay tiempo porque ningún tramo se queda sin velocidad: 2 h 5 min sin paradas
    await expect(recorridos.first()).toContainText('2 h 5 min')
    await page.goto('/recorridos/madrid-puerta-de-atocha/zaragoza-delicias')
    await expect(recorridos.first()).toBeVisible()
    await expect(recorridos.first()).toContainText('306,5 km')
  })
})
