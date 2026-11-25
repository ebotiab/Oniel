import { useLayoutEffect, useRef, type ReactNode, type RefObject } from 'react'

import { abreAparte, navegar } from '../app/navegacion'
import { routePath, type Route } from '../app/state'
import './guide.css'

const STATIONS = [
  ['manzanares', 'Manzanares'],
  ['daimiel', 'Daimiel'],
  ['almagro', 'Almagro'],
  ['ciudad-real', 'Ciudad Real'],
] as const

const EXAMPLE_SEGMENT = { type: 'tramo', id: 'manzanares-ciudad-real:daimiel:almagro' } as const

/** Conserva el lugar de lectura mientras se prueban las vistas del atlas, sin guardarlo entre sesiones. */
export interface GuidePosition {
  scrollTop: number
  linkIndex: number | null
  open: string[]
}

function AtlasLink({ to, children, className }: { to: Partial<Route>; children: ReactNode; className?: string }) {
  const href = routePath({ selection: null, simulacion: false, ...to })
  return (
    <a href={href} className={className} onClick={(event) => {
      if (abreAparte(event)) return
      event.preventDefault()
      navegar(href)
    }}>
      {children}
    </a>
  )
}

export function GuidePage({ position }: { position: RefObject<GuidePosition> }) {
  const page = useRef<HTMLDivElement>(null)
  useLayoutEffect(() => {
    const element = page.current!
    const saved = position.current
    for (const detail of element.querySelectorAll('details')) detail.open = saved.open.includes(detail.id)
    element.scrollTop = saved.scrollTop
    const links = Array.from(element.querySelectorAll('a'))
    if (saved.linkIndex !== null) links[saved.linkIndex]?.focus({ preventScroll: true })
    return () => {
      saved.scrollTop = element.scrollTop
      saved.open = Array.from(element.querySelectorAll('details[open]'), detail => detail.id)
      const focused = document.activeElement
      saved.linkIndex = focused instanceof HTMLAnchorElement && element.contains(focused) ? links.indexOf(focused) : null
    }
  }, [position])

  return (
    <div ref={page} className="pagina" data-testid="pagina-guia">
      <main className="pagina-columna guia" id="guia-contenido" tabIndex={-1} aria-labelledby="guia-titulo">
        <h1 id="guia-titulo" className="pagina-titulo">Guía del atlas</h1>
        <p className="pagina-entrada">Descubre por dónde van las vías, qué estaciones unen y qué trenes tienen previstos los horarios. Empieza con una línea de cuatro estaciones.</p>

        <section className="guia-ejemplo" aria-labelledby="guia-linea">
          <div>
            <h2 id="guia-linea">De Manzanares a Ciudad Real</h2>
            <p>En el mapa, la vía pasa por Daimiel y gira hacia Almagro. En el esquema, esas mismas estaciones están en una recta: sigue su orden de arriba abajo. Arriba no significa norte.</p>
            <AtlasLink className="guia-accion" to={{ linea: 'manzanares-ciudad-real' }}>Ver la línea en el mapa <span aria-hidden="true">→</span></AtlasLink>
          </div>
          <ol className="guia-estaciones" aria-label="Estaciones de la línea, en orden">
            {STATIONS.map(([id, name]) => (
              <li key={id}>
                <AtlasLink to={{ selection: { type: 'nodo', id } }}>{name}</AtlasLink>
              </li>
            ))}
          </ol>
        </section>
        <p className="guia-vuelta">Puedes tocar una estación o la vía entre dos estaciones en el mapa o en el esquema. En móvil, el esquema está debajo del mapa; recoge el panel para ver más mapa. Para seguir leyendo, vuelve a <strong>Guía</strong> en la cabecera (en móvil, dentro de <strong>Menú</strong>) o usa Atrás.</p>

        <section className="guia-preguntas" aria-labelledby="guia-preguntas">
          <h2 id="guia-preguntas">¿Qué te gustaría descubrir?</h2>
          <p>Abre solo la pregunta que te interese. Cada ejemplo te lleva a una vista del atlas.</p>

          <details id="guia-por-donde">
            <summary><h3>¿Por dónde pasa esta línea?</h3></summary>
            <div className="guia-respuesta">
              <p>Localiza Almagro: en el mapa está al sur de Daimiel y Ciudad Real. El esquema endereza el trazado para que puedas seguir las estaciones sin perderte entre las curvas.</p>
              <p>Los círculos son estaciones; la vía entre dos puntos es un tramo. Las barras junto a los tramos cuentan trenes del día indicado, no trenes que estén pasando ahora. El azul señala lo que has elegido.</p>
              <AtlasLink to={{ linea: 'manzanares-ciudad-real' }}>Seguir Manzanares – Ciudad Real</AtlasLink>
            </div>
          </details>
          <details id="guia-estacion">
            <summary><h3>¿Adónde puedo ir desde una estación?</h3></summary>
            <div className="guia-respuesta">
              <p>Abre Daimiel y busca <strong>Destinos directos</strong>. Encontrarás Alcázar de San Juan, que no es una de las cuatro estaciones del esquema: un tren puede continuar por otras líneas sin que cambies de tren.</p>
              <p>El esquema muestra la vía; los destinos muestran los servicios del horario cargado. Que dos estaciones estén unidas por vías no asegura un tren directo entre ellas.</p>
              <AtlasLink to={{ selection: { type: 'nodo', id: 'daimiel' } }}>Consultar los destinos de Daimiel</AtlasLink>
            </div>
          </details>
          <details id="guia-tramo">
            <summary><h3>¿Qué hay entre Daimiel y Almagro?</h3></summary>
            <div className="guia-respuesta">
              <p>Fíjate en <strong>Vía única</strong>: los trenes de ambos sentidos comparten una sola vía. No significa que solo circulen en un sentido.</p>
              <p>En <strong>Trenes que lo recorren</strong>, lee la explicación de las horas: si el tren para en los dos extremos, Oniel usa su horario; si no, calcula su paso. «Estimado» no quiere decir retrasado.</p>
              <AtlasLink to={{ selection: EXAMPLE_SEGMENT }}>Ver el tramo Daimiel – Almagro</AtlasLink>
            </div>
          </details>
          <details id="guia-comparar">
            <summary><h3>¿Qué cambia entre estos dos recorridos?</h3></summary>
            <div className="guia-respuesta">
              <p>De Madrid-Chamartín a Valladolid puedes comparar la alta velocidad por Segovia con la línea convencional por Ávila. Elige cada recorrido: cambiará el trazado resaltado en el mapa.</p>
              <p>Mira los kilómetros y el tiempo <strong>sin paradas</strong>: sirven para comparar caminos. La frase sobre <strong>trenes directos</strong> cuenta lo que ofrece el horario. Un camino dibujado no garantiza un servicio que lo recorra entero, ni ese tiempo es la duración de un viaje.</p>
              <AtlasLink to={{ recorridos: { from: 'madrid-chamartin', to: 'valladolid-campo-grande' } }}>Comparar Madrid – Valladolid</AtlasLink>
            </div>
          </details>
          <details id="guia-horarios">
            <summary><h3>¿De qué fecha son estos horarios?</h3></summary>
            <div className="guia-respuesta">
              <p>Al pie de una ficha verás «Trenes del…» y «horarios descargados el…». La primera fecha es el día que se cuenta; la segunda dice cuándo se obtuvo el fichero. No tienen por qué coincidir con hoy.</p>
              <p>En <strong>Cobertura y fuentes</strong>, busca <strong>Operadores de trenes</strong>: cada uno indica la validez de sus horarios, quién los publica y la fecha de descarga. En <strong>Fuentes y licencias</strong> puedes abrir el documento de origen.</p>
              <p>Un horario publicado describe lo previsto. Oniel no muestra la posición en directo de un tren ni confirma sus retrasos. Antes de viajar, consulta al operador; una interrupción puede impedir un servicio que todavía figure en el horario.</p>
              <AtlasLink to={{ cobertura: true }}>Consultar fechas y fuentes de los horarios</AtlasLink>
            </div>
          </details>
        </section>

        <section className="guia-lectura" aria-labelledby="guia-alcance">
          <h2 id="guia-alcance">Hasta dónde llega el atlas</h2>
          <p>Oniel reúne trazados, estaciones y horarios para entender cómo se conecta la red. Documenta las líneas cargadas: que algo no aparezca aquí no significa que no exista.</p>
          <p>Por ejemplo, desde Ciudad Real sale una conexión gris a trazos hacia Mérida: señala una línea pendiente de cargar, no una vía cerrada. En <AtlasLink to={{ cobertura: true }}>Cobertura y fuentes</AtlasLink>, compara <strong>Líneas cargadas</strong> con <strong>Pendiente de cargar</strong>. Las fuentes de una ficha están en <strong>Más detalle</strong>.</p>
          <p>Si una palabra te frena, toca su subrayado de puntos para leer la definición. El <AtlasLink to={{ glosario: { entrada: null } }}>Glosario</AtlasLink> añade dibujos: <AtlasLink to={{ glosario: { entrada: 'cruces-en-via-unica' } }}>cómo se cruzan dos trenes en vía única</AtlasLink> ayuda a entender el tramo de Daimiel a Almagro.</p>
        </section>

        <details className="guia-opcional" id="guia-cierre">
          <summary><span className="guia-opcional-rotulo">Exploración opcional</span><h2>¿Y si se cerrara un tramo?</h2></summary>
          <div className="guia-respuesta">
            <p>Prueba con Daimiel – Almagro: elige un día y una franja horaria para ver qué trenes quedarían afectados y si tendrían otro camino en las líneas cargadas.</p>
            <p>Es un <strong>cierre hipotético</strong>, no un aviso de una incidencia real. El resultado no decide cómo se reorganizaría el servicio y puede faltar un camino que exista fuera de la cobertura de Oniel.</p>
            <AtlasLink to={{ selection: EXAMPLE_SEGMENT, simulacion: true }}>Probar un cierre hipotético</AtlasLink>
          </div>
        </details>
      </main>
    </div>
  )
}
