import { AtlasLink } from '../app/AtlasLink'
import type { StationClosure } from '../data/types'

export function StationClosureLinks({ journey, scenario }: { journey: StationClosure; scenario?: string | null }) {
  const { from_id: from, to_id: to, from_name, to_name, segment_ids } = journey
  const changes = new Set([...(scenario?.split(';').filter(Boolean) ?? []), ...segment_ids.map(id => `c~${id}`)])
  const recorridos = { from, to, escenario: [...changes].join(';') }
  return (
    <section aria-label="Cierre entre estaciones" data-testid="cierre-estaciones">
      <h3 className="subtitulo">Cierre entre estaciones</h3>
      <p className="texto">Compara los caminos disponibles si se cierra el trayecto entre {from_name} y {to_name}.</p>
      <AtlasLink className="enlace" to={{ recorridos }}>Consultar los recorridos con el cierre</AtlasLink>
      <p className="suave">Horarios de estación · <AtlasLink to={{ selection: { type: 'nodo', id: from } }}>{from_name}</AtlasLink> · <AtlasLink to={{ selection: { type: 'nodo', id: to } }}>{to_name}</AtlasLink></p>
    </section>
  )
}
