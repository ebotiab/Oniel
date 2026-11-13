import { useEffect, useRef, useState } from 'react'

import { normalize } from '../app/search'
import type { Source } from '../data/types'
import { conceptos, terminos, tituloDe } from './glosario'
import { Marca } from '../app/Marca'
import { abreAparte } from '../app/navegacion'
import { rutaGlosario, useAbrirGlosario } from './glosarioContexto'
import { Dibujo } from './glosarioDibujos'
import { PieFuente, Plegable } from './Plegable'

interface Props {
  /** La entrada que pide la URL (`/glosario/<id>`): se lleva a la vista y se señala. */
  entrada: string | null
  /** Fuentes registradas, para citar las referencias de los conceptos. */
  sources: Source[]
  onBack: () => void
}

/** Enlace a otra entrada del glosario: cambia la ruta sin recargar y se puede copiar como cualquier enlace. */
function EnlaceEntrada({ id, children }: { id: string; children: React.ReactNode }) {
  const abrir = useAbrirGlosario()
  return (
    <a
      href={rutaGlosario(id)}
      onClick={(e) => {
        if (abreAparte(e)) return
        e.preventDefault()
        abrir(id)
      }}
    >
      {children}
    </a>
  )
}

function VerTambien({ ids }: { ids?: readonly string[] }) {
  const entradas = (ids ?? []).map((id) => ({ id, titulo: tituloDe(id) })).filter((e): e is { id: string; titulo: string } => Boolean(e.titulo))
  if (!entradas.length) return null
  return (
    <p className="glosario-ver">
      Ver también:{' '}
      {entradas.map((e, i) => (
        <span key={e.id}>
          {i > 0 && ' · '}
          <EnlaceEntrada id={e.id}>{e.titulo}</EnlaceEntrada>
        </span>
      ))}
    </p>
  )
}

/** «Cómo se separan los trenes: bloqueo y cantón» → el título y, en un renglón propio, «Bloqueo y cantón». */
function partes(titulo: string): [string, string | null] {
  const [principal, resto] = titulo.split(': ')
  return [principal!, resto ? resto[0]!.toUpperCase() + resto.slice(1) : null]
}

/** Los artículos de una cita, sin lo que define cada uno: «art. 1.1.1.3 y 1.1.1.4». */
function articulos(cita: string): string {
  return `art. ${new Intl.ListFormat('es', { type: 'conjunction' }).format(cita.match(/\d+(\.\d+)+/g) ?? [])}`
}

/**
 * El glosario, como página propia y sin mapa: un índice, los conceptos que hacen falta para entender la
 * red (cada uno con su dibujo por pasos, un texto corto y su referencia) y, aparte, las palabras de las
 * fichas por orden alfabético, con un campo para filtrarlas. Cada entrada tiene su ruta.
 */
