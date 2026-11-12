// Glosario del visor: los términos técnicos que aparecen en las fichas, con una definición de una o dos
// frases, y los conceptos que hacen falta para entender la red, en unos párrafos y con su referencia.
// Las definiciones son propias, en español llano y tono neutro: explican, no reproducen el texto citado.
// Un término nuevo en una ficha entra aquí y se muestra con el componente `Termino`.

import type { NodeKind } from '../data/types.ts'

interface DefTermino {
  /** Como se titula en el glosario y en la nota. */
  nombre: string
  /** Una o dos frases: lo que basta para seguir leyendo. */
  breve: string
  /** Entradas relacionadas (términos o conceptos), por su id. */
  ver?: readonly string[]
}

interface DefConcepto {
  titulo: string
  parrafos: readonly string[]
  /** De dónde sale: una fuente de `sources.json` y los artículos consultados. */
  referencia: { sourceId: string; titulo: string; cita: string }
  ver?: readonly string[]
}

/** La fuente de los conceptos de circulación en `backend/data/curated/sources.json`. */
const RCF = { sourceId: 'boe-reglamento-circulacion-ferroviaria', titulo: 'Reglamento de Circulación Ferroviaria (Real Decreto 664/2015)' }

const TERMINOS = {
  'administrador-de-infraestructura': {
    nombre: 'Administrador de infraestructura',
    breve:
      'La entidad dueña de las vías y de las estaciones: las construye, las mantiene y dirige la circulación de los trenes de todos los operadores. En España son Adif y Adif Alta Velocidad.',
    ver: ['operador', 'quien-dirige-la-circulacion'],
  },
  'alta-velocidad': {
    nombre: 'Línea de alta velocidad',
    breve: 'Línea construida para que los trenes circulen a 250 km/h o más, con curvas muy amplias y, en España, ancho de vía estándar.',
    ver: ['linea-convencional', 'ancho-de-via'],
  },
  'ancho-de-via': {
    nombre: 'Ancho de vía',
    breve:
      'La distancia entre los dos carriles. La red convencional española usa el ancho ibérico (1.668 mm) y la alta velocidad, el ancho estándar europeo (1.435 mm): un tren solo pasa de una a otra si está preparado para cambiar de ancho.',
    ver: ['cambiador-de-ancho'],
  },
  bifurcacion: {
    nombre: 'Bifurcación',
    breve: 'Punto de una línea donde empieza otra o se juntan varias. Allí un tren puede pasar de una línea a otra.',
  },
  'cambiador-de-ancho': {
    nombre: 'Cambiador de ancho',
    breve:
      'Instalación por la que los trenes preparados para ello pasan despacio mientras la separación de sus ruedas se ajusta al otro ancho de vía. Así un mismo tren puede circular por la alta velocidad y por la red convencional.',
    ver: ['ancho-de-via'],
  },
  'cierre-hipotetico': {
    nombre: 'Cierre hipotético',
    breve:
      'Un supuesto para explorar la red: qué trenes del horario pasarían por un tramo si se cerrara un día, a unas horas. No es un aviso ni una previsión.',
    ver: ['sin-circulacion'],
  },
  electrificacion: {
    nombre: 'Electrificación',
    breve:
      'La forma en que la línea da corriente a los trenes eléctricos, por el cable que va sobre la vía (la catenaria). En España la alta velocidad usa 25.000 voltios en corriente alterna («25 kV») y la mayor parte de la red convencional, 3.000 voltios en corriente continua («3 kV CC»).',
  },
  estacion: {
    nombre: 'Estación',
    breve: 'Lugar con vías y andenes donde los trenes paran para que suban y bajen los viajeros.',
  },
  'horario-publicado': {
    nombre: 'Horario publicado',
    breve:
      'El que cada operador anuncia con antelación: qué trenes hay y a qué hora paran en cada estación. Dice lo que está previsto, no lo que ocurre cada día: no recoge retrasos ni cancelaciones.',
    ver: ['paso-publicado', 'operador'],
  },
  'linea-convencional': {
    nombre: 'Línea convencional',
    breve:
      'Línea de la red que ya existía antes de la alta velocidad, de ancho ibérico. La comparten trenes de media y larga distancia, cercanías y mercancías, a velocidades más bajas.',
    ver: ['alta-velocidad', 'ancho-de-via'],
  },
  operador: {
    nombre: 'Operador',
    breve:
      'La empresa que pone los trenes y vende los billetes. Por una misma línea pueden circular trenes de varios: en la alta velocidad española, Renfe, Ouigo e Iryo.',
    ver: ['administrador-de-infraestructura'],
  },
  paet: {
    nombre: 'PAET (puesto de adelantamiento y estacionamiento de trenes)',
    breve:
      'Punto de la línea con vías de apartado, donde un tren puede detenerse para que otro lo adelante o esperar el tiempo que haga falta. Es una instalación técnica: los viajeros no suben ni bajan en ella.',
    ver: ['como-se-separan-los-trenes'],
  },
  'paso-estimado': {
    nombre: 'Paso estimado',
    breve:
      'El tren no para en alguno de los extremos del tramo, así que Oniel calcula a qué hora lo recorre repartiendo el tiempo entre sus dos paradas más cercanas. La hora lleva un margen de error.',
    ver: ['paso-publicado', 'paso-indeterminado'],
  },
  'paso-indeterminado': {
    nombre: 'Paso indeterminado',
    breve:
      'Oniel no puede fijar a qué hora recorre el tren el tramo, porque alguna de sus paradas queda fuera de las líneas cargadas. En una simulación, también el tren cuyo paso solo roza la franja del cierre dentro del margen de error.',
    ver: ['paso-estimado'],
  },
  'paso-publicado': {
    nombre: 'Paso publicado',
    breve: 'La hora a la que el tren recorre el tramo sale directamente del horario, porque para en las dos estaciones que lo delimitan.',
    ver: ['horario-publicado', 'paso-estimado'],
  },
  'puesto-de-banalizacion': {
    nombre: 'Puesto de banalización',
    breve:
      'Punto de una línea de vía doble con desvíos para pasar de una vía a la otra. Permite que los trenes circulen por cualquiera de las dos vías en los dos sentidos, por ejemplo para sortear un trecho en obras.',
    ver: ['via-doble'],
  },
  'punto-de-referencia': {
    nombre: 'Punto de referencia',
    breve: 'Un lugar de la línea donde hoy no para ningún tren y que Oniel señala porque ayuda a situarse: por ejemplo, donde la vía pasa de única a doble.',
  },
  'punto-kilometrico': {
    nombre: 'Punto kilométrico',
    breve:
      'La distancia medida a lo largo de la vía desde el origen de la línea, en kilómetros. Sirve para situar cualquier punto de la línea: una estación, una señal o una obra.',
  },
  'sin-circulacion': {
    nombre: 'Sin circulación',
    breve:
      'Tramo por el que hoy no pasan trenes, por una obra o por una incidencia, según la fuente que se cita. El horario publicado puede seguir incluyendo trenes que no están circulando.',
    ver: ['horario-publicado', 'cierre-hipotetico'],
  },
  tramo: {
    nombre: 'Tramo',
    breve:
      'Trozo de una línea entre dos puntos consecutivos de los que Oniel tiene cargados: dos estaciones, o una estación y un puesto o una bifurcación. Es la unidad con la que Oniel cuenta los trenes y simula los cierres.',
  },
  'tren-directo': {
    nombre: 'Tren directo',
    breve: 'El que para en las dos estaciones, en ese sentido: se va de una a otra sin cambiar de tren.',
  },
  'velocidad-habitual': {
    nombre: 'Velocidad habitual',
    breve:
      'La velocidad a la que Oniel supone que se recorre el tramo cuando el tren no para en él. Se usa para estimar tiempos y horas de paso; no es un horario.',
    ver: ['velocidad-maxima', 'paso-estimado'],
  },
  'velocidad-maxima': {
    nombre: 'Velocidad máxima',
    breve: 'La mayor velocidad a la que se permite circular por el tramo. No todos los trenes la alcanzan: depende también del tren y de sus paradas.',
    ver: ['velocidad-habitual'],
  },
  'via-doble': {
    nombre: 'Vía doble',
    breve: 'Dos vías, por lo general una para cada sentido: los trenes que van en sentidos contrarios no tienen que esperarse.',
    ver: ['via-unica'],
  },
  'via-unica': {
    nombre: 'Vía única',
    breve:
      'Una sola vía para los dos sentidos. Dos trenes que van en sentidos contrarios solo pueden cruzarse donde hay más de una vía, en una estación o en un apartadero, así que uno espera al otro.',
    ver: ['cruces-en-via-unica', 'via-doble'],
  },
} as const satisfies Record<string, DefTermino>

