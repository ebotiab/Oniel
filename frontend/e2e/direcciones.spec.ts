import { expect, test } from '@playwright/test'

// Las direcciones del visor son limpias (`/tramo/<id>`). Hasta noviembre de 2026 iban detrás de una
// almohadilla (`/#/tramo/<id>`): esos enlaces siguen valiendo y el visor los pasa a la dirección limpia
// sin recargar la página.

const TRAMO = 'lav-madrid-sevilla:urda:ciudad-real'
const MADRID = 'madrid-puerta-de-atocha'

/** Una ruta de cada tipo, con algo que solo se ve en su vista. */
const RUTAS: { ruta: string; testId: string }[] = [
  { ruta: '/', testId: 'vista-red' },
  { ruta: '/linea/manzanares-ciudad-real', testId: 'ficha-linea' },
  { ruta: '/nodo/ciudad-real', testId: 'recorridos-desde-aqui' },
  { ruta: `/tramo/${TRAMO}`, testId: 'detalle-tramo' },
  { ruta: `/tramo/${TRAMO}/cierre`, testId: 'panel-simulacion' },
  { ruta: `/escenario/c~${TRAMO}`, testId: 'panel-simulacion' },
  { ruta: '/recorridos', testId: 'comparador' },
  { ruta: `/recorridos/${MADRID}/cordoba`, testId: 'comparador' },
  { ruta: `/recorridos/${MADRID}/ciudad-real/c~${TRAMO}`, testId: 'recorridos-escenario' },
  { ruta: '/glosario', testId: 'glosario-indice' },
  { ruta: '/glosario/via-unica', testId: 'glosario-indice' },
  { ruta: '/cobertura', testId: 'cobertura-indice' },
  { ruta: '/proyecto/proyecto-lav-mora-alcazar', testId: 'ficha-proyecto' },
]

/** Lo que estas pruebas tocan de la ventana del navegador. */
interface Ventana {
  marca?: boolean
  location: { hash: string }
}

/** La dirección completa de una ruta del visor, sin almohadilla ni nada detrás. */
const direccion = (baseURL: string | undefined, ruta: string) => `${baseURL}${ruta}`

test.describe('Direcciones limpias', () => {
  for (const { ruta, testId } of RUTAS) {
    test(`${ruta} carga al entrar directamente y al recargar`, async ({ page, baseURL }) => {
      const datos: number[] = []
      page.on('response', (r) => {
        if (new URL(r.url()).pathname === '/data/index.json') datos.push(r.status())
      })
      await page.goto(ruta)
      await expect(page.getByTestId(testId).first()).toBeVisible()
      await expect(page).toHaveURL(direccion(baseURL, ruta))
      // los datos se piden a la raíz del sitio, no a una carpeta de la ruta; una página que no
      // los necesita para pintarse (el glosario) puede estar a la vista antes de que lleguen
      await expect.poll(() => datos.length).toBeGreaterThan(0)
      expect(datos.every((estado) => estado === 200)).toBe(true)
      await page.reload()
      await expect(page.getByTestId(testId).first()).toBeVisible()
      await expect(page).toHaveURL(direccion(baseURL, ruta))
    })

    test(`el enlace antiguo /#${ruta} lleva a ${ruta}`, async ({ page, baseURL }) => {
      let cargas = 0
      page.on('load', () => cargas++)
      await page.goto(`/#${ruta}`)
      await expect(page.getByTestId(testId).first()).toBeVisible()
      await expect(page).toHaveURL(direccion(baseURL, ruta))
      // la dirección cambia sin volver a cargar la página
      expect(cargas).toBe(1)
    })
  }

  test('un enlace antiguo pegado con el visor abierto cambia de vista sin recargar', async ({ page, baseURL }) => {
    await page.goto('/')
    await expect(page.getByTestId('vista-red')).toBeVisible()
    await page.evaluate(() => {
      const ventana = globalThis as unknown as Ventana
      ventana.marca = true
      ventana.location.hash = '#/linea/manzanares-ciudad-real'
    })
    await expect(page.getByTestId('ficha-linea')).toBeVisible()
    await expect(page).toHaveURL(direccion(baseURL, '/linea/manzanares-ciudad-real'))
    expect(await page.evaluate(() => (globalThis as unknown as Ventana).marca)).toBe(true)
  })

  test('el salto al contenido no cambia de vista', async ({ page }) => {
    await page.goto('/nodo/ciudad-real')
    await expect(page.getByTestId('recorridos-desde-aqui')).toBeVisible()
    await page.evaluate(() => {
      ;(globalThis as unknown as Ventana).location.hash = '#panel'
    })
    await expect(page).toHaveURL(/\/nodo\/ciudad-real#panel$/)
    await expect(page.getByTestId('recorridos-desde-aqui')).toBeVisible()
  })

  test('el enlace a la ficha de un proyecto no recarga la página y «atrás» vuelve al tramo', async ({ page }) => {
    await page.goto('/tramo/convencional-madrid-alcazar-cordoba:venta-de-cardenas:vilches')
    let cargas = 0
    page.on('load', () => cargas++)
    const enlace = page.getByTestId('proyecto-enlace').first()
    await expect(enlace).toBeVisible()
    await enlace.click()
    await expect(page.getByTestId('ficha-proyecto')).toBeVisible()
    await expect(page).toHaveURL(/\/proyecto\/[a-z0-9-]+$/)
    await page.goBack()
    await expect(page).toHaveURL(/\/tramo\/convencional-madrid-alcazar-cordoba:venta-de-cardenas:vilches$/)
    await expect(page.getByTestId('ficha-proyecto')).toHaveCount(0)
    expect(cargas).toBe(0)
  })
})
