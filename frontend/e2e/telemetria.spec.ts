import { expect, test, type Page, type Request } from '@playwright/test'


// El visor envía a Logfire sus errores, y solo sus errores, cuando está publicado en producción y
// tiene token (src/telemetria/). El servidor de desarrollo de las demás pruebas no tiene token; el de
// URL_TELEMETRIA es el visor compilado como en producción con uno de mentira. Ninguna petición sale
// de verdad: la prueba responde por Logfire.

/** El visor compilado con el token de prueba; el puerto es el que le da playwright.config.ts. */
const URL_TELEMETRIA = `http://127.0.0.1:${Number(process.env.ONIEL_E2E_PORT_TELEMETRIA ?? Number(process.env.ONIEL_E2E_PORT ?? 5199) + 1)}`
const LOGFIRE = 'https://logfire-us.pydantic.dev'

/** Lo que estas pruebas tocan de la ventana del navegador. */
interface Ventana {
  setTimeout(fn: () => void): void
  dispatchEvent(e: unknown): void
}

/** Responde por Logfire y guarda cada petición que el visor le hace. */
async function escucharLogfire(page: Page): Promise<Request[]> {
  const peticiones: Request[] = []
  await page.route(`${LOGFIRE}/**`, async (route) => {
    peticiones.push(route.request())
    await route.fulfill({ status: 200, contentType: 'application/json', body: '{}' })
  })
  return peticiones
}

/** Una excepción no controlada, como la de un fallo del visor. */
const provocarError = (page: Page) =>
  page.evaluate(() => {
    ;(globalThis as unknown as Ventana).setTimeout(() => {
      throw new Error('error provocado por la prueba')
    })
  })

/** El SDK envía lo que tenga pendiente cuando la página se oculta; así no hay que esperar a su temporizador. */
const vaciarEnvios = (page: Page) =>
  page.evaluate(() => (globalThis as unknown as Ventana).dispatchEvent(new Event('pagehide')))

test.describe('Errores del visor en Logfire', () => {
  test('sin token no sale ninguna petición hacia Logfire ni se descarga el SDK, tampoco con un error', async ({ page }) => {
    const peticiones = await escucharLogfire(page)
    const ficheros: string[] = []
    page.on('request', (r) => ficheros.push(new URL(r.url()).pathname))
    page.on('pageerror', () => undefined)
    await page.goto('/')
    await expect(page.getByTestId('vista-red').first()).toBeVisible()
    await provocarError(page)
    await vaciarEnvios(page)
    await page.waitForTimeout(1_000)
    expect(peticiones).toHaveLength(0)
    expect(ficheros.filter((f) => /logfire|opentelemetry/i.test(f))).toEqual([])
  })

  test('con token, una visita sin errores no envía nada', async ({ page }) => {
    const peticiones = await escucharLogfire(page)
    const sdk = page.waitForResponse((r) => /\/assets\/logfire-.*\.js$/.test(new URL(r.url()).pathname))
    await page.goto(`${URL_TELEMETRIA}/`)
    await expect(page.getByTestId('vista-red').first()).toBeVisible()
    // el SDK se descarga aparte, sin retrasar el primer pintado
    expect((await sdk).ok()).toBe(true)
    await page.goto(`${URL_TELEMETRIA}/glosario/via-unica`)
    await expect(page.getByTestId('glosario-indice').first()).toBeVisible()
    await vaciarEnvios(page)
    await page.waitForTimeout(1_000)
    expect(peticiones).toHaveLength(0)
  })

  test('con token, un error provocado envía una sola petición con un solo registro', async ({ page }) => {
    const peticiones = await escucharLogfire(page)
    page.on('pageerror', () => undefined)
    await page.goto(`${URL_TELEMETRIA}/glosario/via-unica?prueba=1#ancla`)
    await expect(page.getByTestId('glosario-indice').first()).toBeVisible()
    await provocarError(page)
    await expect.poll(() => peticiones.length, { timeout: 10_000 }).toBeGreaterThan(0)
    await vaciarEnvios(page)
    await page.waitForTimeout(1_000)
    expect(peticiones).toHaveLength(1)

    const peticion = peticiones[0]!
    expect(peticion.method()).toBe('POST')
    expect(new URL(peticion.url()).pathname).toBe('/v1/traces')
    expect(peticion.headers()['authorization']).toBe('Bearer token-de-prueba')

    const cuerpo = peticion.postData() ?? ''
    const envio = JSON.parse(cuerpo) as {
      resourceSpans: {
        resource: { attributes: { key: string; value: Record<string, unknown> }[] }
        scopeSpans: { spans: { name: string; attributes: { key: string; value: Record<string, unknown> }[] }[] }[]
      }[]
    }
    const registros = envio.resourceSpans.flatMap((r) => r.scopeSpans.flatMap((s) => s.spans))
    expect(registros).toHaveLength(1)
    expect(registros[0]!.name).toBe('Uncaught error')
    const atributos = (lista: { key: string; value: Record<string, unknown> }[]) =>
      Object.fromEntries(lista.map((a) => [a.key, a.value.stringValue ?? a.value.boolValue ?? a.value]))

    // entorno y versión: producción y el commit que compila Vercel
    const recurso = atributos(envio.resourceSpans[0]!.resource.attributes)
    expect(recurso['deployment.environment.name']).toBe('production')
    expect(recurso['service.version']).toBe('c0ffee0')

    // del error: su mensaje, su traza y la ruta del visor, sin parámetros ni fragmento
    const error = atributos(registros[0]!.attributes)
    expect(error['logfire.page.url.path']).toBe('/glosario/via-unica')
    expect(error['exception.message']).toBe('error provocado por la prueba')
    // con la huella que Error tracking necesita para agruparlo y avisar
    expect(String(error['logfire.exception.fingerprint'] ?? '')).not.toBe('')
    expect(cuerpo).not.toContain('prueba=1')
    expect(cuerpo).not.toContain('ancla')
    // nada que identifique a quien visita ni a su sesión
    expect(Object.keys({ ...recurso, ...error }).filter((k) => /session|user\.|client\.address/.test(k))).toEqual([])
    expect(await page.evaluate(() => Object.keys(sessionStorage).concat(Object.keys(localStorage)))).not.toContain(
      'lf_browser_session',
    )
  })
})
