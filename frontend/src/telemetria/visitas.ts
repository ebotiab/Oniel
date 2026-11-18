// Recuento de visitas con Vercel Web Analytics: solo en el visor publicado en producción.
//
// Sirve para saber si el visor se usa y qué se consulta: visitantes por día, páginas vistas, de dónde
// se llega, país y dispositivo (docs/despliegue.md, «Visitas del visor»). No usa cookies ni guarda nada
// en el navegador de quien visita, y de cada página vista solo sale la dirección sin parámetros ni
// fragmento. El script que cuenta lo sirve Vercel desde el propio dominio (`/_vercel/insights/`); aquí
// solo se decide si se carga y qué se deja fuera.

import { inject, type BeforeSendEvent } from '@vercel/analytics'

/** Entorno del despliegue de Vercel (`production`, `preview`); lo fija vite.config.ts al compilar. */
const entorno = (import.meta.env.VITE_ENTORNO as string | undefined) ?? ''

/**
 * Solo cuenta el visor publicado en producción: ni el servidor de desarrollo, ni las pruebas, ni las
 * vistas previas de Vercel. Las dos condiciones se conocen al compilar, así que sin ellas el recuento
 * no forma parte de lo que se publica.
 */
const activa = import.meta.env.PROD && entorno === 'production'

/** Marca de un navegador cuyas visitas no se cuentan; la pone y la quita quien mantiene Oniel. */
export const CLAVE_NO_CONTAR = 'oniel:visitas:no-contar'
/** Parámetro de la dirección que pone (`no`) o quita (`si`) la marca en este navegador. */
const PARAMETRO = 'visitas'

/** `localStorage` puede no estar (navegación privada, almacenamiento bloqueado): entonces no hay marca. */
function marcado(): boolean {
  try {
    return window.localStorage.getItem(CLAVE_NO_CONTAR) !== null
  } catch {
    return false
  }
}

/**
 * Abrir el visor con `?visitas=no` deja de contar las visitas de ese navegador, y con `?visitas=si`
 * vuelve a contarlas. El parámetro se retira de la dirección al momento: que desaparezca es la señal
 * de que se ha aplicado.
 */
function aplicarParametro(): void {
  const direccion = new URL(window.location.href)
  const valor = direccion.searchParams.get(PARAMETRO)
  if (valor !== 'no' && valor !== 'si') return
  try {
    if (valor === 'no') window.localStorage.setItem(CLAVE_NO_CONTAR, '1')
    else window.localStorage.removeItem(CLAVE_NO_CONTAR)
  } catch {
    // Sin almacenamiento no hay dónde guardar la marca; el visor sigue igual.
  }
  direccion.searchParams.delete(PARAMETRO)
  window.history.replaceState(window.history.state, '', direccion.pathname + direccion.search + direccion.hash)
}

/**
 * Lo que no es una visita: un navegador marcado y el navegador integrado de la app de Claude, con el
 * que las sesiones de desarrollo abren producción. Los navegadores automáticos (Playwright, los que se
 * anuncian como `Headless`) los descarta el propio script de Vercel.
 */
function excluida(): boolean {
  return marcado() || /\bClaude\//.test(window.navigator.userAgent)
}

/** De cada página vista sale el origen y la ruta (`/tramo/<id>`), sin parámetros ni fragmento. */
function alEnviar(evento: BeforeSendEvent): BeforeSendEvent | null {
  if (excluida()) return null
  const direccion = new URL(evento.url)
  return { ...evento, url: direccion.origin + direccion.pathname }
}

export function iniciarVisitas(): void {
  if (!activa) return
  aplicarParametro()
  inject({ mode: 'production', beforeSend: alEnviar })
}
