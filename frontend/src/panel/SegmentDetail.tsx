import { useEffect, useState } from 'react'

import { ApiError, fetchSegmentServices } from '../data/api'
import type { InterruptionOut, NetworkOut, SegmentOut, SegmentServicesOut, Source } from '../data/types'
import { formatDate, formatKm, productLabel, shortStop, tracksLabel } from '../app/state'
import { InterruptionNotice } from './InterruptionNotice'
import { KindBadge } from './KindBadge'
import { PieFuente, Plegable } from './Plegable'

interface Props {
  segment: SegmentOut
  network: NetworkOut
  /** Fuentes registradas, para citar al pie del detalle la del tramo. */
  sources: Source[]
  referenceDate: string | null
  /** Interrupciones del servicio vigentes hoy en este tramo. */
  interruptions: InterruptionOut[]
  onSimulate: () => void
  onSelectNode: (id: string) => void
  onBack: () => void
}

export function SegmentDetail({ segment, network, sources, referenceDate, interruptions, onSimulate, onSelectNode, onBack }: Props) {
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
  for (const p of services?.passes ?? []) byProduct.set(productLabel(p.service.product), (byProduct.get(productLabel(p.service.product)) ?? 0) + 1)

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
          <dt>Velocidad máxima</dt>
          <dd>{segment.max_speed_kmh ? `${segment.max_speed_kmh} km/h` : 'sin dato'}</dd>
        </div>
        <div>
          <dt>Vías</dt>
          <dd data-testid="tramo-vias">{tracksLabel(segment.tracks)}</dd>
        </div>
      </dl>

      <Plegable>
        <dl className="datos-tramo datos">
          <div>
            <dt>Puntos kilométricos</dt>
            <dd data-testid="tramo-pk">
              del {formatKm(segment.km_from)} al {formatKm(segment.km_to)}
            </dd>
          </div>
          <div>
            <dt>Velocidad habitual</dt>
            <dd>{segment.typical_speed_kmh ? `${segment.typical_speed_kmh} km/h` : 'sin dato'}</dd>
          </div>
        </dl>
        <p className="suave">
          El punto kilométrico es la distancia medida a lo largo de la vía desde el origen de la línea. La velocidad habitual es la que Oniel usa para
          estimar la hora de paso de los trenes que no paran en el tramo.
        </p>
        <PieFuente de="del trazado" sources={[sources.find((s) => s.id === segment.source_id)]} />
      </Plegable>

      {interruptions.map((i) => (
        <InterruptionNotice key={i.id} interruption={i} />
      ))}

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
      {/* el tramo está interrumpido el día de la lista: los trenes son los del horario, no los que circulan */}
      {services?.interruptions?.map((i) => (
        <p key={i.id} className="nota-horario" data-testid="nota-horario">
          {i.schedule_note}
        </p>
      ))}
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
                    {productLabel(p.service.product)} {p.service.train_number}
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
