// Navegación dentro del visor sin recargar la página. Las rutas las construye `routePath` y las interpreta
// `parseRoute` (`state.ts`); aquí solo está cómo se llega a una desde un enlace.

import type { MouseEvent } from 'react'

/** Lleva el visor a una ruta suya, con una entrada nueva en el historial; App la lee al recibir `popstate`. */
export function navegar(path: string): void {
  if (path !== window.location.pathname) window.history.pushState(null, '', path)
  window.dispatchEvent(new PopStateEvent('popstate'))
}

/** El clic pide abrir el enlace aparte (Ctrl, ⌘, mayúsculas o el botón central): se deja al navegador. */
export function abreAparte(e: MouseEvent): boolean {
  return e.metaKey || e.ctrlKey || e.shiftKey || e.button !== 0
}
