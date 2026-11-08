// Etiquetas y clases de color de los tipos de paso y de los estados de un cierre.
// Van en un módulo propio para que los ficheros de componentes solo exporten componentes.

import type { ClosureStatus, PassKind } from '../data/types'

export const KIND: Record<PassKind, { label: string; cls: string }> = {
  publicado: { label: 'publicado', cls: 'verde' },
  estimado: { label: 'estimado', cls: 'ambar' },
  indeterminado: { label: 'indeterminado', cls: 'gris' },
}

export const STATUS: Record<ClosureStatus, { label: string; plural: string; cls: string }> = {
  afectado_publicado: { label: 'afectado · horario publicado', plural: 'Afectados con horario publicado', cls: 'roja' },
  afectado_estimado: { label: 'afectado · paso estimado', plural: 'Afectados con paso estimado', cls: 'ambar' },
  indeterminado: { label: 'indeterminado', plural: 'Indeterminados', cls: 'gris' },
  no_afectado: { label: 'no afectado', plural: 'No afectados', cls: 'verde' },
}
