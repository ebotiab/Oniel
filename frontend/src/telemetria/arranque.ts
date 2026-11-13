// Errores del visor en Logfire: solo errores, solo en producción y solo si hay token.
//
// Lo que se envía es una excepción no controlada o una promesa rechazada sin atender, con su traza,
// la ruta del visor en la que ocurrió y los datos del navegador que anota el SDK (docs/despliegue.md,
// «Errores del visor»). Una visita sin errores no envía nada.
//
// Este fichero es lo único que va en el arranque: decide si se envía y, si es que sí, guarda los
// errores que ocurran mientras llega el SDK, que se descarga aparte (`./logfire`) para no retrasar
// el primer pintado.

/** Token público de la aplicación web `oniel-visor` de Logfire. Sin él no se envía nada. */
const token = (import.meta.env.VITE_LOGFIRE_TOKEN as string | undefined) ?? ''
/** Entorno del despliegue de Vercel (`production`, `preview`); lo fija vite.config.ts al compilar. */
const entorno = (import.meta.env.VITE_ENTORNO as string | undefined) ?? ''
/** Commit que compila Vercel; es la versión con la que llegan los errores. */
const commit = (import.meta.env.VITE_COMMIT as string | undefined) ?? ''

export interface ErrorCapturado {
  /** El nombre con el que llega a Logfire; son los que usa el SDK. */
  nombre: 'Uncaught error' | 'Unhandled promise rejection'
  error: unknown
  /** Ruta del visor (`/tramo/<id>`), sin parámetros ni fragmento. */
  ruta: string
}

/**
 * Solo envía el visor publicado en producción: ni el servidor de desarrollo, ni las pruebas, ni las
 * vistas previas de Vercel. Como las tres condiciones se conocen al compilar, sin ellas el SDK no
 * llega siquiera a formar parte de lo que se publica.
 */
const activa = import.meta.env.PROD && entorno === 'production' && token !== ''

/** Tope de errores guardados mientras llega el SDK; un fallo en bucle no debe llenar la memoria. */
const MAX_EN_ESPERA = 10

export function iniciarTelemetria(): void {
  if (!activa) return
  const enEspera: ErrorCapturado[] = []
  let enviar = (capturado: ErrorCapturado) => {
    if (enEspera.length < MAX_EN_ESPERA) enEspera.push(capturado)
  }
  const capturar = (nombre: ErrorCapturado['nombre'], error: unknown) =>
    enviar({ nombre, error, ruta: window.location.pathname })
  // Sin fase de captura: un recurso que no carga (una imagen, una tesela) no llega a `window`.
  window.addEventListener('error', (e) => capturar('Uncaught error', (e.error as unknown) ?? e.message))
  window.addEventListener('unhandledrejection', (e) => capturar('Unhandled promise rejection', e.reason as unknown))
  import('./logfire')
    .then(({ configurar }) => {
      enviar = configurar({ token, entorno, commit })
      for (const capturado of enEspera.splice(0)) enviar(capturado)
    })
    .catch(() => {
      // Si el SDK no llega (sin red, un bloqueador), el visor sigue igual y no se envía nada.
      enviar = () => undefined
      enEspera.length = 0
    })
}
