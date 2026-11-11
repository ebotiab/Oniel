import { formatCount, networkCount } from '../app/state'
import type { CoverageOut, InterruptionOut, NetworkOut } from '../data/types'
import { LineList } from './LineList'

interface Props {
  network: NetworkOut
  coverage: CoverageOut | null
  /** Interrupciones vigentes hoy en cualquier línea. */
  interruptions: InterruptionOut[]
  onPickLine: (id: string) => void
  onShowCoverage: () => void
}

/** Vista de la red: lo que se ve cuando no hay ninguna línea elegida. Dice qué hay cargado y por dónde empezar. */
export function NetworkOverview({ network, coverage, interruptions, onPickLine, onShowCoverage }: Props) {
  const cortadas = new Set(interruptions.filter((i) => i.segment_ids.length > 0).map((i) => i.line_id))
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
          Toca una vía en el mapa o elige una línea de la lista para recorrerla estación a estación. Oniel va incorporando las líneas poco a poco.
        </p>
      </div>
      <h3 className="subtitulo">Líneas</h3>
      <LineList lines={network.lines} interruptedLineIds={cortadas} onPick={onPickLine} />
      <p className="nota-esquema">
        <button type="button" className="enlace" onClick={onShowCoverage} data-testid="boton-cobertura">
          Cobertura y fuentes
        </button>
        : qué hay cargado, de dónde sale cada dato y con qué licencia.
      </p>
    </section>
  )
}
