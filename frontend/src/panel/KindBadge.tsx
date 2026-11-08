import type { ClosureStatus, PassKind } from '../data/types'
import { KIND, STATUS } from './labels'

export function KindBadge({ kind, title }: { kind: PassKind; title?: string }) {
  const k = KIND[kind]
  return (
    <span className={`senal ${k.cls}`} title={title}>
      {k.label}
    </span>
  )
}

export function StatusBadge({ status }: { status: ClosureStatus }) {
  const s = STATUS[status]
  return <span className={`senal ${s.cls}`}>{s.label}</span>
}
