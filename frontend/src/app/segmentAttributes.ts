// Lista de atributos de tramo: una entrada por atributo, con todo lo que la ficha del tramo
// necesita para enseñarlo. Los valores llegan en `segment.attributes`, repartidos desde las
// secciones que declara la especificación de cada línea (docs/datos.md, «Atributos de tramo»); un
// atributo nuevo es declarar sus secciones allí y añadir aquí su entrada. La etiqueta, el texto de
// cada valor y el sitio de la ficha son decisiones de diseño: se anotan en docs/diseno.md.

import type { AttributeScalar, AttributeValue, LineSummary, SegmentOut } from '../data/types.ts'
import type { TerminoId } from '../panel/glosario.ts'
import { tracksLabel } from './state.ts'

export interface SegmentAttribute {
  /** La clave del atributo en `segment.attributes`: el `attribute` de sus secciones. */
  clave: string
  /** Cómo se llama en la ficha. */
  etiqueta: string
  /** Si la etiqueta es un término del glosario, cuál. */
  terminoEtiqueta?: TerminoId
  /** El valor en palabras del visitante. */
  formato: (value: AttributeScalar) => string
  /** Si el valor es un término del glosario, cuál. */
  termino?: (value: AttributeScalar) => TerminoId | undefined
  /** Dónde va: con lo esencial, a la vista, o plegado bajo «Más detalle». */
  lugar: 'esencial' | 'detalle'
  /** El valor de la línea entera, que se enseña cuando el tramo no trae el suyo porque el atributo no varía. */
  deLinea?: (line: LineSummary) => AttributeScalar | null
  /** Lo que se dice cuando no hay valor; sin esto, la fila no se enseña. */
  sinDato?: string
  /** Identificador de la celda para las pruebas; por defecto, `tramo-atributo-<clave>`. */
  testId?: string
}

export const SEGMENT_ATTRIBUTES: SegmentAttribute[] = [
  {
    clave: 'tracks',
    etiqueta: 'Vías',
    formato: (v) => tracksLabel(typeof v === 'number' ? v : null),
    termino: (v) => (v === 1 ? 'via-unica' : v === 2 ? 'via-doble' : undefined),
    lugar: 'esencial',
    sinDato: 'sin dato',
    testId: 'tramo-vias',
  },
]

/**
 * Los atributos de un tramo. Una API anterior a ellos solo trae `tracks`: se lee como el atributo
 * del mismo nombre, para que el visor nuevo funcione mientras la API se actualiza.
 */
export function attributesOf(segment: SegmentOut): Record<string, AttributeValue> {
  if (segment.attributes) return segment.attributes
  return segment.tracks === null ? {} : { tracks: { value: segment.tracks, source_id: null, checked_on: null } }
}

export interface FilaAtributo {
  atributo: SegmentAttribute
  /** El valor del tramo o, si no lo trae, el de la línea; nulo si no hay ninguno y la entrada pide decirlo. */
  valor: AttributeValue | null
}

/** Las filas de la ficha de un tramo para un sitio, en el orden de la lista y sin las que no tienen nada que decir. */
export function attributeRows(
  segment: SegmentOut,
  line: LineSummary | undefined,
  lugar: SegmentAttribute['lugar'],
  lista: SegmentAttribute[] = SEGMENT_ATTRIBUTES,
): FilaAtributo[] {
  const propios = attributesOf(segment)
  const filas: FilaAtributo[] = []
  for (const atributo of lista) {
    if (atributo.lugar !== lugar) continue
    const deLinea = line ? (atributo.deLinea?.(line) ?? null) : null
    const valor = propios[atributo.clave] ?? (deLinea === null ? null : { value: deLinea, source_id: null, checked_on: null })
    if (valor || atributo.sinDato !== undefined) filas.push({ atributo, valor })
  }
  return filas
}
