import { expect, test } from '@playwright/test'

/** El campo del buscador: en escritorio está a la vista; en el móvil lo despliega la lupa. */
async function abrirBuscador(page: import('@playwright/test').Page) {
  const lupa = page.getByTestId('buscador-abrir')
  if (await lupa.isVisible()) await lupa.click()
  return page.getByRole('combobox', { name: 'Buscar una estación o una línea' })
}

test.describe('La línea de alta velocidad Barcelona – Girona – Figueres', () => {
  test('la línea tiene su ficha, con sus tres estaciones en el esquema, y describe los TGV cargados', async ({ page }) => {
    await page.goto('/linea/lav-barcelona-figueres')
    await expect(page.getByRole('heading', { name: 'Línea de alta velocidad Barcelona – Girona – Figueres' })).toBeVisible()
    await expect(page.locator('body')).toContainText('Une Barcelona-Sants con Girona y Figueres-Vilafant')
    await expect(page.getByTestId('ficha-linea')).toContainText('los TGV de SNCF Voyageurs entre París y Barcelona')
    const esquema = page.getByTestId('esquema')
    for (const estacion of ['Barcelona-Sants', 'Girona', 'Figueres-Vilafant', 'Límite con la sección internacional']) {
      await expect(esquema).toContainText(estacion)
    }
  })

  for (const [texto, nombre, id] of [
    ['girona', 'Girona', 'girona'],
    ['figueres', 'Figueres-Vilafant', 'figueres-vilafant'],
  ]) {
    test(`el buscador lleva a ${nombre}`, async ({ page }) => {
      await page.goto('/')
      await expect(page.getByTestId('vista-red')).toBeVisible()
      const campo = await abrirBuscador(page)
      await campo.fill(texto)
      const opcion = page.getByRole('option').filter({ hasText: nombre }).filter({ hasText: 'Estación' }).first()
      await expect(opcion).toBeVisible()
      await opcion.click()
      await expect(page).toHaveURL(new RegExp(`/nodo/${id}$`))
      const ficha = page.getByTestId('detalle-nodo')
      await expect(ficha.getByRole('heading', { name: nombre })).toBeVisible()
      // destinos directos del día de referencia
      await expect(ficha).toContainText('Barcelona-Sants')
      await expect(ficha).toContainText('Madrid-Puerta de Atocha')
    })
  }

  test('de Barcelona-Sants ya no sale una conexión a trazos hacia la frontera: sale esta línea', async ({ page }) => {
    await page.goto('/nodo/barcelona-sants')
    const ficha = page.getByTestId('detalle-nodo')
    await expect(ficha.getByRole('heading', { name: 'Barcelona-Sants' })).toBeVisible()
    await expect(ficha).toContainText('empieza la de Girona y Figueres')
    await expect(ficha).not.toContainText('LAV Barcelona – frontera francesa')
    await expect(ficha).toContainText('Girona')
    // las dos líneas de alta velocidad de la estación salen de la misma relación de OpenStreetMap:
    // se cita una vez; la convencional de Portbou y la de Tarragona por la costa salen de otras, y
    // se citan aparte
    const asa = page.getByRole('button', { name: 'Ampliar el panel' })
    if (await asa.isVisible()) await asa.click()
    await ficha.getByTestId('mas-detalle').locator('summary').click()
    const pie = ficha.getByTestId('pie-fuente').first()
    // y las tres son de OpenStreetMap: un solo párrafo, con el editor una vez y el trazado de cada línea detrás
    await expect(pie.locator('p')).toHaveCount(1)
    await expect(pie).toContainText(/^Fuentes del trazado: Colaboradores de OpenStreetMap/)
    expect((await pie.innerText()).match(/Colaboradores de OpenStreetMap/g)).toHaveLength(1)
    expect((await pie.innerText()).match(/osm-relation-11082425/g)).toHaveLength(1)
  })

  test('el final de la línea dice que la sección internacional no está cargada', async ({ page }) => {
    await page.goto('/nodo/limite-seccion-internacional')
    const ficha = page.getByTestId('detalle-nodo')
    await expect(ficha.getByRole('heading', { name: 'Límite con la sección internacional' })).toBeVisible()
    await expect(ficha).toContainText('Sección internacional Figueres – Perpiñán')
    await expect(ficha).toContainText('no cargada todavía')
  })

  test('los tramos son de vía doble, con ERTMS de nivel 1 y ASFA', async ({ page }) => {
    await page.goto('/tramo/lav-barcelona-figueres:girona:figueres-vilafant')
    await expect(page.getByTestId('detalle-tramo')).toBeVisible()
    const asa = page.getByRole('button', { name: 'Ampliar el panel' })
    if (await asa.isVisible()) await asa.click()
    await expect(page.getByTestId('tramo-vias')).toHaveText('Vía doble')
    await expect(page.getByTestId('tramo-atributo-proteccion_tren')).toHaveText('ERTMS de nivel 1 y ASFA')
  })

  test('los TGV de SNCF cuentan una sola vez en Girona–Figueres y hasta el límite', async ({ page }) => {
    for (const tramo of ['girona:figueres-vilafant', 'figueres-vilafant:limite-seccion-internacional']) {
      await page.goto(`/tramo/lav-barcelona-figueres:${tramo}`)
      const ficha = page.getByTestId('detalle-tramo')
      await expect(ficha).toBeVisible()
      const asa = page.getByRole('button', { name: 'Ampliar el panel' })
      if (await asa.isVisible()) await asa.click()
      await expect(page.getByTestId('tramo-operadores')).toContainText('SNCF Voyageurs 4')
      const trenes = ficha.getByTestId('trenes-sncf')
      await expect(trenes.getByRole('heading')).toHaveText('SNCF Voyageurs · 4')
      await expect(trenes.locator('li')).toHaveCount(4)
      for (const numero of ['9706', '9708', '9713', '9715']) {
        await expect(trenes.locator('li').filter({ hasText: `TGV ${numero}` })).toHaveCount(1)
      }
      await expect(trenes).toContainText('Barcelona-Sants')
      await expect(trenes).not.toContainText('Barcelone')
    }
  })

  for (const nodo of ['barcelona-sants', 'girona', 'figueres-vilafant']) {
    test(`la ficha de ${nodo} incluye París con fuente SNCF y sin línea francesa inventada`, async ({ page }) => {
      await page.goto(`/nodo/${nodo}`)
      const ficha = page.getByTestId('detalle-nodo')
      await expect(ficha).toBeVisible()
      const asa = page.getByRole('button', { name: 'Ampliar el panel' })
      if (await asa.isVisible()) await asa.click()
      const todos = ficha.getByTestId('destinos-ver-todos')
      if (await todos.isVisible()) await todos.click()
      const paris = ficha.getByTestId('lista-destinos').locator('li').filter({ hasText: 'Paris Gare de Lyon' })
      await expect(paris).toHaveCount(1)
      await expect(paris).toContainText('2 trenes')
      await expect(paris).toContainText('TGV')
      await expect(paris).toContainText('SNCF Voyageurs')
      await expect(paris.getByRole('button')).toHaveCount(0)
    })
  }

  test('el comparador encuentra Madrid – Girona y Barcelona – Figueres', async ({ page }) => {
    await page.goto('/recorridos/madrid-puerta-de-atocha/girona')
    const recorridos = page.getByTestId('recorrido')
    await expect(recorridos.first()).toBeVisible()
    await expect(recorridos.first()).toContainText('714,1 km')
    await expect(recorridos.first().getByTestId('recorrido-trenes')).toContainText(/\d+ trenes directos en el horario del /)
    await page.goto('/recorridos/barcelona-sants/figueres-vilafant')
    await expect(recorridos.first()).toBeVisible()
    await expect(recorridos.first()).toContainText('128,9 km')
    await expect(recorridos.first().getByTestId('recorrido-trenes')).toContainText(/\d+ trenes directos en el horario del /)
  })
})
