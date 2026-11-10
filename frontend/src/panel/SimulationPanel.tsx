import { useState, type FormEvent } from 'react'

import { ApiError, simulateClosure } from '../data/api'
import { useApiStatus } from '../data/useApiStatus'
import type { ClosureResult, ClosureStatus, InterruptionOut, SegmentOut } from '../data/types'
import { formatDateLong, mainSourceLabel } from '../app/interruptions'
import { formatKm, productLabel, shortStop, todayIso } from '../app/state'
import { StatusBadge } from './KindBadge'
import { STATUS } from './labels'

interface Props {
  segment: SegmentOut
  referenceDate: string | null
  feedStart: string | null
  feedEnd: string | null
  /** Interrupciones del servicio vigentes hoy en el tramo que se va a cerrar. */
  interruptions: InterruptionOut[]
  result: ClosureResult | null
  onResult: (r: ClosureResult | null) => void
  onBack: () => void
}

const ORDER: ClosureStatus[] = ['afectado_publicado', 'afectado_estimado', 'indeterminado', 'no_afectado']

export function SimulationPanel({ segment, referenceDate, feedStart, feedEnd, interruptions, result, onResult, onBack }: Props) {
  const [date, setDate] = useState(() => result?.request.date ?? referenceDate ?? todayIso())
  const [start, setStart] = useState(result?.request.start.slice(0, 5) ?? '08:00')
  const [end, setEnd] = useState(result?.request.end.slice(0, 5) ?? '09:00')
  const [loading, setLoading] = useState(false)
  const [error, setError] = useState<string | null>(null)
  const [openMethod, setOpenMethod] = useState(false)
  const [open, setOpen] = useState<Record<string, boolean>>({ afectado_publicado: true, afectado_estimado: true, indeterminado: true })
  const status = useApiStatus()

  async function submit(e: FormEvent) {
    e.preventDefault()
    setLoading(true)
    setError(null)
    try {
      onResult(await simulateClosure({ segment_id: segment.id, date, start, end }))
    } catch (err) {
      onResult(null)
      setError(err instanceof ApiError ? err.message : 'No se pudo calcular la simulación.')
    } finally {
      setLoading(false)
    }
  }

  const affected = result ? result.counts.afectado_publicado + result.counts.afectado_estimado : 0

  return (
    <section className="detalle simulacion" aria-labelledby="sim-titulo" data-testid="panel-simulacion">
      <button type="button" className="enlace volver" onClick={onBack}>
        ← Volver al tramo
      </button>
      <p className="sobre">Cierre hipotético · {formatKm(segment.length_km)} km</p>
      <h2 id="sim-titulo" className="titulo">
        {segment.from_name} – {segment.to_name}
      </h2>
      <p className="texto suave">
        Elige un día y una franja. Oniel compara la ventana con la hora en que cada tren recorre el tramo y distingue
        horarios publicados, pasos estimados y casos indeterminados.
      </p>
      {/* antes de calcular: el tramo ya está interrumpido hoy; con resultado, lo dice el propio resultado */}
      {!result &&
        interruptions.map((i) => (
          <p key={i.id} className="nota-horario" data-testid="sim-interrumpido">
            Este tramo ya está sin circulación desde el {formatDateLong(i.start_date)} ({mainSourceLabel(i)}). La simulación se calcula sobre el
            horario publicado.
          </p>
        ))}

      <form className="formulario" onSubmit={submit}>
        <label>
          <span>Día</span>
          <input type="date" value={date} min={feedStart ?? undefined} max={feedEnd ?? undefined} onChange={(e) => setDate(e.target.value)} required data-testid="sim-fecha" />
        </label>
        <div className="fila">
          <label>
            <span>Desde</span>
            <input type="time" value={start} onChange={(e) => setStart(e.target.value)} required data-testid="sim-inicio" />
          </label>
          <label>
            <span>Hasta</span>
            <input type="time" value={end} onChange={(e) => setEnd(e.target.value)} required data-testid="sim-fin" />
          </label>
        </div>
        <button type="submit" className="boton primario" disabled={loading} data-testid="sim-calcular">
          {loading ? 'Calculando…' : 'Calcular el efecto del cierre'}
        </button>
      </form>
      {status === 'buscando' && (
        <p className="suave" role="status">
          El servidor de Oniel se está despertando; la simulación se calculará en cuanto responda.
        </p>
      )}
      {error && (
        <p className="aviso" role="alert">
          {error}
        </p>
      )}

      {result && (
        <div className="resultado" data-testid="sim-resultado" aria-live="polite">
          <p className="resumen">
            <strong>{affected}</strong> {affected === 1 ? 'tren afectado' : 'trenes afectados'} de {result.items.length} que recorren el tramo el{' '}
            {result.window_label}
            {result.counts.indeterminado ? `, y ${result.counts.indeterminado} ${result.counts.indeterminado === 1 ? 'indeterminado' : 'indeterminados'}` : ''}.
          </p>
          {result.interruptions?.map((i) => (
            <p key={i.id} className="nota-horario" data-testid="sim-resultado-interrumpido">
              Ese día el tramo ya está interrumpido. {i.schedule_note}
            </p>
          ))}
          {result.alternatives.length > 0 && (
            <aside className="alternativa" aria-label="Recorrido alternativo" data-testid="sim-alternativa">
              <p className="sobre">Recorrido alternativo cargado en Oniel</p>
              {result.alternatives.map((a) => (
                <p key={a.line_id} className="texto">
                  Entre <strong>{a.from_name}</strong> y <strong>{a.to_name}</strong> existe otra línea: {a.line_name.charAt(0).toLowerCase() + a.line_name.slice(1)}
                  {a.via.length ? `, por ${a.via.join(', ')}` : ''}. Son {formatKm(a.length_km)} km frente a {formatKm(a.closed_line_length_km)} km por la línea cerrada
                  {a.single_track_km > 0 ? `, con ${formatKm(a.single_track_km)} km de vía única` : ''}. Oniel no reasigna los trenes afectados; solo señala que la alternativa existe.
                  {a.interruptions?.map((i) => (
                    <span key={i.id} data-testid="sim-alternativa-interrumpida">
                      {' '}
                      Ese día no está disponible: no hay circulación entre {i.from_name} y {i.to_name} desde el {formatDateLong(i.start_date)} (
                      {mainSourceLabel(i)}).
                    </span>
                  ))}
                </p>
              ))}
            </aside>
          )}
          <ul className="contadores">
            {ORDER.map((s) => (
              <li key={s} className={STATUS[s].cls}>
                <strong className="datos">{result.counts[s]}</strong> {STATUS[s].plural.toLowerCase()}
              </li>
            ))}
          </ul>
          {ORDER.map((status) => {
            const items = result.items.filter((i) => i.status === status)
            if (!items.length) return null
            const isOpen = open[status] ?? false
            return (
              <div key={status} className="grupo">
                <button type="button" className="grupo-cabecera" aria-expanded={isOpen} onClick={() => setOpen({ ...open, [status]: !isOpen })}>
                  <StatusBadge status={status} />
                  <span className="datos">{items.length}</span>
                  <span className="chevron" aria-hidden="true">
                    {isOpen ? '−' : '+'}
                  </span>
                </button>
                {isOpen && (
                  <ol className="lista-servicios">
                    {items.map((i) => (
                      <li key={`${i.service.id}-${i.enter}`}>
                        <span className="hora datos">
                          {i.enter ?? '—'}
                          {i.exit ? `–${i.exit}` : ''}
                        </span>
                        <span className="tren">
                          <strong>
                            {productLabel(i.service.product)} {i.service.train_number}
                          </strong>{' '}
                          <span className="suave">
                            {shortStop(i.service.origin_name)} → {shortStop(i.service.destination_name)}
                            {i.from_previous_day ? ' · salió el día anterior' : ''}
                          </span>
                          <details className="porque">
                            <summary>Por qué</summary>
                            <p>{i.explanation}</p>
                          </details>
                        </span>
                      </li>
                    ))}
                  </ol>
                )}
              </div>
            )
          })}
          <button type="button" className="enlace" aria-expanded={openMethod} onClick={() => setOpenMethod(!openMethod)}>
            {openMethod ? 'Ocultar el método' : 'Cómo se calcula'}
          </button>
          {openMethod && (
            <div className="metodo">
              <p className="texto">{result.method}</p>
              <ul className="lista-simple">
                {result.caveats.map((c) => (
                  <li key={c} className="suave">
                    {c}
                  </li>
                ))}
              </ul>
            </div>
          )}
        </div>
      )}
    </section>
  )
}
