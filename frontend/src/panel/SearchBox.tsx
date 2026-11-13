import { useEffect, useId, useMemo, useRef, useState } from 'react'
import { flushSync } from 'react-dom'

import { buildIndex, GLOSSARY_ENTRY, search, type SearchHit, type SearchScope, type SearchTarget } from '../app/search'
import type { NetworkOut } from '../data/types'

interface Props {
  network: NetworkOut | null
  /** «todo» busca estaciones, otros puntos y líneas; «nodos», solo puntos de la red (para elegir una estación). */
  scope?: SearchScope
  label: string
  placeholder: string
  onPick: (target: SearchTarget) => void
  /** Atiende «/» y Ctrl/⌘ + K en toda la página. Solo para el buscador de la cabecera. */
  shortcut?: boolean
  /** En pantallas estrechas: un botón con la lupa que despliega el campo. */
  compact?: boolean
  testId?: string
}

function Lupa() {
  return (
    <svg className="buscador-lupa" viewBox="0 0 16 16" width="16" height="16" aria-hidden="true">
      <circle cx="7" cy="7" r="4.5" fill="none" stroke="currentColor" strokeWidth="1.5" />
      <path d="M10.5 10.5 14 14" fill="none" stroke="currentColor" strokeWidth="1.5" strokeLinecap="round" />
    </svg>
  )
}

function isTyping(target: EventTarget | null): boolean {
  const el = target as HTMLElement | null
  return !!el && (el.tagName === 'INPUT' || el.tagName === 'TEXTAREA' || el.tagName === 'SELECT' || el.isContentEditable)
}

/**
 * Campo de búsqueda con lista de resultados (patrón «combobox» de WAI-ARIA). Es el buscador de la cabecera
 * y, con `scope="nodos"`, el selector de estación de cualquier otro panel.
 */
export function SearchBox({ network, scope = 'todo', label, placeholder, onPick, shortcut = false, compact = false, testId }: Props) {
  const [query, setQuery] = useState('')
  const [open, setOpen] = useState(false)
  const [expanded, setExpanded] = useState(false)
  const [active, setActive] = useState(0)
  const rootRef = useRef<HTMLDivElement>(null)
  const inputRef = useRef<HTMLInputElement>(null)
  const listId = useId()

  const index = useMemo(() => (network ? buildIndex(network, scope) : []), [network, scope])
  const typed = query.trim() !== ''
  // Sin texto, el buscador ofrece las líneas y, tras ellas, el glosario: se llega a cualquiera sin escribir.
  const hits: SearchHit[] = useMemo(
    () => (typed ? search(index, query) : index.filter((e) => (e.target.type === 'linea' && e.weight === 0) || e === GLOSSARY_ENTRY).map((entry) => ({ entry, byCode: false }))),
    [index, query, typed],
  )
  const current = Math.min(active, Math.max(0, hits.length - 1))
  const showList = open && (typed || hits.length > 0)

  const focusField = () => {
    // El foco va en el mismo gesto que despliega el campo: así el móvil abre el teclado.
    flushSync(() => {
      setExpanded(true)
      setOpen(true)
    })
    inputRef.current?.focus()
    inputRef.current?.select()
  }

  const close = () => {
    setOpen(false)
    setExpanded(false)
    setQuery('')
    setActive(0)
  }

  const pick = (hit: SearchHit) => {
    close()
    inputRef.current?.blur()
    onPick(hit.entry.target)
  }

  useEffect(() => {
    if (!shortcut) return
    const onKey = (e: KeyboardEvent) => {
      const slash = e.key === '/' && !e.ctrlKey && !e.metaKey && !e.altKey && !isTyping(e.target)
      const k = e.key.toLowerCase() === 'k' && (e.ctrlKey || e.metaKey)
      if (!slash && !k) return
      e.preventDefault()
      focusField()
    }
    window.addEventListener('keydown', onKey)
    return () => window.removeEventListener('keydown', onKey)
  }, [shortcut])

  useEffect(() => {
    if (showList) document.getElementById(`${listId}-${current}`)?.scrollIntoView({ block: 'nearest' })
  }, [showList, current, listId])

  const onKeyDown = (e: React.KeyboardEvent<HTMLInputElement>) => {
    if (e.key === 'ArrowDown' || e.key === 'ArrowUp') {
      e.preventDefault()
      setOpen(true)
      if (hits.length) setActive((current + (e.key === 'ArrowDown' ? 1 : hits.length - 1)) % hits.length)
    } else if (e.key === 'Enter') {
      const hit = hits[current]
      if (showList && hit) {
        e.preventDefault()
        pick(hit)
      }
    } else if (e.key === 'Escape') {
      e.preventDefault()
      close()
      inputRef.current?.blur()
    }
  }

  if (compact && !expanded)
    return (
      <div className="buscador compacto" data-testid={testId}>
        <button type="button" className="buscador-abrir" aria-label={label} onClick={focusField} data-testid={testId && `${testId}-abrir`}>
          <Lupa />
        </button>
      </div>
    )

  return (
    <div
      ref={rootRef}
      className={`buscador${compact ? ' compacto desplegado' : ''}`}
      data-testid={testId}
      onBlur={(e) => {
        if (!rootRef.current?.contains(e.relatedTarget)) close()
      }}
    >
      <div className="buscador-campo">
        <Lupa />
        <input
          ref={inputRef}
          type="text"
          role="combobox"
          aria-label={label}
          aria-autocomplete="list"
          aria-expanded={showList}
          aria-controls={listId}
          aria-activedescendant={showList && hits.length ? `${listId}-${current}` : undefined}
          placeholder={placeholder}
          autoComplete="off"
          autoCorrect="off"
          autoCapitalize="none"
          spellCheck={false}
          enterKeyHint="go"
          value={query}
          onChange={(e) => {
            setQuery(e.target.value)
            setActive(0)
            setOpen(true)
          }}
          onFocus={() => setOpen(true)}
          onClick={() => setOpen(true)}
          onKeyDown={onKeyDown}
          data-testid={testId && `${testId}-campo`}
        />
        {shortcut && !compact && !typed && (
          <kbd className="buscador-atajo" aria-hidden="true">
            /
          </kbd>
        )}
        {compact && (
          <button type="button" className="buscador-cerrar" onClick={close}>
            Cerrar
          </button>
        )}
      </div>
      <div className="buscador-lista" hidden={!showList}>
        {!typed && hits.length > 0 && <p className="buscador-rotulo">Líneas y glosario</p>}
        <ul id={listId} role="listbox" aria-label={typed ? 'Resultados' : 'Líneas y glosario'}>
          {hits.map((hit, i) => (
            <li
              key={hit.entry.key}
              id={`${listId}-${i}`}
              role="option"
              aria-selected={i === current}
              className={i === current ? 'activo' : undefined}
              // El campo conserva el foco al pulsar un resultado; si lo perdiera, la lista se cerraría antes del clic.
              onMouseDown={(e) => e.preventDefault()}
              onMouseMove={() => setActive(i)}
              onClick={() => pick(hit)}
            >
              <span className="buscador-nombre">{hit.entry.name}</span>
              <span className="buscador-detalle">
                {hit.entry.detail}
                {hit.byCode && <span className="datos"> · código de Adif {hit.entry.adifCode}</span>}
              </span>
            </li>
          ))}
        </ul>
        {typed && hits.length === 0 && (
          <p className="buscador-vacio" role="status">
            {scope === 'todo' ? 'Ninguna estación, línea ni término coincide con ese nombre.' : 'Ninguna estación coincide con ese nombre.'}
          </p>
        )}
      </div>
    </div>
  )
}
