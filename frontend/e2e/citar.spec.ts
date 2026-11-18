import { readFileSync } from 'node:fs'

import { expect, test, type Page } from '@playwright/test'

import { htmlConMeta, metaTramo, SITIO } from '../src/app/meta.ts'
import { cobertura, indice } from './instantanea.ts'

// Citar Oniel desde fuera (docs/diseno.md, «Citar una vista»): cada vista dice en la pestaña qué es, lleva
// al pie de qué día son sus trenes y un botón que copia su dirección exacta, y «Cobertura y fuentes»
// explica cómo citarla.

const TRAMO = 'lav-madrid-barcelona:zaragoza-delicias:bif-huesca'
const DIA = cobertura.reference_date!

const fechaLarga = (iso: string) => new Date(`${iso}T12:00:00`).toLocaleDateString('es-ES', { day: 'numeric', month: 'long', year: 'numeric' })

/** En el móvil la hoja empieza plegada: la despliega para ver la ficha. */
async function abrirPanel(page: Page) {
  const asa = page.getByRole('button', { name: 'Ampliar el panel' })
  if (await asa.isVisible()) await asa.click()
}

/** Pulsa «Copiar enlace a esta vista» y devuelve lo que ha quedado en el portapapeles. */
async function copiarEnlace(page: Page): Promise<string> {
  await page.context().grantPermissions(['clipboard-read', 'clipboard-write'])
  await abrirPanel(page)
  await page.getByTestId('copiar-enlace').click()
  await expect(page.getByTestId('copiar-enlace-estado')).toHaveText('Enlace copiado.')
  return page.evaluate<string>('navigator.clipboard.readText()')
}

const contenido = (page: Page, selector: string) => page.locator(selector).getAttribute('content')

