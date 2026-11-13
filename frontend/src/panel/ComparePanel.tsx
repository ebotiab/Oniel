import { useEffect, useState } from 'react'

import { fetchNodeServices, fetchSegmentServices } from '../data/api'
import type { NetworkOut, Source } from '../data/types'
import { formatDateLong, mainSourceLabel } from '../app/annotations'
import { enumerar, formatDuracion, trenesDelRecorrido, trenesDirectos, type Comparacion, type Recorrido, type TrenDirecto } from '../app/recorridos'
import { formatDayShort, formatKm, shortStop, type Comparador } from '../app/state'
import { PieFuente, Plegable } from './Plegable'
import { SearchBox } from './SearchBox'
import { Termino } from './Termino'

interface Props {
  network: NetworkOut
  comparador: Comparador
  /** Los recorridos entre las dos estaciones; nulo mientras falta alguna o si son la misma. */
  comparacion: Comparacion | null
  /** El recorrido resaltado en el mapa. */
  elegido: Recorrido | null
  sources: Source[]
  referenceDate: string | null
  onChange: (next: Comparador) => void
  onElegir: (key: string) => void
  onBack: () => void
}

/** Los trenes directos entre las dos estaciones y los tramos por los que pasa cada uno. */
interface Trenes {
  date: string
  directos: TrenDirecto[]
  pasos: Map<string, Set<string>>
}

/** La fuente de los horarios en `sources.json`. */
const FUENTE_HORARIOS = 'renfe-gtfs-av-ld-md'

function Extremo({ rotulo, nombre, network, testId, onPick, onClear }: { rotulo: string; nombre: string | null; network: NetworkOut; testId: string; onPick: (id: string) => void; onClear: () => void }) {
  return (
    <div className="extremo" data-testid={testId}>
      <span className="extremo-rotulo">{rotulo}</span>
      {nombre ? (
        <span className="extremo-elegido">
          <strong>{nombre}</strong>
          <button type="button" className="enlace" onClick={onClear} aria-label={`Cambiar la estación: ${rotulo.toLowerCase()} ${nombre}`}>
            Cambiar
          </button>
        </span>
      ) : (
        <SearchBox
          network={network}
          scope="nodos"
          label={`${rotulo}: buscar una estación`}
          placeholder="Buscar una estación"
          onPick={(target) => target.type === 'nodo' && onPick(target.id)}
          testId={`${testId}-buscador`}
        />
      )}
    </div>
  )
}

function trenesTexto(trenes: TrenDirecto[], dia: string): string {
  if (!trenes.length) return `Ningún tren directo en el horario del ${dia}.`
  const rapido = Math.min(...trenes.map((t) => t.minutes))
  const cuantos = trenes.length === 1 ? '1 tren directo' : `${trenes.length} trenes directos`
  return `${cuantos} en el horario del ${dia}; el más rápido tarda ${formatDuracion(rapido)}.`
}

