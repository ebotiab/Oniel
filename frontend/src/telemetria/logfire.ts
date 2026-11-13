// El SDK de Logfire para el navegador, en un fichero aparte que solo se descarga cuando el visor
// publicado tiene token (./arranque.ts). Las opciones son las de la documentación de
// @pydantic/logfire-browser 0.35 (en beta): al subir de versión hay que releerla.

import { configureFrontend, reportError } from '@pydantic/logfire-browser'

import type { ErrorCapturado } from './arranque'

/** Región US, la del proyecto `oniel`. */
const LOGFIRE_URL = 'https://logfire-us.pydantic.dev'

interface Opciones {
  token: string
  entorno: string
  commit: string
}

/** Configura el SDK una sola vez y devuelve la función que envía un error. */
export function configurar({ token, entorno, commit }: Opciones): (capturado: ErrorCapturado) => void {
  configureFrontend({
    baseUrl: LOGFIRE_URL,
    // Token restringido de la aplicación web: solo puede enviar como `oniel-visor`, que es de donde
    // sale el nombre del servicio. No es el token de escritura de la API.
    token,
    // Perfil de solo errores: sin Web Vitals, sin métricas y sin carga de página.
    profile: 'errors',
    // Sin instrumentación automática: no se tocan `fetch` ni los clics. Con ella, cada sondeo de
    // /healthz que no responde mientras Render despierta la API llegaría como un error.
    autoInstrumentations: false,
    // Sin identificador de sesión: no se guarda nada en el navegador de quien visita.
    rum: { session: false, webVitals: false },
    // Los errores los recoge ./arranque.ts desde antes de que llegue este fichero, con la ruta del visor.
    captureGlobalErrors: false,
    serviceVersion: commit || undefined,
    // configureFrontend no admite `environment`; el entorno va como atributo del recurso, con el
    // mismo nombre que usa el backend (`deployment_environment` en las consultas).
    resourceAttributes: { 'deployment.environment.name': entorno },
  })
  return ({ nombre, error, ruta }) => reportError(nombre, error, { 'logfire.page.url.path': ruta })
}
