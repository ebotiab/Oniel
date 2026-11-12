import type { InterruptionOut, SourceRef } from '../data/types'
import { endLabel, formatDateLong } from '../app/interruptions'
import { Termino } from './Termino'

interface Props {
  interruption: InterruptionOut
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

/** Bloque de una interrupción del servicio: dónde, por qué, desde cuándo, hasta cuándo y según quién. */
export function InterruptionNotice({ interruption: i }: Props) {
  const labels = sourceLabels(i.sources)
  return (
    <aside className="interrupcion" aria-label="Interrupción del servicio" data-testid="interrupcion">
      <p className="sobre">
        <span className="senal roja">
          <Termino id="sin-circulacion">sin circulación</Termino>
        </span>{' '}
        {i.from_name} – {i.to_name}
      </p>
      <p className="texto">{i.reason}</p>
      <p className="texto" data-testid="interrupcion-fechas">
        Desde el {formatDateLong(i.start_date)}. {endLabel(i)}
      </p>
      {i.note && <p className="texto suave">{i.note}</p>}
      <p className="suave" data-testid="interrupcion-fuentes">
        {i.sources.length > 1 ? 'Fuentes' : 'Fuente'}:{' '}
        {i.sources.map((s, n) => (
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
        . Comprobado el {formatDateLong(i.checked_on)}.
      </p>
    </aside>
  )
}
