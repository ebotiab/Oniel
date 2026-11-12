// Escenario: una lista de modificaciones sobre la red cargada (cerrar tramos, añadir un enlace
// esbozado entre dos nodos, cambiar la velocidad de un tramo). Es el mismo modelo y la misma cadena
// corta que `backend/src/oniel/routing/scenario.py`; la cadena va en la URL (`/escenario/<cadena>`)
// y en `GET /api/routes?scenario=`. Une las modificaciones con `;` y sus campos con `~`:
//
//   c~<tramo>                       cerrar un tramo
//   e~<nodo>~<nodo>~<km>~<km/h>     enlace esbozado entre dos nodos, con longitud y velocidad
//   v~<tramo>~<km/h>                cambiar la velocidad de un tramo

export interface SketchLink {
  from_node_id: string
  to_node_id: string
  length_km: number
  speed_kmh: number
}

export interface SpeedChange {
  segment_id: string
  speed_kmh: number
}

export interface Scenario {
  closures: string[]
  links: SketchLink[]
  speeds: SpeedChange[]
}

/** El escenario no se puede leer o no encaja con la red (tramo o nodo desconocido). */
export class ScenarioError extends Error {}

const ID = /^[a-z0-9][a-z0-9:-]*$/
const NUMBER = /^[0-9]+(\.[0-9]+)?$/

export function emptyScenario(): Scenario {
  return { closures: [], links: [], speeds: [] }
}

/** Escenario de una sola modificación: el cierre de un tramo. */
export function closureScenario(segmentId: string): Scenario {
  return { closures: [segmentId], links: [], speeds: [] }
}

export function linkId(link: SketchLink): string {
  return `enlace:${link.from_node_id}:${link.to_node_id}`
}

/** El mismo escenario con más tramos cerrados (por ejemplo, los interrumpidos un día). */
export function withClosures(scenario: Scenario, segmentIds: Iterable<string>): Scenario {
  const closures = [...scenario.closures]
  for (const id of segmentIds) if (!closures.includes(id)) closures.push(id)
  return { ...scenario, closures }
}

/** Cadena corta para la URL. */
export function scenarioToCode(scenario: Scenario): string {
  return [
    ...scenario.closures.map((s) => `c~${s}`),
    ...scenario.links.map((k) => `e~${k.from_node_id}~${k.to_node_id}~${k.length_km}~${k.speed_kmh}`),
    ...scenario.speeds.map((v) => `v~${v.segment_id}~${v.speed_kmh}`),
  ].join(';')
}

/** Lee la cadena corta. Una cadena vacía es el escenario sin modificaciones. */
export function scenarioFromCode(code: string): Scenario {
  const scenario = emptyScenario()
  for (const part of code.split(';').map((p) => p.trim())) {
    if (!part) continue
    const [kind, ...args] = part.split('~')
    const [a, b, c, d] = args
    if (kind === 'c' && args.length === 1) scenario.closures.push(identifier(a))
    else if (kind === 'e' && args.length === 4)
      scenario.links.push({ from_node_id: identifier(a), to_node_id: identifier(b), length_km: positive(c), speed_kmh: positive(d) })
    else if (kind === 'v' && args.length === 2) scenario.speeds.push({ segment_id: identifier(a), speed_kmh: positive(b) })
    else throw new ScenarioError(`No se entiende la modificación «${part}» del escenario`)
  }
  return scenario
}

function identifier(value: string | undefined): string {
  if (value === undefined || !ID.test(value)) throw new ScenarioError(`«${value}» no es un identificador de tramo o de nodo`)
  return value
}

function positive(value: string | undefined): number {
  if (value === undefined || !NUMBER.test(value)) throw new ScenarioError(`«${value}» no es un número`)
  const number = Number(value)
  if (number <= 0) throw new ScenarioError(`«${value}» tiene que ser un número mayor que cero`)
  return number
}