test.describe('Título y descripción por vista', () => {
  test('cambian al navegar, también en las etiquetas del enlace compartido', async ({ page }) => {
    await page.goto('/')
    await expect(page).toHaveTitle('Oniel · Cómo está conectada la red ferroviaria')

    await page.goto('/linea/lav-madrid-barcelona')
    await expect(page).toHaveTitle('Línea de alta velocidad Madrid – Zaragoza – Barcelona · Oniel')
    expect(await contenido(page, 'meta[property="og:title"]')).toBe('Línea de alta velocidad Madrid – Zaragoza – Barcelona · Oniel')
    expect(await contenido(page, 'meta[name="description"]')).toMatch(/^Línea de alta velocidad Madrid – Zaragoza – Barcelona: [\d,]+ km en el mapa/)
    expect(await contenido(page, 'meta[property="og:url"]')).toBe(`${SITIO}/linea/lav-madrid-barcelona`)
    expect(await page.locator('link[rel="canonical"]').getAttribute('href')).toBe(`${SITIO}/linea/lav-madrid-barcelona`)
    expect(await contenido(page, 'meta[property="og:image"]')).toBe(`${SITIO}/tarjeta.png`)

    // sin recargar: de la línea a uno de sus tramos, y de ahí a su simulación
    await page.goto(`/tramo/${TRAMO}`)
    await expect(page).toHaveTitle('Tramo Zaragoza-Delicias – Bifurcación Huesca · Oniel')
    await abrirPanel(page)
    await page.getByTestId('boton-simular').click()
    await expect(page).toHaveTitle('Cierre hipotético de Zaragoza-Delicias – Bifurcación Huesca · Oniel')
    expect(await contenido(page, 'meta[name="description"]')).toContain('Es una simulación, no un aviso.')

    await page.goto('/nodo/zaragoza-delicias')
    await expect(page).toHaveTitle('Zaragoza-Delicias · Oniel')
    await page.goto('/recorridos/madrid-puerta-de-atocha/barcelona-sants')
    await expect(page).toHaveTitle('Recorridos de Madrid-Puerta de Atocha a Barcelona-Sants · Oniel')
    expect(await contenido(page, 'meta[name="description"]')).toContain('un tiempo estimado sin paradas')
    await page.goto('/recorridos')
    await expect(page).toHaveTitle('Comparar recorridos · Oniel')
    await page.goto('/sin-otro-camino')
    await expect(page).toHaveTitle('Tramos sin otro camino · Oniel')
    await page.goto('/glosario')
    await expect(page).toHaveTitle('Glosario · Oniel')
    await page.goto('/glosario/via-unica')
    await expect(page).toHaveTitle('Vía única · Glosario · Oniel')
    await page.goto('/cobertura')
    await expect(page).toHaveTitle('Cobertura y fuentes · Oniel')
    // y de vuelta a la red por la marca, sin recargar
    await page.getByTestId('marca').click()
    await expect(page).toHaveTitle('Oniel · Cómo está conectada la red ferroviaria')
  })

  test('la página estática de una vista es el mismo index.html con sus etiquetas', () => {
    const html = readFileSync(new URL('../index.html', import.meta.url), 'utf-8')
    const tramo = indice.segment_features.features.find((f) => f.id === TRAMO)!
    const linea = indice.lines.find((l) => l.id === tramo.properties.line_id)
    const meta = metaTramo(tramo.properties, linea)
    const pagina = htmlConMeta(html, { ...meta, description: `${meta.description} "entre comillas" <y> &` }, `/tramo/${TRAMO}`)
    expect(pagina).toContain('<title>Tramo Zaragoza-Delicias – Bifurcación Huesca · Oniel</title>')
    expect(pagina).toContain('<meta property="og:title" content="Tramo Zaragoza-Delicias – Bifurcación Huesca · Oniel" />')
    expect(pagina).toContain(`<meta property="og:url" content="${SITIO}/tramo/${TRAMO}" />`)
    expect(pagina).toContain(`<link rel="canonical" href="${SITIO}/tramo/${TRAMO}" />`)
    // lo que podría romper la etiqueta va escapado
    expect(pagina).toContain('&quot;entre comillas&quot; &lt;y&gt; &amp;" />')
    // ninguna etiqueta se queda con el texto de la portada, y lo demás no cambia
    expect(pagina).not.toContain('Cómo está conectada la red ferroviaria')
    expect(pagina).not.toContain('recorrerla línea a línea')
    expect(pagina).toContain('<script type="module" src="/src/main.tsx"></script>')
    expect(pagina.split('\n').length).toBe(html.split('\n').length)
  })
})

