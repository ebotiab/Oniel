import { useEffect, useState, type ReactNode } from 'react'

import type { AlternativesOut, AnnotationOut, CoverageOut, NetworkOut, SegmentAlternatives, Source } from '../data/types'
import { fetchAlternatives, type ApiStatus } from '../data/api'
import { conAlternativa, costeCorto, grupoPrincipal, sinAlternativa, trenes } from '../app/alternativas'
import { annotationHref, formatCount, formatDate, formatKm, lineLabel, lineKind, listaEs, routePath } from '../app/state'
import { ANNOTATION_LAYERS } from '../app/annotationLayers'
import { formatDateLong, lugar } from '../app/annotations'
import { agruparFuentes } from '../app/fuentes'
import { abreAparte, navegar } from '../app/navegacion'
import { AnnotationNotice } from './AnnotationNotice'
import { Muestra } from './Legend'
import { Plegable } from './Plegable'
import { Termino } from './Termino'

interface Props {
  coverage: CoverageOut
  network: NetworkOut
  /** Día de los trenes que se cuentan por tramo. */
  referenceDate: string | null
  onSelectSegment: (id: string) => void
  onPickLine: (id: string) => void
  /** Anotaciones de red vigentes hoy; cada tipo tiene su apartado. */
  annotations: AnnotationOut[]
  status: ApiStatus
  onBack: () => void
}

/** Tramos sin otro camino a la vista antes de «Ver los … restantes», como en los destinos directos de una estación. */
const A_LA_VISTA = 8

/**
 * Tramos cuyos trenes no tendrían otro camino en las líneas cargadas si el tramo se cortara, del
 * que más trenes lleva al que menos; los demás, plegados, con lo que añade su otro camino.
 */
