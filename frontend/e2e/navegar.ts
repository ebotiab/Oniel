import type { Page } from '@playwright/test'

import { zonaDeLinea } from './instantanea.ts'

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
 * Despliega todas las zonas de la lista de líneas, que con más de doce líneas empiezan plegadas
 * (docs/diseno.md, «Elegir línea»). Solo para la prueba que mira la lista entera: cada despliegue
 * cambia qué líneas resalta el mapa y lo repinta, y en el móvil del CI, que pinta sin tarjeta
 * gráfica, son de 1,3 a 2 segundos por zona. La prueba que solo quiere llegar a una línea usa
 * `abrirLinea`, que cuesta lo mismo con ocho zonas que con quince.
 */
export async function abrirZonas(page: Page) {
  const lista = page.getByTestId('lista-lineas')
  await lista.locator('.zona-cabecera').first().waitFor()
  const plegadas = lista.locator('.zona-cabecera[aria-expanded="false"]')
  while ((await plegadas.count()) > 0) await plegadas.first().click()
}

/** Despliega una sola zona de la lista de líneas, si está plegada. */
export async function abrirZona(page: Page, id: string) {
  const cabecera = page.getByTestId(`zona-${id}`).locator('.zona-cabecera')
  await cabecera.waitFor()
  if ((await cabecera.getAttribute('aria-expanded')) !== 'true') await cabecera.click()
}

/**
 * Abre una línea desde la lista, como un visitante: despliega la zona en la que está (la lee de la
 * instantánea, así que la prueba no tiene que saberla) y toca su renglón. Vale también para un
 * baipás o un enlace, que van en la zona de la línea de la que cuelgan.
 */
export async function abrirLinea(page: Page, lineId: string) {
  await abrirZona(page, zonaDeLinea(lineId))
  await page.getByTestId(`linea-${lineId}`).click()
}
