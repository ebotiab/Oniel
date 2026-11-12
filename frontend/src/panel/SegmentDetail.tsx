import { useEffect, useState } from 'react'

import { ApiError, fetchSegmentServices } from '../data/api'
import type { AnnotationOut, NetworkOut, Operator, SegmentOut, SegmentPassOut, SegmentServicesOut, Source } from '../data/types'
import { formatDate, formatKm, lineKind, listaEs, productLabel, shortStop } from '../app/state'
import { AnnotationNotice } from './AnnotationNotice'
import { KindBadge } from './KindBadge'
import { PieFuente, Plegable } from './Plegable'
import { FilasAtributos } from './SegmentAttributes'
import { Termino } from './Termino'

interface Props {
  segment: SegmentOut
  network: NetworkOut
  /** Fuentes registradas, para citar al pie del detalle la del tramo. */
  sources: Source[]
  /** Operadores registrados, para nombrar al de cada tren. */
  operators: Operator[]
  referenceDate: string | null
  /** Anotaciones de red vigentes hoy en este tramo. */
  annotations: AnnotationOut[]
  /** Interrupciones ya terminadas que afectaron a este tramo: van en el detalle, como registro. */
  past?: AnnotationOut[]
  onSimulate: () => void
  onSelectNode: (id: string) => void
  onBack: () => void
}

export function SegmentDetail({ segment, network, sources, operators, referenceDate, annotations, past = [], onSimulate, onSelectNode, onBack }: Props) {
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

  // Los trenes de cada operador, del que más tiene al que menos; dentro, por hora de paso.
  const operatorName = (id: string) => operators.find((o) => o.id === id)?.name ?? id
  const byOperator = new Map<string, SegmentPassOut[]>()
  for (const p of services?.passes ?? []) byOperator.set(p.service.operator_id, [...(byOperator.get(p.service.operator_id) ?? []), p])
  const groups = [...byOperator.entries()]
    .map(([id, passes]) => ({ id, name: operatorName(id), passes }))
    .sort((a, b) => b.passes.length - a.passes.length || a.name.localeCompare(b.name, 'es'))

  // Operadores que circulan por la línea y no publican sus horarios: sus trenes no están en la lista.
  const missing = operators.filter((o) => o.timetable === 'no_publicado' && line?.operator_ids?.includes(o.id))

  return (
    <section className="detalle" aria-labelledby="detalle-titulo" data-testid="detalle-tramo">
      <button type="button" className="enlace volver" onClick={onBack}>
        ← Toda la línea
      </button>
      {/* lo primero, el tipo de vía en palabras: el mismo que dicen el trazo del mapa y la leyenda */}
      <p className="sobre" data-testid="tramo-tipo">
        {line && lineKind(line) === 'alta velocidad' ? <Termino id="alta-velocidad">Alta velocidad</Termino> : <Termino id="linea-convencional">Línea convencional</Termino>}
        {segment.tracks === 1 && (
          <>
            , <Termino id="via-unica">vía única</Termino>
          </>
        )}
      </p>
      <p className="sobre">
        <Termino id="tramo">Tramo</Termino> {segment.seq} de {line?.segment_count ?? '–'} · {line?.name}
      </p>
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
          <dt>
            <Termino id="velocidad-maxima">Velocidad máxima</Termino>
          </dt>
          <dd>{segment.max_speed_kmh ? `${segment.max_speed_kmh} km/h` : 'sin dato'}</dd>
        </div>
        <FilasAtributos segment={segment} line={line} lugar="esencial" />
      </dl>

      <Plegable>
        <dl className="datos-tramo datos">
          <div>
            <dt>
              <Termino id="punto-kilometrico">Puntos kilométricos</Termino>
            </dt>
            <dd data-testid="tramo-pk">
              del {formatKm(segment.km_from)} al {formatKm(segment.km_to)}
            </dd>
          </div>
          <div>
            <dt>
              <Termino id="velocidad-habitual">Velocidad habitual</Termino>
            </dt>
            <dd>{segment.typical_speed_kmh ? `${segment.typical_speed_kmh} km/h` : 'sin dato'}</dd>
          </div>
          <FilasAtributos segment={segment} line={line} lugar="detalle" />
        </dl>
        <p className="suave">
          El punto kilométrico es la distancia medida a lo largo de la vía desde el origen de la línea. La velocidad habitual es la que Oniel usa para
          estimar la hora de paso de los trenes que no paran en el tramo.
        </p>
        <PieFuente de="del trazado" sources={[sources.find((s) => s.id === segment.source_id)]} />
        {past.length > 0 && (
          <section className="anteriores" data-testid="interrupciones-anteriores">
            <p className="sobre">Interrupciones anteriores en este tramo</p>
            {past.map((a) => (
              <AnnotationNotice key={a.id} annotation={a} pasada />
            ))}
          </section>
        )}
      </Plegable>

      {annotations.map((a) => (
        <AnnotationNotice key={a.id} annotation={a} />
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
          {/* lo primero, de quién son los trenes: el total de la barra del esquema, por operador */}
          {groups.length > 0 && (
            <p className="texto datos" data-testid="tramo-operadores">
              {groups.length === 1 ? `Solo ${groups[0]!.name}` : groups.map((g) => `${g.name} ${g.passes.length}`).join(' · ')}
            </p>
          )}
          {missing.length > 0 && (
            <p className="suave" data-testid="tramo-operadores-sin-horarios">
              No están los trenes de {listaEs(missing.map((o) => o.name))}, que también opera{missing.length > 1 ? 'n' : ''} en esta línea: no publica
              {missing.length > 1 ? 'n' : ''} sus horarios en un formato abierto.
            </p>
          )}
          <p className="suave">
            {[...byProduct.entries()].map(([p, n]) => `${n} ${p}`).join(' · ')}. Paso con <Termino id="paso-publicado">horario publicado</Termino> en{' '}
            {services.counts.publicado}, <Termino id="paso-estimado">estimado</Termino> en {services.counts.estimado}
            {services.counts.indeterminado > 0 && (
              <>
                , <Termino id="paso-indeterminado">indeterminado</Termino> en {services.counts.indeterminado}
              </>
            )}
            .
          </p>
          <div data-testid="lista-servicios">
            {groups.map((g) => (
              <div key={g.id} data-testid={`trenes-${g.id}`}>
                {groups.length > 1 && (
                  <h4 className="operador">
                    {g.name} <span className="datos suave">· {g.passes.length}</span>
                  </h4>
                )}
                <ol className="lista-servicios">
                  {g.passes.map((p) => (
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
              </div>
            ))}
          </div>
        </>
      )}
    </section>
  )
}