function TramosSinAlternativa({ coverage, network, referenceDate, onSelectSegment }: Pick<Props, 'coverage' | 'network' | 'referenceDate' | 'onSelectSegment'>) {
  const [datos, setDatos] = useState<AlternativesOut | null>(null)
  const [fallo, setFallo] = useState(false)
  const [todos, setTodos] = useState(false)
  useEffect(() => {
    let vivo = true
    fetchAlternatives(referenceDate ?? undefined)
      .then((d) => vivo && setDatos(d))
      .catch(() => vivo && setFallo(true))
    return () => {
      vivo = false
    }
  }, [referenceDate])

  const fila = (s: SegmentAlternatives, derecha: string, debajo: string) => {
    const segment = network.segments.find((x) => x.id === s.segment_id)
    if (!segment) return null
    return (
      <li key={s.segment_id}>
        <span className="destino">
          <button type="button" className="enlace" onClick={() => onSelectSegment(s.segment_id)} data-testid={`tramo-${s.segment_id}`}>
            {segment.from_name} – {segment.to_name}
          </button>
          <span className="suave">{debajo}</span>
        </span>
        <span className="cuantos datos">{derecha}</span>
      </li>
    )
  }
  const linea = (s: SegmentAlternatives) => {
    const line = network.lines.find((l) => l.id === network.segments.find((x) => x.id === s.segment_id)?.line_id)
    return line ? `${lineKind(line) === 'alta velocidad' ? 'Alta velocidad' : 'Línea convencional'} ${lineLabel(line)}` : ''
  }
  const sin = datos ? sinAlternativa(datos.segments) : []
  const con = datos ? conAlternativa(datos.segments) : []
  const resto = sin.length - A_LA_VISTA
  const faltan = datos ? coverage.operators.filter((o) => datos.missing_operator_ids.includes(o.id)).map((o) => o.name) : []

  return (
    <>
      {fallo && <p className="texto suave">No se ha podido cargar este apartado.</p>}
      {!datos && !fallo && <p className="texto suave">Cargando…</p>}
      {datos && (
        <div data-testid="tramos-sin-alternativa">
          <p className="texto suave" data-testid="alternativa-alcance">
            {sin.length > 0
              ? 'Si uno de estos tramos se cortara, sus trenes no tendrían otro camino en las líneas que Oniel tiene cargadas.'
              : 'Si se cortara un tramo cualquiera, sus trenes tendrían otro camino en las líneas que Oniel tiene cargadas.'}{' '}
            No quiere decir que {sin.length > 0 ? 'no exista' : 'sea el único'} en la red real.
            {faltan.length > 0 && ` Faltan los trenes de ${listaEs(faltan)}, que no publica${faltan.length > 1 ? 'n' : ''} sus horarios en un formato abierto.`}
          </p>
          {sin.length > 0 && (
            <ol className="lista-destinos" data-testid="lista-sin-alternativa">
              {(todos ? sin : sin.slice(0, A_LA_VISTA)).map((s) =>
                fila(s, s.without_alternative === s.trains ? trenes(s.trains) : `${s.without_alternative} de ${trenes(s.trains)}`, linea(s)),
              )}
            </ol>
          )}
          {resto > 0 && (
            <p className="texto">
              <button type="button" className="enlace" onClick={() => setTodos(!todos)} aria-expanded={todos} data-testid="sin-alternativa-ver-todos">
                {todos ? 'Ver solo los que más trenes llevan' : resto === 1 ? 'Ver el tramo restante' : `Ver los ${resto} tramos restantes`}
              </button>
            </p>
          )}
          {con.length > 0 && (
            <Plegable
              rotulo={sin.length > 0 ? `${con.length === 1 ? 'El otro tramo tiene' : `Los otros ${con.length} tramos tienen`} otro camino` : `Los ${con.length} tramos y lo que añade su otro camino`}
              memoria="tramos-con-alternativa"
              testId="tramos-con-alternativa"
            >
              <p className="suave">
                Del que más trenes lleva al que menos. Lo que añade el otro camino es lo de los trenes más numerosos de cada tramo: kilómetros por cada línea y
                tiempo a la velocidad habitual, sin paradas. Oniel solo comprueba que el camino existe y cuánto mide: no mira si el tren cabe por él (ancho
                de vía, paradas, sitio en la vía).
              </p>
              <ol className="lista-destinos" data-testid="lista-con-alternativa">
                {con.map((s) => {
                  const principal = grupoPrincipal(s)
                  return fila(s, trenes(s.trains), principal?.alternative ? costeCorto(principal.alternative) : '')
                })}
              </ol>
            </Plegable>
          )}
          {datos.date && <p className="suave destinos-nota">Trenes del {formatDate(datos.date)}, un tramo cortado cada vez y sin contar las interrupciones vigentes.</p>}
        </div>
      )}
    </>
  )
}

/** Un enlace a otra vista del visor: cambia la ruta sin recargar y se puede copiar o abrir aparte. */
function Enlace({ href, onGo, children, testId }: { href: string; onGo?: () => void; children: ReactNode; testId?: string }) {
  return (
    <a
      href={href}
      data-testid={testId}
      onClick={(e) => {
        if (abreAparte(e)) return
        e.preventDefault()
        if (onGo) onGo()
        else navegar(href)
      }}
    >
      {children}
    </a>
  )
}

