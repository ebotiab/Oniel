import { useEffect, useState } from 'react'

import { fetchHistory } from '../data/api'
import type { HistoryPoint, Operator, ServiceHistoryOut, Source } from '../data/types'
import { formatCount, formatDayShort, formatDayShortYear } from '../app/state'

interface Props {
  /** De qué es la ficha: una estación o un tramo. */
  kind: 'nodes' | 'segments'
  id: string
  operators: Operator[]
  sources: Source[]
  /** Cita la fuente de los horarios al pie. La ficha de la estación ya la cita justo debajo. */
  conFuente?: boolean
}

/** Los ficheros de una misma fuente se relevan entre sí: son los que se pueden comparar. */
function porFuente(points: HistoryPoint[]): HistoryPoint[][] {
  const grupos = new Map<string, HistoryPoint[]>()
  for (const p of points) grupos.set(p.source_id, [...(grupos.get(p.source_id) ?? []), p])
  // Hace falta más de un horario de la fuente, y que en alguno haya trenes aquí.
  return [...grupos.values()].filter((g) => g.length > 1 && g.some((p) => p.trains > 0))
}

const trenes = (n: number) => `${formatCount(n)} ${n === 1 ? 'tren' : 'trenes'}`

/**
 * Qué cambia de un horario al anterior de su operador, contados los dos en los mismos días. El día
 * de referencia de dos horarios seguidos suele coincidir, y entonces no dice nada; esto sí.
 */
function cambio(p: HistoryPoint, anterior: string): string | null {
  const c = p.change
  if (!c) return null
  const dias = `Del ${formatDayShort(c.date_from)} al ${formatDayShort(c.date_to)}, ${trenes(c.trains_after)}`
  const diferencia = c.trains_after - c.trains_before
  if (diferencia === 0) return `${dias}: los mismos que en ${anterior} esos mismos días.`
  return `${dias}: ${formatCount(Math.abs(diferencia))} ${diferencia > 0 ? 'más' : 'menos'} que en ${anterior} esos mismos días (${formatCount(c.trains_before)}).`
}

/**
 * Cómo cambia el servicio de un horario publicado al siguiente: los trenes de cada fichero
 * importado en su día de referencia, una línea por operador. Solo cifras con su fecha; no dice por
 * qué cambian. Con un solo horario por operador no hay nada que comparar y no se muestra nada.
 */
export function ServiceHistory({ kind, id, operators, sources, conFuente = false }: Props) {
  const [history, setHistory] = useState<ServiceHistoryOut | null>(null)

  // Las fichas se montan con key={id}, así que el estado se reinicia al cambiar de estación o tramo.
  useEffect(() => {
    let alive = true
    fetchHistory(kind, id)
      .then((h) => alive && setHistory(h))
      .catch(() => {
        /* sin histórico no se muestra nada: es un complemento del detalle */
      })
    return () => {
      alive = false
    }
  }, [kind, id])

  const grupos = porFuente(history?.points ?? [])
  if (!grupos.length) return null
  const fuentes = grupos.map((g) => sources.find((s) => s.id === g[0]!.source_id)).filter((s): s is Source => Boolean(s))

  return (
    <div className="evolucion" data-testid="evolucion">
      <p className="sobre">De un horario al siguiente</p>
      {grupos.map((g) => {
        const operador = operators.find((o) => o.id === g[0]!.operator_id)
        const testId = `evolucion-${g[0]!.operator_id ?? g[0]!.source_id}`
        const punto = (p: HistoryPoint) => `del ${formatDayShortYear(p.retrieved_on)}: ${trenes(p.trains)} el ${formatDayShort(p.date)}`
        // Con tres o más horarios un renglón ya no se lee: una lista por fechas, del más antiguo al más reciente.
        if (g.length > 2) {
          return (
            <div key={g[0]!.source_id} data-testid={testId}>
              {operador && <p className="texto">{operador.name}</p>}
              <ul className="lista-simple datos">
                {g.map((p) => (
                  <li key={p.dataset_id}>
                    Horario {punto(p)}
                    {p.change && <span className="suave"> {cambio(p, 'el horario anterior')}</span>}
                  </li>
                ))}
              </ul>
            </div>
          )
        }
        const ultimo = g[1]!
        return (
          <div key={g[0]!.source_id}>
            <p className="texto datos" data-testid={testId}>
              {operador ? `${operador.name}. ` : ''}
              {g.map((p, i) => `${i ? 'horario' : 'Horario'} ${punto(p)}`).join(' · ')}
            </p>
            {ultimo.change && (
              <p className="texto datos" data-testid={`${testId}-cambio`}>
                {cambio(ultimo, `el horario del ${formatDayShortYear(ultimo.change.previous_retrieved_on)}`)}
              </p>
            )}
          </div>
        )
      })}
      <p className="suave">
        Oniel guarda cada horario que descarga para poder compararlos. La fecha de cada horario es el día en que se descargó, y la cifra, los trenes
        que {kind === 'nodes' ? 'paran aquí' : 'recorren el tramo'} en un día laborable de los primeros que cubre. Si los días son distintos, parte de
        la diferencia puede venir del día de la semana.
      </p>
      {grupos.some((g) => g.some((p) => p.change)) && (
        <p className="suave">
          Para ver qué cambia de un horario al siguiente se cuentan los dos en los mismos días, las cuatro primeras semanas del más reciente: un tren
          por cada día que circula.
        </p>
      )}
      {conFuente &&
        fuentes.map((s) => (
          <p key={s.id} className="suave" data-testid="evolucion-fuente">
            Fuente de los horarios:{' '}
            {s.url ? (
              <a href={s.url} target="_blank" rel="noreferrer">
                {s.publisher}
              </a>
            ) : (
              s.publisher
            )}
            . {s.name}. <span className="datos">Identificador de la fuente: {s.id}</span>
          </p>
        ))}
    </div>
  )
}
