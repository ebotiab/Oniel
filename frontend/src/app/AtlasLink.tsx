import type { ReactNode } from 'react'

import { abreAparte, navegar } from './navegacion'
import { routePath, type Route } from './state'

export function AtlasLink({ to, children, className }: { to: Partial<Route>; children: ReactNode; className?: string }) {
  const href = routePath({ selection: null, simulacion: false, ...to })
  return (
    <a href={href} className={className} onClick={(event) => {
      if (abreAparte(event)) return
      event.preventDefault()
      navegar(href)
    }}>
      {children}
    </a>
  )
}
