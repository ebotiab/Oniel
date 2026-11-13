import { useEffect, useMemo, useState, type MouseEvent } from 'react'

import { conAlternativa, costeCorto, grupoPrincipal, rangoTrenes, sinAlternativa, sinAlternativaPorLinea, trenes } from '../app/alternativas'
import { abreAparte } from '../app/navegacion'
import { formatDate, lineKind, lineShortLabel, listaEs, routePath } from '../app/state'
import { fetchAlternatives } from '../data/api'
import type { AlternativesOut, CoverageOut, NetworkOut, SegmentAlternatives } from '../data/types'
import { Muestra } from './Legend'
import { Plegable } from './Plegable'

interface Props {
  network: NetworkOut
  coverage: CoverageOut | null
  /** Día de los trenes que se cuentan por tramo. */
  referenceDate: string | null
  onSelectSegment: (id: string) => void
  onSimulate: (id: string) => void
  /** Lo que la vista pide resaltar en el mapa: todos los tramos sin otro camino y, en azul, los que se están mirando. */
  onMapa: (tramos: { todos: string[]; mirados: string[]; encuadre: string[] } | null) => void
}

/**
 * «Tramos sin otro camino»: los tramos cuyos trenes no tendrían por dónde ir en las líneas cargadas si el
 * tramo se cortara. Un renglón por línea, de la que más trenes deja sin camino a la que menos; al abrirla,
 * sus tramos en el orden en que se recorren. El mapa atenúa el resto de la red y pinta en azul lo que se mira.
 * Los demás tramos van plegados, con lo que añade su otro camino.
 */
