import type { Page } from '@playwright/test'

/** Retiene solo este recurso; al soltarlo, el servidor entrega el fichero real. */
export async function retener(page: Page, url: string | RegExp) {
  let soltar!: () => void
  const retenida = new Promise<void>((resolve) => { soltar = resolve })
  await page.route(url, async (route) => {
    await retenida
    await route.continue().catch(() => {}) // puede haberse cancelado al cerrar la página
  })
  return soltar
}
