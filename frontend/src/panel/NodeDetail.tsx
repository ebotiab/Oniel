import { Fragment, useEffect, useState } from 'react'

import { ApiError, fetchNodeServices } from '../data/api'
import type { AnnotationOut, NetworkOut, NodeOut, NodeServicesOut, Operator, Source } from '../data/types'
import { KIND_LABEL, formatDate, formatKm, lineKind, lineShortLabel, productLabel, shortStop } from '../app/state'
import { capasDe } from '../app/annotationLayers'
import { isInterruption } from '../app/annotations'
import { AnnotationNotice } from './AnnotationNotice'
import { DirectDestinations } from './DirectDestinations'
import { PieFuente, Plegable } from './Plegable'

interface Props {
  node: NodeOut
  network: NetworkOut
  /** Fuentes registradas, para citar al pie del detalle las de sus líneas. */
  sources: Source[]
  /** Operadores registrados, para nombrar al de cada tren cuando paran los de varios. */
  operators: Operator[]
  referenceDate: string | null
  /** Anotaciones vigentes hoy, por id de tramo. */
  annotated: Map<string, AnnotationOut[]>
  onSelectSegment: (id: string) => void
  /** Abre la ficha de otra estación de la red: un destino directo. */
  onSelectNode: (id: string) => void
  /** Salta a una de las líneas que pasan por el nodo. */
  onGoLine: (lineId: string) => void
  /** Abre el comparador de recorridos con este nodo como salida. */
  onCompare: () => void
  onBack: () => void
}