export function NoAlternativePanel({ network, coverage, referenceDate, onSelectSegment, onSimulate, onMapa }: Props) {
  const [datos, setDatos] = useState<AlternativesOut | null>(null)
  const [fallo, setFallo] = useState(false)
  const [abierta, setAbierta] = useState<string | null>(null)
  const [elegido, setElegido] = useState<string | null>(null)
  const [encima, setEncima] = useState<string | null>(null)
  useEffect(() => {
    let vivo = true
    fetchAlternatives(referenceDate ?? undefined)
      .then((d) => vivo && setDatos(d))
      .catch(() => vivo && setFallo(true))
    return () => {
      vivo = false
    }
  }, [referenceDate])

  const sin = useMemo(() => (datos ? sinAlternativa(datos.segments) : []), [datos])
  const con = useMemo(() => (datos ? conAlternativa(datos.segments) : []), [datos])
  const lineas = useMemo(() => sinAlternativaPorLinea(sin, network), [sin, network])
  const faltan = datos && coverage ? coverage.operators.filter((o) => datos.missing_operator_ids.includes(o.id)).map((o) => o.name) : []

  // El mapa: todos los tramos sin otro camino y, en azul, el tramo elegido o la línea sobre la que se está.
  // Pasar el puntero por una línea la pinta sin mover el mapa; abrirla o elegir un tramo, además, lo encuadra.
  const todos = useMemo(() => sin.map((s) => s.segment_id), [sin])
  const { mirados, encuadre } = useMemo(() => {
    const deLinea = (id: string | null) => lineas.find((l) => l.line.id === id)?.tramos.map((s) => s.segment_id) ?? []
    const fijo = elegido ? [elegido] : deLinea(abierta)
    return { mirados: encima ? deLinea(encima) : fijo, encuadre: fijo.length ? fijo : todos }
  }, [lineas, encima, elegido, abierta, todos])
  useEffect(() => {
    onMapa(datos ? { todos, mirados, encuadre } : null)
  }, [datos, todos, mirados, encuadre, onMapa])
  useEffect(() => () => onMapa(null), [onMapa])

  const nombre = (id: string) => {
    const s = network.segments.find((x) => x.id === id)
    return s ? `${s.from_name} – ${s.to_name}` : id
  }
  const cuantos = (s: SegmentAlternatives) => (s.without_alternative === s.trains ? trenes(s.trains) : `${s.without_alternative} de ${trenes(s.trains)}`)
  const ir = (e: MouseEvent, hacer: () => void) => {
    if (abreAparte(e)) return
    e.preventDefault()
    hacer()
  }

  return (
    <section className="sin-camino" aria-labelledby="sin-camino-titulo" data-testid="vista-sin-otro-camino">
      <h2 id="sin-camino-titulo" className="titulo">
        Tramos sin otro camino
      </h2>
      {fallo && <p className="texto suave">No se ha podido cargar esta vista.</p>}
      {!datos && !fallo && <p className="texto suave">Cargando…</p>}
      {datos && (
        <div data-testid="tramos-sin-alternativa">
          <p className="entrada" data-testid="alternativa-alcance">
            {sin.length > 0
              ? 'Si uno de estos tramos se cortara, sus trenes no tendrían por dónde ir en las líneas que Oniel tiene cargadas.'
              : 'Si se cortara un tramo cualquiera, sus trenes tendrían otro camino en las líneas que Oniel tiene cargadas.'}{' '}
            No quiere decir que {sin.length > 0 ? 'no exista otro camino' : 'sea el único'} en la red real.
          </p>
          {sin.length > 0 && (
            <p className="texto sin-camino-resumen" data-testid="sin-camino-resumen">
              Son {sin.length} de los {sin.length + con.length} tramos con trenes, en {lineas.length === 1 ? 'una línea' : `${lineas.length} líneas`}. En el mapa, lo demás va atenuado.
            </p>
          )}
          {lineas.length > 0 && (
            <ol className="sin-camino-lineas" data-testid="lista-sin-alternativa">
              {lineas.map(({ line, tramos, min, max }) => {
                const abiertaEsta = abierta === line.id
                const entera = tramos.length === line.segment_count
                return (
                  <li key={line.id} className={abiertaEsta ? 'abierta' : undefined} data-testid={`sin-camino-linea-${line.id}`}>
                    <button
                      type="button"
                      className="sin-camino-linea"
                      aria-expanded={abiertaEsta}
                      onClick={() => {
                        setAbierta(abiertaEsta ? null : line.id)
                        setElegido(null)
                      }}
                      onPointerEnter={() => setEncima(line.id)}
                      onPointerLeave={() => setEncima(null)}
                    >
                      <span className="sin-camino-nombre">
                        <Muestra trazo={lineKind(line) === 'alta velocidad' ? 'alta-velocidad' : 'convencional'} />
                        {lineShortLabel(line)}
                      </span>
                      <span className="cuantos datos">{rangoTrenes(min, max)}</span>
                      <span className="suave">
                        {entera ? `Toda la línea, ${tramos.length} tramos` : tramos.length === 1 ? `1 de sus ${line.segment_count} tramos` : `${tramos.length} de sus ${line.segment_count} tramos`}
                      </span>
                      <span className="suave sin-camino-ver">{abiertaEsta ? 'Ocultar' : 'Ver los tramos'}</span>
                    </button>
                    {abiertaEsta && (
                      <ol className="sin-camino-tramos">
                        {tramos.map((s) => {
                          const activo = elegido === s.segment_id
                          const principal = s.groups[0]
                          return (
                            <li key={s.segment_id} className={activo ? 'activo' : undefined}>
                              <button type="button" className="sin-camino-tramo" aria-pressed={activo} onClick={() => setElegido(activo ? null : s.segment_id)} data-testid={`tramo-${s.segment_id}`}>
                                <span>{nombre(s.segment_id)}</span>
                                <span className="cuantos datos">{cuantos(s)}</span>
                              </button>
                              {activo && (
                                <div className="sin-camino-detalle" data-testid="sin-camino-detalle">
                                  {principal && s.groups.length > 1 && (
                                    <p className="suave">
                                      Los más numerosos ({principal.trains}) van entre {principal.from_name} y {principal.to_name}.
                                    </p>
                                  )}
                                  <p>
                                    <a
                                      href={routePath({ selection: { type: 'tramo', id: s.segment_id }, simulacion: false })}
                                      onClick={(e) => ir(e, () => onSelectSegment(s.segment_id))}
                                      data-testid="sin-camino-ficha"
                                    >
                                      Ver el tramo
                                    </a>
                                    <a
                                      href={routePath({ selection: { type: 'tramo', id: s.segment_id }, simulacion: true })}
                                      onClick={(e) => ir(e, () => onSimulate(s.segment_id))}
                                      data-testid="sin-camino-simular"
                                    >
                                      Simular su cierre
                                    </a>
                                  </p>
                                </div>
                              )}
                            </li>
                          )
                        })}
                      </ol>
                    )}
                  </li>
                )
              })}
            </ol>
          )}
          {faltan.length > 0 && (
            <p className="suave destinos-nota" data-testid="sin-camino-faltan">
              Faltan los trenes de {listaEs(faltan)}, que no publica{faltan.length > 1 ? 'n' : ''} sus horarios en un formato abierto.
            </p>
          )}
          {datos.date && <p className="suave destinos-nota">Trenes del {formatDate(datos.date)}, un tramo cortado cada vez y sin contar las interrupciones vigentes.</p>}
          {con.length > 0 && (
            <Plegable
              rotulo={sin.length > 0 ? `${con.length === 1 ? 'El otro tramo tiene' : `Los otros ${con.length} tramos tienen`} otro camino` : `Los ${con.length} tramos y lo que añade su otro camino`}
              memoria="tramos-con-alternativa"
              testId="tramos-con-alternativa"
            >
              <p className="suave">
                Del que más trenes lleva al que menos. Lo que añade el otro camino es lo de los trenes más numerosos de cada tramo: kilómetros por cada línea y
                tiempo a la velocidad habitual, sin paradas. Oniel solo comprueba que el camino existe y cuánto mide: no mira si el tren cabe por él (ancho de
                vía, paradas, sitio en la vía).
              </p>
              <ol className="lista-destinos" data-testid="lista-con-alternativa">
                {con.map((s) => {
                  const principal = grupoPrincipal(s)
                  return (
                    <li key={s.segment_id}>
                      <span className="destino">
                        <button type="button" className="enlace" onClick={() => onSelectSegment(s.segment_id)} data-testid={`tramo-${s.segment_id}`}>
                          {nombre(s.segment_id)}
                        </button>
                        <span className="suave">{principal?.alternative ? costeCorto(principal.alternative) : ''}</span>
                      </span>
                      <span className="cuantos datos">{trenes(s.trains)}</span>
                    </li>
                  )
                })}
              </ol>
            </Plegable>
          )}
        </div>
      )}
    </section>
  )
}
