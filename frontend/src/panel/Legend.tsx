import type { LineSummary } from '../data/types'
import { lineKind } from '../app/state'

interface Props {
  closed: boolean
  /** Hay algún tramo con una interrupción del servicio vigente hoy. */
  interrupted: boolean
  lines: LineSummary[]
  singleTrack: boolean
}

export function Legend({ closed, interrupted, lines, singleTrack }: Props) {
  const kinds = new Set(lines.map(lineKind))
  const several = kinds.size > 1
  return (
    <div className="leyenda" aria-label="Leyenda">
      {several ? (
        <>
          {kinds.has('alta velocidad') && (
            <>
              <span className="muestra via" aria-hidden="true" />
              <span>Alta velocidad</span>
            </>
          )}
          {kinds.has('convencional') && (
            <>
              <span className="muestra via convencional" aria-hidden="true" />
              <span>Línea convencional</span>
            </>
          )}
        </>
      ) : (
        <>
          <span className="muestra via" aria-hidden="true" />
          <span>Tramo disponible en Oniel</span>
        </>
      )}
      {singleTrack && (
        <>
          <span className="muestra via unica" aria-hidden="true" />
          <span>Tramo de vía única</span>
        </>
      )}
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
