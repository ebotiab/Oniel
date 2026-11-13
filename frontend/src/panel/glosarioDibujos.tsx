// Los dibujos de los conceptos del glosario: unas viñetas por concepto, en SVG, con el vocabulario del mapa.
// La vía es tinta con trazos de papel, el tren es una pastilla de papel con borde de tinta y el color solo
// aparece en las señales (rojo, cerrada; verde, abierta), que es lo que significa en la vía. Cada viñeta
// lleva al lado su frase (`pasos` en `glosario.ts`): el dibujo no afirma nada que el texto no diga.
// Todas comparten un lienzo de 400 unidades de ancho, para que el trazo pese lo mismo de una a otra.

import type { ReactNode } from 'react'

import type { ConceptoId } from './glosario'

const ANCHO = 400
type Color = 'roja' | 'verde'

/** Una vía a lo largo de un camino: doble, con los trazos clásicos; única, más fina y con los trazos espaciados. */
function Via({ d, unica = false }: { d: string; unica?: boolean }) {
  return (
    <>
      <path d={d} fill="none" stroke="var(--tinta)" strokeWidth={unica ? 2.4 : 3.4} />
      <path d={d} fill="none" stroke="var(--papel)" strokeWidth={unica ? 1.2 : 1.7} strokeDasharray={unica ? '2 12' : '2 6'} strokeDashoffset={-3} />
    </>
  )
}

/** Un tren sobre la vía, con el morro redondeado hacia donde va. `cabina` pinta en el morro lo que repite la cabina. */
function Tren({ x, y, sentido = 1, cabina }: { x: number; y: number; sentido?: 1 | -1; cabina?: Color }) {
  const largo = 54
  const cola = sentido === 1 ? x : x + largo
  const s = sentido
  return (
    <>
      <path
        d={`M${cola} ${y - 7} h${s * (largo - 10)} q${s * 10} 0 ${s * 10} 7 q0 7 ${-s * 10} 7 h${-s * (largo - 10)} z`}
        fill="var(--papel)"
        stroke="var(--tinta)"
        strokeWidth={2}
        strokeLinejoin="round"
      />
      <path d={`M${cola + s * 7} ${y - 1.5} h${s * (largo - (cabina ? 28 : 22))}`} stroke="var(--tinta)" strokeWidth={2} strokeDasharray="6 3" />
      {cabina && <circle cx={cola + s * (largo - 9)} cy={y} r={3.2} fill={`var(--senal-${cabina})`} />}
    </>
  )
}

/** Una señal junto a la vía: un poste y un foco. Sin color, no dice nada (apagada). */
function Senal({ x, y, color }: { x: number; y: number; color?: Color }) {
  return (
    <>
      <path d={`M${x} ${y - 5} v-17`} stroke="var(--tinta)" strokeWidth={1.6} />
      <circle cx={x} cy={y - 28} r={6.5} fill={color ? `var(--senal-${color})` : 'var(--papel)'} stroke="var(--tinta)" strokeWidth={1.6} />
      {!color && <path d={`M${x - 3.2} ${y - 31.2} l6.4 6.4 m0 -6.4 l-6.4 6.4`} stroke="var(--tinta-2)" strokeWidth={1.4} />}
    </>
  )
}

/** El límite entre dos cantones. */
function Limite({ x, y }: { x: number; y: number }) {
  return <path d={`M${x} ${y - 14} v28`} stroke="var(--tinta-3)" strokeWidth={1} strokeDasharray="2 3" />
}

/** Un trecho de vía marcado con el fondo hundido: el cantón ocupado. */
function Banda({ x1, x2, y }: { x1: number; x2: number; y: number }) {
  return <rect x={x1} y={y - 14} width={x2 - x1} height={28} fill="var(--papel-3)" />
}

function Vineta({ alto = 86, children }: { alto?: number; children: ReactNode }) {
  return (
    <svg className="glosario-dibujo" viewBox={`0 0 ${ANCHO} ${alto}`} aria-hidden="true">
      {children}
    </svg>
  )
}