/** Comparador de recorridos: dos estaciones y los caminos que las unen, del más corto al más largo. */
export function ComparePanel({ network, comparador, comparacion, elegido, sources, referenceDate, onChange, onElegir, onBack }: Props) {
  const { from, to } = comparador
  const nombre = (id: string | null) => (id ? (network.nodes.find((n) => n.id === id)?.name ?? null) : null)
  const [cargados, setCargados] = useState<{ clave: string; trenes: Trenes } | null>(null)
  const recorridos = comparacion?.recorridos ?? []
  const claves = [...new Set(recorridos.flatMap((r) => r.tramosClave))].filter((id) => network.segments.some((s) => s.id === id))
  const clavesTexto = claves.join('|')
  const consulta = `${from}>${to}@${referenceDate}:${clavesTexto}`
  // Los trenes de otra consulta no valen para esta: hasta que lleguen los suyos, no se enseña ninguno.
  const trenes = cargados?.clave === consulta ? cargados.trenes : null

  // Trenes directos: los que paran en las dos estaciones, en ese orden, y por dónde pasa cada uno.
  useEffect(() => {
    if (!from || !to || !clavesTexto) return
    let alive = true
    const dia = referenceDate ?? undefined
    const ids = clavesTexto.split('|')
    Promise.all([fetchNodeServices(from, dia), fetchNodeServices(to, dia), Promise.all(ids.map((id) => fetchSegmentServices(id, dia)))])
      .then(([origen, destino, tramos]) => {
        if (!alive) return
        const pasos = new Map(tramos.map((t, i) => [ids[i]!, new Set(t.passes.map((p) => p.service.id))]))
        setCargados({ clave: consulta, trenes: { date: origen.date, directos: trenesDirectos(origen.calls, destino.calls), pasos } })
      })
      .catch(() => {
        // Sin los horarios, el comparador sigue sirviendo: kilómetros, tiempo estimado y vía única no dependen de ellos.
      })
    return () => {
      alive = false
    }
  }, [from, to, clavesTexto, referenceDate, consulta])

  const masLargo = Math.max(1, ...recorridos.map((r) => r.route.length_km))
  const dia = trenes ? formatDayShort(trenes.date) : ''
  const lineasUsadas = new Set(recorridos.flatMap((r) => r.route.line_ids))
  const fuentes = [...new Set(network.lines.filter((l) => lineasUsadas.has(l.id)).map((l) => l.source_id))].map((id) => sources.find((s) => s.id === id))

  return (
    <section className="comparador" aria-labelledby="comparador-titulo" data-testid="comparador">
      <button type="button" className="enlace volver" onClick={onBack} data-testid="volver-red">
        ← Toda la red
      </button>
      <h2 id="comparador-titulo" className="titulo">
        Comparar recorridos
      </h2>
      <div className="extremos">
        <Extremo rotulo="Desde" nombre={nombre(from)} network={network} testId="recorridos-desde" onPick={(id) => onChange({ ...comparador, from: id })} onClear={() => onChange({ ...comparador, from: null })} />
        <Extremo rotulo="Hasta" nombre={nombre(to)} network={network} testId="recorridos-hasta" onPick={(id) => onChange({ ...comparador, to: id })} onClear={() => onChange({ ...comparador, to: null })} />
        {from && to && (
          <button type="button" className="enlace invertir" onClick={() => onChange({ ...comparador, from: to, to: from })} data-testid="recorridos-invertir">
            Invertir el sentido
          </button>
        )}
      </div>

      {(!from || !to) && (
        <p className="entrada" data-testid="recorridos-ayuda">
          Elige dos estaciones, con el buscador o tocándolas en el mapa, para ver por dónde se va de una a otra y qué diferencia hay entre un camino y otro.
        </p>
      )}
      {from && to && from === to && <p className="aviso">Elige dos estaciones distintas.</p>}
      {comparacion?.escenarioIlegible && <p className="aviso">El supuesto del enlace no encaja con la red cargada y no se ha aplicado.</p>}
      {comparacion && comparacion.escenario.length > 0 && (
        <p className="texto" data-testid="recorridos-escenario">
          Con un supuesto: {enumerar(comparacion.escenario)}.{' '}
          <button type="button" className="enlace" onClick={() => onChange({ from, to })}>
            Quitar el supuesto
          </button>
        </p>
      )}

      {comparacion && recorridos.length === 0 && <p className="aviso">No hay ningún recorrido entre estas dos estaciones con las líneas cargadas.</p>}
      {comparacion && recorridos.length > 0 && (
        <>
          <p className="texto" data-testid="recorridos-resumen">
            {recorridos.length === 1 ? 'Un solo recorrido con las líneas cargadas.' : `${recorridos.length === 2 ? 'Dos' : recorridos.length === 3 ? 'Tres' : 'Cuatro'} recorridos, del más corto al más largo.`}
            {trenes && ` ${trenes.directos.length === 0 ? 'No hay trenes directos' : trenes.directos.length === 1 ? 'Hay 1 tren directo' : `Hay ${trenes.directos.length} trenes directos`} en este sentido en el horario del ${dia}.`}
          </p>
          <ol className="recorridos">
            {recorridos.map((r) => {
              const activo = r.key === elegido?.key
              const { route } = r
              const suyos = trenes ? trenesDelRecorrido(r, trenes.directos, trenes.pasos) : null
              return (
                <li key={r.key} className={activo ? 'recorrido activo' : 'recorrido'} data-testid="recorrido">
                  <button type="button" className="recorrido-titulo" aria-pressed={activo} onClick={() => onElegir(r.key)}>
                    {r.titulo}
                  </button>
                  {(r.lineas || r.alternativa) && (
                    <p className="suave">{[r.lineas, r.alternativa ? (r.lineas ? 'el más corto que no está cortado' : 'El más corto que no está cortado') : null].filter(Boolean).join(' · ')}</p>
                  )}
                  <p className="recorrido-cifras datos">
                    {formatKm(route.length_km)} km · {route.time_min === null ? 'tiempo sin estimar' : `${formatDuracion(route.time_min)} sin paradas`} ·{' '}
                    {route.single_track_km > 0 ? `${formatKm(route.single_track_km)} km de ` : 'sin '}
                    <Termino id="via-unica">vía única</Termino>
                  </p>
                  <span className="recorrido-barra" style={{ width: `${(route.length_km / masLargo) * 100}%` }} aria-hidden="true">
                    {route.legs.map((leg, i) => (
                      <span key={i} style={{ flexGrow: Math.max(leg.length_km, 1) }} />
                    ))}
                  </span>
                  {r.cortes.map((c) => (
                    <p key={c.id} className="nota-horario" data-testid="recorrido-corte">
                      {c.interruption
                        ? `Sin circulación hoy entre ${c.from_name} y ${c.to_name}, desde el ${formatDateLong(c.interruption.start_date)} (${mainSourceLabel(c.interruption)}).`
                        : `Cerrado en este supuesto entre ${c.from_name} y ${c.to_name}.`}
                    </p>
                  ))}
                  {route.via.length > 0 && <p className="suave">Pasa por {enumerar(route.via.map(shortStop))}.</p>}
                  {r.baipases && (
                    <p className="suave" data-testid="recorrido-baipases">
                      {r.baipases}
                    </p>
                  )}
                  {suyos && (
                    <p className="suave" data-testid="recorrido-trenes">
                      {trenesTexto(suyos, dia)}
                    </p>
                  )}
                </li>
              )
            })}
          </ol>
          {comparacion.sinPaso && (
            <p className="texto" data-testid="recorridos-sin-paso">
              Hoy ninguno de estos recorridos tiene circulación de un extremo a otro, y las líneas cargadas no ofrecen otro camino.
            </p>
          )}
          <p className="nota-esquema" data-testid="recorridos-limites">
            El tiempo sirve para comparar un recorrido con otro; no es un horario, porque no cuenta paradas ni esperas. Oniel une las líneas donde comparten estación sin mirar el <Termino id="ancho-de-via">ancho de vía</Termino>: no todos los trenes pueden pasar de una a otra. El recorrido elegido se ve en azul en el mapa.
          </p>
          <Plegable>
            {recorridos.map((r) => (
              <div key={r.key} data-testid="recorrido-detalle">
                <p className="texto">
                  <strong>{r.titulo}</strong>
                </p>
                <ul className="lista-simple datos">
                  {r.route.legs.map((leg, i) => (
                    <li key={i}>
                      {leg.line_id ? leg.line_name : 'Enlace hipotético, que no se dibuja en el mapa'}, de {shortStop(leg.from_name)} a {shortStop(leg.to_name)}: {formatKm(leg.length_km)} km
                      {leg.time_min !== null ? `, ${formatDuracion(leg.time_min)}` : ''}
                      {leg.single_track_km > 0 ? `, ${formatKm(leg.single_track_km)} km de vía única` : ''}
                    </li>
                  ))}
                </ul>
              </div>
            ))}
            <p className="suave">
              Oniel une todas las líneas cargadas en una sola red y busca los caminos que no pasan dos veces por el mismo punto. Enseña los {recorridos.length > 1 ? 'más cortos' : 'que hay'}, hasta tres, y descarta los que dan un rodeo de más del doble respecto a otro más corto
              {comparacion.ocultos > 0 ? ` (aquí hay ${comparacion.ocultos === 1 ? 'uno más, más largo, que no se enseña' : `${comparacion.ocultos} más, más largos, que no se enseñan`})` : ''}. Los kilómetros se miden por cada línea.
            </p>
            <p className="suave">
              El tiempo es el de recorrer cada tramo a su velocidad habitual, sin parar, sin acelerar ni frenar y sin esperar a otro tren donde solo hay una vía. Un tren real tarda más.
            </p>
            <p className="suave">
              La alta velocidad tiene las vías más juntas (ancho estándar) que la red convencional (ancho ibérico). Solo los trenes preparados para cambiar de ancho pueden pasar de una a otra, y lo hacen en instalaciones concretas que Oniel todavía no tiene en cuenta.
            </p>
            {trenes && (
              <p className="suave">
                Un <Termino id="tren-directo">tren directo</Termino> es el que para en las dos estaciones, en este sentido, el {formatDateLong(trenes.date)}. Se asigna a un recorrido cuando pasa por el primer y el último tramo de cada una de sus líneas.
                {recorridos.some((r) => r.baipases) ? ' El recorrido se mide por los baipases, y también cuentan en él los trenes que entran en las estaciones que rodean.' : ''}
              </p>
            )}
            <PieFuente de="del trazado" sources={fuentes} />
            {trenes && <PieFuente de="de los horarios" sources={[sources.find((s) => s.id === FUENTE_HORARIOS)]} />}
          </Plegable>
        </>
      )}
    </section>
  )
}
