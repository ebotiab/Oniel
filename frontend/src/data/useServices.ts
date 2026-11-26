import { useEffect, useState } from 'react'

import { useApiStatus } from './useApiStatus'

// La ficha se monta con la clave de la estación o del tramo. Un cambio de origen o fecha
// conserva el horario visible mientras su día siga sirviendo para la consulta.
export function useServices<T extends { date: string }>(
  load: (id: string, date?: string) => Promise<T>, id: string, date: string | null, enabled = true,
) {
  const available = useApiStatus() === 'disponible'
  const [loaded, setLoaded] = useState<T | null>(null)
  const [failedDay, setFailedDay] = useState<string | null>()
  useEffect(() => {
    if (!enabled) return
    let active = true
    load(id, date ?? undefined)
      .then((data) => {
        if (active) {
          setLoaded(data)
          setFailedDay(undefined)
        }
      })
      .catch(() => { if (active) setFailedDay(date) })
    return () => { active = false }
  }, [load, id, date, enabled, available])

  const data = !date || loaded?.date === date ? loaded : null
  return { data, unavailable: !data && failedDay === date }
}
