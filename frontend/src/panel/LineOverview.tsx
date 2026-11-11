import type { CoverageOut, InterruptionOut, NetworkOut } from '../data/types'
import { formatDateLong, mainSourceLabel } from '../app/interruptions'
import type { Selection } from '../app/state'
import { formatDate, formatDayShort, formatKm, gaugeLabel, lineKind, lineShortLabel } from '../app/state'
import { PieFuente, Plegable } from './Plegable'
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
  /** Interrupciones vigentes hoy en cualquier línea; aquí se muestran las de la línea a la vista. */
  interruptions: InterruptionOut[]
  onSelect: (sel: Selection) => void
  onHover: (id: string | null) => void
  compact: boolean
}

export function LineOverview({ network, coverage, counts, lineId, onChangeLine, selection, hoverId, closedSegmentId, interruptions, onSelect, onHover, compact }: Props) {
  const line = network.lines.find((l) => l.id === lineId) ?? network.lines[0]
  if (!line) return null
  // La descripción curada va en párrafos separados por una línea en blanco: el primero se lee de
  // entrada y el resto queda plegado. Los datos técnicos no se repiten en ella: van en la ficha.
  const [entrada, ...resto] = (line.description ?? '')
    .split(/\n\s*\n/)
    .map((p) => p.trim())
    .filter(Boolean)
  const gestor = line.infrastructure_manager?.name.split(' / ')[0]
  const numero = line.short_name
  const ancho = gaugeLabel(line.gauge_mm).replace(/^ancho /, '') + (line.gauge_mm ? ` (${line.gauge_mm.toLocaleString('es-ES', { useGrouping: 'always' })} mm)` : '')
  // Lo que entiende cualquiera, a la vista; el ancho, la electrificación y el número de línea, en el detalle.
  const ficha = [`${formatKm(line.length_km)} km`, line.max_speed_kmh ? `hasta ${line.max_speed_kmh} km/h` : null].filter((d): d is string => Boolean(d))
  // En el móvil la cabecera no lleva la frase de entrada: la descripción entera va en el detalle.
  const parrafos = compact ? [entrada, ...resto].filter((p): p is string => Boolean(p)) : resto
  const cuts = interruptions.filter((i) => i.line_id === line.id && i.segment_ids.length > 0)
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
        <Plegable>
          {parrafos.map((p) => (
            <p key={p} className="texto">
              {p}
            </p>
          ))}
          <dl className="datos-tramo datos" data-testid="linea-detalle">
            {gestor && (
              <div>
                <dt>Quién la gestiona</dt>
                <dd>{gestor}</dd>
              </div>
            )}
            {numero && (
              <div>
                <dt>Número en la red de Adif</dt>
                <dd>{numero}</dd>
              </div>
            )}
            <div>
              <dt>Ancho de vía</dt>
              <dd>{ancho}</dd>
            </div>
            {line.electrification && (
              <div>
                <dt>Electrificación</dt>
                <dd>{line.electrification}</dd>
              </div>
            )}
          </dl>
          <PieFuente de="del trazado" sources={[coverage?.sources.find((s) => s.id === line.source_id)]} />
        </Plegable>
      </div>
      {cuts.length > 0 && (
        <ul className="cortes-linea" aria-label="Tramos sin circulación hoy" data-testid="cortes-linea">
          {cuts.map((i) => (
            <li key={i.id}>
              <button type="button" className="enlace" onClick={() => onSelect({ type: 'tramo', id: i.segment_ids[0]! })}>
                Sin circulación entre {i.from_name} y {i.to_name}
              </button>{' '}
              <span className="suave">
                desde el {formatDateLong(i.start_date)} ({mainSourceLabel(i)})
              </span>
            </li>
          ))}
        </ul>
      )}
      <StripDiagram
        network={network}
        lineId={line.id}
        selection={selection}
        hoverId={hoverId}
        closedSegmentId={closedSegmentId}
        interruptions={cuts}
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