export function NodeDetail({ node, network, sources, operators, referenceDate, annotated, onSelectSegment, onSelectNode, onGoLine, onCompare, onBack }: Props) {
  const [calls, setCalls] = useState<NodeServicesOut | null>(null)
  const [error, setError] = useState<string | null>(null)
  const adjacent = network.segments.filter((s) => s.from_node_id === node.id || s.to_node_id === node.id)
  const connections = network.connections.filter((c) => c.node_id === node.id)
  const station = node.kind === 'estacion'
  // Un nodo puede pertenecer a varias líneas (Madrid y Córdoba): su kilómetro en cada una.
  const memberships = network.nodes
    .filter((n) => n.id === node.id)
    .map((n) => ({ km: n.km, line: network.lines.find((l) => l.id === n.line_id) }))
  const lineOf = (lineId: string) => network.lines.find((l) => l.id === lineId)
  // Anotaciones de los tramos que confluyen aquí, cada una una sola vez.
  const cuts = [...new Map(adjacent.flatMap((s) => annotated.get(s.id) ?? []).map((a) => [a.id, a])).values()]

  // App monta este componente con key={node.id}, así que el estado se reinicia al cambiar de nodo.
  useEffect(() => {
    if (!station) return
    let alive = true
    fetchNodeServices(node.id, referenceDate ?? undefined)
      .then((c) => alive && setCalls(c))
      .catch((e: unknown) => alive && setError(e instanceof ApiError ? e.message : 'No se pudieron cargar los trenes.'))
    return () => {
      alive = false
    }
  }, [node.id, referenceDate, station])

  // El operador de cada tren solo se nombra si aquí paran los de más de uno.
  const severalOperators = new Set(calls?.calls.map((c) => c.operator_id)).size > 1
  // Operadores de sus líneas que no publican sus horarios: sus trenes faltan en los destinos.
  const lineOperators = new Set(memberships.flatMap((m) => m.line?.operator_ids ?? []))
  const missing = operators.filter((o) => o.timetable === 'no_publicado' && lineOperators.has(o.id))
  // Fuentes de los horarios de los trenes que paran aquí, para citarlas al pie del detalle.
  const callOperators = new Set(calls?.calls.map((c) => c.operator_id))
  const timetables = operators.filter((o) => callOperators.has(o.id)).map((o) => sources.find((s) => s.id === o.source_id))
  const operatorName = (id: string | undefined) => operators.find((o) => o.id === id)?.name ?? id ?? ''

  return (
    <section className="detalle" aria-labelledby="detalle-titulo" data-testid="detalle-nodo">
      <button type="button" className="enlace volver" onClick={onBack}>
        ← Toda la línea
      </button>
      <p className="sobre">{KIND_LABEL[node.kind]}</p>
      <h2 id="detalle-titulo" className="titulo">
        {node.name}
      </h2>
      {memberships.length > 1 && (
        <div data-testid="nodo-lineas">
          <p className="texto">Aquí se encuentran {memberships.length} líneas:</p>
          <ul className="lista-simple">
            {memberships.map(
              (m) =>
                m.line && (
                  <li key={m.line.id}>
                    <button type="button" className="enlace" onClick={() => onGoLine(m.line!.id)} data-testid={`nodo-linea-${m.line.id}`}>
                      {lineShortLabel(m.line)}
                    </button>{' '}
                    <span className="suave">{lineKind(m.line)}</span>
                  </li>
                ),
            )}
          </ul>
        </div>
      )}
      {node.description && <p className="texto">{node.description}</p>}
      {station && (
        <p className="texto">
          <button type="button" className="enlace" onClick={onCompare} data-testid="recorridos-desde-aqui">
            Comparar recorridos desde aquí
          </button>
        </p>
      )}

      <Plegable>
        <dl className="datos-tramo datos">
          {memberships.map((m) => (
            <div key={m.line?.id ?? '?'}>
              <dt>Punto kilométrico{memberships.length > 1 && m.line ? ` en ${lineShortLabel(m.line)}` : ''}</dt>
              <dd data-testid="nodo-pk">km {formatKm(m.km)}</dd>
            </div>
          ))}
          {node.adif_code && (
            <div>
              <dt>Código de Adif</dt>
              <dd>{node.adif_code}</dd>
            </div>
          )}
        </dl>
        <p className="suave">
          El punto kilométrico es la distancia medida a lo largo de la vía desde el origen de la línea.
          {node.adif_code ? ' El código es el número con el que Adif identifica esta dependencia.' : ''}
        </p>
        <PieFuente de="del trazado" sources={memberships.map((m) => sources.find((s) => s.id === m.line?.source_id))} />
        {station && (
          <>
            <p className="suave">
              Un destino directo es una estación en la que para, después de esta, un tren al que se puede subir aquí. No cuentan las paradas en las
              que el tren solo recoge viajeros. Solo están los trenes que recorren alguna de las líneas cargadas en Oniel.
            </p>
            <PieFuente de="de los horarios" sources={timetables} />
          </>
        )}
      </Plegable>

      {node.details.contexto_2026 && (
        <aside className="contexto" aria-label="Contexto de 2026">
          <p className="texto">{node.details.contexto_2026}</p>
          {node.details.fuentes && (
            <p className="suave">
              Fuentes:{' '}
              {node.details.fuentes.map((f, i) => (
                <span key={f.url}>
                  {i > 0 && ' · '}
                  <a href={f.url} target="_blank" rel="noreferrer">
                    {f.title}
                  </a>
                </span>
              ))}
            </p>
          )}
        </aside>
      )}

      {cuts.map((a) => (
        <AnnotationNotice key={a.id} annotation={a} />
      ))}

      {station && calls?.destinations && (
        <DirectDestinations
          destinations={calls.destinations}
          date={calls.date}
          network={network}
          operators={operators}
          missing={missing}
          interrupted={[...annotated.values()].some((list) => list.some(isInterruption))}
          onSelectNode={onSelectNode}
        />
      )}

      <h3 className="subtitulo">Tramos que salen de aquí</h3>
      <ul className="lista-simple">
        {adjacent.map((s) => (
          <li key={s.id}>
            <button type="button" className="enlace" onClick={() => onSelectSegment(s.id)}>
              {s.from_name} – {s.to_name}
            </button>{' '}
            <span className="suave datos">
              {formatKm(s.length_km)} km{memberships.length > 1 && lineOf(s.line_id) ? ` · ${lineShortLabel(lineOf(s.line_id)!)}` : ''}
              {s.tracks === 1 ? ' · vía única' : ''}
            </span>
            {capasDe(annotated.get(s.id))
              .filter((capa) => capa.trazo)
              .map(({ kind, ficha }) => {
                const senal = ficha.senal(annotated.get(s.id)!.find((a) => a.kind === kind)!)
                return (
                  <Fragment key={kind}>
                    {' '}
                    <span className={`senal ${senal.clase}`}>{senal.texto}</span>
                  </Fragment>
                )
              })}
          </li>
        ))}
        {connections.map((c) => (
          <li key={c.id} className="suave">
            {c.name} hacia {c.towards} <span className="senal gris">no cargada todavía</span>
          </li>
        ))}
      </ul>

      {station && (
        <>
          <h3 className="subtitulo">
            Trenes que paran aquí
            {calls && (
              <span className="datos suave">
                {' '}
                · {calls.calls.length} el {formatDate(calls.date)}
              </span>
            )}
          </h3>
          {error && <p className="aviso">{error}</p>}
          {!calls && !error && <p className="suave">Cargando…</p>}
          {calls && (
            <ol className="lista-servicios">
              {calls.calls.map((c) => (
                <li key={c.service_id}>
                  <span className="hora datos">{c.departure ?? c.arrival ?? '—'}</span>
                  <span className="tren">
                    <strong>
                      {productLabel(c.product)} {c.train_number}
                    </strong>{' '}
                    <span className="suave">
                      {shortStop(c.origin_name)} → {shortStop(c.destination_name)}
                      {severalOperators ? ` · ${operatorName(c.operator_id)}` : ''}
                    </span>
                  </span>
                </li>
              ))}
            </ol>
          )}
        </>
      )}
    </section>
  )
}
