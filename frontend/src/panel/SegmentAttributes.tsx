import { attributeRows, type SegmentAttribute } from '../app/segmentAttributes'
import type { LineSummary, SegmentOut } from '../data/types'
import { Termino } from './Termino'

interface Props {
  segment: SegmentOut
  line: LineSummary | undefined
  lugar: SegmentAttribute['lugar']
}

/** Las filas de los atributos de un tramo para un sitio de la ficha; van dentro de una lista `dl`. */
export function FilasAtributos({ segment, line, lugar }: Props) {
  return (
    <>
      {attributeRows(segment, line, lugar).map(({ atributo, valor }) => {
        const texto = valor ? atributo.formato(valor.value) : atributo.sinDato
        const termino = valor ? atributo.termino?.(valor.value) : undefined
        return (
          <div key={atributo.clave}>
            <dt>{atributo.terminoEtiqueta ? <Termino id={atributo.terminoEtiqueta}>{atributo.etiqueta}</Termino> : atributo.etiqueta}</dt>
            <dd data-testid={atributo.testId ?? `tramo-atributo-${atributo.clave}`}>{termino ? <Termino id={termino}>{texto}</Termino> : texto}</dd>
          </div>
        )
      })}
    </>
  )
}
