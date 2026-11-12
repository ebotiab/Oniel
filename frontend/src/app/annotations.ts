// Anotaciones de red: lo que pasa sobre la red entre dos fechas según una fuente. Aquí, cuáles
// están vigentes un día, a qué tramos afectan y cómo se dicen sus fechas. Lo que cambia de un tipo
// a otro (dibujo, leyenda, ficha, notas) está en el registro de capas, annotationLayers.ts.

import type { AnnotationOut, InterruptionOut, NetworkOut } from '../data/types.ts'

/** Vigente los días start_date <= día < ended_on (ended_on es el día en que termina); sin límite por el lado que falte. */
export function isActive(a: AnnotationOut, day: string): boolean {
  return (a.start_date === null || a.start_date <= day) && (a.ended_on === null || day < a.ended_on)
}

/** Una interrupción del servicio: va de un nodo a otro de una línea y corta la circulación en sus tramos. */
export function isInterruption(a: AnnotationOut): a is InterruptionOut {
  return a.kind === 'interrupcion'
}

export function activeAnnotations(network: NetworkOut | null, day: string): AnnotationOut[] {
  return (network?.annotations ?? []).filter((a) => isActive(a, day))
}

export function activeInterruptions(network: NetworkOut | null, day: string): InterruptionOut[] {
  return activeAnnotations(network, day).filter(isInterruption)
}

/** Interrupciones que ya terminaron: la circulación se reanudó ese día o antes. Quedan como registro. */
export function pastInterruptions(network: NetworkOut | null, day: string): InterruptionOut[] {
  return (network?.annotations ?? []).filter(isInterruption).filter((a) => a.ended_on !== null && a.ended_on <= day)
}

/** Anotaciones que afectan a cada tramo, por id de tramo. */
export function bySegment<A extends AnnotationOut>(annotations: A[]): Map<string, A[]> {
  const out = new Map<string, A[]>()
  for (const a of annotations) {
    for (const id of a.segment_ids) out.set(id, [...(out.get(id) ?? []), a])
  }
  return out
}

/** «6 de septiembre de 2026», sin día de la semana. */
export function formatDateLong(iso: string): string {
  const d = new Date(`${iso}T12:00:00`)
  return d.toLocaleDateString('es-ES', { day: 'numeric', month: 'long', year: 'numeric' })
}

/** Quien publica la fuente principal, para citarlo en una línea («Adif»). */
export function mainSourceLabel(a: AnnotationOut): string {
  return a.sources[0]?.publisher.split(';')[0]?.trim() ?? 'fuente sin registrar'
}
