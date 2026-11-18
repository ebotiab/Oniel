import { expect, test, type Page } from '@playwright/test'


// El visor publicado en producción cuenta sus visitas con Vercel Web Analytics (src/telemetria/visitas.ts).
// El script que cuenta lo sirve Vercel; en el visor compilado de URL_TELEMETRIA ocupa su sitio un fichero
// vacío (playwright.config.ts), así que nada sale de la prueba. Lo que se comprueba es lo que decide el
// visor: si carga el script, qué dirección dejaría salir y qué navegadores deja fuera.

/** El visor compilado como en producción; el puerto es el que le da playwright.config.ts. */
const URL_TELEMETRIA = `http://127.0.0.1:${Number(process.env.ONIEL_E2E_PORT_TELEMETRIA ?? Number(process.env.ONIEL_E2E_PORT ?? 5199) + 1)}`
const SCRIPT = '/_vercel/insights/script.js'
const CLAVE_NO_CONTAR = 'oniel:visitas:no-contar'

/** Lo que estas pruebas tocan de la ventana del navegador. */
interface Ventana {
  va?: unknown
  vaq?: [string, unknown][]
  localStorage: { getItem(clave: string): string | null }
}

/**
 * Pasa una página vista por el filtro que el visor le da al script y devuelve la dirección que saldría,
 * o `null` si la visita no se cuenta.
 */
const direccionEnviada = (page: Page, url: string) =>
  page.evaluate((direccion) => {
    const cola = (globalThis as unknown as Ventana).vaq ?? []
    const filtro = cola.find(([nombre]) => nombre === 'beforeSend')?.[1] as
      | ((evento: { type: 'pageview'; url: string }) => { url: string } | null)
      | undefined
    if (filtro === undefined) throw new Error('el visor no ha dado ningún filtro al script')
    return filtro({ type: 'pageview', url: direccion })?.url ?? null
  }, url)

const marca = (page: Page) =>
  page.evaluate((clave) => (globalThis as unknown as Ventana).localStorage.getItem(clave), CLAVE_NO_CONTAR)

test.describe('Visitas del visor', () => {
  test('fuera de producción no se carga el script ni se prepara ningún envío', async ({ page }) => {
    const ficheros: string[] = []
    page.on('request', (r) => ficheros.push(new URL(r.url()).pathname))
    await page.goto('/?visitas=no')
    await expect(page.getByTestId('vista-red').first()).toBeVisible()
    expect(ficheros.filter((f) => f.startsWith('/_vercel/'))).toEqual([])
    expect(await page.evaluate(() => typeof (globalThis as unknown as Ventana).va)).toBe('undefined')
    // el parámetro tampoco hace nada: no hay recuento del que salirse
    expect(await marca(page)).toBeNull()
  })

  test('publicado, carga el script una vez y de cada página sale solo el origen y la ruta', async ({ page }) => {
    const cargas: string[] = []
    page.on('request', (r) => {
      if (new URL(r.url()).pathname === SCRIPT) cargas.push(r.url())
    })
    const script = page.waitForResponse((r) => new URL(r.url()).pathname === SCRIPT)
    await page.goto(`${URL_TELEMETRIA}/glosario/via-unica?prueba=1#ancla`)
    await expect(page.getByTestId('glosario-indice').first()).toBeVisible()
    expect((await script).ok()).toBe(true)
    expect(cargas).toEqual([`${URL_TELEMETRIA}${SCRIPT}`])
    expect(await direccionEnviada(page, `${URL_TELEMETRIA}/glosario/via-unica?prueba=1#ancla`)).toBe(
      `${URL_TELEMETRIA}/glosario/via-unica`,
    )
    // nada guardado en el navegador de quien visita
    expect(await marca(page)).toBeNull()
  })

  test('con ?visitas=no ese navegador deja de contarse y con ?visitas=si vuelve a contarse', async ({ page }) => {
    await page.goto(`${URL_TELEMETRIA}/glosario/via-unica?visitas=no`)
    await expect(page.getByTestId('glosario-indice').first()).toBeVisible()
    // el parámetro se retira de la dirección: es la señal de que se ha aplicado
    await expect(page).toHaveURL(`${URL_TELEMETRIA}/glosario/via-unica`)
    expect(await direccionEnviada(page, `${URL_TELEMETRIA}/glosario/via-unica`)).toBeNull()

    // la marca sigue en las visitas siguientes
    await page.goto(`${URL_TELEMETRIA}/`)
    await expect(page.getByTestId('vista-red').first()).toBeVisible()
    expect(await direccionEnviada(page, `${URL_TELEMETRIA}/`)).toBeNull()

    await page.goto(`${URL_TELEMETRIA}/?visitas=si`)
    await expect(page.getByTestId('vista-red').first()).toBeVisible()
    await expect(page).toHaveURL(`${URL_TELEMETRIA}/`)
    expect(await direccionEnviada(page, `${URL_TELEMETRIA}/`)).toBe(`${URL_TELEMETRIA}/`)
    expect(await marca(page)).toBeNull()
  })

  test.describe('desde el navegador de la app de Claude', () => {
    test.use({
      userAgent:
        'Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 (KHTML, like Gecko) Claude/5.1231.2 Chrome/156.0.8078.75 Safari/537.36',
    })

    test('la visita no se cuenta', async ({ page }) => {
      await page.goto(`${URL_TELEMETRIA}/`)
      await expect(page.getByTestId('vista-red').first()).toBeVisible()
      expect(await direccionEnviada(page, `${URL_TELEMETRIA}/`)).toBeNull()
    })
  })
})
