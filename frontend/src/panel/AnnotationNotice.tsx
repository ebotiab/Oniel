import type { AnnotationOut, SourceRef } from '../data/types'
import { annotationLayer } from '../app/annotationLayers'
import { formatDateLong } from '../app/annotations'

interface Props {
  annotation: AnnotationOut
}

/** Rótulo breve de cada fuente: quien la publica, numerado cuando aporta más de una («Adif (2)»). */
function sourceLabels(sources: SourceRef[]): string[] {
  const seen = new Map<string, number>()
  return sources.map((s) => {
    const publisher = s.publisher.split(';')[0]!.trim()
    const n = (seen.get(publisher) ?? 0) + 1
    seen.set(publisher, n)
    return n > 1 ? `${publisher} (${n})` : publisher
  })
}

/** Dónde cae: de un nodo a otro, en un nodo o, con geometría propia, su nombre. */
function lugar(a: AnnotationOut): string | null {
  if (a.from_name && a.to_name) return `${a.from_name} – ${a.to_name}`
  return a.node_name ?? a.title
}

/**
 * Ficha de una anotación de red: dónde, qué, desde cuándo, hasta cuándo y según quién, con la fuente
 * y la fecha de comprobación al pie. La etiqueta, el renglón de fechas y el aspecto salen de la capa
 * de su tipo (annotationLayers.ts); un tipo sin capa no se enseña.
 */
export function AnnotationNotice({ annotation: a }: Props) {
  const capa = annotationLayer(a.kind)
  if (!capa) return null
  const { ficha } = capa
  const labels = sourceLabels(a.sources)
  const donde = lugar(a)
  return (
    <aside className={ficha.clase} aria-label={ficha.rotulo} data-testid={ficha.testId}>
      <p className="sobre">
        <span className={`senal ${ficha.senal.clase}`}>{ficha.senal.texto}</span> {donde}
      </p>
      {a.title && a.title !== donde && <p className="texto">{a.title}</p>}
      {a.reason && <p className="texto">{a.reason}</p>}
      <p className="texto" data-testid={`${ficha.testId}-fechas`}>
        {ficha.fechas(a)}
      </p>
      {a.note && <p className="texto suave">{a.note}</p>}
      <p className="suave" data-testid={`${ficha.testId}-fuentes`}>
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
    </aside>
  )
}
