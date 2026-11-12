import { Fragment, useEffect, useState } from 'react'

import type { AnnotationOut, LineSummary } from '../data/types'
import { leyendaDe } from '../app/annotationLayers'
import { lineKind } from '../app/state'
import type { Trazo } from '../map/layers'

interface Props {
  closed: boolean
  /** Anotaciones vigentes hoy: cada tipo con entrada de leyenda aparece mientras tenga alguna. */
  annotations: AnnotationOut[]
  lines: LineSummary[]
  singleTrack: boolean
  /** Trazo resaltado en el mapa: el que se toca en la leyenda o sobre el que se pasa. */
  highlight: Trazo | null
  onHighlight: (trazo: Trazo | null) => void
  /** Se ha fijado un trazo con un clic o un toque: el mapa lo encuadra. */
  onPin?: (trazo: Trazo) => void
}

/** Muestra de un trazo con el mismo dibujo que el mapa: filete claro, trazos blancos o trazos espaciados. */
export function Muestra({ trazo }: { trazo: Trazo }) {
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

export function Legend({ closed, annotations, lines, singleTrack, highlight, onHighlight, onPin }: Props) {
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
        if (next) onPin?.(next)
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
      {leyendaDe(annotations).map((entrada) => (
        <Fragment key={entrada.testId}>
          <span className={`muestra ${entrada.clase}`} aria-hidden="true" data-testid={entrada.testId} />
          <span>{entrada.texto}</span>
        </Fragment>
      ))}
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

interface TrazosProps {
  lines: LineSummary[]
  singleTrack: boolean
  highlight: Trazo | null
  onHighlight: (trazo: Trazo | null) => void
  /** Se ha fijado un trazo con un clic o un toque: el mapa lo encuadra. */
  onPin?: (trazo: Trazo) => void
}

/**
 * Leyenda del móvil: solo los trazos de la vía, en un renglón dentro del panel. Un toque resalta ese
 * trazo en el mapa y otro lo suelta; al salir de la vista (por ejemplo, al abrir un tramo) se suelta solo.
 */
export function LeyendaTrazos({ lines, singleTrack, highlight, onHighlight, onPin }: TrazosProps) {
  const kinds = new Set(lines.map(lineKind))
  // onHighlight es el setter de estado de App, estable: el efecto solo se deshace al desmontar.
  useEffect(() => () => onHighlight(null), [onHighlight])
  const trazos: [Trazo, string][] = []
  if (kinds.has('alta velocidad')) trazos.push(['alta-velocidad', 'Alta velocidad'])
  if (kinds.has('convencional')) trazos.push(['convencional', 'Línea convencional'])
  if (singleTrack) trazos.push(['via-unica', 'Vía única'])
  if (trazos.length < 2) return null
  return (
    <div className="leyenda-trazos" role="group" aria-label="Trazos de la vía en el mapa" data-testid="leyenda-trazos">
      {trazos.map(([trazo, texto]) => (
        <button
          key={trazo}
          type="button"
          className="leyenda-tipo"
          aria-pressed={highlight === trazo}
          title="Resaltar en el mapa"
          data-testid={`leyenda-${trazo}`}
          onClick={() => {
            const next = highlight === trazo ? null : trazo
            onHighlight(next)
            if (next) onPin?.(next)
          }}
        >
          <Muestra trazo={trazo} />
          <span>{texto}</span>
        </button>
      ))}
    </div>
  )
}
