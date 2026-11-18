import { useEffect, useRef, useState } from 'react'

import { formatDateLong } from '../app/annotations'
import { formatDayShortYear, listaEs } from '../app/state'
import type { CoverageOut } from '../data/types'

interface Props {
  coverage: CoverageOut | null
  /** La ruta de la vista (`routePath`): es lo que se copia, con el dominio delante. */
  ruta: string
  /** El día de los trenes de la vista, si no es el de referencia (una simulación con su día). */
  dia?: string | null
  /** Variante con el pie fijo bajo el panel (docs/diseno.md, «Citar una vista»). */
  fijo?: boolean
}

/** «el 17 nov 2026 (Renfe) y el 12 nov 2026 (Ouigo)»: cuándo se descargó el fichero de horarios de cada operador. */
function descargas(coverage: CoverageOut): string | null {
  const datasets = [...(coverage.datasets ?? [])].sort((a, b) => b.retrieved_on.localeCompare(a.retrieved_on))
  if (!datasets.length) return null
  const nombre = (id: string | null) => coverage.operators.find((o) => o.id === id)?.name ?? null
  return listaEs(
    datasets.map((d) => {
      const operador = nombre(d.operator_id)
      return `el ${formatDayShortYear(d.retrieved_on)}${operador ? ` (${operador})` : ''}`
    }),
  )
}

/**
 * El pie de cada vista del panel: de qué día son los trenes que se cuentan, cuándo se descargaron los
 * horarios y un botón que copia la dirección exacta de la vista, para citarla desde fuera
 * (docs/diseno.md, «Citar una vista»).
 */
export function PieVista({ coverage, ruta, dia, fijo = false }: Props) {
  const [estado, setEstado] = useState<'reposo' | 'copiado' | 'manual'>('reposo')
  const campo = useRef<HTMLInputElement>(null)
  const enlace = window.location.origin + ruta

  // El aviso de «copiado» dura un momento; al cambiar de vista el pie se monta de nuevo (App le da la ruta como clave).
  useEffect(() => {
    if (estado !== 'copiado') return
    const t = window.setTimeout(() => setEstado('reposo'), 4000)
    return () => window.clearTimeout(t)
  }, [estado])
  // Sin permiso para escribir en el portapapeles, la dirección queda a la vista y seleccionada.
  useEffect(() => {
    if (estado === 'manual') campo.current?.select()
  }, [estado])

  async function copiar() {
    try {
      await navigator.clipboard.writeText(enlace)
      setEstado('copiado')
    } catch {
      setEstado('manual')
    }
  }

  const referencia = dia ?? coverage?.reference_date ?? null
  const descargados = coverage ? descargas(coverage) : null
  return (
    <footer className={fijo ? 'pie-vista fijo' : 'pie-vista'} data-testid="pie-vista">
      {referencia && (
        <p className="pie-vista-fecha" data-testid="pie-vista-fecha">
          Trenes del {formatDateLong(referencia)}
          {descargados ? `, según los horarios descargados ${descargados}` : ''}.
        </p>
      )}
      <p className="pie-vista-accion">
        <button type="button" className={fijo ? 'boton menor' : 'enlace'} onClick={() => void copiar()} data-testid="copiar-enlace">
          Copiar enlace a esta vista
        </button>
        <span role="status" data-testid="copiar-enlace-estado">
          {estado === 'copiado' ? 'Enlace copiado.' : ''}
        </span>
      </p>
      {estado === 'manual' && (
        <label className="pie-vista-manual">
          <span>El navegador no deja copiarlo: cópialo de aquí.</span>
          <input ref={campo} type="text" readOnly value={enlace} data-testid="copiar-enlace-manual" />
        </label>
      )}
    </footer>
  )
}
