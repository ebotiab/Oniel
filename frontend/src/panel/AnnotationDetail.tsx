import type { AnnotationOut } from '../data/types'
import { annotationLayer } from '../app/annotationLayers'
import { formatPartialDate, lugar, sourceLabels } from '../app/annotations'
import { PieDeAnotacion } from './AnnotationNotice'

interface Props {
  annotation: AnnotationOut
  /** Abre el primer tramo de una anotación que va de un nodo a otro de una línea. */
  onSelectSegment: (id: string) => void
  onBack: () => void
}

/**
 * Ficha propia de una anotación de red (hoy, un proyecto): qué es y en qué estado está, dónde cae,
 * sus hitos fechados con la fuente de cada uno y, al pie, las fuentes y el día de la comprobación.
 * La etiqueta, el renglón de fechas y el aviso sobre el dibujo salen de la capa de su tipo.
 */
export function AnnotationDetail({ annotation: a, onSelectSegment, onBack }: Props) {
  const capa = annotationLayer(a.kind)
  if (!capa) return null
  const { ficha } = capa
  const senal = ficha.senal(a)
  const fechas = ficha.fechas(a)
  const donde = lugar(a)
  const titulo = a.title ?? donde ?? ficha.rotulo
  const hitos = a.milestones ?? []
  const labels = sourceLabels(a.sources)
  // La fuente de cada hito es una de las de la anotación: se cita con el mismo rótulo que al pie.
  const fuenteDe = (sourceId: string) => {
    const n = a.sources.findIndex((s) => s.id === sourceId)
    return n >= 0 ? { source: a.sources[n]!, rotulo: labels[n]! } : null
  }
  const primerTramo = a.segment_ids[0]
  return (
    <section className="detalle" aria-labelledby="anotacion-titulo" data-testid={`ficha-${ficha.testId}`}>
      <button type="button" className="enlace volver" onClick={onBack}>
        ← Toda la red
      </button>
      <p className="sobre" data-testid={`ficha-${ficha.testId}-estado`}>
        {ficha.rotulo} <span className={`senal ${senal.clase}`}>{senal.texto}</span>
      </p>
      <h2 id="anotacion-titulo" className="titulo">
        {titulo}
      </h2>
      {a.reason && <p className="texto">{a.reason}</p>}
      {donde && donde !== titulo && (
        <p className="texto">
          {primerTramo ? (
            <button type="button" className="enlace" onClick={() => onSelectSegment(primerTramo)}>
              {donde}
            </button>
          ) : (
            donde
          )}
        </p>
      )}
      {fechas && (
        <p className="texto" data-testid={`ficha-${ficha.testId}-fechas`}>
          {fechas}
        </p>
      )}
      {a.note && <p className="texto suave">{a.note}</p>}
      {a.geometry && capa.geometria && <p className="texto suave">{capa.geometria.aviso}</p>}
      {hitos.length > 0 && (
        <>
          <h3 className="subtitulo">Lo que se sabe, con su fecha</h3>
          <ul className="hitos" data-testid={`ficha-${ficha.testId}-hitos`}>
            {hitos.map((h) => {
              const fuente = fuenteDe(h.source_id)
              return (
                <li key={`${h.date}-${h.text}`}>
                  <span className="datos hito-fecha">{formatPartialDate(h.date)}</span>
                  <span>
                    {h.text}{' '}
                    {fuente && (
                      <span className="suave">
                        (
                        {fuente.source.url ? (
                          <a href={fuente.source.url} target="_blank" rel="noreferrer" title={fuente.source.name}>
                            {fuente.rotulo}
                          </a>
                        ) : (
                          fuente.rotulo
                        )}
                        )
                      </span>
                    )}
                  </span>
                </li>
              )
            })}
          </ul>
        </>
      )}
      <PieDeAnotacion annotation={a} testId={`ficha-${ficha.testId}-fuentes`} />
    </section>
  )
}
