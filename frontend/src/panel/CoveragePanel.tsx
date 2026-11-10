import type { CoverageOut, InterruptionOut } from '../data/types'
import type { ApiStatus } from '../data/api'
import { formatDate, formatKm } from '../app/state'
import { InterruptionNotice } from './InterruptionNotice'

interface Props {
  coverage: CoverageOut
  /** Interrupciones del servicio vigentes hoy. */
  interruptions: InterruptionOut[]
  status: ApiStatus
  onClose: () => void
}

export function CoveragePanel({ coverage, interruptions, status, onClose }: Props) {
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
        Operadores: {coverage.operators.map((o) => o.name).join(', ')}.
        {status === 'ausente' ? ' Esta vista previa muestra una instantánea estática; la simulación necesita el servidor.' : ''}
        {status === 'buscando' ? ' El servidor se está despertando; hasta que responda se muestra la instantánea estática.' : ''}
      </p>
      <h3 className="subtitulo">Interrupciones del servicio</h3>
      {interruptions.length > 0 ? (
        <div data-testid="cobertura-interrupciones">
          <p className="texto suave">
            Tramos de las líneas cargadas en los que hoy no circulan trenes. Se registran y se revisan a mano, cada una con sus fuentes y la fecha de la
            última comprobación.
          </p>
          {interruptions.map((i) => (
            <InterruptionNotice key={i.id} interruption={i} />
          ))}
        </div>
      ) : (
        <p className="texto suave">Oniel no tiene registrada ninguna interrupción vigente hoy en las líneas cargadas.</p>
      )}
      <h3 className="subtitulo">Pendiente de cargar</h3>
      <p className="texto suave">
        El resto de la red ferroviaria española, otros operadores (Iryo, Ouigo, mercancías) y otros medios de transporte. El modelo
        de datos ya los contempla: cada línea, nodo y servicio lleva su fuente, su licencia y su fecha.
      </p>
      <h3 className="subtitulo">Fuentes</h3>
      <ul className="fuentes">
        {coverage.sources.map((s) => (
          <li key={s.id}>
            <strong>{s.name}</strong>
            <br />
            <span className="suave">
              {s.publisher} · {s.license} · {s.retrieved_on ? `consultado el ${formatDate(s.retrieved_on)}` : ''}
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
