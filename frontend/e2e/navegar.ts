import type { Page } from '@playwright/test'

export type Seccion = 'mapa' | 'recorridos' | 'sin-otro-camino' | 'glosario' | 'cobertura'

/** En el móvil los enlaces de la cabecera van tras «Menú»: lo abre si está cerrado. */
export async function abrirMenu(page: Page) {
  const boton = page.getByTestId('nav-menu-boton')
  if ((await boton.isVisible()) && (await boton.getAttribute('aria-expanded')) !== 'true') await boton.click()
}

/** Va a una sección por la navegación de la cabecera, como lo haría un visitante en escritorio o en el móvil. */
export async function irA(page: Page, seccion: Seccion) {
  await abrirMenu(page)
  await page.getByTestId(`nav-${seccion}`).click()
}

/**
 * Abre las zonas plegadas de la lista de líneas. Con más de doce líneas la lista arranca como un
 * índice de zonas y ninguna línea está a la vista: quien va a pulsar una tiene que abrir antes la suya.
 */
export async function abrirZonas(page: Page) {
  const lista = page.getByTestId('lista-lineas')
  await lista.locator('.zona-cabecera').first().waitFor()
  const plegadas = lista.locator('.zona-cabecera[aria-expanded="false"]')
  // cada zona abierta deja de casar con el selector: se abre siempre la primera que quede
  while ((await plegadas.count()) > 0) await plegadas.first().click()
}
