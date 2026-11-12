import { Fragment } from 'react'

import type { ConnectionOut, NodeKind, NodeOut } from '../data/types'
import { TERMINO_DE_NODO } from './glosario'
import { Termino } from './Termino'

interface Props {
  /** Los puntos de la línea que dibuja el esquema. */
  nodes: NodeOut[]
  connections: ConnectionOut[]
}

type Simbolo = 'estacion' | 'puesto' | 'bifurcacion' | 'conexion'

/** Los puestos técnicos que el esquema dibuja con un rombo, con el nombre corto que lleva la clave. */
const PUESTOS: [NodeKind, string][] = [
  ['paet', 'PAET'],
  ['pb', 'puesto de banalización'],
  ['cambiador', 'cambiador de ancho'],
]

/** Un símbolo con el mismo dibujo que en el esquema: círculo hueco, rombo, punto o trazo oblicuo. */
function Muestra({ simbolo }: { simbolo: Simbolo }) {
  return (
    <svg className="clave-simbolo" width={16} height={16} viewBox="0 0 16 16" aria-hidden="true">
      {simbolo === 'estacion' && <circle cx={8} cy={8} r={5} fill="var(--papel)" stroke="var(--tinta)" strokeWidth={2.5} />}
      {simbolo === 'puesto' && <rect x={3.5} y={3.5} width={9} height={9} fill="var(--tinta)" transform="rotate(45 8 8)" />}
      {simbolo === 'bifurcacion' && <circle cx={8} cy={8} r={3.5} fill="var(--tinta)" />}
      {simbolo === 'conexion' && <path d="M1 13 L15 4" stroke="var(--tinta-3)" strokeWidth={2.5} strokeDasharray="3 3" fill="none" />}
    </svg>
  )
}

/**
 * Clave de los símbolos del esquema, justo debajo de él: cada símbolo con su nombre, que es un término
 * del glosario. Solo lleva los símbolos que tiene la línea que se está viendo.
 */
export function ClaveEsquema({ nodes, connections }: Props) {
  const tipos = new Set(nodes.map((n) => n.kind))
  const puestos = PUESTOS.filter(([kind]) => tipos.has(kind))
  const enLinea = new Set(nodes.map((n) => n.id))
  const conConexion = tipos.has('bifurcacion') || connections.some((c) => enLinea.has(c.node_id))
  return (
    <ul className="clave-esquema" aria-label="Símbolos del esquema" data-testid="clave-esquema">
      {tipos.has('estacion') && (
        <li>
          <Muestra simbolo="estacion" />
          <Termino id="estacion">Estación</Termino>
        </li>
      )}
      {puestos.length > 0 && (
        <li>
          <Muestra simbolo="puesto" />
          <span>
            Puesto técnico:{' '}
            {puestos.map(([kind, nombre], i) => (
              <Fragment key={kind}>
                {i > 0 && (i === puestos.length - 1 ? ' o ' : ', ')}
                <Termino id={TERMINO_DE_NODO[kind]}>{nombre}</Termino>
              </Fragment>
            ))}
          </span>
        </li>
      )}
      {tipos.has('referencia') && (
        <li>
          <Muestra simbolo="puesto" />
          <Termino id="punto-de-referencia">Punto de referencia</Termino>
        </li>
      )}
      {tipos.has('bifurcacion') && (
        <li>
          <Muestra simbolo="bifurcacion" />
          <Termino id="bifurcacion">Bifurcación</Termino>
        </li>
      )}
      {conConexion && (
        <li>
          <Muestra simbolo="conexion" />
          <span>Conexión con otra línea</span>
        </li>
      )}
    </ul>
  )
}
