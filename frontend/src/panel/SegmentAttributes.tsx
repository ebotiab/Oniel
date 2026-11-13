import { attributeRows, attributeSources, type SegmentAttribute } from '../app/segmentAttributes'
import { formatDateLong } from '../app/annotations'
import type { LineSummary, SegmentOut, Source } from '../data/types'
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

/** «A, B y C» con las etiquetas en minúscula salvo la primera. */
function enumerar(etiquetas: string[]): string {
  const dichas = etiquetas.map((e, i) => (i === 0 ? e : e.charAt(0).toLowerCase() + e.slice(1)))
  return dichas.length < 2 ? dichas.join('') : `${dichas.slice(0, -1).join(', ')} y ${dichas[dichas.length - 1]}`
}

/**
 * De dónde salen los atributos que la ficha enseña, a la vista o plegados, y cuándo se comprobaron: un
 * renglón por fuente, al pie de «Más detalle». No usa `PieFuente` porque la fecha es la de comprobación de
 * cada valor, no la de descarga de la fuente.
 */
export function FuentesAtributos({ segment, line, sources }: Omit<Props, 'lugar'> & { sources: Source[] }) {
  const fuentes = attributeSources([...attributeRows(segment, line, 'esencial'), ...attributeRows(segment, line, 'detalle')])
  if (!fuentes.length) return null
  return (
    <div className="pie-fuente" data-testid="atributos-fuente">
      {fuentes.map((f) => {
        const fuente = sources.find((s) => s.id === f.sourceId)
        return (
          <p key={f.sourceId} className="suave">
            {enumerar(f.etiquetas)}: {fuente?.url ? (
              <a href={fuente.url} target="_blank" rel="noreferrer">
                {fuente.publisher}
              </a>
            ) : (
              (fuente?.publisher ?? f.sourceId)
            )}
            {f.checkedOn ? `, comprobado el ${formatDateLong(f.checkedOn)}` : ''}. {fuente ? `${fuente.name}. ` : ''}
            <span className="datos">Identificador de la fuente: {f.sourceId}</span>
          </p>
        )
      })}
    </div>
  )
}