export function GlossaryPage({ entrada, sources, onBack }: Props) {
  const pagina = useRef<HTMLDivElement>(null)
  const [filtro, setFiltro] = useState('')
  const existe = entrada !== null && tituloDe(entrada) !== null
  // La entrada de la URL queda arriba de la página; sin entrada, el glosario empieza por el principio.
  useEffect(() => {
    if (existe) document.getElementById(`glosario-${entrada}`)?.scrollIntoView({ block: 'start' })
    else pagina.current?.scrollTo({ top: 0 })
  }, [entrada, existe])
  const fuente = (id: string) => sources.find((s) => s.id === id)
  const referencias = [...new Set(conceptos.map((c) => c.referencia.sourceId))].map(fuente)
  // Se filtra por el nombre y por la definición, sin acentos ni mayúsculas; la palabra que pide la URL no se oculta.
  const consulta = normalize(filtro)
  const visibles = consulta ? terminos.filter((t) => t.id === entrada || normalize(`${t.nombre} ${t.breve}`).includes(consulta)) : terminos

  return (
    <div ref={pagina} className="pagina" data-testid="pagina-glosario">
      <header className="pagina-cabecera">
        <Marca />
        <button type="button" className="cobertura-pill" onClick={onBack} data-testid="glosario-volver">
          ← Volver al mapa
        </button>
      </header>
      <main className="pagina-columna glosario" aria-labelledby="glosario-titulo">
        <p className="sobre">Para entender la red</p>
        <h1 id="glosario-titulo" className="pagina-titulo">
          Glosario
        </h1>
        <p className="pagina-entrada">
          Unas ideas sobre cómo circulan los trenes, cada una con su dibujo, y las palabras que aparecen en las fichas.
        </p>

        <nav className="pagina-indice" aria-label="Índice del glosario" data-testid="glosario-indice">
          <p className="pagina-indice-rotulo">Cómo funciona</p>
          <ul>
            {conceptos.map((c) => (
              <li key={c.id}>
                <EnlaceEntrada id={c.id}>{partes(c.titulo)[0]}</EnlaceEntrada>
              </li>
            ))}
            <li className="aparte">
              <a
                href={rutaGlosario(null)}
                onClick={(e) => {
                  e.preventDefault()
                  document.getElementById('glosario-palabras')?.scrollIntoView({ block: 'start' })
                }}
              >
                Palabras, de la A a la Z
              </a>
            </li>
          </ul>
        </nav>

        {conceptos.map((c) => {
          const [titulo, subtitulo] = partes(c.titulo)
          const url = fuente(c.referencia.sourceId)?.url
          return (
            <article key={c.id} id={`glosario-${c.id}`} className="glosario-concepto" data-testid={`glosario-${c.id}`} aria-current={c.id === entrada ? 'true' : undefined}>
              <h2>
                {titulo}
                {subtitulo && <span className="glosario-subtitulo">{subtitulo}</span>}
              </h2>
              <ol className="glosario-pasos">
                {c.pasos.map((paso, i) => (
                  <li key={paso}>
                    <div className="glosario-lamina"><Dibujo concepto={c.id} paso={i} /></div>
                    <p>{paso}</p>
                  </li>
                ))}
              </ol>
              {c.parrafos.map((p) => (
                <p key={p} className="glosario-texto">
                  {p}
                </p>
              ))}
              <p className="glosario-referencia">
                Referencia: {url ? <a href={url} target="_blank" rel="noreferrer">{c.referencia.titulo}</a> : c.referencia.titulo}, {articulos(c.referencia.cita)}.
              </p>
              <VerTambien ids={c.ver} />
            </article>
          )
        })}

        <section id="glosario-palabras" className="glosario-palabras" aria-labelledby="glosario-palabras-titulo">
          <h2 id="glosario-palabras-titulo">Palabras</h2>
          <p className="glosario-nota">Las que aparecen en las fichas. Allí llevan un subrayado de puntos y se explican al tocarlas.</p>
          <input
            type="search"
            className="glosario-filtro"
            placeholder="Filtrar palabras"
            aria-label="Filtrar palabras"
            value={filtro}
            onChange={(e) => setFiltro(e.target.value)}
            data-testid="glosario-filtro"
          />
          <p className="visually-hidden" role="status">
            {consulta ? `${visibles.length} de ${terminos.length} palabras` : ''}
          </p>
          {visibles.length ? (
            <dl>
              {visibles.map((t) => (
                <div key={t.id} id={`glosario-${t.id}`} className="glosario-palabra" data-testid={`glosario-${t.id}`} aria-current={t.id === entrada ? 'true' : undefined}>
                  <dt>{t.nombre}</dt>
                  <dd>
                    {t.breve}
                    <VerTambien ids={t.ver} />
                  </dd>
                </div>
              ))}
            </dl>
          ) : (
            <p className="glosario-nota" data-testid="glosario-sin-palabras">
              Ninguna palabra coincide con «{filtro.trim()}».
            </p>
          )}
        </section>

        <Plegable>
          <p className="suave">
            Las definiciones y los dibujos son de Oniel, hechos para quien no conoce el ferrocarril: resumen lo esencial y dejan fuera los casos
            particulares. Los conceptos de circulación siguen el reglamento que se cita en cada uno, que es el texto que vale.
          </p>
          <PieFuente de="de los conceptos" sources={referencias} />
        </Plegable>
      </main>
    </div>
  )
}
