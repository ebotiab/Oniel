// Registro de capas de anotaciones: una entrada por tipo, con todo lo que el visor necesita para
// enseñarlo. El mapa, el esquema de línea, la leyenda, la ficha y las listas leen de aquí, así que
// un tipo nuevo (una obra, un proyecto) es una entrada más y no toca ninguno de ellos. Los textos
// y los colores de cada entrada son decisiones de diseño: se anotan en docs/diseno.md.

import type { AnnotationOut } from '../data/types.ts'
import { ROJA } from '../map/colors.ts'
import { formatDateLong, mainSourceLabel } from './annotations.ts'

/** Una etiqueta de color junto a un texto («sin circulación»). */
export interface Senal {
  /** Clases de la etiqueta, además de `senal`. */
  clase: string
  texto: string
}

export interface AnnotationLayer {
  /** El tipo de anotación (`kind`) que dibuja esta capa. */
  kind: string
  /**
   * Cómo se marcan sus tramos mientras está vigente, en el mapa y en el esquema de línea; nulo si
   * el tipo no cambia el dibujo de la vía.
   */
  trazo: {
    /** Propiedad con la que se marca el tramo en el mapa y atributo `data-` en el esquema. */
    propiedad: string
    /** Color en el mapa y el mismo color como variable CSS para el esquema. */
    color: string
    colorCss: string
    /** Opacidad del halo cuando el tramo está además seleccionado. */
    haloSeleccionado: number
    /** Lo que se añade a la descripción del tramo para quien no ve el color. */
    descripcion: string
  } | null
  /** Entrada de la leyenda del mapa; solo aparece cuando hay alguna anotación vigente del tipo. */
  leyenda: { clase: string; texto: string; testId: string } | null
  /** Ficha: el bloque que explica una anotación en el panel. */
  ficha: {
    clase: string
    rotulo: string
    senal: Senal
    testId: string
    /** Renglón de fechas: desde cuándo y lo que se sabe del final. */
    fechas: (a: AnnotationOut) => string
  }
  /** Notas en las listas: junto a una línea de la red y en la cabecera de la línea. */
  lista: {
    /** Etiqueta junto a una línea con alguna anotación vigente del tipo. */
    senal: Senal
    /** Lista de la cabecera de la línea: su rótulo y, por anotación, el enlace y el dato que lo sigue. */
    rotulo: string
    testId: string
    enlace: (a: AnnotationOut) => string
    detalle: (a: AnnotationOut) => string
  } | null
  /** Sección del panel «Qué hay en esta versión». */
  cobertura: { titulo: string; entrada: string; vacio: string; testId: string }
}

/** Lo que se sabe del final de una interrupción: la reanudación, la previsión publicada o que no hay fecha. */
export function endLabel(a: AnnotationOut): string {
  if (a.ended_on) return `La circulación se reanudó el ${formatDateLong(a.ended_on)}.`
  if (a.expected_end_date) return `Reanudación prevista: ${formatDateLong(a.expected_end_date)}.`
  if (a.expected_end_text) return `Reanudación prevista: ${a.expected_end_text}.`
  return 'Sin fecha prevista de reanudación.'
}

const desde = (a: AnnotationOut) => (a.start_date ? `desde el ${formatDateLong(a.start_date)}` : '')

const SIN_CIRCULACION: Senal = { clase: 'roja', texto: 'sin circulación' }

/** Interrupciones del servicio: el rojo de «sin circulación» (docs/diseno.md). */
const interrupcion: AnnotationLayer = {
  kind: 'interrupcion',
  trazo: { propiedad: 'interrumpido', color: ROJA, colorCss: 'var(--senal-roja)', haloSeleccionado: 0.3, descripcion: 'sin circulación hoy' },
  leyenda: { clase: 'sin-circulacion', texto: 'Sin circulación hoy', testId: 'leyenda-interrupcion' },
  ficha: {
    clase: 'interrupcion',
    rotulo: 'Interrupción del servicio',
    senal: SIN_CIRCULACION,
    testId: 'interrupcion',
    fechas: (a) => `${a.start_date ? `Desde el ${formatDateLong(a.start_date)}. ` : ''}${endLabel(a)}`,
  },
  lista: {
    senal: { clase: 'roja', texto: 'un tramo sin circulación' },
    rotulo: 'Tramos sin circulación hoy',
    testId: 'cortes-linea',
    enlace: (a) => `Sin circulación entre ${a.from_name} y ${a.to_name}`,
    detalle: (a) => `${desde(a)} (${mainSourceLabel(a)})`,
  },
  cobertura: {
    titulo: 'Interrupciones del servicio',
    entrada:
      'Tramos de las líneas cargadas en los que hoy no circulan trenes. Se registran y se revisan a mano, cada una con sus fuentes y la fecha de la última comprobación.',
    vacio: 'Oniel no tiene registrada ninguna interrupción vigente hoy en las líneas cargadas.',
    testId: 'cobertura-interrupciones',
  },
}

/** Las capas, en el orden en que se enseñan y en que mandan sobre el dibujo de un tramo. */
export const ANNOTATION_LAYERS: readonly AnnotationLayer[] = [interrupcion]

export function annotationLayer(kind: string): AnnotationLayer | undefined {
  return ANNOTATION_LAYERS.find((l) => l.kind === kind)
}

/** Capas con trazo propio: las que cambian el dibujo de la vía. */
export const CAPAS_CON_TRAZO = ANNOTATION_LAYERS.flatMap((l) => (l.trazo ? [{ kind: l.kind, ...l.trazo }] : []))

/** La capa que manda en el dibujo de un tramo: la primera del registro con trazo entre sus anotaciones. */
export function trazoDe(annotations: readonly AnnotationOut[] | undefined) {
  if (!annotations?.length) return null
  return CAPAS_CON_TRAZO.find((c) => annotations.some((a) => a.kind === c.kind)) ?? null
}

/** Las capas que tienen alguna de estas anotaciones, en el orden del registro. */
export function capasDe(annotations: readonly AnnotationOut[] | undefined): AnnotationLayer[] {
  if (!annotations?.length) return []
  return ANNOTATION_LAYERS.filter((l) => annotations.some((a) => a.kind === l.kind))
}
