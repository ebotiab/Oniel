import { useMemo, useState } from 'react'

import { normalize } from '../app/search'
import { formatKm, lineKind, lineShortLabel } from '../app/state'
import type { LineSummary } from '../data/types'
import { Muestra } from './Legend'
import { Termino } from './Termino'

interface Props {
  lines: LineSummary[]
  /** Líneas con algún tramo sin circulación hoy. */
  interruptedLineIds: Set<string>
  onPick: (id: string) => void
}

/** A partir de este número de líneas la lista lleva un campo para filtrarla por nombre. */
export const FILTER_FROM = 8

const GROUPS = [
  { kind: 'alta velocidad', label: 'Alta velocidad', trazo: 'alta-velocidad', termino: 'alta-velocidad' },
  { kind: 'convencional', label: 'Línea convencional', trazo: 'convencional', termino: 'linea-convencional' },
] as const

/**
 * Lista de las líneas cargadas, agrupada por tipo. Es la misma con tres líneas que con cien: cada línea
 * ocupa un renglón doble, la lista se desplaza dentro del panel y, cuando son muchas, se filtra por nombre.
 */
export function LineList({ lines, interruptedLineIds, onPick }: Props) {
  const [query, setQuery] = useState('')
  const filterable = lines.length >= FILTER_FROM
  const shown = useMemo(() => {
    const tokens = normalize(query).split(' ').filter(Boolean)
    if (!tokens.length) return lines
    return lines.filter((l) => {
      const text = normalize(l.name)
      return tokens.every((t) => text.includes(t))
    })
  }, [lines, query])
  return (
    <div className="lista-lineas" data-testid="lista-lineas">
      {filterable && (
        <input
          type="search"
          className="filtro-lineas"
          aria-label="Filtrar las líneas por nombre"
          placeholder="Filtrar por nombre"
          autoComplete="off"
          spellCheck={false}
          value={query}
          onChange={(e) => setQuery(e.target.value)}
          data-testid="filtro-lineas"
        />
      )}
      {GROUPS.map((g) => {
        const group = shown.filter((l) => lineKind(l) === g.kind)
        if (!group.length) return null
        return (
          <section key={g.kind} aria-label={g.label}>
            <h4 className="grupo-lineas">
              <Muestra trazo={g.trazo} />
              <Termino id={g.termino}>{g.label}</Termino>
              <span className="datos suave">{group.length}</span>
            </h4>
            <ul>
              {group.map((l) => (
                <li key={l.id}>
                  <button
                    type="button"
                    className="fila-linea"
                    onClick={() => onPick(l.id)}
                    data-testid={`linea-${l.id}`}
                  >
                    <span className="fila-linea-nombre">{lineShortLabel(l)}</span>
                    <span className="fila-linea-detalle datos">
                      {formatKm(l.length_km)} km{l.max_speed_kmh ? ` · hasta ${l.max_speed_kmh} km/h` : ''}
                      {interruptedLineIds.has(l.id) && <span className="senal roja">un tramo sin circulación</span>}
                    </span>
                  </button>
                </li>
              ))}
            </ul>
          </section>
        )
      })}
      {shown.length === 0 && (
        <p className="suave" role="status">
          Ninguna línea coincide con ese nombre.
        </p>
      )}
    </div>
  )
}
