import { useState, type ReactNode } from 'react'

import type { Source } from '../data/types'
import { formatDateLong } from '../app/annotations'

const PREFIJO = 'oniel:plegable:'

function recordado(memoria: string): boolean {
  try {
    return window.sessionStorage.getItem(PREFIJO + memoria) === 'abierto'
  } catch {
    return false // sin almacenamiento (modo privado estricto) el plegable funciona igual, sin memoria
  }
}

function recordar(memoria: string, abierto: boolean): void {
  try {
    if (abierto) window.sessionStorage.setItem(PREFIJO + memoria, 'abierto')
    else window.sessionStorage.removeItem(PREFIJO + memoria)
  } catch {
    /* sin almacenamiento no se recuerda */
  }
}

interface Props {
  /** Rótulo del plegable. Todas las fichas usan el mismo: «Más detalle». */
  rotulo?: string
  /**
   * Clave con la que se recuerda, durante la sesión, si el visitante lo dejó abierto. Las fichas
   * comparten la clave por defecto: quien abre el detalle de un tramo lo encuentra abierto en el siguiente.
   */
  memoria?: string
  testId?: string
  children: ReactNode
}

/**
 * El detalle de una ficha: cerrado de entrada, a un toque. Es un `<details>` nativo, así que se abre
 * con el teclado (Intro o Espacio sobre el rótulo) y los lectores de pantalla anuncian su estado.
 */
export function Plegable({ rotulo = 'Más detalle', memoria = 'detalle', testId = 'mas-detalle', children }: Props) {
  const [abierto, setAbierto] = useState(() => recordado(memoria))
  return (
    <details
      className="plegable"
      open={abierto}
      data-testid={testId}
      onToggle={(e) => {
        const ahora = e.currentTarget.open
        setAbierto(ahora)
        recordar(memoria, ahora)
      }}
    >
      <summary>{rotulo}</summary>
      <div className="plegable-contenido">{children}</div>
    </details>
  )
}

/**
 * Pie de una ficha: de dónde sale el dato y cuándo se consultó. Las fuentes de un mismo editor van en un solo
 * párrafo: una estación de varias líneas cita OpenStreetMap una vez, con el trazado de cada línea detrás.
 */
export function PieFuente({ sources, de }: { sources: (Source | undefined)[]; de: string }) {
  // una estación de dos líneas con el mismo trazado de origen (Barcelona-Sants) lo cita una sola vez
  const fuentes = sources.filter((s, i): s is Source => Boolean(s) && sources.findIndex((o) => o?.id === s?.id) === i)
  if (!fuentes.length) return null
  const porEditor = new Map<string, Source[]>()
  for (const s of fuentes) porEditor.set(s.publisher, [...(porEditor.get(s.publisher) ?? []), s])
  return (
    <div className="pie-fuente" data-testid="pie-fuente">
      {[...porEditor.entries()].map(([editor, grupo]) => {
        const s = grupo[0]!
        if (grupo.length === 1)
          return (
            <p key={s.id} className="suave">
              Fuente {de}: {s.url ? (
                <a href={s.url} target="_blank" rel="noreferrer">
                  {s.publisher}
                </a>
              ) : (
                s.publisher
              )}
              {s.retrieved_on ? `, consultada el ${formatDateLong(s.retrieved_on)}` : ''}. {s.name}. <span className="datos">Identificador de la fuente: {s.id}</span>
            </p>
          )
        // Varias del mismo editor: el editor una vez y, detrás, cada una con su enlace; la fecha se dice una
        // vez si es la misma y, si no, con cada una.
        const mismaFecha = grupo.every((g) => g.retrieved_on === s.retrieved_on)
        return (
          <p key={editor} className="suave">
            Fuentes {de}: {editor}
            {mismaFecha && s.retrieved_on ? `, consultadas el ${formatDateLong(s.retrieved_on)}` : ''}.{' '}
            {grupo.map((g, i) => (
              <span key={g.id}>
                {i > 0 && '; '}
                {g.url ? (
                  <a href={g.url} target="_blank" rel="noreferrer">
                    {g.name}
                  </a>
                ) : (
                  g.name
                )}
                {!mismaFecha && g.retrieved_on ? ` (consultada el ${formatDateLong(g.retrieved_on)})` : ''}
              </span>
            ))}
            . <span className="datos">Identificadores de las fuentes: {grupo.map((g) => g.id).join(', ')}</span>
          </p>
        )
      })}
    </div>
  )
}
