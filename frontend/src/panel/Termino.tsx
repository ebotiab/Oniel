import { useEffect, useId, useRef, useState, type ReactNode } from 'react'
import { flushSync } from 'react-dom'

import { termino, type TerminoId } from './glosario'
import { abreAparte } from '../app/navegacion'
import { rutaGlosario, useAbrirGlosario } from './glosarioContexto'

interface Props {
  id: TerminoId
  /** El texto tal y como va en la ficha; sin él, el nombre del término. */
  children?: ReactNode
}

/** Margen entre la nota y los bordes de la pantalla, y entre la nota y su término. */
const MARGEN = 12
const SEPARACION = 6
/** Alto que se le supone a la nota para decidir si cabe debajo del término (las más largas rondan los 190 px). */
const ALTO_PREVISTO = 200

/**
 * Un término técnico dentro de una ficha: un botón con subrayado de puntos que abre, pegada a él, una nota
 * con la definición y el enlace a su entrada del glosario. La nota es un `popover` nativo: se abre con un
 * toque, con Intro o con Espacio, se cierra con otro toque, tocando fuera o con Escape, y solo hay una
 * abierta a la vez. No depende de pasar el ratón por encima, así que funciona igual al tacto.
 */
export function Termino({ id, children }: Props) {
  const t = termino(id)
  const notaId = useId()
  const boton = useRef<HTMLButtonElement>(null)
  const nota = useRef<HTMLSpanElement>(null)
  // La nota no está en el documento hasta que el visitante se acerca al término: una lista de cien trenes
  // lleva cien etiquetas «estimado» y no hace falta cien notas.
  const [montada, setMontada] = useState(false)
  const [abierta, setAbierta] = useState(false)
  const abrirGlosario = useAbrirGlosario()

  // La nota no sigue al término si la ficha se desplaza o la ventana cambia: se cierra.
  useEffect(() => {
    if (!abierta) return
    const cerrar = (e: Event) => {
      if (e.target instanceof Node && nota.current?.contains(e.target)) return
      nota.current?.hidePopover()
    }
    window.addEventListener('scroll', cerrar, { capture: true, passive: true })
    window.addEventListener('resize', cerrar)
    return () => {
      window.removeEventListener('scroll', cerrar, { capture: true })
      window.removeEventListener('resize', cerrar)
    }
  }, [abierta])

  /** Coloca la nota bajo el término, o encima si debajo no cabe, sin salirse de la pantalla. */
  const colocar = () => {
    const el = nota.current
    const origen = boton.current?.getBoundingClientRect()
    if (!el || !origen) return
    const ancho = Math.min(320, window.innerWidth - 2 * MARGEN)
    const left = Math.max(MARGEN, Math.min(origen.left, window.innerWidth - ancho - MARGEN))
    const debajo = window.innerHeight - origen.bottom
    const encima = debajo < ALTO_PREVISTO && origen.top > debajo
    el.style.width = `${ancho}px`
    el.style.left = `${left}px`
    el.style.top = encima ? 'auto' : `${origen.bottom + SEPARACION}px`
    el.style.bottom = encima ? `${window.innerHeight - origen.top + SEPARACION}px` : 'auto'
    el.style.maxHeight = `${Math.max(encima ? origen.top : debajo, 120) - SEPARACION - MARGEN}px`
  }

  const preparar = () => setMontada(true)

  return (
    <>
      <button
        ref={boton}
        type="button"
        className="termino"
        popoverTarget={notaId}
        aria-expanded={abierta}
        onPointerEnter={preparar}
        onPointerDown={preparar}
        onFocus={preparar}
        // quien llega sin puntero ni foco (un lector de pantalla que pulsa directamente): la nota se monta antes de que el botón la busque
        onClick={() => {
          if (!montada) flushSync(preparar)
        }}
        data-termino={id}
      >
        {children ?? t.nombre}
      </button>
      {montada && (
        <span
          ref={nota}
          id={notaId}
          popover="auto"
          role="note"
          className="termino-nota"
          data-testid="termino-nota"
          onBeforeToggle={(e) => {
            if (e.newState === 'open') colocar()
          }}
          onToggle={(e) => setAbierta(e.newState === 'open')}
        >
          <strong className="termino-nota-nombre">{t.nombre}</strong>
          <span className="termino-nota-texto">{t.breve}</span>
          <a
            className="termino-nota-enlace"
            href={rutaGlosario(id)}
            onClick={(e) => {
              // con Ctrl, ⌘ o el botón central el enlace se abre aparte, como cualquier otro
              if (abreAparte(e)) return
              e.preventDefault()
              nota.current?.hidePopover()
              abrirGlosario(id)
            }}
          >
            Ver en el glosario
          </a>
        </span>
      )}
    </>
  )
}
