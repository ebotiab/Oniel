// Cómo abre el glosario cualquier componente del panel, por hondo que esté: App da la función y
// `Termino` la usa en el enlace «Ver en el glosario» de su nota.

import { createContext, useContext } from 'react'

/** Abre el glosario; con un id, en esa entrada (término o concepto). */
export type AbrirGlosario = (id: string | null) => void

export const GlosarioContext = createContext<AbrirGlosario>(() => {})

export function useAbrirGlosario(): AbrirGlosario {
  return useContext(GlosarioContext)
}

/** La ruta de una entrada del glosario, para que el enlace se pueda copiar o abrir en otra pestaña. */
export function hashGlosario(id: string | null): string {
  return id ? `#/glosario/${encodeURIComponent(id)}` : '#/glosario'
}
