import { useSyncExternalStore } from 'react'

import { todayIso } from './state'

const HOUR_MS = 60 * 60 * 1000

function subscribe(notify: () => void): () => void {
  let timer: number
  function sync() {
    // La medianoche peninsular siempre cae en una hora UTC en punto, incluso el día del cambio de hora.
    window.clearTimeout(timer)
    timer = window.setTimeout(sync, HOUR_MS - Date.now() % HOUR_MS)
    notify()
  }
  sync()
  document.addEventListener('visibilitychange', sync)
  window.addEventListener('pageshow', sync)
  return () => {
    window.clearTimeout(timer)
    document.removeEventListener('visibilitychange', sync)
    window.removeEventListener('pageshow', sync)
  }
}

/** React actualiza la vista cuando cambia el día de la red, también al recuperar una pestaña suspendida. */
export function useToday(): string {
  return useSyncExternalStore(subscribe, todayIso)
}
