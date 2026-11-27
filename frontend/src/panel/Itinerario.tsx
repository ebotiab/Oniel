import type { Itinerary, Source } from '../data/types'

/** La identificación de la vía tiene su propia fuente, distinta de las horas comerciales. */
export function Itinerario({ itinerary, sources }: { itinerary?: Itinerary; sources: Source[] }) {
  if (!itinerary) return null
  if (!itinerary.source_id) return <> · itinerario pendiente de confirmar</>
  const fuente = sources.find((s) => s.id === itinerary.source_id)
  return <> · itinerario acreditado{fuente?.url && <> · <a href={fuente.url}>{fuente.name}</a></>}</>
}
