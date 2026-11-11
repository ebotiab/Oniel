import { useState } from 'react'

import type { LineSummary } from '../data/types'
import { lineKind } from '../app/state'
import type { Trazo } from '../map/layers'

interface Props {
  closed: boolean
  /** Hay algún tramo con una interrupción del servicio vigente hoy. */
  interrupted: boolean
  lines: LineSummary[]
  singleTrack: boolean
  /** Trazo resaltado en el mapa: el que se toca en la leyenda o sobre el que se pasa. */
  highlight: Trazo | null
  onHighlight: (trazo: Trazo | null) => void
}

/** Muestra de un trazo con el mismo dibujo que el mapa: filete claro, trazos blancos o trazos espaciados. */
function Muestra({ trazo }: { trazo: Trazo }) {
  const grosor = trazo === 'alta-velocidad' ? 5 : trazo === 'convencional' ? 3.2 : 2
  return (
    <svg className="muestra-via" width={26} height={6} viewBox="0 0 26 6" aria-hidden="true">
      <line x1={0} y1={3} x2={26} y2={3} stroke="var(--tinta)" strokeWidth={grosor} />
      {trazo === 'alta-velocidad' ? (
        <line x1={0} y1={3} x2={26} y2={3} stroke="var(--papel)" strokeWidth={1.4} />
      ) : (
        <line x1={0} y1={3} x2={26} y2={3} stroke="var(--papel)" strokeWidth={grosor * 0.5} strokeDasharray={trazo === 'convencional' ? '1.2 3.6' : '1.2 8.4'} strokeDashoffset={-2} />
      )}
    </svg>
  )
}

export function Legend({ closed, interrupted, lines, singleTrack, highlight, onHighlight }: Props) {
  const kinds = new Set(lines.map(lineKind))
  const several = kinds.size > 1
  // Fijado con un toque o un clic; al pasar por encima se resalta sin fijar.
  const [pinned, setPinned] = useState<Trazo | null>(null)
  const tipo = (trazo: Trazo, texto: string) => (
    <button
      type="button"
      className="leyenda-tipo"
      aria-pressed={highlight === trazo}
      title="Resaltar en el mapa"
      data-testid={`leyenda-${trazo}`}
      onClick={() => {
        const next = pinned === trazo ? null : trazo
        setPinned(next)
        onHighlight(next)
      }}
      onMouseEnter={() => onHighlight(trazo)}
      onMouseLeave={() => onHighlight(pinned)}
      onFocus={() => onHighlight(trazo)}
      onBlur={() => onHighlight(pinned)}
    >
      <Muestra trazo={trazo} />
      <span>{texto}</span>
    </button>
  )
  return (
    <div className="leyenda" aria-label="Leyenda">
      {several ? (
        <>
          {kinds.has('alta velocidad') && tipo('alta-velocidad', 'Alta velocidad')}
          {kinds.has('convencional') && tipo('convencional', 'Línea convencional')}
        </>
      ) : (
        <>
          <Muestra trazo={kinds.has('alta velocidad') ? 'alta-velocidad' : 'convencional'} />
          <span>Tramo disponible en Oniel</span>
        </>
      )}
      {singleTrack && tipo('via-unica', 'Vía única')}
      <span className="muestra conexion" aria-hidden="true" />
      <span>Conexión no cargada todavía</span>
      {interrupted && (
        <>
          <span className="muestra sin-circulacion" aria-hidden="true" data-testid="leyenda-interrupcion" />
          <span>Sin circulación hoy</span>
        </>
      )}
      <span className="muestra seleccion" aria-hidden="true" />
      <span>Tramo seleccionado</span>
      {closed && (
        <>
          <span className="muestra cierre" aria-hidden="true" />
          <span>Cierre simulado</span>
        </>
      )}
    </div>
  )
}
