import '@fontsource-variable/archivo/wdth.css'
// La hoja de MapLibre va aquí, antes que las del visor, y no con el mapa (que se carga aparte): las
// reglas del visor que la corrigen (.mapa, la posición de los controles) tienen que ir después.
import 'maplibre-gl/dist/maplibre-gl.css'
import { StrictMode } from 'react'
import { createRoot } from 'react-dom/client'

import App from './app/App'
import './index.css'

createRoot(document.getElementById('root')!).render(
  <StrictMode>
    <App />
  </StrictMode>,
)
