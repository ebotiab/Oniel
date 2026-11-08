import { useEffect, useState } from 'react'

import { ApiError, fetchSegmentServices } from '../data/api'
import type { NetworkOut, SegmentOut, SegmentServicesOut } from '../data/types'
import { formatDate, formatKm, shortStop } from '../app/state'
import { KindBadge } from './KindBadge'

interface Props {
  segment: SegmentOut
  network: NetworkOut
  referenceDate: string | null
  onSimulate: () => void
  onSelectNode: (id: string) => void
  onBack: () => void
}

export function SegmentDetail({ segment, network, referenceDate, onSimulate, onSelectNode, onBack }: Props) {
  const [services, setServices] = useState<SegmentServicesOut | null>(null)
  const [error, setError] = useState<string | null>(null)
  const line = network.lines.find((l) => l.id === segment.line_id)

  // App monta este componente con key={segment.id}, así que el estado se reinicia al cambiar de tramo.
  useEffect(() => {
    let alive = true
    fetchSegmentServices(segment.id, referenceDate ?? undefined)
      .then((s) => alive && setServices(s))
      .catch((e: unknown) => alive && setError(e instanceof ApiError ? e.message : 'No se pudieron cargar los servicios.'))
    return () => {
      alive = false
    }
  }, [segment.id, referenceDate])

  const byProduct = new Map<string, number>()
  for (const p of services?.passes ?? []) byProduct.set(p.service.product, (byProduct.get(p.service.product) ?? 0) + 1)

  return (
    <section className="detalle" aria-labelledby="detalle-titulo" data-testid="detalle-tramo">
      <button type="button" className="enlace volver" onClick={onBack}>
        ← Toda la línea
      </button>
      <p className="sobre">Tramo {segment.seq} de {line?.segment_count ?? '–'} · {line?.name}</p>
      <h2 id="detalle-titulo" className="titulo">
        <button type="button" className="enlace-nodo" onClick={() => onSelectNode(segment.from_node_id)}>
          {segment.from_name}
        </button>
        <span aria-hidden="true"> – </span>
        <button type="button" className="enlace-nodo" onClick={() => onSelectNode(segment.to_node_id)}>
          {segment.to_name}
        </button>
      </h2>
      <dl className="datos-tramo datos">
        <div>
          <dt>Longitud</dt>
          <dd>{formatKm(segment.length_km)} km</dd>
        </div>
        <div>
          <dt>Puntos kilométricos</dt>
          <dd>
            {formatKm(segment.km_from)} → {formatKm(segment.km_to)}
          </dd>
        </div>
        <div>
          <dt>Velocidad máxima</dt>
          <dd>{segment.max_speed_kmh ? `${segment.max_speed_kmh} km/h` : 'sin dato'}</dd>
        </div>
        <div>
          <dt>Velocidad habitual</dt>
          <dd>{segment.typical_speed_kmh ? `${segment.typical_speed_kmh} km/h` : 'sin dato'}</dd>
        </div>
      </dl>

      <div className="acciones">
        <button type="button" className="boton primario" onClick={onSimulate} data-testid="boton-simular">
          Simular un cierre en este tramo
        </button>
      </div>

      <h3 className="subtitulo">
        Trenes que lo recorren
        {services && (
          <span className="datos suave">
            {' '}
            · {services.passes.length} el {formatDate(services.date)}
          </span>
        )}
      </h3>
      {error && <p className="aviso">{error}</p>}
      {!services && !error && <p className="suave">Cargando servicios…</p>}
      {services && (
        <>
          <p className="suave">
            {[...byProduct.entries()].map(([p, n]) => `${n} ${p}`).join(' · ')}. Paso con horario publicado en {services.counts.publicado},
            estimado en {services.counts.estimado}
            {services.counts.indeterminado ? `, indeterminado en ${services.counts.indeterminado}` : ''}.
          </p>
          <ol className="lista-servicios" data-testid="lista-servicios">
            {services.passes.map((p) => (
              <li key={`${p.service.id}-${p.enter}`}>
                <span className="hora datos">{p.enter ?? '—'}</span>
                <span className="tren">
                  <strong>
                    {p.service.product} {p.service.train_number}
                  </strong>{' '}
                  <span className="suave">
                    {shortStop(p.service.origin_name)} → {shortStop(p.service.destination_name)}
                  </span>
                </span>
                <KindBadge kind={p.kind} title={p.basis} />
              </li>
            ))}
          </ol>
        </>
      )}
    </section>
  )
}