/** Tres cantones seguidos, con la señal de entrada del segundo y del tercero; `ocupado` es el que lleva la banda. */
function Cantones({ detras, delante, ocupado, senales }: { detras: number; delante: number; ocupado: [number, number]; senales: [Color, Color] }) {
  const y = 60
  return (
    <Vineta>
      <Banda x1={ocupado[0]} x2={ocupado[1]} y={y} />
      <Via d={`M0 ${y} H${ANCHO}`} />
      <Limite x={130} y={y} />
      <Limite x={250} y={y} />
      <Senal x={130} y={y} color={senales[0]} />
      <Senal x={250} y={y} color={senales[1]} />
      <Tren x={detras} y={y} />
      <Tren x={delante} y={y} />
    </Vineta>
  )
}

/** Una vía única con una estación de dos vías en el centro. */
function Cruce({ children }: { children: ReactNode }) {
  const y = 64
  return (
    <Vineta>
      <Via d={`M0 ${y} H${ANCHO}`} unica />
      <Via d={`M96 ${y} L122 ${y - 28} H278 L304 ${y}`} unica />
      {children}
    </Vineta>
  )
}

/** Un carril visto de frente, apoyado en la traviesa: cabeza, alma y patín. `x` es su cara interior y `lado` hacia dónde queda el resto del carril. */
function Carril({ x, y, lado }: { x: number; y: number; lado: 1 | -1 }) {
  const c = x + lado * 4
  return (
    <path
      d={`M${c - 4} ${y - 16} h8 v5 h-2.6 v7.5 h6.6 v3.5 h-16 v-3.5 h6.6 v-7.5 h-2.6 z`}
      fill="var(--tinta)"
    />
  )
}

/** Una cota entre dos caras interiores de carril, con su medida encima. */
function Cota({ x1, x2, y, texto }: { x1: number; x2: number; y: number; texto: string }) {
  return (
    <>
      <path d={`M${x1} ${y} H${x2} M${x1} ${y - 4} v8 M${x2} ${y - 4} v8`} stroke="var(--tinta-2)" strokeWidth={1} />
      <text x={(x1 + x2) / 2} y={y - 6} textAnchor="middle">
        {texto}
      </text>
    </>
  )
}

/** Un eje del tren visto de frente: dos ruedas que pisan los carriles, con la pestaña por dentro, unidas por el eje. */
function Eje({ x1, x2, y }: { x1: number; x2: number; y: number }) {
  const pisa = y - 16
  const rueda = (x: number, lado: 1 | -1) => {
    const [a, b] = [x, x + lado * 13].sort((m, n) => m - n) as [number, number]
    const [p, q] = [x, x - lado * 3.5].sort((m, n) => m - n) as [number, number]
    return (
      <>
        <rect x={p} y={pisa - 14} width={q - p} height={19} fill="var(--tinta)" />
        <rect x={a} y={pisa - 40} width={b - a} height={40} rx={1.5} fill="var(--papel)" stroke="var(--tinta)" strokeWidth={1.6} />
      </>
    )
  }
  return (
    <>
      <path d={`M${x1 - 4} ${pisa - 20} H${x2 + 4}`} stroke="var(--tinta)" strokeWidth={4} />
      {rueda(x1, -1)}
      {rueda(x2, 1)}
    </>
  )
}

/** La vía vista de frente, a escala: 1.668 mm son 250 unidades. `IZQ` es la cara interior del carril de la izquierda. */
const MM = 250 / 1668
const IZQ = 75
const IBERICO = IZQ + 1668 * MM
const ESTANDAR = IZQ + 1435 * MM

