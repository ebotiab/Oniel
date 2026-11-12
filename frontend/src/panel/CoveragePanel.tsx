import { Fragment, useEffect, useState } from 'react'

import type { AlternativesOut, AnnotationOut, CoverageOut, NetworkOut, SegmentAlternatives } from '../data/types'
import { fetchAlternatives, type ApiStatus } from '../data/api'
import { conAlternativa, costeCorto, grupoPrincipal, sinAlternativa, trenes } from '../app/alternativas'
import { formatDate, formatKm, lineLabel, lineKind, listaEs } from '../app/state'
import { ANNOTATION_LAYERS } from '../app/annotationLayers'
import { AnnotationNotice } from './AnnotationNotice'
import { Plegable } from './Plegable'
import { Termino } from './Termino'

interface Props {
  coverage: CoverageOut
  network: NetworkOut
  /** Día de los trenes que se cuentan por tramo. */
  referenceDate: string | null
  onSelectSegment: (id: string) => void
  /** Anotaciones de red vigentes hoy; cada tipo tiene su apartado. */
  annotations: AnnotationOut[]
  status: ApiStatus
  onClose: () => void
}

/**
 * Tramos cuyos trenes no tendrían otro camino en las líneas cargadas si el tramo se cortara, del
 * que más trenes lleva al que menos; los demás, plegados, con lo que añade su otro camino.
 */
function TramosSinAlternativa({ coverage, network, referenceDate, onSelectSegment }: Pick<Props, 'coverage' | 'network' | 'referenceDate' | 'onSelectSegment'>) {
  const [datos, setDatos] = useState<AlternativesOut | null>(null)
  const [fallo, setFallo] = useState(false)
  useEffect(() => {
    let vivo = true
    fetchAlternatives(referenceDate ?? undefined)
      .then((d) => vivo && setDatos(d))
      .catch(() => vivo && setFallo(true))
    return () => {
      vivo = false
    }
  }, [referenceDate])

  const fila = (s: SegmentAlternatives, derecha: string, debajo: string) => {
    const segment = network.segments.find((x) => x.id === s.segment_id)
    if (!segment) return null
    return (
      <li key={s.segment_id}>
        <span className="destino">
          <button type="button" className="enlace" onClick={() => onSelectSegment(s.segment_id)} data-testid={`tramo-${s.segment_id}`}>
            {segment.from_name} – {segment.to_name}
          </button>
          <span className="suave">{debajo}</span>
        </span>
        <span className="cuantos datos">{derecha}</span>
      </li>
    )
  }
  const linea = (s: SegmentAlternatives) => {
    const line = network.lines.find((l) => l.id === network.segments.find((x) => x.id === s.segment_id)?.line_id)
    return line ? `${lineKind(line) === 'alta velocidad' ? 'Alta velocidad' : 'Línea convencional'} ${lineLabel(line)}` : ''
  }
  const sin = datos ? sinAlternativa(datos.segments) : []
  const con = datos ? conAlternativa(datos.segments) : []
  const faltan = datos ? coverage.operators.filter((o) => datos.missing_operator_ids.includes(o.id)).map((o) => o.name) : []

  return (
    <>
      <h3 className="subtitulo">Tramos con más trenes y sin alternativa</h3>
      {fallo && <p className="texto suave">No se ha podido cargar este apartado.</p>}
      {!datos && !fallo && <p className="texto suave">Cargando…</p>}
      {datos && (
        <div data-testid="tramos-sin-alternativa">
          <p className="texto suave" data-testid="alternativa-alcance">
            {sin.length > 0
              ? 'Si uno de estos tramos se cortara, sus trenes no tendrían otro camino en las líneas que Oniel tiene cargadas.'
              : 'Si se cortara un tramo cualquiera, sus trenes tendrían otro camino en las líneas que Oniel tiene cargadas.'}{' '}
            No quiere decir que {sin.length > 0 ? 'no exista' : 'sea el único'} en la red real.
            {faltan.length > 0 && ` Faltan los trenes de ${listaEs(faltan)}, que no publica${faltan.length > 1 ? 'n' : ''} sus horarios en un formato abierto.`}
          </p>
          {sin.length > 0 && (
            <ol className="lista-destinos" data-testid="lista-sin-alternativa">
              {sin.map((s) => fila(s, s.without_alternative === s.trains ? trenes(s.trains) : `${s.without_alternative} de ${trenes(s.trains)}`, linea(s)))}
            </ol>
          )}
          {con.length > 0 && (
            <Plegable
              rotulo={sin.length > 0 ? `${con.length === 1 ? 'El otro tramo tiene' : `Los otros ${con.length} tramos tienen`} otro camino` : `Los ${con.length} tramos y lo que añade su otro camino`}
              memoria="tramos-con-alternativa"
              testId="tramos-con-alternativa"
            >
              <p className="suave">
                Del que más trenes lleva al que menos. Lo que añade el otro camino es lo de los trenes más numerosos de cada tramo: kilómetros por cada línea y
                tiempo a la velocidad habitual, sin paradas. Oniel solo comprueba que el camino existe y cuánto mide: no mira si el tren cabe por él (ancho
                de vía, paradas, sitio en la vía).
              </p>
              <ol className="lista-destinos" data-testid="lista-con-alternativa">
                {con.map((s) => {
                  const principal = grupoPrincipal(s)
                  return fila(s, trenes(s.trains), principal?.alternative ? costeCorto(principal.alternative) : '')
                })}
              </ol>
            </Plegable>
          )}
          {datos.date && <p className="suave destinos-nota">Trenes del {formatDate(datos.date)}, un tramo cortado cada vez y sin contar las interrupciones vigentes.</p>}
        </div>
      )}
    </>
  )
}

export function CoveragePanel({ coverage, network, referenceDate, annotations, status, onSelectSegment, onClose }: Props) {
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
      <TramosSinAlternativa coverage={coverage} network={network} referenceDate={referenceDate} onSelectSegment={onSelectSegment} />
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
