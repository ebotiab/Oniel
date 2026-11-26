import '@fontsource-variable/archivo/wdth.css'
// La hoja de MapLibre va aquí, antes que las del visor, y no con el mapa (que se carga aparte): las
// reglas del visor que la corrigen (.mapa, la posición de los controles) tienen que ir después.
import 'maplibre-gl/dist/maplibre-gl.css'
import { StrictMode } from 'react'
import { createRoot } from 'react-dom/client'

import App from './app/App'
import { legacyHashPath } from './app/state'
import './index.css'
import { iniciarTelemetria } from './telemetria/arranque'
import { iniciarVisitas } from './telemetria/visitas'

// Antes que nada, para no perder un error del propio arranque. No hace nada fuera de producción o sin token.
iniciarTelemetria()
// El recuento de visitas, también solo en producción. Va antes de leer la ruta porque retira de la
// dirección el parámetro con el que un navegador deja de contarse.
iniciarVisitas()

// Un enlace antiguo (`/#/tramo/<id>`) pasa a su dirección limpia antes de que el visor lea la ruta, sin recargar.
const limpia = legacyHashPath(window.location.hash)
if (limpia !== null) window.history.replaceState(null, '', limpia + window.location.search)

const root = document.getElementById('root')!
createRoot(root).render(
  <StrictMode>
    <App />
  </StrictMode>,
)
// React puede hacer su primer pintado después de DOMContentLoaded. Conserva el estado de carga
// hasta que ese pintado sustituya los hijos de #root. Si el módulo falla, queda la lectura.
root.querySelector('.inicio-estatico')?.classList.add('montando')
