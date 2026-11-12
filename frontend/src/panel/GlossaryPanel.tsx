import { useEffect } from 'react'

import type { Source } from '../data/types'
import { conceptos, terminos, tituloDe } from './glosario'
import { hashGlosario, useAbrirGlosario } from './glosarioContexto'
import { PieFuente, Plegable } from './Plegable'

interface Props {
  /** La entrada que pide la URL (`#/glosario/<id>`): se lleva a la vista y se resalta. */
  entrada: string | null
  /** Fuentes registradas, para citar al pie del detalle las referencias de los conceptos. */
  sources: Source[]
  onBack: () => void
}

/** Enlace a otra entrada del glosario: cambia la ruta sin recargar y se puede copiar como cualquier enlace. */
function EnlaceEntrada({ id, className, children }: { id: string; className?: string; children: React.ReactNode }) {
  const abrir = useAbrirGlosario()
  return (
    <a
      className={className}
      href={hashGlosario(id)}
      onClick={(e) => {
        if (e.metaKey || e.ctrlKey || e.shiftKey || e.button !== 0) return
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
    <p className="suave glosario-ver">
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

/**
 * El glosario completo: primero los conceptos que hacen falta para entender la red, en unos párrafos y con su
 * referencia, y después los términos de las fichas por orden alfabético. Cada entrada tiene su ruta.
 */
export function GlossaryPanel({ entrada, sources, onBack }: Props) {
  const existe = entrada !== null && tituloDe(entrada) !== null
  // La entrada de la URL queda arriba del panel; sin entrada, el glosario empieza por el principio.
  useEffect(() => {
    if (existe) document.getElementById(`glosario-${entrada}`)?.scrollIntoView({ block: 'start' })
    else document.getElementById('glosario-titulo')?.scrollIntoView({ block: 'end' })
  }, [entrada, existe])
  const clase = (id: string) => (id === entrada ? 'glosario-entrada activa' : 'glosario-entrada')
  const fuente = (id: string) => sources.find((s) => s.id === id)
  const referencias = [...new Set(conceptos.map((c) => c.referencia.sourceId))].map(fuente)

  return (
    <section className="detalle glosario" aria-labelledby="glosario-titulo" data-testid="panel-glosario">
      <button type="button" className="enlace volver" onClick={onBack} data-testid="glosario-volver">
        ← Volver
      </button>
      <p className="sobre">Para entender la red</p>
      <h2 id="glosario-titulo" className="titulo">
        Glosario
      </h2>
      <p className="entrada">
        Primero, unas ideas sobre cómo circulan los trenes. Después, las palabras que aparecen en las fichas, por orden alfabético: en cualquier ficha, las
        que llevan un subrayado de puntos se explican al tocarlas.
      </p>

      <h3 className="subtitulo">Cómo funciona</h3>
      {conceptos.map((c) => (
        <article key={c.id} id={`glosario-${c.id}`} className={clase(c.id)} data-testid={`glosario-${c.id}`} aria-current={c.id === entrada ? 'true' : undefined}>
          <h4 className="glosario-nombre">
            <EnlaceEntrada id={c.id} className="enlace-nodo">
              {c.titulo}
            </EnlaceEntrada>
          </h4>
          {c.parrafos.map((p) => (
            <p key={p} className="texto">
              {p}
            </p>
          ))}
          <p className="suave glosario-referencia">
            Referencia: {fuente(c.referencia.sourceId)?.url ? <a href={fuente(c.referencia.sourceId)!.url!} target="_blank" rel="noreferrer">{c.referencia.titulo}</a> : c.referencia.titulo}
            , {c.referencia.cita}.
          </p>
          <VerTambien ids={c.ver} />
        </article>
      ))}

      <h3 className="subtitulo">Términos</h3>
      {terminos.map((t) => (
        <article key={t.id} id={`glosario-${t.id}`} className={clase(t.id)} data-testid={`glosario-${t.id}`} aria-current={t.id === entrada ? 'true' : undefined}>
          <h4 className="glosario-nombre">
            <EnlaceEntrada id={t.id} className="enlace-nodo">
              {t.nombre}
            </EnlaceEntrada>
          </h4>
          <p className="texto">{t.breve}</p>
          <VerTambien ids={t.ver} />
        </article>
      ))}

      <Plegable>
        <p className="suave">
          Las definiciones son de Oniel, escritas para quien no conoce el ferrocarril: resumen lo esencial y dejan fuera los casos particulares. Los conceptos
          de circulación siguen el reglamento que se cita en cada uno, que es el texto que vale.
        </p>
        <PieFuente de="de los conceptos" sources={referencias} />
      </Plegable>
    </section>
  )
}