/** La traviesa y un carril en cada cara interior de `caras`: el de la izquierda mira a la derecha y los demás, al revés. */
function Seccion({ caras, alto = 104, children }: { caras: readonly number[]; alto?: number; children?: ReactNode }) {
  const y = alto - 14
  return (
    <Vineta alto={alto}>
      <rect x={34} y={y} width={332} height={9} fill="var(--papel-3)" stroke="var(--tinta-3)" strokeWidth={1} />
      {caras.map((x, i) => (
        <Carril key={x} x={x} y={y} lado={i === 0 ? -1 : 1} />
      ))}
      {children}
    </Vineta>
  )
}
/** Las viñetas de cada concepto, en el orden de sus frases. `Record` obliga a que ninguno se quede sin dibujo. */
const DIBUJOS: Record<ConceptoId, readonly (() => ReactNode)[]> = {
  'anchos-de-via': [
    () => <Seccion caras={[IZQ, IBERICO]}>
      <Eje x1={IZQ} x2={IBERICO} y={90} />
      <Cota x1={IZQ} x2={IBERICO} y={20} texto="1.668 mm" />
    </Seccion>,
    () => <Seccion caras={[IZQ, ESTANDAR]}>
      <Eje x1={IZQ} x2={ESTANDAR} y={90} />
      <Cota x1={IZQ} x2={ESTANDAR} y={20} texto="1.435 mm" />
    </Seccion>,
    () => <Seccion caras={[IZQ, ESTANDAR, IBERICO]}>
      <Cota x1={IZQ} x2={IBERICO} y={30} texto="1.668 mm, ancho ibérico" />
      <Cota x1={IZQ} x2={ESTANDAR} y={60} texto="1.435 mm, ancho estándar" />
    </Seccion>,
  ],
  'como-se-separan-los-trenes': [
    () => <Cantones detras={14} delante={150} ocupado={[130, 250]} senales={['roja', 'verde']} />,
    () => <Cantones detras={72} delante={190} ocupado={[130, 250]} senales={['roja', 'verde']} />,
    () => <Cantones detras={72} delante={292} ocupado={[250, ANCHO]} senales={['verde', 'roja']} />,
  ],
  'cruces-en-via-unica': [
    () => <Cruce>
      <Tren x={8} y={64} />
      <Tren x={338} y={64} sentido={-1} />
    </Cruce>,
    () => <Cruce>
      <Senal x={266} y={36} color="roja" />
      <Tren x={190} y={36} />
      <Tren x={318} y={64} sentido={-1} />
    </Cruce>,
    () => <Cruce>
      <Senal x={266} y={36} color="verde" />
      <Tren x={204} y={36} />
      <Tren x={20} y={64} sentido={-1} />
    </Cruce>,
  ],
  'marcha-a-la-vista': [
    () => <Vineta>
      <Via d={`M0 60 H${ANCHO}`} />
      <Senal x={210} y={60} />
      <Tren x={140} y={60} />
    </Vineta>,
    () => <Vineta>
      {/* lo que el maquinista ve por delante: un abanico desde el morro del tren */}
      <path d="M144 60 L262 36 V84 Z" fill="var(--papel-3)" />
      <Via d={`M0 60 H${ANCHO}`} />
      <Tren x={90} y={60} />
      <path d="M147 76 v5 H259 v-5" fill="none" stroke="var(--tinta-3)" strokeWidth={1} />
    </Vineta>,
  ],
  'quien-dirige-la-circulacion': [
    () => <Vineta alto={132}>
      <path d="M200 34 V52 H88 V73 M200 52 H218 V73 M200 52 H348 V73" fill="none" stroke="var(--tinta-3)" strokeWidth={1} strokeDasharray="2 3" />
      <rect x={136} y={8} width={128} height={26} rx={2} fill="var(--papel)" stroke="var(--tinta)" strokeWidth={1.6} />
      <text x={200} y={25.5} textAnchor="middle">
        puesto de mando
      </text>
      <Via d={`M0 108 H${ANCHO}`} />
      {[70, 200, 330].map((x, i) => (
        <g key={x}>
          <Senal x={x + 18} y={108} color={i === 0 ? 'roja' : 'verde'} />
          <circle cx={x} cy={108} r={5} fill="var(--papel)" stroke="var(--tinta)" strokeWidth={2.5} />
        </g>
      ))}
      <Tren x={100} y={108} />
    </Vineta>,
  ],
  'sistemas-que-vigilan-al-tren': [
    () => <Vineta>
      <Via d={`M0 60 H${ANCHO}`} />
      <Senal x={262} y={60} color="roja" />
      <Tren x={150} y={60} cabina="roja" />
    </Vineta>,
    () => <Vineta>
      {/* la velocidad a la que puede ir en cada punto, como un techo sobre la vía */}
      <path d={`M0 26 H190 L262 44 H${ANCHO}`} fill="none" stroke="var(--tinta-2)" strokeWidth={1.5} strokeDasharray="5 4" />
      <text x={6} y={15}>velocidad a la que puede ir</text>
      <Via d={`M0 66 H${ANCHO}`} />
      <Tren x={120} y={66} />
    </Vineta>,
  ],
}

/** La viñeta de un paso de un concepto. */
export function Dibujo({ concepto, paso }: { concepto: ConceptoId; paso: number }) {
  return DIBUJOS[concepto][paso]?.() ?? null
}
