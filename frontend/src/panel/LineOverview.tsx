import type { CoverageOut, NetworkOut } from '../data/types'
import type { Selection } from '../app/state'
import { formatDate, formatKm, gaugeLabel, lineKind, lineShortLabel } from '../app/state'
import { StripDiagram } from './StripDiagram'

interface Props {
  network: NetworkOut
  coverage: CoverageOut | null
  counts: Record<string, number> | null
  lineId: string
  onChangeLine: (id: string) => void
  selection: Selection
  hoverId: string | null
  closedSegmentId: string | null
  onSelect: (sel: Selection) => void
  onHover: (id: string | null) => void
  compact: boolean
}

export function LineOverview({ network, coverage, counts, lineId, onChangeLine, selection, hoverId, closedSegmentId, onSelect, onHover, compact }: Props) {
  const line = network.lines.find((l) => l.id === lineId) ?? network.lines[0]
  if (!line) return null
  const opened = line.opened_on ? new Date(`${line.opened_on}T12:00:00`).getFullYear() : null
  const singleTrackKm = network.segments.filter((s) => s.line_id === line.id && s.tracks === 1).reduce((acc, s) => acc + s.length_km, 0)
  return (
    <section className="resumen-linea" aria-labelledby="linea-titulo">
      {network.lines.length > 1 && (
        <div className="selector-lineas" role="tablist" aria-label="Líneas cargadas">
          {network.lines.map((l) => (
            <button
              key={l.id}
              type="button"
              role="tab"
              aria-selected={l.id === line.id}
              className={`pestana-linea ${l.id === line.id ? 'activa' : ''}`}
              onClick={() => onChangeLine(l.id)}
              data-testid={`selector-linea-${l.id}`}
            >
              <span className="pestana-nombre">{lineShortLabel(l)}</span>
              <span className="pestana-tipo suave">{lineKind(l)}</span>
            </button>
          ))}
        </div>
      )}
      <div className="cabecera-linea">
        <h2 id="linea-titulo" className="titulo">
          {line.name}
        </h2>
        <p className="sobre">
          {line.infrastructure_manager?.name.split(' / ')[0]}, línea {line.short_name} · {formatKm(line.length_km)} km · {gaugeLabel(line.gauge_mm)} · {line.electrification}
          {opened ? ` · abierta en ${opened}` : ''}
          {singleTrackKm > 0 ? ` · ${formatKm(singleTrackKm)} km de vía única` : ''}
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
        lineId={line.id}
        selection={selection}
        hoverId={hoverId}
        closedSegmentId={closedSegmentId}
        counts={counts}
        onSelect={onSelect}
        onHover={onHover}
        compact={compact}
      />
      {!compact && <p className="pista suave">Toca una estación o un tramo, aquí o en el mapa, para ver qué pasa por él. El trazo fino marca la vía única.</p>}
    </section>
  )
}
