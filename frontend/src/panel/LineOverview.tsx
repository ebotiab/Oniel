import type { CoverageOut, NetworkOut } from '../data/types'
import type { Selection } from '../app/state'
import { formatDate, formatKm } from '../app/state'
import { StripDiagram } from './StripDiagram'

interface Props {
  network: NetworkOut
  coverage: CoverageOut | null
  counts: Record<string, number> | null
  selection: Selection
  hoverId: string | null
  closedSegmentId: string | null
  onSelect: (sel: Selection) => void
  onHover: (id: string | null) => void
  compact: boolean
}

export function LineOverview({ network, coverage, counts, selection, hoverId, closedSegmentId, onSelect, onHover, compact }: Props) {
  const line = network.lines[0]
  if (!line) return null
  const opened = line.opened_on ? new Date(`${line.opened_on}T12:00:00`).getFullYear() : null
  return (
    <section className="resumen-linea" aria-labelledby="linea-titulo">
      <div className="cabecera-linea">
        <h2 id="linea-titulo" className="titulo">
          {line.name}
        </h2>
        <p className="sobre">
          {line.infrastructure_manager?.name.split(' / ')[0]}, línea {line.short_name} · {formatKm(line.length_km)} km · ancho estándar · {line.electrification}
          {opened ? ` · abierta en ${opened}` : ''}
        </p>
        {!compact && line.description && (
          <details className="sobre-linea">
            <summary>Sobre la línea</summary>
            <p className="texto suave">{line.description}</p>
          </details>
        )}
        {!compact && coverage?.reference_date && (
          <p className="suave datos-dia">
            Las barras cuentan los trenes de cada tramo el {formatDate(coverage.reference_date)}, según los horarios publicados por Renfe.
          </p>
        )}
      </div>
      <StripDiagram
        network={network}
        selection={selection}
        hoverId={hoverId}
        closedSegmentId={closedSegmentId}
        counts={counts}
        onSelect={onSelect}
        onHover={onHover}
        compact={compact}
      />
      {!compact && <p className="pista suave">Toca una estación o un tramo, aquí o en el mapa, para ver qué pasa por él.</p>}
    </section>
  )
}
