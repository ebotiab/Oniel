import { useEffect, useState } from 'react'

import { ApiError, fetchNodeServices } from '../data/api'
import type { NetworkOut, NodeOut, NodeServicesOut } from '../data/types'
import { KIND_LABEL, formatDate, formatKm, shortStop } from '../app/state'

interface Props {
  node: NodeOut
  network: NetworkOut
  referenceDate: string | null
  onSelectSegment: (id: string) => void
  onBack: () => void
}

export function NodeDetail({ node, network, referenceDate, onSelectSegment, onBack }: Props) {
  const [calls, setCalls] = useState<NodeServicesOut | null>(null)
  const [error, setError] = useState<string | null>(null)
  const adjacent = network.segments.filter((s) => s.from_node_id === node.id || s.to_node_id === node.id)
  const connections = network.connections.filter((c) => c.node_id === node.id)
  const station = node.kind === 'estacion'

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

  return (
    <section className="detalle" aria-labelledby="detalle-titulo" data-testid="detalle-nodo">
      <button type="button" className="enlace volver" onClick={onBack}>
        ← Toda la línea
      </button>
      <p className="sobre">
        {KIND_LABEL[node.kind]} · km {formatKm(node.km)}
        {node.adif_code ? ` · código Adif ${node.adif_code}` : ''}
      </p>
      <h2 id="detalle-titulo" className="titulo">
        {node.name}
      </h2>
      {node.description && <p className="texto">{node.description}</p>}

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

      <h3 className="subtitulo">Tramos que confluyen</h3>
      <ul className="lista-simple">
        {adjacent.map((s) => (
          <li key={s.id}>
            <button type="button" className="enlace" onClick={() => onSelectSegment(s.id)}>
              {s.from_name} – {s.to_name}
            </button>{' '}
            <span className="suave datos">{formatKm(s.length_km)} km</span>
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
                      {c.product} {c.train_number}
                    </strong>{' '}
                    <span className="suave">
                      {shortStop(c.origin_name)} → {shortStop(c.destination_name)}
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
