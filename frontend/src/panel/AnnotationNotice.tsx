import type { AnnotationOut } from '../data/types'
import { annotationHref, annotationLayer } from '../app/annotationLayers'
import { formatDateLong, lugar, sourceLabels } from '../app/annotations'
import { Termino } from './Termino'

interface Props {
  annotation: AnnotationOut
  /** La anotación ya terminó: se enseña como registro, sin el color de señal de las vigentes. */
  pasada?: boolean
}

/**
 * Ficha de una anotación de red: dónde, qué, desde cuándo, hasta cuándo y según quién, con la fuente
 * y la fecha de comprobación al pie. La etiqueta, el renglón de fechas y el aspecto salen de la capa
 * de su tipo (annotationLayers.ts); un tipo sin capa no se enseña.
 */
export function AnnotationNotice({ annotation: a, pasada = false }: Props) {
  const capa = annotationLayer(a.kind)
  if (!capa) return null
  if (pasada && !capa.ficha.pasada) return null
  // Una que ya terminó se enseña con el rótulo, la etiqueta y el identificador de «pasada», sin color de señal.
  const ficha = pasada && capa.ficha.pasada ? { ...capa.ficha, ...capa.ficha.pasada, senal: capa.ficha.senal, clase: `${capa.ficha.clase} pasada` } : capa.ficha
  const donde = lugar(a)
  const senal = pasada && capa.ficha.pasada ? capa.ficha.pasada.senal : capa.ficha.senal(a)
  const fechas = ficha.fechas(a)
  const href = annotationHref(a)
  return (
    <aside className={ficha.clase} aria-label={ficha.rotulo} data-testid={ficha.testId}>
      <p className="sobre">
        <span className={`senal ${senal.clase}`}>{senal.termino ? <Termino id={senal.termino}>{senal.texto}</Termino> : senal.texto}</span> {donde}
      </p>
      {a.title && a.title !== donde && <p className="texto">{a.title}</p>}
      {a.reason && <p className="texto">{a.reason}</p>}
      {fechas && (
        <p className="texto" data-testid={`${ficha.testId}-fechas`}>
          {fechas}
        </p>
      )}
      {a.note && <p className="texto suave">{a.note}</p>}
      {href && ficha.enlace && (
        <p className="texto">
          <a className="enlace" href={href} data-testid={`${ficha.testId}-enlace`}>
            {ficha.enlace}
          </a>
        </p>
      )}
      <PieDeAnotacion annotation={a} testId={`${ficha.testId}-fuentes`} />
    </aside>
  )
}

/** Pie de una anotación: sus fuentes, con enlace, y el día de la última comprobación. */
export function PieDeAnotacion({ annotation: a, testId }: { annotation: AnnotationOut; testId: string }) {
  const labels = sourceLabels(a.sources)
  return (
    <p className="suave" data-testid={testId}>
      {a.sources.length > 1 ? 'Fuentes' : 'Fuente'}:{' '}
      {a.sources.map((s, n) => (
        <span key={s.id}>
          {n > 0 && ' · '}
          {s.url ? (
            <a href={s.url} target="_blank" rel="noreferrer" title={s.name} aria-label={`${labels[n]}: ${s.name}`}>
              {labels[n]}
            </a>
          ) : (
            labels[n]
          )}
        </span>
      ))}
      . Comprobado el {formatDateLong(a.checked_on)}.
    </p>
  )
}
