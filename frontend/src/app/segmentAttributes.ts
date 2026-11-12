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

interface ValorDicho {
  texto: string
  termino?: TerminoId
}

/** La fuente se consultó y no da el dato para el tramo: se dice tal cual, que no es lo mismo que no tenerlo. */
const SIN_DATO_PUBLICADO: ValorDicho = { texto: 'Sin dato publicado' }

const PROTECCION_TREN: Record<string, ValorDicho> = {
  asfa: { texto: 'ASFA', termino: 'asfa' },
  lzb_asfa: { texto: 'LZB y ASFA', termino: 'lzb' },
  ertms_n1: { texto: 'ERTMS de nivel 1', termino: 'ertms' },
  ertms_n2: { texto: 'ERTMS de nivel 2', termino: 'ertms' },
  sin_dato_publicado: SIN_DATO_PUBLICADO,
}

const BLOQUEO: Record<string, ValorDicho> = {
  bca: { texto: 'De control automático', termino: 'bloqueo-de-control-automatico' },
  bab: { texto: 'Automático banalizado', termino: 'bloqueo-automatico' },
  bad: { texto: 'Automático de vía doble', termino: 'bloqueo-automatico' },
  bau: { texto: 'Automático de vía única', termino: 'bloqueo-automatico' },
  blau: { texto: 'De liberación automática en vía única', termino: 'bloqueo' },
  // un tramo que cambia de bloqueo donde Oniel no tiene nodo
  bab_bad: { texto: 'Automático: banalizado en una parte y de vía doble en otra', termino: 'bloqueo-automatico' },
  sin_dato_publicado: SIN_DATO_PUBLICADO,
}

const MANDO: Record<string, ValorDicho> = {
  ctc: { texto: 'Control de tráfico centralizado', termino: 'control-de-trafico-centralizado' },
  // el mapa rotula el bloqueo sin «ctc» y su leyenda distingue los dos casos: la fuente dice que no lo hay
  sin_ctc: { texto: 'Sin control centralizado', termino: 'control-de-trafico-centralizado' },
  sin_dato_publicado: SIN_DATO_PUBLICADO,
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
  // Señalización: lo que da el mapa 4 de la Declaración sobre la Red (docs/datos.md, «Señalización y
  // protección del tren»). Las claves de cada valor son las de `ATTRIBUTE_RULES` en el backend.
  {
    clave: 'proteccion_tren',
    etiqueta: 'Protección del tren',
    terminoEtiqueta: 'proteccion-del-tren',
    formato: (v) => PROTECCION_TREN[String(v)]?.texto ?? String(v),
    termino: (v) => PROTECCION_TREN[String(v)]?.termino,
    lugar: 'detalle',
  },
  {
    clave: 'bloqueo',
    etiqueta: 'Bloqueo',
    terminoEtiqueta: 'bloqueo',
    formato: (v) => BLOQUEO[String(v)]?.texto ?? String(v),
    termino: (v) => BLOQUEO[String(v)]?.termino,
    lugar: 'detalle',
  },
  {
    clave: 'mando',
    etiqueta: 'Mando',
    terminoEtiqueta: 'puesto-de-mando',
    formato: (v) => MANDO[String(v)]?.texto ?? String(v),
    termino: (v) => MANDO[String(v)]?.termino,
    lugar: 'detalle',
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

export interface FuenteAtributos {
  sourceId: string
  /** El día más reciente en que se comprobó alguno de sus valores. */
  checkedOn: string | null
  /** Las etiquetas de los atributos que da, en el orden de la ficha. */
  etiquetas: string[]
}

/** Las fuentes de los atributos que un tramo enseña en un sitio de la ficha: una por fuente, con lo que da cada una. */
export function attributeSources(filas: FilaAtributo[]): FuenteAtributos[] {
  const porFuente = new Map<string, FuenteAtributos>()
  for (const { atributo, valor } of filas) {
    if (!valor?.source_id) continue
    const fuente = porFuente.get(valor.source_id) ?? { sourceId: valor.source_id, checkedOn: null, etiquetas: [] }
    fuente.etiquetas.push(atributo.etiqueta)
    if (valor.checked_on && (!fuente.checkedOn || valor.checked_on > fuente.checkedOn)) fuente.checkedOn = valor.checked_on
    porFuente.set(valor.source_id, fuente)
  }
  return [...porFuente.values()]
}
