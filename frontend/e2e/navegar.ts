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

export type Zona = 'cataluna' | 'levante' | 'madrid-castilla-la-mancha' | 'extremadura' | 'andalucia'

/**
 * Despliega una zona de la lista de líneas si está plegada. Con más de doce líneas la lista arranca
 * como un índice de zonas (`FOLD_ABOVE`), y para elegir una línea hay que abrir antes la suya.
 */
export async function abrirZona(page: Page, zona: Zona) {
  const cabecera = page.getByTestId(`zona-${zona}`).locator('.zona-cabecera')
  if ((await cabecera.getAttribute('aria-expanded')) !== 'true') await cabecera.click()
}
