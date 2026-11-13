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
 * Despliega las zonas de la lista de líneas. Con más de doce líneas las zonas empiezan plegadas
 * (docs/diseno.md, «Elegir línea»): una prueba que busca una línea en la lista las abre antes.
 */
export async function abrirZonas(page: Page) {
  const lista = page.getByTestId('lista-lineas')
  await lista.locator('.zona-cabecera').first().waitFor()
  const plegadas = lista.locator('.zona-cabecera[aria-expanded="false"]')
  while ((await plegadas.count()) > 0) await plegadas.first().click()
}