const CONCEPTOS = {
  'como-se-separan-los-trenes': {
    titulo: 'Cómo se separan los trenes: bloqueo y cantón',
    parrafos: [
      'Un tren no puede frenar en poco espacio: según su velocidad, necesita cientos de metros o varios kilómetros para detenerse. Por eso no basta con que el maquinista vea al tren de delante, como en una carretera.',
      'La vía se divide en trozos llamados cantones. En condiciones normales, en un cantón no puede haber más de un tren a la vez: hasta que el primero no lo ha dejado libre, el siguiente no recibe permiso para entrar.',
      'El bloqueo es el sistema que lo garantiza y que impide, además, que dos trenes circulen por la misma vía en sentidos contrarios. En las líneas principales es automático: la propia vía detecta el tren y las señales que protegen el cantón se cierran solas. Donde no lo hay, las estaciones de los dos extremos se ponen de acuerdo por teléfono antes de dar paso a cada tren.',
    ],
    referencia: { ...RCF, cita: 'artículo 1.1.1.3, definiciones de bloqueo y de cantón de bloqueo, y artículo 1.1.1.4, tipos de bloqueo' },
    ver: ['cruces-en-via-unica', 'marcha-a-la-vista'],
  },
  'cruces-en-via-unica': {
    titulo: 'Vía única: cómo se cruzan los trenes',
    parrafos: [
      'En un tramo de vía única, los trenes de los dos sentidos comparten una sola vía. Dos trenes que van en sentidos contrarios solo pueden cruzarse donde hay más de una vía: en una estación o en un apartadero. Uno entra, se detiene y espera a que el otro pase.',
      'Entre dos de esos puntos, el bloqueo solo deja entrar un tren: mientras el trecho está ocupado, el que viene de frente no recibe permiso para salir.',
      'Una vía única admite menos trenes que una doble, y el retraso de uno se traslada al que lo espera. En el mapa de Oniel es el trazo más fino, y el comparador de recorridos dice cuántos kilómetros de vía única tiene cada camino.',
    ],
    referencia: { ...RCF, cita: 'artículo 1.1.1.3, definiciones de bloqueo y de línea' },
    ver: ['via-unica', 'como-se-separan-los-trenes'],
  },
  'marcha-a-la-vista': {
    titulo: 'Marcha a la vista',
    parrafos: [
      'Es una forma de circular que se ordena al maquinista cuando el sistema habitual no puede asegurar que la vía está libre, por ejemplo tras una avería en las señales.',
      'El tren avanza con precaución y a una velocidad que le permita detenerse dentro del trecho de vía que el maquinista ve por delante. La seguridad pasa a depender de lo que se ve, así que se circula despacio.',
    ],
    referencia: { ...RCF, cita: 'artículo 1.5.1.4, condiciones de marcha especiales' },
    ver: ['como-se-separan-los-trenes'],
  },
  'quien-dirige-la-circulacion': {
    titulo: 'Quién dirige la circulación: puesto de mando y control centralizado',
    parrafos: [
      'Los trenes de todos los operadores circulan con el permiso del administrador de la infraestructura. Lo da desde los puestos de mando: centros desde los que se sigue y se regula el tráfico en tiempo real.',
      'Las líneas principales tienen control de tráfico centralizado (CTC): desde un puesto central se manejan a distancia las señales y los desvíos de muchas estaciones y de los trayectos entre ellas, sin que tenga que haber una persona en cada una.',
    ],
    referencia: { ...RCF, cita: 'artículo 1.1.1.3, definiciones de puesto de mando y de control de tráfico centralizado' },
    ver: ['administrador-de-infraestructura'],
  },
  'sistemas-que-vigilan-al-tren': {
    titulo: 'Sistemas que vigilan al tren: ASFA, LZB y ERTMS',
    parrafos: [
      'Además de las señales que ve el maquinista, el tren lleva sistemas que repiten o sustituyen esas señales en la cabina y que actúan si no se atienden.',
      'El ASFA repite en la cabina lo que indican las señales de la vía y frena el tren en algunos casos, como al rebasar una señal que ordena parar. El LZB y el ERTMS supervisan el tren de forma continua: saben en cada momento a qué velocidad puede ir y lo frenan si la supera. El ERTMS es el sistema europeo común.',
      'La velocidad máxima a la que se permite circular por una línea depende también del sistema con el que esté equipada.',
    ],
    referencia: { ...RCF, cita: 'artículo 1.1.1.4, abreviaturas ASFA, ERTMS y LZB, y artículo 1.1.1.7' },
    ver: ['velocidad-maxima', 'como-se-separan-los-trenes'],
  },
} as const satisfies Record<string, DefConcepto>

