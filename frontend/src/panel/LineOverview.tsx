import type { CoverageOut, NetworkOut } from '../data/types'
import type { Selection } from '../app/state'
import { formatDate, formatDayShort, formatKm, gaugeLabel, lineKind, lineShortLabel } from '../app/state'
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
  // La descripción curada va en párrafos separados por una línea en blanco: el primero se lee de
  // entrada y el resto queda plegado. Los datos técnicos no se repiten en ella: van en la ficha.
  const [entrada, ...resto] = (line.description ?? '')
    .split(/\n\s*\n/)
    .map((p) => p.trim())
    .filter(Boolean)
  const gestor = line.infrastructure_manager?.name.split(' / ')[0]
  const numero = line.short_name ? `${/ y /.test(line.short_name) ? 'líneas' : 'línea'} ${line.short_name}` : null
  const antetitulo = [gestor, numero].filter(Boolean).join(', ')
  const ficha = [
    `${formatKm(line.length_km)} km`,
    line.max_speed_kmh ? `${line.max_speed_kmh} km/h` : null,
    gaugeLabel(line.gauge_mm),
    line.electrification,
  ].filter((d): d is string => Boolean(d))
  const dia = coverage?.reference_date ?? null
  const conBarras = Boolean(counts && dia && Object.keys(counts).length)
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
      <div className="cabecera-linea" data-testid="cabecera-linea">
        {!compact && antetitulo && <p className="antetitulo">{antetitulo}</p>}
        <h2 id="linea-titulo" className="titulo">
          {line.name}
        </h2>
        <ul className="ficha-linea datos" aria-label="Datos de la línea" data-testid="ficha-linea">
          {ficha.map((d) => (
            <li key={d}>{d}</li>
          ))}
        </ul>
        {!compact && entrada && (
          <p className="entrada" data-testid="linea-entrada">
            {entrada}
          </p>
        )}
        {!compact && resto.length > 0 && (
          <details key={line.id} className="sobre-linea">
            <summary>Más sobre la línea</summary>
            {resto.map((p) => (
              <p key={p} className="texto">
                {p}
              </p>
            ))}
          </details>
        )}
      </div>
      <StripDiagram
        network={network}
        lineId={line.id}
        selection={selection}
        hoverId={hoverId}
        closedSegmentId={closedSegmentId}
        counts={counts}
        countsLabel={conBarras && dia ? `trenes el ${formatDayShort(dia)}` : null}
        onSelect={onSelect}
        onHover={onHover}
        compact={compact}
      />
      {!compact && (
        <p className="nota-esquema" data-testid="nota-esquema">
          {conBarras && dia ? `Las barras cuentan los trenes de cada tramo el ${formatDate(dia)}, según los horarios de Renfe. ` : ''}
          Toca una estación o un tramo para ver sus trenes.
        </p>
      )}
    </section>
  )
}
