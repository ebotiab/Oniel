// Cómo dice el visor lo que pasaría con los trenes de un tramo si se cortara: si tienen otro camino
// en las líneas cargadas y cuánto añade. El cálculo es del servidor (`oniel.analysis.criticality`,
// exportado a `alternatives.json`); aquí solo están las frases. La palabra «alternativa» lleva
// siempre al lado «en las líneas que Oniel tiene cargadas».

import type { AlternativeRoute, LineSummary, SegmentAlternatives, SegmentTrainGroup } from '../data/types.ts'
import { formatDuracion } from './recorridos.ts'

const lista = new Intl.ListFormat('es', { style: 'long', type: 'conjunction' })

/** «1 tren», «43 trenes». */
export function trenes(n: number): string {
  return n === 1 ? '1 tren' : `${n} trenes`
}

/**
 * Lo que añade el otro camino, en una frase: «97 km y 1 h 44 min más», «90 km y 1 h 6 min menos»,
 * «105 km más y 29 min menos». Los kilómetros van sin decimales: es una comparación, no una medida.
 */
export function coste(a: AlternativeRoute): string {
  const km = Math.round(Math.abs(a.extra_km))
  const signoKm = km === 0 ? 0 : Math.sign(a.extra_km)
  const min = a.extra_min === null ? null : Math.abs(a.extra_min)
  const signoMin = a.extra_min === null || a.extra_min === 0 ? 0 : Math.sign(a.extra_min)
  const palabra = (signo: number) => (signo > 0 ? 'más' : 'menos')
  const parteKm = km === 0 ? 'los mismos kilómetros' : `${km} km`
  if (min === null) return km === 0 ? parteKm : `${parteKm} ${palabra(signoKm)}`
  const parteMin = min === 0 ? 'el mismo tiempo' : formatDuracion(min)
  // mismo signo en los dos: la palabra se dice una vez, al final
  if (signoKm !== 0 && signoKm === signoMin) return `${parteKm} y ${parteMin} ${palabra(signoKm)}`
  return `${parteKm}${signoKm === 0 ? '' : ` ${palabra(signoKm)}`} y ${parteMin}${signoMin === 0 ? '' : ` ${palabra(signoMin)}`}`
}

/** Lo mismo, corto, para una fila de lista: «+97 km · +1 h 44 min», «−90 km · −1 h 6 min». */
export function costeCorto(a: AlternativeRoute): string {
  const signo = (n: number) => (n > 0 ? '+' : n < 0 ? '−' : '')
  const km = Math.round(a.extra_km)
  const partes = [`${signo(km)}${Math.abs(km)} km`]
  if (a.extra_min !== null) partes.push(`${signo(a.extra_min)}${formatDuracion(Math.abs(a.extra_min))}`)
  return partes.join(' · ')
}

/** «la línea convencional Manzanares – Ciudad Real y la línea de alta velocidad Madrid – Sevilla». */
export function porLineas(lineIds: string[], lines: LineSummary[]): string {
  const nombres = lineIds.map((id) => {
    const nombre = lines.find((l) => l.id === id)?.name ?? id
    return `la ${nombre.charAt(0).toLowerCase()}${nombre.slice(1)}`
  })
  return lista.format(nombres)
}

/** El grupo con más trenes de los que tienen otro camino: el que resume el tramo en una fila. */
export function grupoPrincipal(s: SegmentAlternatives): SegmentTrainGroup | undefined {
  return s.groups.find((g) => g.alternative !== null)
}

/**
 * La frase de la ficha del tramo: lo esencial, a la vista. El desglose por grupos de trenes va en
 * «Más detalle».
 */
export function fraseTramo(s: SegmentAlternatives): string {
  if (s.trains === 0) return ''
  const donde = 'en las líneas que Oniel tiene cargadas'
  const sus = s.trains === 1 ? 'su único tren' : `sus ${s.trains} trenes`
  if (s.without_alternative === s.trains) {
    return `Si este tramo se cortara, ${sus} no tendría${s.trains === 1 ? '' : 'n'} otro camino ${donde}. No quiere decir que no exista en la red real.`
  }
  const principal = grupoPrincipal(s)
  const cuanto = principal?.alternative
    ? s.groups.length === 1
      ? ` Ese camino tiene ${coste(principal.alternative)}.`
      : ` Para los más numerosos (${principal.trains}, entre ${principal.from_name} y ${principal.to_name}), ${coste(principal.alternative)}.`
    : ''
  if (s.without_alternative === 0) {
    return `Si este tramo se cortara, ${sus} tendría${s.trains === 1 ? '' : 'n'} otro camino ${donde}.${cuanto}`
  }
  return `Si este tramo se cortara, ${s.without_alternative} de ${sus} no tendría${s.without_alternative === 1 ? '' : 'n'} otro camino ${donde}; los demás, sí.${cuanto}`
}

/** Tramos cuyos trenes se quedan sin otro camino, del que deja a más trenes sin él al que menos. */
export function sinAlternativa(segments: SegmentAlternatives[]): SegmentAlternatives[] {
  return segments.filter((s) => s.without_alternative > 0).sort((a, b) => b.without_alternative - a.without_alternative || b.trains - a.trains)
}

/** Los demás tramos con trenes, del que más lleva al que menos. */
export function conAlternativa(segments: SegmentAlternatives[]): SegmentAlternatives[] {
  return segments.filter((s) => s.trains > 0 && s.without_alternative === 0).sort((a, b) => b.trains - a.trains)
}
