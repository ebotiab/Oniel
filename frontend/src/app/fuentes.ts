// Las fuentes de «Cobertura y fuentes», agrupadas por lo que aportan. `sources.json` no dice de qué tipo
// es cada fuente: el grupo sale de dónde se usa en los datos que el visor ya tiene cargados.

import type { AnnotationOut, CoverageOut, Source } from '../data/types'
import { conceptos } from '../panel/glosario'

export interface GrupoDeFuentes {
  id: string
  titulo: string
  /** Qué sale de estas fuentes, en una frase. */
  entrada: string
  fuentes: Source[]
}

const GRUPOS = [
  { id: 'horarios', titulo: 'Horarios', entrada: 'Los trenes de cada operador: por dónde pasan, dónde paran y a qué hora.' },
  { id: 'trazado', titulo: 'Trazado y mapa', entrada: 'Por dónde va cada línea, dónde están sus estaciones y el mapa de fondo.' },
  {
    id: 'lineas',
    titulo: 'Características de las líneas',
    entrada: 'Puntos kilométricos, velocidades, número de vías, electrificación, señalización y la historia de cada línea.',
  },
  {
    id: 'anotaciones',
    titulo: 'Interrupciones y proyectos',
    entrada: 'Avisos, notas de prensa, anuncios oficiales y noticias de los que sale cada interrupción y cada proyecto.',
  },
  { id: 'glosario', titulo: 'Glosario', entrada: 'El reglamento que siguen los conceptos de circulación del glosario.' },
] as const

/**
 * Reparte las fuentes en grupos, cada una en uno solo y en el primero que le toque: horarios (las de los
 * operadores), trazado y mapa (las de las líneas, las demás de OpenStreetMap y el mapa base),
 * interrupciones y proyectos (las que cita alguna anotación), glosario (las referencias de sus
 * conceptos) y, las demás, características de las líneas. Dentro de cada grupo conservan su orden.
 */
export function agruparFuentes(coverage: CoverageOut, annotations: readonly AnnotationOut[]): GrupoDeFuentes[] {
  const horarios = new Set(coverage.operators.filter((o) => o.role === 'operador').map((o) => o.source_id))
  const trazado = new Set(coverage.lines.map((l) => l.source_id))
  const anotaciones = new Set(annotations.flatMap((a) => a.sources.map((s) => s.id)))
  const glosario = new Set<string>(conceptos.map((c) => c.referencia.sourceId))
  const grupoDe = (s: Source): (typeof GRUPOS)[number]['id'] => {
    if (horarios.has(s.id)) return 'horarios'
    if (trazado.has(s.id) || s.id.startsWith('osm-') || s.id === 'openfreemap') return 'trazado'
    if (anotaciones.has(s.id)) return 'anotaciones'
    if (glosario.has(s.id)) return 'glosario'
    return 'lineas'
  }
  return GRUPOS.map((g) => ({ ...g, fuentes: coverage.sources.filter((s) => grupoDe(s) === g.id) })).filter((g) => g.fuentes.length > 0)
}
