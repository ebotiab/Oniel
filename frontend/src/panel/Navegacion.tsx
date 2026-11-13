import { useEffect, useRef, useState, type MouseEvent } from 'react'

import { abreAparte } from '../app/navegacion'
import { routePath } from '../app/state'
import type { ApiStatus } from '../data/api'

/** Las secciones de Oniel: lo que la cabecera enlaza desde cualquier vista. */
export type Seccion = 'mapa' | 'recorridos' | 'sin-otro-camino' | 'glosario' | 'cobertura'

interface Entrada {
  id: Seccion
  nombre: string
  /** Lo que dice de ella el menú del móvil, en una frase. */
  frase: string
  href: string
}

/**
 * Una sección nueva es una entrada más de esta lista. En escritorio son enlaces de texto en la barra; en el
 * móvil, los renglones del menú, así que el número de secciones no estrecha la cabecera.
 */
const SECCIONES: Entrada[] = [
  { id: 'mapa', nombre: 'Mapa', frase: 'La red, línea a línea', href: '/' },
  {
    id: 'recorridos',
    nombre: 'Comparar recorridos',
    frase: 'Por dónde se va de una estación a otra',
    href: routePath({ selection: null, simulacion: false, recorridos: { from: null, to: null } }),
  },
  {
    id: 'sin-otro-camino',
    nombre: 'Tramos sin otro camino',
    frase: 'Dónde un corte deja a los trenes sin paso',
    href: routePath({ selection: null, simulacion: false, sinOtroCamino: true }),
  },
  { id: 'glosario', nombre: 'Glosario', frase: 'Qué significa cada término', href: routePath({ selection: null, simulacion: false, glosario: { entrada: null } }) },
  { id: 'cobertura', nombre: 'Cobertura y fuentes', frase: 'Qué hay cargado y de dónde sale', href: routePath({ selection: null, simulacion: false, cobertura: true }) },
]

interface Props {
  /** La sección a la vista: se marca con `aria-current`. */
  actual: Seccion
  onIr: (seccion: Seccion) => void
  /** En el móvil los enlaces van tras un botón «Menú». */
  mobile: boolean
  /** El estado del servidor solo se dice mientras no responde. */
  status: ApiStatus | null
}

/** Lo que se dice del servidor mientras no responde; nada cuando ya lo hace. */
function Estado({ status }: { status: ApiStatus | null }) {
  if (status !== 'buscando' && status !== 'ausente') return null
  return (
    <span className="senal gris" data-testid="estado-servidor">
      {status === 'buscando' ? 'despertando el servidor…' : 'vista estática'}
    </span>
  )
}

/** La navegación de la cabecera: la misma en el mapa y en las páginas de lectura, con la sección actual marcada. */
export function Navegacion({ actual, onIr, mobile, status }: Props) {
  const [abierto, setAbierto] = useState(false)
  const caja = useRef<HTMLDivElement>(null)

  // El menú del móvil se cierra con Escape o al tocar fuera de él.
  useEffect(() => {
    if (!abierto) return
    const fuera = (e: PointerEvent) => {
      if (!caja.current?.contains(e.target as Node)) setAbierto(false)
    }
    const tecla = (e: KeyboardEvent) => {
      if (e.key === 'Escape') setAbierto(false)
    }
    document.addEventListener('pointerdown', fuera)
    document.addEventListener('keydown', tecla)
    return () => {
      document.removeEventListener('pointerdown', fuera)
      document.removeEventListener('keydown', tecla)
    }
  }, [abierto])

  const enlace = (s: Entrada, frase: boolean) => (
    <a
      key={s.id}
      href={s.href}
      aria-current={s.id === actual ? 'page' : undefined}
      onClick={(e: MouseEvent) => {
        if (abreAparte(e)) return
        e.preventDefault()
        setAbierto(false)
        onIr(s.id)
      }}
      data-testid={`nav-${s.id}`}
    >
      {s.nombre}
      {frase && <small>{s.frase}</small>}
    </a>
  )

  if (!mobile)
    return (
      <nav className="nav" aria-label="Secciones" data-testid="nav">
        <Estado status={status} />
        {SECCIONES.map((s) => enlace(s, false))}
      </nav>
    )
  return (
    <div className="nav-movil" ref={caja}>
      <button type="button" className="nav-menu-boton" aria-expanded={abierto} aria-controls="nav-menu" onClick={() => setAbierto(!abierto)} data-testid="nav-menu-boton">
        {abierto ? 'Cerrar' : 'Menú'}
      </button>
      {abierto && (
        <nav id="nav-menu" className="nav-menu" aria-label="Secciones" data-testid="nav">
          {SECCIONES.map((s) => enlace(s, true))}
          <Estado status={status} />
        </nav>
      )}
    </div>
  )
}
