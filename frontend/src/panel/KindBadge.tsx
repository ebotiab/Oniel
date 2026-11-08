import type { ClosureStatus, PassKind } from '../data/types'

const KIND: Record<PassKind, { label: string; cls: string }> = {
  publicado: { label: 'publicado', cls: 'verde' },
  estimado: { label: 'estimado', cls: 'ambar' },
  indeterminado: { label: 'indeterminado', cls: 'gris' },
}

export const STATUS: Record<ClosureStatus, { label: string; plural: string; cls: string }> = {
  afectado_publicado: { label: 'afectado · horario publicado', plural: 'Afectados con horario publicado', cls: 'roja' },
  afectado_estimado: { label: 'afectado · paso estimado', plural: 'Afectados con paso estimado', cls: 'ambar' },
  indeterminado: { label: 'indeterminado', plural: 'Indeterminados', cls: 'gris' },
  no_afectado: { label: 'no afectado', plural: 'No afectados', cls: 'verde' },
}

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
