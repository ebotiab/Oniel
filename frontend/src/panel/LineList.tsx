import { useEffect, useMemo, useState } from 'react'

import { normalize } from '../app/search'
import type { AnnotationLayer } from '../app/annotationLayers'
import { bypassesOf, formatCount, lineKind, lineShortLabel, mainLines } from '../app/state'
import type { LineSummary, NodeOut, ZoneOut } from '../data/types'
import { Muestra } from './Legend'
import { Termino } from './Termino'

interface Props {
  lines: LineSummary[]
  /** Los nodos de la red, cada uno con su línea: de ellos salen las estaciones por las que pasa cada una. */
  nodes: Pick<NodeOut, 'name' | 'kind' | 'line_id'>[]
  /** Capas de anotaciones con algo vigente hoy en cada línea, por id de línea. */
  notes: Map<string, AnnotationLayer[]>
  onPick: (id: string) => void
  /** Las líneas por las que se pasa (una fila, o todas las de una zona): el mapa las resalta. Nulo al salir. */
  onHighlight: (ids: string[] | null) => void
}

/** A partir de este número de líneas la lista lleva un campo para filtrarla. */
export const FILTER_FROM = 8
/** Con más líneas que estas, las zonas empiezan plegadas y la lista es un índice de zonas. */
export const FOLD_ABOVE = 12

/** Las líneas sin zona declarada no se pierden: van al final, en un grupo propio. */
const SIN_ZONA: ZoneOut = { id: 'sin-zona', name: 'Otras líneas', sort_order: Number.MAX_SAFE_INTEGER, cities: [] }

const TIPOS = [
  { trazo: 'alta-velocidad', termino: 'alta-velocidad', label: 'Alta velocidad' },
  { trazo: 'convencional', termino: 'linea-convencional', label: 'Línea convencional' },
] as const

const cuantas = (n: number) => (n === 1 ? '1 línea' : `${formatCount(n)} líneas`)

/** Dentro de una zona: primero la alta velocidad y, en cada tipo, de la línea más larga a la más corta. */
function porTipoYLongitud(a: LineSummary, b: LineSummary): number {
  const av = (l: LineSummary) => Number(lineKind(l) === 'alta velocidad')
  return av(b) - av(a) || b.length_km - a.length_km || a.name.localeCompare(b.name, 'es')
}

/**
 * Lista de las líneas cargadas, agrupada por la zona a la que llevan y pensada para decenas de líneas: cada
 * línea es un renglón, cada zona se pliega y, cuando son muchas, la lista arranca como un índice de zonas.
 * El filtro busca en el nombre y en las estaciones por las que pasa cada línea. Un baipás no es un
 * renglón más: va colgado de la línea de la que sale, sangrado, y no cuenta en los recuentos.
 */
