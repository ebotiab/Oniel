import type { ReactNode } from 'react'

import type { AnnotationOut, CoverageOut, LineDetailOut, NetworkOut } from '../data/types'
import { capasDe } from '../app/annotationLayers'
import type { Selection } from '../app/state'
import { formatDate, formatDayShort, formatKm, gaugeLabel, listaEs } from '../app/state'
import { PieFuente, Plegable } from './Plegable'
import { ClaveEsquema } from './ClaveEsquema'
import { StripDiagram } from './StripDiagram'
import { Termino } from './Termino'

interface Props {
  notice?: ReactNode
  network: NetworkOut
  coverage: CoverageOut | null
  detail: LineDetailOut | null | undefined
  lineId: string
  /** Vuelve a la vista de la red. */
  onShowNetwork: () => void
  selection: Selection
  hoverId: string | null
  closedSegmentId: string | null
  /** Anotaciones vigentes hoy en cualquier línea; aquí se muestran las de la línea a la vista. */
  annotations: AnnotationOut[]
  onSelect: (sel: Selection) => void
  onHover: (id: string | null) => void
  compact: boolean
  /** Leyenda de los trazos, cuando va dentro del panel (en el móvil): sobre el esquema. */
  leyenda?: ReactNode
}

export function LineOverview({ notice, network, coverage, detail, lineId, onShowNetwork, selection, hoverId, closedSegmentId, annotations, onSelect, onHover, compact, leyenda = null }: Props) {
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
  const cuts = annotations.filter((a) => a.line_id === line.id && a.segment_ids.length > 0)
  const dia = detail?.date
  const compatible = Boolean(dia && (!coverage?.reference_date || dia === coverage.reference_date))
  const counts = compatible ? detail?.counts ?? null : null
  const countsMax = detail?.network_max_count
  // De quién son los trenes que cuentan las barras, y de quién faltan porque no publica sus horarios.
  const operadores = (coverage?.operators ?? []).filter((o) => line.operator_ids?.includes(o.id))
  const conHorarios = operadores.filter((o) => o.timetable !== 'no_publicado').map((o) => o.name)
  const sinHorarios = operadores.filter((o) => o.timetable === 'no_publicado').map((o) => o.name)
  const noOficiales = operadores.filter((o) => o.timetable === 'no_oficial').map((o) => o.name)
  const conBarras = Boolean(counts && dia && (countsMax ?? Object.keys(counts).length))
  return (
    <section className="resumen-linea" aria-labelledby="linea-titulo">
      <div className="cabecera-linea" data-testid="cabecera-linea">
        <button type="button" className="enlace volver" onClick={onShowNetwork} data-testid="volver-red">
          ← Toda la red
        </button>
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
        {notice}
        {detail === null && <p className="aviso">Detalle de la línea no disponible.</p>}
        {detail && !compatible && <p className="aviso">Horarios no disponibles para esta consulta.</p>}
        <Plegable>
          {parrafos.map((p) => (
            <p key={p} className="texto">
              {p}
            </p>
          ))}
          <dl className="datos-tramo datos" data-testid="linea-detalle">
            {gestor && (
              <div>
                <dt>
                  <Termino id="administrador-de-infraestructura">Quién la gestiona</Termino>
                </dt>
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
              <dt>
                <Termino id="ancho-de-via">Ancho de vía</Termino>
              </dt>
              <dd>{ancho}</dd>
            </div>
            {line.electrification && (
              <div>
                <dt>
                  <Termino id="electrificacion">Electrificación</Termino>
                </dt>
                <dd>{line.electrification}</dd>
              </div>
            )}
          </dl>
          <PieFuente de="del trazado" sources={[coverage?.sources.find((s) => s.id === line.source_id)]} />
        </Plegable>
      </div>
      {capasDe(cuts).map(
        ({ kind, lista }) =>
          lista && (
            <ul key={kind} className="cortes-linea" aria-label={lista.rotulo} data-testid={lista.testId}>
              {cuts
                .filter((a) => a.kind === kind)
                .map((a) => (
                  <li key={a.id}>
                    <button type="button" className="enlace" onClick={() => onSelect({ type: 'tramo', id: a.segment_ids[0]! })}>
                      {lista.enlace(a)}
                    </button>{' '}
                    <span className="suave">{lista.detalle(a)}</span>
                  </li>
                ))}
            </ul>
          ),
      )}
      {leyenda}
      {line.id === 'avila-salamanca' && (
        <p className="texto">
          Desde la <button type="button" className="enlace" onClick={() => onSelect({ type: 'nodo', id: 'avila' })}>estación de Ávila</button> hasta la bifurcación, el recorrido comparte la línea de Valladolid.
        </p>
      )}
      <StripDiagram
        network={network}
        lineId={line.id}
        selection={selection}
        hoverId={hoverId}
        closedSegmentId={closedSegmentId}
        annotations={cuts}
        counts={counts}
        countsMax={countsMax}
        countsLabel={conBarras && dia ? `trenes el ${formatDayShort(dia)}` : null}
        onSelect={onSelect}
        onHover={onHover}
        compact={compact}
      />
      <ClaveEsquema nodes={network.nodes.filter((n) => n.line_id === line.id)} connections={network.connections} />
      {!compact && (
        <p className="nota-esquema" data-testid="nota-esquema">
          {conBarras && dia ? `Las barras cuentan los trenes de cada tramo el ${formatDate(dia)}, según los horarios de ${conHorarios.length ? listaEs(conHorarios) : 'los operadores cargados'}${sinHorarios.length ? `; no incluyen los de ${listaEs(sinHorarios)}` : ''}${noOficiales.length ? `; los de ${listaEs(noOficiales)}, de una compilación no oficial` : ''}. ` : ''}
          Toca una estación o un tramo para ver sus trenes. A la derecha de cada nombre aparecen los kilómetros medidos desde el inicio del trazado en el mapa.
        </p>
      )}
    </section>
  )
}
