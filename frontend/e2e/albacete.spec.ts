import { expect, test } from '@playwright/test'

import { abrirZona } from './navegar.ts'

/** El campo del buscador: en escritorio está a la vista; en el móvil lo despliega la lupa. */
async function abrirBuscador(page: import('@playwright/test').Page) {
  const lupa = page.getByTestId('buscador-abrir')
  if (await lupa.isVisible()) await lupa.click()
  return page.getByRole('combobox', { name: 'Buscar una estación o una línea' })
}

test.describe('La línea de Alcázar de San Juan a La Encina por Albacete', () => {
  test('el buscador lleva a Albacete y su ficha dice a dónde se llega sin cambiar de tren', async ({ page }) => {
    await page.goto('/')
    await expect(page.getByTestId('vista-red')).toBeVisible()
    const campo = await abrirBuscador(page)
    await campo.fill('albacete')
    const primero = page.getByRole('option').first()
    await expect(primero).toContainText('Albacete-Los Llanos')
    await expect(primero).toContainText('Estación')
    await campo.press('Enter')
    await expect(page).toHaveURL(/\/nodo\/albacete-los-llanos$/)
    const ficha = page.getByTestId('detalle-nodo')
    await expect(ficha.getByRole('heading', { name: 'Albacete-Los Llanos' })).toBeVisible()
    await expect(ficha).toContainText('vías de dos anchos')
    // destinos directos del día de referencia: delante, los de la alta velocidad por Cuenca
    await expect(ficha).toContainText('Cuenca-Fernando Zóbel')
    await expect(ficha).toContainText('Alcázar de San Juan')
    // y, al desplegar la lista, los de la línea convencional
    await page.getByTestId('destinos-ver-todos').click()
    await expect(ficha).toContainText('Socuéllamos')
  })

  test('la ficha de Alcázar de San Juan enseña destinos directos hacia Levante', async ({ page }) => {
    await page.goto('/nodo/alcazar-de-san-juan')
    const ficha = page.getByTestId('detalle-nodo')
    await expect(ficha.getByRole('heading', { name: 'Alcázar de San Juan' })).toBeVisible()
    await expect(ficha).toContainText('hacia Andalucía y hacia Levante')
    // Albacete está entre los seis destinos con más trenes, que son los que se ven de entrada
    await expect(ficha).toContainText('Albacete-Los Llanos')
    await expect(ficha).toContainText('Regional e Intercity')
  })

  test('la línea aparece en Levante y también por sus estaciones de Castilla-La Mancha', async ({ page }) => {
    await page.goto('/')
    const ampliar = page.getByRole('button', { name: 'Ampliar el panel' })
    if (await ampliar.isVisible()) await ampliar.click()
    for (const [zona, fila] of [
      ['levante', 'linea-alcazar-albacete'],
      ['madrid-castilla-la-mancha', 'linea-alcazar-albacete--madrid-castilla-la-mancha'],
    ]) {
      await abrirZona(page, zona)
      await expect(page.getByTestId(fila)).toContainText('La Encina')
    }
  })

  test('la línea tiene su ficha, con Alcázar como enlace y sus estaciones en el esquema', async ({ page }) => {
    await page.goto('/linea/alcazar-albacete')
    await expect(page.getByRole('heading', { name: 'Línea convencional Alcázar de San Juan – Albacete – La Encina' })).toBeVisible()
    await expect(page.locator('body')).toContainText('cruza La Mancha')
    const esquema = page.getByTestId('esquema')
    await expect(esquema).toContainText('Alcázar de San Juan')
    await expect(esquema).toContainText('Villarrobledo')
    await expect(esquema).toContainText('Albacete-Los Llanos')
    await expect(esquema).toContainText('Almansa')
    await expect(esquema).toContainText('La Encina')
    await expect(page.locator('.maplibregl-canvas')).toBeVisible()
  })

  test('un tramo dice su vía doble y su bloqueo, y que no tiene control centralizado', async ({ page }) => {
    await page.goto('/tramo/alcazar-albacete:villarrobledo:minaya')
    const ficha = page.getByTestId('detalle-tramo')
    await expect(ficha).toBeVisible()
    await expect(page.getByTestId('tramo-vias')).toHaveText('Vía doble')
    // la señalización va bajo «Más detalle»: está en la ficha aunque plegada
    await expect(ficha.getByText('Automático de vía doble')).toHaveCount(1)
    await expect(page.getByTestId('tramo-atributo-mando')).toHaveText('Sin control centralizado')
    await expect(ficha.getByText('Sin dato publicado')).toHaveCount(0)
  })

  test('el comparador encuentra el recorrido de Madrid a Albacete por Alcázar', async ({ page }) => {
    await page.goto('/recorridos/madrid-puerta-de-atocha/albacete-los-llanos')
    const recorridos = page.getByTestId('recorrido')
    await expect(recorridos.first()).toBeVisible()
    await expect(recorridos.first()).toContainText('277,6 km')
    await expect(recorridos.first()).toContainText('Por Alcázar de San Juan')
    await expect(recorridos.first()).toContainText('Recorre dos líneas')
  })
})

const levante = [
  { madrid: 'madrid-puerta-de-atocha', destino: 'alicante-terminal', km: 453.8, minutos: 179, av: 478.4 },
  { madrid: 'madrid-chamartin', destino: 'alicante-terminal', km: 461.3, minutos: 186, av: 486.2 },
  { madrid: 'madrid-puerta-de-atocha', destino: 'valencia-estacio-del-nord', km: 484, minutos: 190, av: 390.4 },
  { madrid: 'madrid-chamartin', destino: 'valencia-estacio-del-nord', km: 491.5, minutos: 198, av: 398.2 },
]

