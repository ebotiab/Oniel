import { useSyncExternalStore } from 'react'

import { apiStatus, onApiStatus, type ApiStatus } from './api'

/** Estado de la API (buscando, disponible o ausente) como valor reactivo. */
export function useApiStatus(): ApiStatus {
  return useSyncExternalStore(onApiStatus, apiStatus)
}
