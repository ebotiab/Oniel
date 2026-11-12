import { useState } from 'react'

import type { Destination, NetworkOut, Operator } from '../data/types'
import { formatDate, listaEs, productLabel, shortStop } from '../app/state'

/** Destinos a la vista antes de «Ver los … restantes»: los más frecuentes caben sin desplazar el panel. */
const A_LA_VISTA = 6

interface Props {
  /** Destinos directos del día, del más frecuente al menos. */
  destinations: Destination[]
  date: string
  network: NetworkOut
  operators: Operator[]
  /** Operadores de las líneas de la estación que no publican sus horarios: sus trenes faltan. */
  missing: Operator[]
  /** Hay alguna interrupción vigente en la red: los destinos son los del horario publicado. */
  interrupted: boolean
  onSelectNode: (id: string) => void
}

/** «de 07:55 a 22:01», o «a las 08:12» si solo hay una salida. */
function horas(d: Destination): string {
  return d.first_departure === d.last_departure ? `a las ${d.first_departure}` : `de ${d.first_departure} a ${d.last_departure}`
}

/**
 * A dónde se llega desde una estación sin cambiar de tren: cada destino con sus trenes del día, el
 * tipo de servicio y entre qué horas salen. Los destinos que están en la red cargada son enlaces.
 */
export function DirectDestinations({ destinations, date, network, operators, missing, interrupted, onSelectNode }: Props) {
  const [todos, setTodos] = useState(false)
  const enLaRed = new Set(network.nodes.map((n) => n.id))
  const operatorName = (id: string) => operators.find((o) => o.id === id)?.name ?? id
  // El operador solo se nombra si desde aquí salen trenes de más de uno.
  const variosOperadores = new Set(destinations.flatMap((d) => d.operators.map((o) => o.operator_id))).size > 1
  const visibles = todos ? destinations : destinations.slice(0, A_LA_VISTA)
  const resto = destinations.length - A_LA_VISTA

  return (
    <div data-testid="destinos-directos">
      <h3 className="subtitulo">
        Destinos directos
        <span className="datos suave">
          {' '}
          · {destinations.length} el {formatDate(date)}
        </span>
      </h3>
      {destinations.length === 0 ? (
        <p className="suave">Ningún tren con viajeros sale de aquí hacia otra estación en el horario de ese día.</p>
      ) : (
        <>
          <p className="texto">Estaciones a las que se llega desde aquí sin cambiar de tren, de la que tiene más trenes a la que menos.</p>
          {interrupted && (
            <p className="nota-horario" data-testid="destinos-nota-horario">
              Son los trenes del horario publicado: no descuenta los que hoy no circulan por una interrupción.
            </p>
          )}
          <ol className="lista-destinos" data-testid="lista-destinos">
            {visibles.map((d) => (
              <li key={d.node_id ?? d.stop_id}>
                <span className="destino">
                  {d.node_id && enLaRed.has(d.node_id) ? (
                    <button type="button" className="enlace" onClick={() => onSelectNode(d.node_id!)} data-testid={`destino-${d.node_id}`}>
                      {d.name}
                    </button>
                  ) : (
                    <strong>{shortStop(d.name)}</strong>
                  )}
                  <span className="suave">
                    {listaEs(d.products.map(productLabel))} · {horas(d)}
                    {variosOperadores ? ` · ${d.operators.map((o) => (d.operators.length > 1 ? `${operatorName(o.operator_id)} ${o.trains}` : operatorName(o.operator_id))).join(', ')}` : ''}
                  </span>
                </span>
                <span className="cuantos datos">{d.trains === 1 ? '1 tren' : `${d.trains} trenes`}</span>
              </li>
            ))}
          </ol>
          {resto > 0 && (
            <p className="texto">
              <button type="button" className="enlace" onClick={() => setTodos(!todos)} aria-expanded={todos} data-testid="destinos-ver-todos">
                {todos ? 'Ver solo los más frecuentes' : resto === 1 ? 'Ver el destino restante' : `Ver los ${resto} destinos restantes`}
              </button>
            </p>
          )}
          {missing.length > 0 && (
            <p className="suave destinos-nota" data-testid="destinos-sin-horarios">
              No están los trenes de {listaEs(missing.map((o) => o.name))}: no publica{missing.length > 1 ? 'n' : ''} sus horarios en un formato abierto.
            </p>
          )}
        </>
      )}
    </div>
  )
}