for (const { madrid, destino, km, minutos, av } of levante) {
  test(`se ven la alta velocidad y la convencional entre ${madrid} y ${destino} en ambos sentidos`, async ({ page }) => {
    for (const [desde, hasta] of [[madrid, destino], [destino, madrid]]) {
      await page.goto(`/recorridos/${desde}/${hasta}`)
      const tarjetas = page.getByTestId('recorrido')
      const convencional = tarjetas.filter({ hasText: km.toFixed(1).replace('.', ',') + ' km' })
      await expect(convencional).toBeVisible()
      await expect(convencional).toContainText(`${Math.floor(minutos / 60)} h ${minutos % 60} min sin paradas`)
      await expect(tarjetas.filter({ hasText: av.toFixed(1).replace('.', ',') + ' km' })).toBeVisible()
    }
  })
}

test('la API y el visor cuentan los mismos servicios y sitúan la convencional entre los recorridos visibles', { tag: '@api' }, async ({ request }) => {
  test.skip(Boolean(process.env.ONIEL_E2E_STATIC), 'Necesita la API local')
  for (const nodo of ['almansa', 'la-encina']) {
    const estatico = await (await request.get(`/data/nodes/${nodo}.json`)).json() as { date: string; calls: unknown[] }
    const resp = await request.get(`/api/nodes/${nodo}/services`, { params: { date: estatico.date } })
    expect(resp.ok()).toBe(true)
    expect((await resp.json() as { calls: unknown[] }).calls).toEqual(estatico.calls)
    expect(estatico.calls.length).toBeGreaterThan(0)
  }
  const tramo = 'enlace-la-encina-caudete:la-encina:caudete'
  const ficha = await (await request.get(`/api/segments/${tramo}/services`)).json() as { segment: { station_closure: { from_id: string; to_id: string } }; passes: unknown[] }
  expect(ficha.segment.station_closure).toMatchObject({ from_id: 'la-encina', to_id: 'caudete' })
  expect(ficha.passes).toEqual([])
  const cierre = await request.post('/api/simulations/closure', { data: { segment_id: tramo, date: '2026-12-11', start: '08:00', end: '09:00' } })
  expect(cierre.status()).toBe(422)
  expect(await cierre.text()).toContain('entre La Encina y Caudete')
  const desvio = await request.get('/api/routes', { params: { from: 'la-encina', to: 'caudete', scenario: `c~${tramo}` } })
  expect(desvio.ok()).toBe(true)
  const resultado = await desvio.json() as { routes: { segment_ids: string[] }[] }
  for (const r of resultado.routes) expect(r.segment_ids).not.toContain(tramo)
  for (const { madrid, destino, km, minutos, av } of levante) {
    for (const [from, to] of [[madrid, destino], [destino, madrid]] as const) {
      const resp = await request.get('/api/routes', { params: { from, to } })
      expect(resp.ok()).toBe(true)
      const { routes } = await resp.json() as { routes: { node_ids: string[]; length_km: number; time_min: number }[] }
      const visibles = routes.slice(0, 3)
      const convencional = visibles.find((r) => r.length_km === km)
      expect(convencional?.node_ids).toEqual(expect.arrayContaining(['alcazar-de-san-juan', 'albacete-los-llanos', 'almansa', 'la-encina']))
      expect(convencional?.time_min).toBe(minutos)
      expect(visibles.find((r) => r.length_km === av)?.node_ids).toContain('cuenca-fernando-zobel')
    }
  }
})

for (const [nombre, id] of [['Almansa', 'almansa'], ['La Encina', 'la-encina']] as const) {
  test(`el buscador distingue la estación de ${nombre} y abre su ficha`, async ({ page }) => {
    await page.goto('/')
    await expect(page.getByTestId('vista-red')).toBeVisible()
    const campo = await abrirBuscador(page)
    await campo.fill(nombre)
    const estacion = page.getByRole('option').filter({ hasText: nombre }).filter({ hasText: 'Estación' })
    await expect(estacion).toHaveCount(1)
    await estacion.click()
    await expect(page).toHaveURL(new RegExp(`/nodo/${id}$`))
    await expect(page.getByTestId('detalle-nodo').getByRole('heading', { name: nombre, exact: true })).toBeVisible()
  })
}

test('el cierre de Albacete a Almansa abre el comparador entre las dos estaciones', async ({ page }) => {
  const tramo = 'alcazar-albacete:albacete-los-llanos:bif-chinchilla'
  await page.goto(`/tramo/${tramo}/cierre`)
  const cierre = page.getByTestId('cierre-estaciones')
  await expect(cierre.getByRole('link', { name: 'Albacete-Los Llanos' })).toHaveAttribute('href', '/nodo/albacete-los-llanos')
  await expect(cierre.getByRole('link', { name: 'Almansa', exact: true })).toHaveAttribute('href', '/nodo/almansa')
  await cierre.getByRole('link', { name: 'Consultar los recorridos con el cierre' }).click()
  await expect(page).toHaveURL(/\/recorridos\/albacete-los-llanos\/almansa\//)
  await expect(page.getByTestId('recorridos-escenario')).toContainText('cierre')
})
