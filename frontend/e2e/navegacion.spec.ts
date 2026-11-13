import { expect, test } from '@playwright/test'

import { abrirMenu, irA } from './navegar.ts'

// La navegación de la cabecera: la misma en el mapa y en las páginas de lectura, con la sección a la vista marcada.
test.describe('Navegación de la cabecera', () => {
  test('lleva a las cinco secciones y marca la que se está viendo', async ({ page }) => {
    await page.goto('/')
    await expect(page.getByTestId('vista-red')).toBeVisible()
    await abrirMenu(page)
    const nav = page.getByTestId('nav')
    await expect(nav.getByRole('link')).toHaveText([/^Mapa/, /^Comparar recorridos/, /^Tramos sin otro camino/, /^Glosario/, /^Cobertura y fuentes/])
    await expect(page.getByTestId('nav-mapa')).toHaveAttribute('aria-current', 'page')

    await irA(page, 'recorridos')
    await expect(page).toHaveURL(/\/recorridos$/)
    await expect(page.getByTestId('comparador')).toBeVisible()
    await abrirMenu(page)
    await expect(page.getByTestId('nav-recorridos')).toHaveAttribute('aria-current', 'page')
    await expect(page.getByTestId('nav-mapa')).not.toHaveAttribute('aria-current', 'page')

    await irA(page, 'sin-otro-camino')
    await expect(page).toHaveURL(/\/sin-otro-camino$/)
    await expect(page.getByTestId('vista-sin-otro-camino')).toBeVisible()
    await abrirMenu(page)
    await expect(page.getByTestId('nav-sin-otro-camino')).toHaveAttribute('aria-current', 'page')
    await irA(page, 'recorridos')

    // de una página de lectura a otra sin pasar por el mapa: la cabecera es la misma
    await irA(page, 'glosario')
    await expect(page).toHaveURL(/\/glosario$/)
    await expect(page.getByTestId('pagina-glosario')).toBeVisible()
    await abrirMenu(page)
    await expect(page.getByTestId('nav-glosario')).toHaveAttribute('aria-current', 'page')
    await irA(page, 'cobertura')
    await expect(page).toHaveURL(/\/cobertura$/)
    await expect(page.getByTestId('pagina-cobertura')).toBeVisible()
    await abrirMenu(page)
    await expect(page.getByTestId('nav-cobertura')).toHaveAttribute('aria-current', 'page')

    // «Mapa» devuelve a lo que se estaba viendo antes de las páginas: el comparador
    await irA(page, 'mapa')
    await expect(page).toHaveURL(/\/recorridos$/)
    await expect(page.getByTestId('comparador')).toBeVisible()
    // y, ya en el mapa, lleva a la vista de la red
    await irA(page, 'mapa')
    await expect(page).toHaveURL(/\/$/)
    await expect(page.getByTestId('vista-red')).toBeVisible()
  })

  test('la vista de la red ya no lleva los enlaces al pie, y la cabecera no tapa las páginas', async ({ page }) => {
    await page.goto('/')
    const red = page.getByTestId('vista-red')
    await expect(red).toBeVisible()
    await expect(red.getByText('Cobertura y fuentes')).toHaveCount(0)
    await expect(red.getByText('Comparar recorridos')).toHaveCount(0)

    await page.goto('/cobertura')
    const titulo = page.getByTestId('pagina-cobertura').getByRole('heading', { level: 1 })
    await expect(titulo).toBeVisible()
    const cabecera = (await page.locator('.cabecera').boundingBox())!
    expect((await titulo.boundingBox())!.y).toBeGreaterThan(cabecera.y + cabecera.height)
    // la marca lleva a la vista de la red desde una página
    await page.getByTestId('marca').click()
    await expect(page).toHaveURL(/\/$/)
    await expect(red).toBeVisible()
  })

  test('los enlaces son direcciones reales: se pueden abrir en otra pestaña', async ({ page }) => {
    await page.goto('/')
    await abrirMenu(page)
    await expect(page.getByTestId('nav-mapa')).toHaveAttribute('href', '/')
    await expect(page.getByTestId('nav-recorridos')).toHaveAttribute('href', '/recorridos')
    await expect(page.getByTestId('nav-sin-otro-camino')).toHaveAttribute('href', '/sin-otro-camino')
    await expect(page.getByTestId('nav-glosario')).toHaveAttribute('href', '/glosario')
    await expect(page.getByTestId('nav-cobertura')).toHaveAttribute('href', '/cobertura')
  })

  test('en el móvil los enlaces van tras «Menú», que se cierra al elegir y con Escape', async ({ page, isMobile }) => {
    test.skip(!isMobile, 'el menú solo existe en la composición del móvil')
    await page.goto('/')
    await expect(page.getByTestId('vista-red')).toBeVisible()
    await expect(page.getByTestId('nav')).toHaveCount(0)
    const boton = page.getByTestId('nav-menu-boton')
    await expect(boton).toHaveText('Menú')
    await boton.click()
    await expect(boton).toHaveAttribute('aria-expanded', 'true')
    // cada enlace lleva su nombre completo y una frase
    await expect(page.getByTestId('nav-cobertura')).toContainText('Qué hay cargado y de dónde sale')
    await page.keyboard.press('Escape')
    await expect(page.getByTestId('nav')).toHaveCount(0)
    await boton.click()
    await page.getByTestId('nav-glosario').click()
    await expect(page).toHaveURL(/\/glosario$/)
    await expect(page.getByTestId('nav')).toHaveCount(0)
    // la cabecera cabe en la pantalla: nada se sale por la derecha
    const caja = (await boton.boundingBox())!
    expect(caja.x + caja.width).toBeLessThanOrEqual(page.viewportSize()!.width)
  })

  test('sin servidor, la cabecera lo dice con una etiqueta gris', async ({ page }) => {
    test.skip(!process.env.ONIEL_E2E_STATIC, 'con la API arrancada el servidor responde y la etiqueta no aparece')
    await page.goto('/')
    await expect(page.getByTestId('vista-red')).toBeVisible()
    await abrirMenu(page)
    await expect(page.getByTestId('estado-servidor')).toHaveText('vista estática')
  })
})