export function LineList({ lines: todas, nodes, notes, onPick, onHighlight }: Props) {
  const lines = useMemo(() => mainLines(todas), [todas])
  const [query, setQuery] = useState('')
  // Las zonas que el visitante ha abierto o cerrado a mano; las demás siguen la regla general.
  const [tocadas, setTocadas] = useState<Record<string, boolean>>({})
  const filterable = lines.length >= FILTER_FROM
  // Al elegir una línea la lista desaparece sin que el cursor salga de la fila: se suelta el resalte.
  useEffect(() => () => onHighlight(null), [onHighlight])
  const plegadas = lines.length > FOLD_ABOVE

  const estaciones = useMemo(() => {
    const out = new Map<string, { name: string; text: string }[]>()
    for (const n of nodes) {
      if (n.kind !== 'estacion') continue
      const list = out.get(n.line_id) ?? []
      list.push({ name: n.name, text: normalize(n.name) })
      out.set(n.line_id, list)
    }
    return out
  }, [nodes])

  const tokens = normalize(query).split(' ').filter(Boolean)
  const filtrando = tokens.length > 0
  // Cada línea que coincide, con la estación por la que coincide cuando no es por su nombre.
  const shown = useMemo(() => {
    const out: { line: LineSummary; por: string | null }[] = []
    for (const line of lines) {
      const coincide = (nombre: string) => tokens.every((t) => normalize(nombre).includes(t))
      if (!tokens.length || coincide(line.name)) out.push({ line, por: null })
      else {
        const est = estaciones.get(line.id)?.find((e) => tokens.every((t) => e.text.includes(t)))
        if (est) out.push({ line, por: est.name })
        // por el nombre de uno de sus baipases, que va colgado de ella
        else if (bypassesOf(todas, line.id).some((b) => coincide(b.name))) out.push({ line, por: null })
      }
    }
    return out
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [lines, todas, estaciones, query])

  const zonas = useMemo(() => {
    const byId = new Map<string, { zone: ZoneOut; rows: typeof shown; all: LineSummary[] }>()
    for (const line of lines) {
      const zone = line.zone ?? SIN_ZONA
      const z = byId.get(zone.id) ?? { zone, rows: [], all: [] }
      z.all.push(line)
      byId.set(zone.id, z)
    }
    for (const row of shown) byId.get((row.line.zone ?? SIN_ZONA).id)!.rows.push(row)
    return [...byId.values()]
      .filter((z) => z.rows.length)
      .sort((a, b) => a.zone.sort_order - b.zone.sort_order)
      .map((z) => ({ ...z, rows: z.rows.sort((a, b) => porTipoYLongitud(a.line, b.line)) }))
  }, [lines, shown])

  const tipos = TIPOS.filter((t) => lines.some((l) => (lineKind(l) === 'alta velocidad') === (t.trazo === 'alta-velocidad')))
  const resaltar = (ids: string[] | null) => ({
    onMouseEnter: () => onHighlight(ids),
    onMouseLeave: () => onHighlight(null),
    onFocus: () => onHighlight(ids),
    onBlur: () => onHighlight(null),
  })

  return (
    <div className="lista-lineas" data-testid="lista-lineas">
      {filterable && (
        <input
          type="search"
          className="filtro-lineas"
          aria-label="Filtrar las líneas por nombre, ciudad o estación"
          placeholder="Filtrar por línea, ciudad o estación"
          autoComplete="off"
          spellCheck={false}
          value={query}
          onChange={(e) => setQuery(e.target.value)}
          data-testid="filtro-lineas"
        />
      )}
      {/* La clave de los trazos: con las líneas agrupadas por zona, el tipo de cada una lo dice su muestra. */}
      <p className="clave-lineas" data-testid="clave-lineas">
        {tipos.map((t) => (
          <span key={t.trazo}>
            <Muestra trazo={t.trazo} />
            <Termino id={t.termino}>{t.label}</Termino>
          </span>
        ))}
      </p>
      {zonas.map(({ zone, rows, all }) => {
        // filtrando, las zonas con coincidencias están siempre abiertas
        const abierta = filtrando || (tocadas[zone.id] ?? !plegadas)
        const conNota = [...new Set(all.flatMap((l) => notes.get(l.id) ?? []))].filter((capa) => capa.lista)
        // Las ciudades de la zona que tienen estación en alguna de sus líneas.
        const ciudades = zone.cities.filter((c) => all.some((l) => estaciones.get(l.id)?.some((e) => e.text.startsWith(normalize(c)))))
        return (
          <section key={zone.id} className="zona-lineas" aria-label={zone.name} data-testid={`zona-${zone.id}`}>
            <h4>
              <button
                type="button"
                className="zona-cabecera"
                aria-expanded={abierta}
                onClick={() => setTocadas((cur) => ({ ...cur, [zone.id]: !abierta }))}
                {...resaltar(all.flatMap((l) => [l.id, ...bypassesOf(todas, l.id).map((b) => b.id)]))}
              >
                <span className="zona-chevron" aria-hidden="true">
                  ›
                </span>
                <span className="zona-nombre">{zone.name}</span>
                <span className="datos suave">{cuantas(rows.length)}</span>
                {!abierta && (ciudades.length > 0 || conNota.length > 0) && (
                  <span className="zona-detalle">
                    {ciudades.join(', ')}
                    {conNota.map(({ kind, lista }) => {
                      const n = all.filter((l) => notes.get(l.id)?.some((c) => c.kind === kind)).length
                      return (
                        lista && (
                          <span key={kind} className={`senal ${lista.senal.clase}`}>
                            {n === 1 ? 'una línea' : `${n} líneas`} con {lista.senal.texto}
                          </span>
                        )
                      )
                    })}
                  </span>
                )}
              </button>
            </h4>
            {abierta && (
              <ul>
                {rows.map(({ line: l, por }) => {
                  const senales = notes.get(l.id)?.filter((capa) => capa.lista) ?? []
                  const av = lineKind(l) === 'alta velocidad'
                  const baipases = bypassesOf(todas, l.id)
                  return (
                    <li key={l.id}>
                      <button
                        type="button"
                        className="fila-linea"
                        onClick={() => onPick(l.id)}
                        data-testid={`linea-${l.id}`}
                        {...resaltar([l.id, ...baipases.map((b) => b.id)])}
                      >
                        <span className="fila-linea-trazo" title={av ? 'Alta velocidad' : 'Línea convencional'}>
                          <Muestra trazo={av ? 'alta-velocidad' : 'convencional'} />
                          <span className="visually-hidden">{av ? 'Alta velocidad' : 'Línea convencional'}: </span>
                        </span>
                        <span className="fila-linea-nombre">{lineShortLabel(l)}</span>
                        <span className="fila-linea-km datos">{formatCount(Math.round(l.length_km))} km</span>
                        {(por || senales.length > 0) && (
                          <span className="fila-linea-detalle">
                            {por && <span>pasa por {por}</span>}
                            {senales.map(
                              ({ kind, lista }) =>
                                lista && (
                                  <span key={kind} className={`senal ${lista.senal.clase}`}>
                                    {lista.senal.texto}
                                  </span>
                                ),
                            )}
                          </span>
                        )}
                      </button>
                      {baipases.length > 0 && (
                        <ul className="baipases-linea" aria-label={`${baipases.every((b) => b.bypass_of) ? 'Baipases' : baipases.some((b) => b.bypass_of) ? 'Baipases y enlaces' : 'Enlaces'} de ${lineShortLabel(l)}`}>
                          {baipases.map((b) => (
                            <li key={b.id}>
                              <button type="button" className="fila-baipas" onClick={() => onPick(b.id)} data-testid={`linea-${b.id}`} {...resaltar([b.id])}>
                                <span>{b.name}</span>
                                <span className="fila-linea-km datos">{formatCount(Math.round(b.length_km))} km</span>
                              </button>
                            </li>
                          ))}
                        </ul>
                      )}
                    </li>
                  )
                })}
              </ul>
            )}
          </section>
        )
      })}
      {shown.length === 0 && (
        <p className="suave" role="status">
          Ninguna línea coincide. Prueba con una ciudad o una estación.
        </p>
      )}
    </div>
  )
}