export type TerminoId = keyof typeof TERMINOS
export type ConceptoId = keyof typeof CONCEPTOS

export interface Termino extends DefTermino {
  id: TerminoId
}

export interface Concepto extends DefConcepto {
  id: ConceptoId
}

/** Los conceptos, en el orden en que conviene leerlos. */
export const conceptos: Concepto[] = (Object.keys(CONCEPTOS) as ConceptoId[]).map((id) => ({ id, ...CONCEPTOS[id] }))

/** Los términos, por orden alfabético de su nombre. */
export const terminos: Termino[] = (Object.keys(TERMINOS) as TerminoId[])
  .map((id) => ({ id, ...TERMINOS[id] }))
  .sort((a, b) => a.nombre.localeCompare(b.nombre, 'es'))

export function termino(id: TerminoId): Termino {
  return { id, ...TERMINOS[id] }
}

/** El título de una entrada cualquiera, sea término o concepto; nulo si el id no existe. */
export function tituloDe(id: string): string | null {
  if (id in TERMINOS) return TERMINOS[id as TerminoId].nombre
  if (id in CONCEPTOS) return CONCEPTOS[id as ConceptoId].titulo
  return null
}

/** El término que define cada tipo de punto de la red. */
export const TERMINO_DE_NODO: Record<NodeKind, TerminoId> = {
  estacion: 'estacion',
  paet: 'paet',
  pb: 'puesto-de-banalizacion',
  bifurcacion: 'bifurcacion',
  cambiador: 'cambiador-de-ancho',
  referencia: 'punto-de-referencia',
}
