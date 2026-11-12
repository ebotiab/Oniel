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

/** Dibujo de una anotación con geometría propia en el mapa: línea de puntos o de trazos, en tinta. */
export type Dibujo = 'puntos' | 'trazos'

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
  /**
   * Cómo se dibuja en el mapa una anotación del tipo con geometría propia; nulo si el tipo no las
   * dibuja. `aviso` dice en la ficha qué es y qué no es ese dibujo.
   */
  geometria: { dibujo: (a: AnnotationOut) => Dibujo; aviso: string } | null
  /** Entradas de la leyenda del mapa; cada una aparece mientras haya alguna anotación vigente que la cumpla. */
  leyenda: { clase: string; texto: string; testId: string; cuando?: (a: AnnotationOut) => boolean }[]
  /** Segmento de la URL de la ficha propia de cada anotación (`#/<ruta>/<id>`); nulo si el tipo no la tiene. */
  ruta: string | null
  /** Ficha: el bloque que explica una anotación en el panel, y su ficha propia si tiene ruta. */
  ficha: {
    clase: string
    rotulo: string
    senal: (a: AnnotationOut) => Senal
    testId: string
    /** Renglón de fechas: desde cuándo y lo que se sabe del final. Vacío si no hay nada que decir. */
    fechas: (a: AnnotationOut) => string
    /** Texto del enlace del bloque a la ficha propia. */
    enlace?: string
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
  geometria: null,
  leyenda: [{ clase: 'sin-circulacion', texto: 'Sin circulación hoy', testId: 'leyenda-interrupcion' }],
  ruta: null,
  ficha: {
    clase: 'interrupcion',
    rotulo: 'Interrupción del servicio',
    senal: () => SIN_CIRCULACION,
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

/** Los estados de un proyecto, como se dicen en el visor. */
export const ESTADO_DE_PROYECTO: Record<string, string> = {
  en_estudio: 'en estudio',
  en_proyecto: 'en proyecto',
  licitado: 'licitado',
  en_obras: 'en obras',
  parado: 'parado',
  sin_ejecutar: 'sin ejecutar',
  en_servicio: 'en servicio',
}

const enObras = (a: AnnotationOut) => a.status === 'en_obras'
const dibujoDeProyecto = (a: AnnotationOut): Dibujo => (enObras(a) ? 'trazos' : 'puntos')

/** Lo que se sabe de las fechas de un proyecto en obras; de los demás hablan sus hitos. */
function fechasDeProyecto(a: AnnotationOut): string {
  const partes: string[] = []
  if (a.start_date) partes.push(`Obras desde el ${formatDateLong(a.start_date)}.`)
  if (a.ended_on) partes.push(`En servicio desde el ${formatDateLong(a.ended_on)}.`)
  else if (a.expected_end_date) partes.push(`Final previsto: ${formatDateLong(a.expected_end_date)}.`)
  else if (a.expected_end_text) partes.push(`Final previsto: ${a.expected_end_text}.`)
  return partes.join(' ')
}

/**
 * Proyectos: lo previsto, en obras o parado alrededor de la red. En tinta y sin color: línea de
 * puntos lo que solo existe sobre el papel, trazos largos lo que está en obras (docs/diseno.md). Un
 * proyecto sobre una vía que ya existe no cambia su dibujo: se explica en la ficha de sus tramos.
 */
const proyecto: AnnotationLayer = {
  kind: 'proyecto',
  trazo: null,
  geometria: {
    dibujo: dibujoDeProyecto,
    aviso: 'La línea del mapa es un esbozo entre los lugares que nombra la fuente: no es el trazado del proyecto.',
  },
  leyenda: [
    { clase: 'de-proyecto', texto: 'Proyecto', testId: 'leyenda-proyecto', cuando: (a) => a.geometry !== null && !enObras(a) },
    { clase: 'de-proyecto-en-obras', texto: 'Proyecto en obras', testId: 'leyenda-proyecto-en-obras', cuando: (a) => a.geometry !== null && enObras(a) },
  ],
  ruta: 'proyecto',
  ficha: {
    clase: 'proyecto',
    rotulo: 'Proyecto',
    senal: (a) => ({ clase: 'gris', texto: ESTADO_DE_PROYECTO[a.status] ?? a.status }),
    testId: 'proyecto',
    fechas: fechasDeProyecto,
    enlace: 'Ver la ficha del proyecto',
  },
  lista: null,
  cobertura: {
    titulo: 'Proyectos',
    entrada:
      'Lo que está previsto, en obras o parado alrededor de las líneas cargadas, con su estado según la fuente. Se registran y se revisan a mano, cada uno con sus fuentes y la fecha de la última comprobación.',
    vacio: 'Oniel no tiene registrado ningún proyecto alrededor de las líneas cargadas.',
    testId: 'cobertura-proyectos',
  },
}

/** Las capas, en el orden en que se enseñan y en que mandan sobre el dibujo de un tramo. */
export const ANNOTATION_LAYERS: readonly AnnotationLayer[] = [interrupcion, proyecto]

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

/** La capa de la anotación cuya ficha propia tiene esta ruta (`#/<ruta>/<id>`). */
export function layerByRoute(ruta: string): AnnotationLayer | undefined {
  return ANNOTATION_LAYERS.find((l) => l.ruta === ruta)
}

/** El enlace a la ficha propia de una anotación; nulo si su tipo no la tiene. */
export function annotationHref(a: AnnotationOut): string | null {
  const ruta = annotationLayer(a.kind)?.ruta
  return ruta ? `#/${ruta}/${encodeURIComponent(a.id)}` : null
}

/** Las entradas de leyenda que tocan con estas anotaciones, en el orden del registro. */
export function leyendaDe(annotations: readonly AnnotationOut[]) {
  return ANNOTATION_LAYERS.flatMap((l) =>
    l.leyenda.filter((e) => annotations.some((a) => a.kind === l.kind && (e.cuando?.(a) ?? true))).map((e) => ({ kind: l.kind, ...e })),
  )
}

/** El dibujo en el mapa de una anotación con geometría propia; nulo si no se dibuja. */
export function dibujoDe(a: AnnotationOut): Dibujo | null {
  if (!a.geometry) return null
  return annotationLayer(a.kind)?.geometria?.dibujo(a) ?? null
}