test.describe('El pie de cada vista', () => {
  test('dice de qué día son los trenes y cuándo se descargaron los horarios', async ({ page }) => {
    for (const ruta of ['/', '/linea/lav-madrid-barcelona', `/tramo/${TRAMO}`, '/nodo/zaragoza-delicias', '/sin-otro-camino']) {
      await page.goto(ruta)
      await abrirPanel(page)
      const fecha = page.getByTestId('pie-vista-fecha')
      await expect(fecha).toContainText(`Trenes del ${fechaLarga(DIA)}, según los horarios descargados el `)
      // un fichero de horarios por operador cargado, cada uno con su nombre
      for (const d of cobertura.datasets ?? []) await expect(fecha).toContainText(`(${cobertura.operators.find((o) => o.id === d.operator_id)!.name})`)
    }
  })

  test('«Copiar enlace a esta vista» copia la dirección de un tramo', async ({ page, baseURL }) => {
    await page.goto(`/tramo/${TRAMO}`)
    expect(await copiarEnlace(page)).toBe(`${baseURL}/tramo/${TRAMO}`)
  })

  test('el enlace de una comparación la abre tal cual', async ({ page, baseURL }) => {
    await page.goto('/recorridos')
    await page.goto('/recorridos/madrid-puerta-de-atocha/barcelona-sants')
    const enlace = await copiarEnlace(page)
    expect(enlace).toBe(`${baseURL}/recorridos/madrid-puerta-de-atocha/barcelona-sants`)
    // pegado en otra pestaña enseña la misma comparación
    const otra = await page.context().newPage()
    await otra.goto(enlace)
    await abrirPanel(otra)
    await expect(otra.getByTestId('comparador')).toBeVisible()
    await expect(otra.getByTestId('recorridos-resumen')).toBeVisible()
    await expect(otra.getByTestId('recorrido').first()).toBeVisible()
  })

  test('el enlace de una simulación lleva el tramo, el día y la franja', async ({ page, baseURL }) => {
    await page.goto(`/tramo/${TRAMO}/cierre`)
    await abrirPanel(page)
    // al elegir la franja, la dirección la recoge
    await page.getByTestId('sim-inicio').fill('06:30')
    await page.getByTestId('sim-fin').fill('10:15')
    await expect(page).toHaveURL(new RegExp(`/tramo/${TRAMO}/cierre/${DIA}/06:30-10:15$`))
    const enlace = await copiarEnlace(page)
    expect(enlace).toBe(`${baseURL}/tramo/${TRAMO}/cierre/${DIA}/06:30-10:15`)
    // pegado en otra pestaña abre la simulación de ese tramo con el día y la franja puestos
    const otra = await page.context().newPage()
    await otra.goto(enlace)
    await abrirPanel(otra)
    await expect(otra.getByTestId('panel-simulacion')).toBeVisible()
    await expect(otra.getByRole('heading', { name: 'Zaragoza-Delicias – Bifurcación Huesca' })).toBeVisible()
    await expect(otra.getByTestId('sim-fecha')).toHaveValue(DIA)
    await expect(otra.getByTestId('sim-inicio')).toHaveValue('06:30')
    await expect(otra.getByTestId('sim-fin')).toHaveValue('10:15')
    await expect(otra).toHaveURL(enlace)
    await expect(otra.getByTestId('pie-vista-fecha')).toContainText(`Trenes del ${fechaLarga(DIA)}`)
    // una franja que no se entiende se ignora: queda la simulación sin franja
    await otra.goto(`/tramo/${TRAMO}/cierre/ayer/por-la-tarde`)
    await expect(otra.getByTestId('sim-inicio')).toHaveValue('08:00')
    await expect(otra).toHaveURL(new RegExp(`/tramo/${TRAMO}/cierre$`))
  })
})

test.describe('«Cómo citar Oniel»', () => {
  test('está al final de «Cobertura y fuentes», con el ejemplo y los límites', async ({ page }) => {
    await page.goto('/cobertura')
    await page.getByTestId('cobertura-indice').getByRole('link', { name: 'Cómo citar Oniel' }).click()
    const apartado = page.getByTestId('cobertura-citar')
    await expect(apartado.getByRole('heading', { name: 'Cómo citar Oniel' })).toBeInViewport()
    // de quién son los datos: los operadores con horarios cargados, con su licencia, y el trazado
    const datos = page.getByTestId('citar-datos')
    for (const o of cobertura.operators.filter((o) => o.timetable === 'cargado')) await expect(datos).toContainText(o.name)
    await expect(datos).toContainText('CC BY 4.0')
    await expect(datos).toContainText('OpenStreetMap (ODbL 1.0)')
    // qué fecha poner, y un ejemplo con la dirección de una línea
    await expect(page.getByTestId('citar-fecha')).toContainText(`que hoy es el ${fechaLarga(DIA)}`)
    await expect(page.getByTestId('citar-ejemplo')).toContainText(/^Oniel, «Línea .+», con los horarios de .+ del \d+ de \S+ de \d{4}\. https:\/\/oniel\.vercel\.app\/linea\/\S+ \(consultado el \d+ de \S+ de \d{4}\)\.$/)
    // los límites: quién no publica horarios y que los tiempos del comparador son estimaciones
    const limites = page.getByTestId('citar-limites')
    for (const o of cobertura.operators.filter((o) => o.timetable === 'no_publicado')) await expect(limites).toContainText(`Faltan los trenes de ${o.name}`)
    await expect(limites).toContainText('son estimaciones sin paradas ni esperas')
    await expect(limites).toContainText('no anuncia ningún corte')
  })
})