/** Una dirección sin el protocolo ni la barra final, para enseñarla como texto de un enlace. */
const sinProtocolo = (url: string) => url.replace(/^https?:\/\//, '').replace(/\/$/, '')

const TIPOS = [
  { kind: 'alta velocidad', label: 'Alta velocidad', trazo: 'alta-velocidad', termino: 'alta-velocidad' },
  { kind: 'convencional', label: 'Línea convencional', trazo: 'convencional', termino: 'linea-convencional' },
] as const

/** Una fuente: su nombre enlazado, quién la publica, su licencia y el día de la consulta, y qué se toma de ella. */
function Fuente({ source: s }: { source: Source }) {
  return (
    <li id={`fuente-${s.id}`} data-testid={`fuente-${s.id}`}>
      <p className="fuente-nombre">
        {s.url ? (
          <a href={s.url} target="_blank" rel="noreferrer">
            {s.name}
          </a>
        ) : (
          s.name
        )}
      </p>
      <p className="fuente-ficha">
        {s.publisher}
        {s.license && (
          <>
            {' · '}
            {s.license_url ? (
              <a href={s.license_url} target="_blank" rel="noreferrer">
                {s.license}
              </a>
            ) : (
              s.license
            )}
          </>
        )}
        {s.retrieved_on && ` · consultada el ${formatDateLong(s.retrieved_on)}`}
      </p>
      {(s.coverage || s.notes) && (
        <div className="fuente-detalle">
          {s.coverage && <p>{s.coverage}</p>}
          {s.notes && <p>{s.notes}</p>}
        </div>
      )}
      <p className="fuente-id datos">Identificador de la fuente: {s.id}</p>
    </li>
  )
}

/**
 * «Cobertura y fuentes», como página propia y sin mapa: lo que hay cargado de un vistazo, las líneas,
 * los operadores de trenes, lo que Oniel sabe de la red (interrupciones, proyectos, tramos sin otro
 * camino), lo que falta y, al final, todas las fuentes con su licencia y su fecha, agrupadas por lo
 * que aportan.
 */
export function CoveragePage({ coverage, network, referenceDate, annotations, status, onSelectSegment, onPickLine, onBack }: Props) {
  const operadores = coverage.operators
    .filter((o) => o.role === 'operador')
    // primero los que tienen horarios cargados
    .sort((a, b) => Number(a.timetable === 'no_publicado') - Number(b.timetable === 'no_publicado'))
  const sinHorarios = operadores.filter((o) => o.timetable === 'no_publicado').map((o) => o.name)
  const capas = ANNOTATION_LAYERS.map((capa) => ({ capa, vigentes: annotations.filter((a) => a.kind === capa.kind) }))
  const grupos = agruparFuentes(coverage, network.annotations)
  const apartados = [
    { id: 'lineas', titulo: 'Líneas cargadas' },
    { id: 'operadores', titulo: 'Operadores de trenes' },
    ...capas.map(({ capa }) => ({ id: capa.kind, titulo: capa.cobertura.titulo })),
    { id: 'sin-alternativa', titulo: 'Tramos sin alternativa' },
    { id: 'pendiente', titulo: 'Pendiente de cargar' },
    { id: 'fuentes', titulo: 'Fuentes y licencias' },
  ]
  const cifras = [
    { cifra: formatCount(coverage.lines.length), que: 'Líneas cargadas' },
    { cifra: formatKm(coverage.total_length_km), que: 'Kilómetros' },
    { cifra: formatCount(coverage.station_count), que: 'Estaciones' },
    { cifra: formatCount(coverage.service_count), que: 'Trenes distintos' },
  ]

  return (
    <div className="pagina" data-testid="pagina-cobertura">
      <header className="pagina-cabecera">
        <div className="marca-bloque">
          <span className="marca">Oniel</span>
          <span className="lema">Cómo está conectada la red ferroviaria</span>
        </div>
        <button type="button" className="cobertura-pill" onClick={onBack} data-testid="cobertura-volver">
          ← Volver al mapa
        </button>
      </header>
      <main className="pagina-columna cobertura" aria-labelledby="cob-titulo">
        <p className="sobre">Qué hay en esta versión</p>
        <h1 id="cob-titulo" className="pagina-titulo">
          Cobertura y fuentes
        </h1>
        <p className="pagina-entrada">Qué líneas y qué trenes tiene cargados Oniel, lo que todavía falta y de dónde sale cada dato.</p>

        <dl className="cobertura-cifras datos" data-testid="cobertura-cifras">
          {cifras.map((c) => (
            <div key={c.que}>
              <dt>{c.que}</dt>
              <dd>{c.cifra}</dd>
            </div>
          ))}
        </dl>
        <p className="cobertura-nota" data-testid="cobertura-validez">
          Horarios válidos del {coverage.feed_start ? formatDate(coverage.feed_start) : '–'} al {coverage.feed_end ? formatDate(coverage.feed_end) : '–'}.
          {status === 'ausente' ? ' Esta vista previa muestra una instantánea estática; la simulación necesita el servidor.' : ''}
          {status === 'buscando' ? ' El servidor se está despertando; hasta que responda se muestra la instantánea estática.' : ''}
        </p>

        <nav className="pagina-indice" aria-label="Índice de la página" data-testid="cobertura-indice">
          <p className="pagina-indice-rotulo">En esta página</p>
          <ul>
            {apartados.map((a) => (
              <li key={a.id}>
                <a
                  href={`#cobertura-${a.id}`}
                  onClick={(e) => {
                    e.preventDefault()
                    document.getElementById(`cobertura-${a.id}`)?.scrollIntoView({ block: 'start' })
                  }}
                >
                  {a.titulo}
                </a>
              </li>
            ))}
          </ul>
        </nav>

        <section id="cobertura-lineas" className="cobertura-apartado" aria-labelledby="cob-lineas">
          <h2 id="cob-lineas">Líneas cargadas</h2>
          <p className="cobertura-texto">Cada una lleva a su recorrido en el mapa, estación a estación.</p>
          <div data-testid="cobertura-lineas">
            {TIPOS.map((g) => {
              const lineas = coverage.lines.filter((l) => lineKind(l) === g.kind)
              if (!lineas.length) return null
              return (
                <section key={g.kind} aria-label={g.label}>
                  <h3 className="cobertura-grupo">
                    <Muestra trazo={g.trazo} />
                    <Termino id={g.termino}>{g.label}</Termino>
                    <span className="datos">{lineas.length}</span>
                  </h3>
                  <ul className="cobertura-lineas">
                    {lineas.map((l) => (
                      <li key={l.id}>
                        <Enlace href={routePath({ selection: null, simulacion: false, linea: l.id })} onGo={() => onPickLine(l.id)} testId={`cobertura-linea-${l.id}`}>
                          {lineLabel(l)}
                        </Enlace>
                        <span className="datos">{formatKm(l.length_km)} km</span>
                      </li>
                    ))}
                  </ul>
                </section>
              )
            })}
          </div>
        </section>

        <section id="cobertura-operadores" className="cobertura-apartado" aria-labelledby="cob-operadores">
          <h2 id="cob-operadores">
            <Termino id="operador">Operadores</Termino> de trenes
          </h2>
          <p className="cobertura-texto">
            Los horarios son los que publica cada operador. No reflejan interrupciones ni alteraciones del servicio: las que Oniel conoce se señalan aparte, con
            su fuente y la fecha en que se comprobaron.
          </p>
          <dl className="cobertura-operadores" data-testid="cobertura-operadores">
            {operadores.map((o) => {
              const source = coverage.sources.find((s) => s.id === o.source_id)
              const dataset = coverage.datasets?.find((d) => d.operator_id === o.id)
              const cargado = o.timetable !== 'no_publicado'
              return (
                <div key={o.id} data-testid={`operador-${o.id}`}>
                  <dt>{o.name}</dt>
                  <dd>
                    <p className="operador-estado">
                      {cargado
                        ? `Horarios cargados${dataset ? `, válidos del ${formatDateLong(dataset.valid_from)} al ${formatDateLong(dataset.valid_to)}` : ''}.`
                        : 'No publica sus horarios en un formato abierto: sus trenes no están cargados ni contados.'}
                    </p>
                    {source ? (
                      <dl className="operador-ficha">
                        <div>
                          <dt>{cargado ? 'Fuente' : 'Consultado en'}</dt>
                          <dd>
                            {source.url ? (
                              <a href={source.url} target="_blank" rel="noreferrer">
                                {cargado ? source.name : sinProtocolo(source.url)}
                              </a>
                            ) : (
                              source.name
                            )}
                          </dd>
                        </div>
                        {cargado && (
                          <div>
                            <dt>Publica</dt>
                            <dd>{source.publisher}</dd>
                          </div>
                        )}
                        {cargado && source.license && (
                          <div>
                            <dt>Licencia</dt>
                            <dd>
                              {source.license_url ? (
                                <a href={source.license_url} target="_blank" rel="noreferrer">
                                  {source.license}
                                </a>
                              ) : (
                                source.license
                              )}
                            </dd>
                          </div>
                        )}
                        {(dataset?.retrieved_on ?? source.retrieved_on) && (
                          <div>
                            <dt>{cargado ? 'Descargado' : 'Comprobado'}</dt>
                            <dd>el {formatDateLong(dataset?.retrieved_on ?? source.retrieved_on!)}</dd>
                          </div>
                        )}
                      </dl>
                    ) : (
                      <p className="operador-estado">Sin fuente registrada.</p>
                    )}
                  </dd>
                </div>
              )
            })}
          </dl>
        </section>

        {capas.map(({ capa, vigentes }) => (
          <section key={capa.kind} id={`cobertura-${capa.kind}`} className="cobertura-apartado" aria-labelledby={`cob-${capa.kind}`}>
            <h2 id={`cob-${capa.kind}`}>{capa.cobertura.titulo}</h2>
            {vigentes.length === 0 ? (
              <p className="cobertura-texto">{capa.cobertura.vacio}</p>
            ) : (
              <div data-testid={capa.cobertura.testId}>
                <p className="cobertura-texto">{capa.cobertura.entrada}</p>
                {capa.ruta ? (
                  // Un tipo con ficha propia se enumera: cada uno, con su estado, lleva a su ficha.
                  <ul className="cobertura-anotaciones">
                    {vigentes.map((a) => {
                      const senal = capa.ficha.senal(a)
                      return (
                        <li key={a.id}>
                          <Enlace href={annotationHref(a) ?? '/'} testId={`${capa.ficha.testId}-enlace`}>
                            {a.title ?? lugar(a)}
                          </Enlace>
                          <span className={`senal ${senal.clase}`}>{senal.texto}</span>
                        </li>
                      )
                    })}
                  </ul>
                ) : (
                  <div className="cobertura-avisos">
                    {vigentes.map((a) => (
                      <AnnotationNotice key={a.id} annotation={a} />
                    ))}
                  </div>
                )}
              </div>
            )}
          </section>
        ))}

        <section id="cobertura-sin-alternativa" className="cobertura-apartado" aria-labelledby="cob-sin-alternativa">
          <h2 id="cob-sin-alternativa">Tramos con más trenes y sin alternativa</h2>
          <TramosSinAlternativa coverage={coverage} network={network} referenceDate={referenceDate} onSelectSegment={onSelectSegment} />
        </section>

        <section id="cobertura-pendiente" className="cobertura-apartado" aria-labelledby="cob-pendiente">
          <h2 id="cob-pendiente">Pendiente de cargar</h2>
          <p className="cobertura-texto">
            El resto de la red ferroviaria española, los trenes de Cercanías y de mercancías y otros medios de transporte.
            {sinHorarios.length > 0 && ` Tampoco están los trenes de ${listaEs(sinHorarios)}, que no publica${sinHorarios.length > 1 ? 'n' : ''} sus horarios en un formato abierto.`}
          </p>
          <p className="cobertura-texto">El modelo de datos ya los contempla: cada línea, nodo y servicio lleva su fuente, su licencia y su fecha.</p>
        </section>

        <section id="cobertura-fuentes" className="cobertura-apartado" aria-labelledby="cob-fuentes">
          <h2 id="cob-fuentes">Fuentes y licencias</h2>
          <p className="cobertura-texto">
            Todo lo que enseña Oniel sale de una de estas {coverage.sources.length} fuentes. Van agrupadas por lo que aportan; al abrir un grupo, cada una dice
            quién la publica, con qué licencia y el día en que se consultó.
          </p>
          <div className="cobertura-fuentes" data-testid="cobertura-fuentes">
            {grupos.map((g) => (
              <details key={g.id} className="fuentes-grupo" data-testid={`fuentes-${g.id}`}>
                <summary>
                  <span className="fuentes-titulo">
                    {g.titulo} <span className="datos">{g.fuentes.length}</span>
                  </span>
                  <span className="fuentes-entrada">{g.entrada}</span>
                </summary>
                <ul>
                  {g.fuentes.map((s) => (
                    <Fuente key={s.id} source={s} />
                  ))}
                </ul>
              </details>
            ))}
          </div>
        </section>
      </main>
    </div>
  )
}
