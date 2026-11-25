import type { ReactNode } from 'react'

import { abreAparte, navegar } from '../app/navegacion'
import { routePath, type Route } from '../app/state'
import './guide.css'

const STATIONS = [
  ['manzanares', 'Manzanares'],
  ['daimiel', 'Daimiel'],
  ['almagro', 'Almagro'],
  ['ciudad-real', 'Ciudad Real'],
] as const

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

export function GuidePage() {
  return (
    <div className="pagina" data-testid="pagina-guia">
      <main className="pagina-columna guia" id="guia-contenido" tabIndex={-1} aria-labelledby="guia-titulo">
        <h1 id="guia-titulo" className="pagina-titulo">Guía del atlas</h1>
        <p className="pagina-entrada">
          Oniel te ayuda a entender cómo está conectada la red ferroviaria española. El mapa sitúa cada línea
          en el territorio y el esquema te permite seguirla estación a estación. Las fichas reúnen lo que se conoce
          de cada línea y de dónde sale esa información. Para empezar, busca una estación que conozcas o prueba el siguiente recorrido.
        </p>

        <section className="guia-ejemplo" aria-labelledby="guia-linea">
          <div>
            <h2 id="guia-linea">De Manzanares a Ciudad Real</h2>
            <p>Lee el esquema de arriba abajo. Elige una estación para ver qué líneas llegan a ella y adónde puedes ir sin cambiar de tren.</p>
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

        <section className="guia-preguntas" aria-labelledby="guia-preguntas">
          <h2 id="guia-preguntas">¿Qué te gustaría descubrir?</h2>
          <ul>
            <li>
              <AtlasLink to={{ selection: { type: 'tramo', id: 'manzanares-ciudad-real:daimiel:almagro' } }}>¿Qué hay entre Daimiel y Almagro?</AtlasLink>
              <p>Abre el tramo que une las estaciones. Su ficha explica cómo es la vía y qué trenes tienen previsto pasar. También puedes probar un cierre hipotético.</p>
            </li>
            <li>
              <AtlasLink to={{ recorridos: { from: 'madrid-chamartin', to: 'valladolid-campo-grande' } }}>¿Por dónde se va de Madrid a Valladolid?</AtlasLink>
              <p>Compara el camino por Segovia con el de Ávila. Elige cada recorrido para verlo en el mapa y comparar su longitud.</p>
            </li>
          </ul>
        </section>

        <section className="guia-lectura" aria-labelledby="guia-datos">
          <h2 id="guia-datos">Cómo interpretar los datos</h2>
          <p>Los horarios describen el servicio previsto para el día que indica la ficha. Una conexión dibujada a trazos señala una parte de la red pendiente de incorporar.</p>
          <p>En <AtlasLink to={{ cobertura: true }}>Cobertura y fuentes</AtlasLink> puedes comprobar qué se ha documentado y en qué fecha. Si encuentras una palabra nueva, búscala en el <AtlasLink to={{ glosario: { entrada: null } }}>Glosario</AtlasLink>.</p>
        </section>
      </main>
    </div>
  )
}
