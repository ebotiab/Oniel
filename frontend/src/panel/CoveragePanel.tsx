import { Fragment } from 'react'

import type { AnnotationOut, CoverageOut } from '../data/types'
import type { ApiStatus } from '../data/api'
import { formatDate, formatKm } from '../app/state'
import { ANNOTATION_LAYERS } from '../app/annotationLayers'
import { AnnotationNotice } from './AnnotationNotice'
import { Termino } from './Termino'

interface Props {
  coverage: CoverageOut
  /** Anotaciones de red vigentes hoy; cada tipo tiene su apartado. */
  annotations: AnnotationOut[]
  status: ApiStatus
  onClose: () => void
}

export function CoveragePanel({ coverage, annotations, status, onClose }: Props) {
  return (
    <section className="detalle cobertura" aria-labelledby="cob-titulo" data-testid="panel-cobertura">
      <button type="button" className="enlace volver" onClick={onClose}>
        ← Cerrar
      </button>
      <p className="sobre">Qué hay en esta versión</p>
      <h2 id="cob-titulo" className="titulo">
        Cobertura y fuentes
      </h2>
      <p className="texto">{coverage.notice}</p>
      <dl className="datos-tramo datos">
        <div>
          <dt>Líneas cargadas</dt>
          <dd>{coverage.lines.length}</dd>
        </div>
        <div>
          <dt>Kilómetros</dt>
          <dd>{formatKm(coverage.total_length_km)}</dd>
        </div>
        <div>
          <dt>Estaciones</dt>
          <dd>{coverage.station_count}</dd>
        </div>
        <div>
          <dt>Trenes distintos</dt>
          <dd>{coverage.service_count}</dd>
        </div>
      </dl>
      <p className="suave">
        Horarios válidos del {coverage.feed_start ? formatDate(coverage.feed_start) : '–'} al {coverage.feed_end ? formatDate(coverage.feed_end) : '–'}.
        {status === 'ausente' ? ' Esta vista previa muestra una instantánea estática; la simulación necesita el servidor.' : ''}
        {status === 'buscando' ? ' El servidor se está despertando; hasta que responda se muestra la instantánea estática.' : ''}
      </p>
      <h3 className="subtitulo">
        <Termino id="operador">Operadores</Termino> de trenes
      </h3>
      <ul className="fuentes" data-testid="cobertura-operadores">
        {coverage.operators
          .filter((o) => o.role === 'operador')
          // primero los que tienen horarios cargados
          .sort((a, b) => Number(a.timetable === 'no_publicado') - Number(b.timetable === 'no_publicado'))
          .map((o) => {
            const source = coverage.sources.find((s) => s.id === o.source_id)
            const dataset = coverage.datasets?.find((d) => d.operator_id === o.id)
            return (
              <li key={o.id}>
                <strong>{o.name}</strong>
                <br />
                {o.timetable === 'no_publicado' ? (
                  <span className="suave">
                    No publica sus horarios en un formato abierto: sus trenes no están cargados ni contados.
                    {source?.url && (
                      <>
                        {' '}
                        Consultado en{' '}
                        <a href={source.url} target="_blank" rel="noreferrer">
                          {source.url.replace(/^https?:\/\//, '')}
                        </a>
                        {source.retrieved_on ? ` el ${formatDate(source.retrieved_on)}` : ''}.
                      </>
                    )}
                  </span>
                ) : (
                  <span className="suave">
                    {source ? `${source.name} · ${source.publisher} · ${source.license}` : 'Sin fuente registrada'}
                    {dataset ? ` · válidos del ${formatDate(dataset.valid_from)} al ${formatDate(dataset.valid_to)}` : ''}
                  </span>
                )}
              </li>
            )
          })}
      </ul>
      {ANNOTATION_LAYERS.map(({ kind, cobertura }) => {
        const vigentes = annotations.filter((a) => a.kind === kind)
        return (
          <Fragment key={kind}>
            <h3 className="subtitulo">{cobertura.titulo}</h3>
            {vigentes.length > 0 ? (
              <div data-testid={cobertura.testId}>
                <p className="texto suave">{cobertura.entrada}</p>
                {vigentes.map((a) => (
                  <AnnotationNotice key={a.id} annotation={a} />
                ))}
              </div>
            ) : (
              <p className="texto suave">{cobertura.vacio}</p>
            )}
          </Fragment>
        )
      })}
      <h3 className="subtitulo">Pendiente de cargar</h3>
      <p className="texto suave">
        El resto de la red ferroviaria española, los trenes de Cercanías y de mercancías y otros medios de transporte. El modelo
        de datos ya los contempla: cada línea, nodo y servicio lleva su fuente, su licencia y su fecha.
      </p>
      <h3 className="subtitulo">Fuentes</h3>
      <ul className="fuentes">
        {coverage.sources.map((s) => (
          <li key={s.id}>
            <strong>{s.name}</strong>
            <br />
            <span className="suave">
              {s.publisher} ·{' '}
              {s.license_url ? (
                <a href={s.license_url} target="_blank" rel="noreferrer">
                  {s.license}
                </a>
              ) : (
                s.license
              )}{' '}
              · {s.retrieved_on ? `consultado el ${formatDate(s.retrieved_on)}` : ''}
            </span>
            {s.coverage && <p className="suave">{s.coverage}</p>}
            {s.notes && <p className="suave nota">{s.notes}</p>}
            {s.url && (
              <a href={s.url} target="_blank" rel="noreferrer">
                {s.url.replace(/^https?:\/\//, '')}
              </a>
            )}
          </li>
        ))}
      </ul>
    </section>
  )
}
