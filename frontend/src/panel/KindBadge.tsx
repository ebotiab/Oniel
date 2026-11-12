import type { ClosureStatus, PassKind } from '../data/types'
import type { TerminoId } from './glosario'
import { KIND, STATUS } from './labels'
import { Termino } from './Termino'

const TERMINO: Record<PassKind, TerminoId> = { publicado: 'paso-publicado', estimado: 'paso-estimado', indeterminado: 'paso-indeterminado' }

export function KindBadge({ kind, title }: { kind: PassKind; title?: string }) {
  const k = KIND[kind]
  return (
    <span className={`senal ${k.cls}`} title={title}>
      <Termino id={TERMINO[kind]}>{k.label}</Termino>
    </span>
  )
}

export function StatusBadge({ status }: { status: ClosureStatus }) {
  const s = STATUS[status]
  return <span className={`senal ${s.cls}`}>{s.label}</span>
}
