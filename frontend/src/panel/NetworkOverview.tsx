import { formatCount, networkCount } from '../app/state'
import type { AnnotationOut, CoverageOut, NetworkOut } from '../data/types'
import { capasDe } from '../app/annotationLayers'
import { LineList } from './LineList'

interface Props {
  network: NetworkOut
  coverage: CoverageOut | null
  /** Anotaciones vigentes hoy en cualquier línea. */
  annotations: AnnotationOut[]
  onPickLine: (id: string) => void
  /** Las líneas por las que pasa el cursor o el foco en la lista: el mapa las resalta. */
  onHighlightLines: (ids: string[] | null) => void
}

/** Vista de la red: lo que se ve cuando no hay ninguna línea elegida. Dice qué hay cargado y por dónde empezar. */
export function NetworkOverview({ network, coverage, annotations, onPickLine, onHighlightLines }: Props) {
  // Qué capas tienen algún tramo anotado hoy en cada línea: su nota va junto al nombre.
  const notas = new Map(
    network.lines.map((l) => [l.id, capasDe(annotations.filter((a) => a.line_id === l.id && a.segment_ids.length > 0))] as const),
  )
  const ficha = [networkCount(network.lines), coverage ? `${formatCount(coverage.station_count)} estaciones` : null].filter((d): d is string => Boolean(d))
  return (
    <section className="vista-red" aria-labelledby="red-titulo" data-testid="vista-red">
      <div className="cabecera-linea">
        <h2 id="red-titulo" className="titulo">
          La red ferroviaria española, línea a línea
        </h2>
        <ul className="ficha-linea datos" aria-label="Lo que hay cargado" data-testid="ficha-red">
          {ficha.map((d) => (
            <li key={d}>{d}</li>
          ))}
        </ul>
        <p className="entrada">
          Toca una vía en el mapa o elige una línea de la lista, por zonas, para recorrerla estación a estación. Oniel va incorporando las líneas poco a poco.
        </p>
      </div>
      <h3 className="subtitulo">Líneas</h3>
      <LineList lines={network.lines} nodes={network.nodes} notes={notas} onPick={onPickLine} onHighlight={onHighlightLines} />
    </section>
  )
}
