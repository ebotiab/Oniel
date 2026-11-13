import type { Page } from '@playwright/test'

export type Seccion = 'mapa' | 'recorridos' | 'glosario' | 'cobertura'

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
