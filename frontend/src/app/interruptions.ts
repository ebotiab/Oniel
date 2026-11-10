// Interrupciones del servicio: cuáles están vigentes un día y cómo se dicen sus fechas.

import type { InterruptionOut, NetworkOut } from '../data/types'

/** Vigente los días start_date <= día < ended_on (ended_on es el día en que vuelve a haber trenes). */
export function isActive(i: InterruptionOut, day: string): boolean {
  return i.start_date <= day && (i.ended_on === null || day < i.ended_on)
}

export function activeInterruptions(network: NetworkOut | null, day: string): InterruptionOut[] {
  return (network?.interruptions ?? []).filter((i) => isActive(i, day))
}

/** Interrupciones que afectan a cada tramo, por id de tramo. */
export function bySegment(interruptions: InterruptionOut[]): Map<string, InterruptionOut[]> {
  const out = new Map<string, InterruptionOut[]>()
  for (const i of interruptions) {
    for (const id of i.segment_ids) out.set(id, [...(out.get(id) ?? []), i])
  }
  return out
}

/** «6 de septiembre de 2026», sin día de la semana. */
export function formatDateLong(iso: string): string {
  const d = new Date(`${iso}T12:00:00`)
  return d.toLocaleDateString('es-ES', { day: 'numeric', month: 'long', year: 'numeric' })
}

/** Lo que se sabe del final: la reanudación, la previsión publicada o que no hay fecha. */
export function endLabel(i: InterruptionOut): string {
  if (i.ended_on) return `La circulación se reanudó el ${formatDateLong(i.ended_on)}.`
  if (i.expected_end_date) return `Reanudación prevista: ${formatDateLong(i.expected_end_date)}.`
  if (i.expected_end_text) return `Reanudación prevista: ${i.expected_end_text}.`
  return 'Sin fecha prevista de reanudación.'
}

/** Quien publica la fuente principal, para citarlo en una línea («Adif»). */
export function mainSourceLabel(i: InterruptionOut): string {
  return i.sources[0]?.publisher.split(';')[0]?.trim() ?? 'fuente sin registrar'
}
