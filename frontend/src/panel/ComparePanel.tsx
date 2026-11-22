import { useEffect, useMemo, useRef, useState, type ReactNode } from 'react'

import { fetchNodeServices, fetchSegmentServices } from '../data/api'
import type { NetworkOut, Source } from '../data/types'
import { formatDateLong, mainSourceLabel } from '../app/annotations'
import { diferenciaConSupuesto, enumerar, formatDuracion, fraseTrenesFuera, lineaRecta, trenesDelRecorrido, trenesDirectos, trenesFueraDeLosRecorridos, velocidadesHabituales, type Comparacion, type Recorrido, type TrenDirecto } from '../app/recorridos'
import { emptyScenario, scenarioFromCode, scenarioToCode, type Scenario, type SketchLink } from '../routing/scenario'
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

/** Una estación por elegir. `etiqueta` la nombra para los lectores de pantalla cuando el rótulo a la vista no basta («y»). */
function Extremo({ rotulo, etiqueta = rotulo, nombre, network, testId, onPick, onClear }: { rotulo: string; etiqueta?: string; nombre: string | null; network: NetworkOut; testId: string; onPick: (id: string) => void; onClear: () => void }) {
  return (
    <div className="extremo" data-testid={testId}>
      <span className="extremo-rotulo">{rotulo}</span>
      {nombre ? (
        <span className="extremo-elegido">
          <strong>{nombre}</strong>
          <button type="button" className="enlace" onClick={onClear} aria-label={`Cambiar la estación: ${etiqueta.toLowerCase()} ${nombre}`}>
            Cambiar
          </button>
        </span>
      ) : (
        <SearchBox
          network={network}
          scope="nodos"
          label={`${etiqueta}: buscar una estación`}
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

function leer(code: string | undefined): Scenario {
  try {
    return scenarioFromCode(code ?? '')
  } catch {
    return emptyScenario()
  }
}

/** Topes de lo que se puede escribir: bastan para cualquier vía de la península y evitan cifras absurdas. */
const KM_MAXIMOS = 2000
const KMH_MAXIMOS = 500

/**
 * Una cifra que escribe el visitante. Mientras se escribe puede estar vacía o a medias; solo pasa a la
 * URL cuando es un número válido, y al salir del campo vuelve a enseñar el valor en vigor.
 */
function Cifra({ rotulo, valor, unidad, maximo, testId, onCambio }: { rotulo: string; valor: number; unidad: string; maximo: number; testId: string; onCambio: (n: number) => void }) {
  const [escrito, setEscrito] = useState<string | null>(null)
  return (
    <label className="via-cifra">
      <span className="extremo-rotulo">{rotulo}</span>
      <input
        type="number"
        inputMode="decimal"
        min={1}
        max={maximo}
        step="any"
        value={escrito ?? String(valor)}
        data-testid={testId}
        onChange={(e) => {
          setEscrito(e.target.value)
          const n = Number(e.target.value)
          if (e.target.value.trim() && Number.isFinite(n) && n >= 1 && n <= maximo) onCambio(Math.round(n * 10) / 10)
        }}
        onBlur={() => setEscrito(null)}
      />
      <span className="datos">{unidad}</span>
    </label>
  )
}

/**
 * La vía supuesta: dos estaciones, cuánto mide y a qué velocidad se recorre. Todo vive en el escenario
 * de la URL; aquí solo se guardan las estaciones mientras falta una de las dos.
 */
function ViaSupuesta({ network, comparador, onChange }: { network: NetworkOut; comparador: Comparador; onChange: (next: Comparador) => void }) {
  const escenario = leer(comparador.escenario)
  const via = escenario.links[0] ?? null
  const [a, setA] = useState<string | null>(null)
  const [b, setB] = useState<string | null>(null)
  const habituales = useMemo(() => velocidadesHabituales(network), [network])
  const nodo = (id: string | null) => (id ? (network.nodes.find((n) => n.id === id) ?? null) : null)
  const recta = (x: string, y: string) => {
    const [p, q] = [nodo(x), nodo(y)]
    return p && q ? Math.max(1, Math.round(lineaRecta(p, q))) : 1
  }
  const poner = (link: SketchLink | null) => {
    const code = scenarioToCode({ ...escenario, links: link ? [link, ...escenario.links.slice(1)] : escenario.links.slice(1) })
    onChange({ from: comparador.from, to: comparador.to, ...(code ? { escenario: code } : {}) })
  }
  const desde = via?.from_node_id ?? a
  const hasta = via?.to_node_id ?? b
  const elegir = (lado: 'desde' | 'hasta', id: string | null) => {
    const na = lado === 'desde' ? id : desde
    const nb = lado === 'hasta' ? id : hasta
    setA(na)
    setB(nb)
    // Al cambiar una estación la longitud vuelve a ser la línea recta entre las dos; la velocidad se conserva.
    if (na && nb && na !== nb) poner({ from_node_id: na, to_node_id: nb, length_km: recta(na, nb), speed_kmh: via?.speed_kmh ?? habituales.convencional })
    else if (via) poner(null)
  }
  return (
    <div className="via-campos" data-testid="via-supuesta">
      <Extremo rotulo="Entre" etiqueta="Vía supuesta, primera estación" nombre={nodo(desde)?.name ?? null} network={network} testId="via-desde" onPick={(id) => elegir('desde', id)} onClear={() => elegir('desde', null)} />
      <Extremo rotulo="y" etiqueta="Vía supuesta, segunda estación" nombre={nodo(hasta)?.name ?? null} network={network} testId="via-hasta" onPick={(id) => elegir('hasta', id)} onClear={() => elegir('hasta', null)} />
      {desde && hasta && desde === hasta && <p className="aviso">Elige dos estaciones distintas.</p>}
      {via && (
        <>
          <div className="via-cifras">
            <Cifra rotulo="Mide" valor={via.length_km} unidad="km" maximo={KM_MAXIMOS} testId="via-km" onCambio={(n) => poner({ ...via, length_km: n })} />
            <Cifra rotulo="Se recorre a" valor={via.speed_kmh} unidad="km/h" maximo={KMH_MAXIMOS} testId="via-kmh" onCambio={(n) => poner({ ...via, speed_kmh: n })} />
          </div>
          <p className="suave">
            <button type="button" className="enlace" onClick={() => poner({ ...via, speed_kmh: habituales.convencional })} data-testid="via-kmh-convencional">
              {habituales.convencional} km/h, como una línea convencional
            </button>
            {' · '}
            <button type="button" className="enlace" onClick={() => poner({ ...via, speed_kmh: habituales.altaVelocidad })} data-testid="via-kmh-alta-velocidad">
              {habituales.altaVelocidad} km/h, como la alta velocidad
            </button>
          </p>
          <p className="suave" data-testid="via-cifras-origen">
            Las dos cifras las pones tú. Oniel propone de entrada {recta(via.from_node_id, via.to_node_id)} km, la distancia en línea recta entre las dos estaciones (una vía real mide más, porque rodea el relieve), y {habituales.convencional} km/h, la velocidad habitual de las líneas convencionales cargadas.
          </p>
        </>
      )}
    </div>
  )
}

/** Un recorrido de la lista. `supuesto` marca el que usaría la vía que no existe. */
function Tarjeta({ r, activo, masLargo, onElegir, supuesto, children }: { r: Recorrido; activo: boolean; masLargo: number; onElegir: (key: string) => void; supuesto: boolean; children?: ReactNode }) {
  const { route } = r
  const vias = route.legs.filter((leg) => !leg.line_id)
  return (
    <li className={`recorrido${activo ? ' activo' : ''}${supuesto ? ' supuesto' : ''}`} data-testid={supuesto ? 'recorrido-supuesto' : 'recorrido'}>
      {supuesto && <span className="etiqueta-supuesto">Supuesto: esta vía no existe</span>}
      <button type="button" className="recorrido-titulo" aria-pressed={activo} onClick={() => onElegir(r.key)}>
        {r.titulo}
      </button>
      {(r.lineas || r.alternativa) && <p className="suave">{[r.lineas, r.alternativa ? (r.lineas ? 'el más corto que no está cortado' : 'El más corto que no está cortado') : null].filter(Boolean).join(' · ')}</p>}
      <p className="recorrido-cifras datos">
        {formatKm(route.length_km)} km · {route.time_min === null ? 'tiempo sin estimar' : `${formatDuracion(route.time_min)} sin paradas`} · {route.single_track_km > 0 ? `${formatKm(route.single_track_km)} km de ` : 'sin '}
        <Termino id="via-unica">vía única</Termino>
      </p>
      <span className="recorrido-barra" style={{ width: `${(route.length_km / masLargo) * 100}%` }} aria-hidden="true">
        {route.legs.map((leg, i) => (
          <span key={i} className={leg.line_id ? undefined : 'trecho-supuesto'} style={{ flexGrow: Math.max(leg.length_km, 1) }} />
        ))}
      </span>
      {vias.map((via, i) => (
        <p key={i} className="suave" data-testid="recorrido-via">
          De ellos, {formatKm(via.length_km)} km por la vía supuesta entre {shortStop(via.from_name)} y {shortStop(via.to_name)}
          {via.time_min !== null ? `, ${formatDuracion(via.time_min)}` : ''}.
        </p>
      ))}
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
      {children}
    </li>
  )
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

  const dia = trenes ? formatDayShort(trenes.date) : ''
  const supuestos = comparacion?.supuestos ?? []
  const escenario = leer(comparador.escenario)
  const via = escenario.links[0] ?? null
  // El formulario de la vía supuesta se abre a petición; con una vía en la URL está siempre abierto.
  const [abierta, setAbierta] = useState(false)
  const cajaRef = useRef<HTMLDivElement>(null)
  const [irAlSupuesto, setIrAlSupuesto] = useState(0)
  useEffect(() => {
    if (irAlSupuesto) cajaRef.current?.scrollIntoView({ block: 'start' })
  }, [irAlSupuesto])
  const conEscenario = (next: Scenario): Comparador => {
    const code = scenarioToCode(next)
    return { from, to, ...(code ? { escenario: code } : {}) }
  }
  const masLargo = Math.max(1, ...[...recorridos, ...supuestos].map((r) => r.route.length_km))
  const diferencia = supuestos.length > 0 ? diferenciaConSupuesto(recorridos, supuestos) : null
  const tarjeta = (r: Recorrido, supuesto: boolean) => {
    // Por una vía que no existe no pasa ningún tren: de los supuestos no se cuentan.
    const suyos = trenes && !supuesto ? trenesDelRecorrido(r, trenes.directos, trenes.pasos) : null
    return (
      <Tarjeta key={r.key} r={r} activo={r.key === elegido?.key} masLargo={masLargo} onElegir={onElegir} supuesto={supuesto}>
        {suyos && (
          <p className="suave" data-testid="recorrido-trenes">
            {trenesTexto(suyos, dia)}
          </p>
        )}
      </Tarjeta>
    )
  }
  // Los trenes directos que no siguen ninguno de los recorridos van por una vía que no está cargada.
  const fuera = trenes ? fraseTrenesFuera(trenesFueraDeLosRecorridos(recorridos, trenes.directos, trenes.pasos), trenes.directos.length, recorridos.length) : null
  const todos = [...recorridos, ...supuestos]
  const lineasUsadas = new Set(todos.flatMap((r) => r.route.line_ids))
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
      {comparacion?.escenarioIlegible && <p className="aviso">El supuesto de la dirección no encaja con la red cargada y no se ha aplicado.</p>}
      {comparacion && comparacion.escenario.length > 0 && (
        <p className="texto" data-testid="recorridos-escenario">
          Con un supuesto: {enumerar(comparacion.escenario)}.{' '}
          <button type="button" className="enlace" onClick={() => onChange(conEscenario({ ...emptyScenario(), links: escenario.links }))}>
            Quitar el supuesto
          </button>
        </p>
      )}
      {comparacion && (
        <p className="texto" data-testid="via-entrada">
          {via && !comparacion.escenarioIlegible ? `Se compara además con una vía supuesta entre ${nombre(via.from_node_id)} y ${nombre(via.to_node_id)}, que no existe. ` : ''}
          <button
            type="button"
            className="enlace"
            onClick={() => {
              setAbierta(true)
              setIrAlSupuesto((n) => n + 1)
            }}
            data-testid="via-ir"
          >
            {via ? 'Ver el supuesto' : 'Probar con una vía que no existe'}
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
          {fuera && (
            <p className="suave" data-testid="recorridos-trenes-fuera">
              {fuera}
            </p>
          )}
          {via && (
            <h3 className="via-titulo hoy" data-testid="recorridos-hoy">
              Hoy
            </h3>
          )}
          <ol className="recorridos">{recorridos.map((r) => tarjeta(r, false))}</ol>
          {comparacion.sinPaso && (
            <p className="texto" data-testid="recorridos-sin-paso">
              Hoy ninguno de estos recorridos tiene circulación de un extremo a otro, y las líneas cargadas no ofrecen otro camino.
            </p>
          )}
        </>
      )}

      {comparacion && (
        <div className="via-supuesta" ref={cajaRef} data-testid="via-caja">
          <h3 className="via-titulo">¿Y si hubiera una vía que hoy no existe?</h3>
          {!via && !abierta ? (
            <p className="texto">
              Une dos estaciones con una vía supuesta y compara lo que se tardaría con los recorridos de hoy.{' '}
              <button type="button" className="enlace" onClick={() => setAbierta(true)} data-testid="via-abrir">
                Elegir las dos estaciones
              </button>
            </p>
          ) : (
            <>
              <ViaSupuesta network={network} comparador={comparador} onChange={onChange} />
              {diferencia && (
                <p className="texto via-diferencia" data-testid="via-diferencia">
                  {diferencia}
                </p>
              )}
              {via && !comparacion.escenarioIlegible && supuestos.length === 0 && (
                <p className="texto" data-testid="via-sin-uso">
                  Ningún recorrido entre {nombre(from)} y {nombre(to)} usaría esa vía: los que pasan por ella dan un rodeo de más del doble respecto a otro más corto.
                </p>
              )}
              {supuestos.length > 0 && <ol className="recorridos">{supuestos.map((r) => tarjeta(r, true))}</ol>}
              <p className="suave" data-testid="via-aviso">
                Esta vía no existe y Oniel no la toma de ningún proyecto: es un supuesto de quien consulta, para comparar. El resultado es una estimación sin paradas, no un horario. La dirección de esta página guarda el supuesto: sirve para enlazarlo.
              </p>
              <button
                type="button"
                className="enlace"
                onClick={() => {
                  setAbierta(false)
                  onChange(conEscenario({ ...escenario, links: [] }))
                }}
                data-testid="via-quitar"
              >
                Quitar la vía supuesta
              </button>
            </>
          )}
        </div>
      )}

      {comparacion && todos.length > 0 && (
        <>
          <p className="nota-esquema" data-testid="recorridos-limites">
            El tiempo sirve para comparar un recorrido con otro; no es un horario, porque no cuenta paradas ni esperas. Oniel une las líneas donde comparten estación sin mirar el <Termino id="ancho-de-via">ancho de vía</Termino>: no todos los trenes pueden pasar de una a otra. El recorrido elegido se ve en azul en el mapa.
          </p>
          <Plegable>
            {todos.map((r) => (
              <div key={r.key} data-testid="recorrido-detalle">
                <p className="texto">
                  <strong>{r.titulo}</strong>
                </p>
                <ul className="lista-simple datos">
                  {r.route.legs.map((leg, i) => (
                    <li key={i}>
                      {leg.line_id ? leg.line_name : 'Vía supuesta, que no existe'}, de {shortStop(leg.from_name)} a {shortStop(leg.to_name)}: {formatKm(leg.length_km)} km
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
            {via && (
              <p className="suave" data-testid="via-metodo">
                La vía supuesta cuenta como un tramo más, con los kilómetros y la velocidad escritos en el supuesto: su tiempo es su longitud entre su velocidad. No se le suponen paradas, vía única ni trenes. Los recorridos que la usarían, hasta dos, se buscan igual que los demás. La recta de trazos del mapa solo une las dos estaciones: no es un trazado.
              </p>
            )}
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
