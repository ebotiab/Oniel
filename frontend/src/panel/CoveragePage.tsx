import type { ReactNode } from 'react'

import type { AnnotationOut, CoverageOut, NetworkOut, Source } from '../data/types'
import type { ApiStatus } from '../data/api'
import { annotationHref, bypassesOf, formatCount, formatDate, formatKm, lineLabel, lineKind, listaEs, mainLines, parentOf, routePath, todayIso } from '../app/state'
import { SITIO } from '../app/meta'
import { ANNOTATION_LAYERS } from '../app/annotationLayers'
import { formatDateLong, lugar } from '../app/annotations'
import { agruparFuentes } from '../app/fuentes'
import { abreAparte, navegar } from '../app/navegacion'
import { AnnotationNotice } from './AnnotationNotice'
import { Muestra } from './Legend'
import { Termino } from './Termino'

interface Props {
  coverage: CoverageOut
  network: NetworkOut
  onPickLine: (id: string) => void
  /** Anotaciones de red vigentes hoy; cada tipo tiene su apartado. */
  annotations: AnnotationOut[]
  status: ApiStatus
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
 * los operadores de trenes, lo que Oniel sabe de la red (interrupciones y proyectos), lo que falta y, al final, todas las fuentes con su licencia y su fecha, agrupadas por lo
 * que aportan.
 */
export function CoveragePage({ coverage, network, annotations, status, onPickLine }: Props) {
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
    { id: 'pendiente', titulo: 'Pendiente de cargar' },
    { id: 'fuentes', titulo: 'Fuentes y licencias' },
    { id: 'citar', titulo: 'Cómo citar Oniel' },
  ]
  // De quién son los horarios y con qué licencia los publica: lo dice la fuente de cada operador cargado.
  const conHorarios = operadores
    .filter((o) => o.timetable === 'cargado')
    .map((o) => ({ nombre: o.name, licencia: coverage.sources.find((f) => f.id === o.source_id)?.license ?? null }))
  // El ejemplo de cita usa la línea más larga de las cargadas.
  const lineaDeEjemplo = mainLines(coverage.lines).reduce<(typeof coverage.lines)[number] | undefined>((a, l) => (a && a.length_km >= l.length_km ? a : l), undefined)
  const cifras = [
    { cifra: formatCount(mainLines(coverage.lines).length), que: 'Líneas cargadas' },
    { cifra: formatKm(coverage.total_length_km), que: 'Kilómetros' },
    { cifra: formatCount(coverage.station_count), que: 'Estaciones' },
    { cifra: formatCount(coverage.service_count), que: 'Trenes distintos' },
  ]

  return (
    <div className="pagina" data-testid="pagina-cobertura">
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
              const lineas = mainLines(coverage.lines).filter((l) => lineKind(l) === g.kind)
              if (!lineas.length) return null
              return (
                <section key={g.kind} aria-label={g.label}>
                  <h3 className="cobertura-grupo">
                    <Muestra trazo={g.trazo} />
                    <Termino id={g.termino}>{g.label}</Termino>
                    <span className="datos">{lineas.length}</span>
                  </h3>
                  <ul className="cobertura-lineas">
                    {lineas.flatMap((l) => [l, ...bypassesOf(coverage.lines, l.id)]).map((l) => (
                      <li key={l.id} className={parentOf(l) ? 'cobertura-baipas' : undefined}>
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
          <p className="cobertura-texto" data-testid="cobertura-sin-otro-camino">
            Qué tramos de estas líneas dejarían a sus trenes sin paso si se cortaran está en{' '}
            <Enlace href={routePath({ selection: null, simulacion: false, sinOtroCamino: true })}>Tramos sin otro camino</Enlace>.
          </p>
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

        <section id="cobertura-citar" className="cobertura-apartado" aria-labelledby="cob-citar" data-testid="cobertura-citar">
          <h2 id="cob-citar">Cómo citar Oniel</h2>
          <p className="cobertura-texto">
            Oniel es un mapa de la red ferroviaria española hecho con datos públicos. No es una fuente oficial ni la web de ningún operador: ordena lo que
            publican otros y dice de dónde sale cada dato.
          </p>
          <h3>De quién son los datos</h3>
          <p className="cobertura-texto" data-testid="citar-datos">
            Los datos son de quien los publica, y al citar una cifra conviene nombrarlo.
            {conHorarios.length > 0 &&
              ` Los horarios son de ${listaEs(conHorarios.map((o) => (o.licencia ? `${o.nombre} (${o.licencia})` : o.nombre)))}.`}{' '}
            El trazado de las líneas es de los colaboradores de OpenStreetMap (ODbL 1.0). Los puntos kilométricos, las velocidades y la señalización salen de
            documentos públicos de Adif y del Boletín Oficial del Estado. Cada fuente, con su licencia, está en «Fuentes y licencias».
          </p>
          <h3>Qué fecha poner</h3>
          <p className="cobertura-texto" data-testid="citar-fecha">
            Dos: el día al que se refieren los trenes{coverage.reference_date ? `, que hoy es el ${formatDateLong(coverage.reference_date)},` : ''} y el día en
            que consultaste Oniel. Los horarios se renuevan cuando el operador publica otros, y una cifra de hoy puede no ser la del mes que viene.
          </p>
          <p className="cobertura-texto">
            Cada vista del mapa dice esas fechas al pie, junto a «Copiar enlace a esta vista», que da la dirección exacta de lo que estás viendo: una línea,
            una estación, un tramo, una comparación de recorridos o una simulación con su día y su franja.
          </p>
          {lineaDeEjemplo && (
            <>
              <h3>Un ejemplo</h3>
              <p className="cobertura-cita" data-testid="citar-ejemplo">
                Oniel, «{lineaDeEjemplo.name}»
                {conHorarios.length > 0 && `, con los horarios de ${listaEs(conHorarios.map((o) => o.nombre))}`}
                {coverage.reference_date && ` del ${formatDateLong(coverage.reference_date)}`}. {SITIO}
                {routePath({ selection: null, simulacion: false, linea: lineaDeEjemplo.id })} (consultado el {formatDateLong(todayIso())}).
              </p>
            </>
          )}
          <h3>Lo que hay que decir al citar una cifra</h3>
          <ul className="cobertura-limites" data-testid="citar-limites">
            {sinHorarios.length > 0 && (
              <li>
                Faltan los trenes de {listaEs(sinHorarios)}, que no publica{sinHorarios.length > 1 ? 'n' : ''} sus horarios en un formato abierto: donde
                opera{sinHorarios.length > 1 ? 'n' : ''}, pasan más trenes de los que Oniel cuenta.
              </li>
            )}
            <li>Tampoco están los trenes de Cercanías ni los de mercancías.</li>
            <li>Los trenes se cuentan en un día concreto y con el horario publicado: no reflejan retrasos, supresiones ni interrupciones del servicio.</li>
            <li>
              Los tiempos de «Comparar recorridos» son estimaciones sin paradas ni esperas. Sirven para comparar un camino con otro; no son el tiempo de
              ningún tren.
            </li>
            <li>Una simulación de cierre es hipotética: dice qué trenes pasarían por el tramo en esa franja, no anuncia ningún corte.</li>
            <li>«Sin otro camino» quiere decir sin otro camino entre las líneas que Oniel tiene cargadas, que no son toda la red.</li>
          </ul>
        </section>
      </main>
    </div>
  )
}
