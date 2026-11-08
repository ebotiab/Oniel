import { useCallback, useEffect, useMemo, useState } from 'react'

import { currentMode, detectMode, fetchCoverage, fetchNetwork, fetchSegmentCounts, type DataMode } from '../data/api'
import type { ClosureResult, CoverageOut, NetworkOut } from '../data/types'
import { MapView } from '../map/MapView'
import { CoveragePanel } from '../panel/CoveragePanel'
import { Legend } from '../panel/Legend'
import { LineOverview } from '../panel/LineOverview'
import { NodeDetail } from '../panel/NodeDetail'
import { SegmentDetail } from '../panel/SegmentDetail'
import { SimulationPanel } from '../panel/SimulationPanel'
import { parseHash, toHash, type Selection } from './state'
import './app.css'

function useMedia(query: string): boolean {
  const [matches, setMatches] = useState(() => window.matchMedia(query).matches)
  useEffect(() => {
    const mq = window.matchMedia(query)
    const onChange = () => setMatches(mq.matches)
    mq.addEventListener('change', onChange)
    return () => mq.removeEventListener('change', onChange)
  }, [query])
  return matches
}

export default function App() {
  const [network, setNetwork] = useState<NetworkOut | null>(null)
  const [coverage, setCoverage] = useState<CoverageOut | null>(null)
  const [mode, setMode] = useState<DataMode>('estatico')
  const [loadError, setLoadError] = useState<string | null>(null)
  const [route, setRoute] = useState(() => parseHash(window.location.hash))
  const [hoverId, setHoverId] = useState<string | null>(null)
  const [result, setResult] = useState<ClosureResult | null>(null)
  const [showCoverage, setShowCoverage] = useState(false)
  const [sheetOpen, setSheetOpen] = useState(false)
  const [counts, setCounts] = useState<Record<string, number> | null>(null)
  const mobile = useMedia('(max-width: 760px)')

  useEffect(() => {
    detectMode()
      .then(async (m) => {
        setMode(m)
        const [net, cov] = await Promise.all([fetchNetwork(), fetchCoverage()])
        setNetwork(net)
        setCoverage(cov)
        try {
          setCounts((await fetchSegmentCounts(cov.reference_date ?? undefined)).counts)
        } catch {
          /* los contadores son opcionales */
        }
      })
      .catch(() => setLoadError('No se ha podido cargar la red. Comprueba la conexión o el servidor de Oniel.'))
  }, [])

  // Sincronizar el hash con la selección
  useEffect(() => {
    const onHash = () => setRoute(parseHash(window.location.hash))
    window.addEventListener('hashchange', onHash)
    return () => window.removeEventListener('hashchange', onHash)
  }, [])
  useEffect(() => {
    const h = toHash(route)
    if (window.location.hash !== h) window.history.replaceState(null, '', h)
  }, [route])

  const select = useCallback((sel: Selection) => {
    setRoute({ selection: sel, simulacion: false })
    setResult(null)
    setShowCoverage(false)
    if (sel) setSheetOpen(true)
  }, [])

  const selection = route.selection
  const segment = useMemo(
    () => (selection?.type === 'tramo' ? network?.segments.find((s) => s.id === selection.id) ?? null : null),
    [network, selection],
  )
  const node = useMemo(
    () => (selection?.type === 'nodo' ? network?.nodes.find((n) => n.id === selection.id) ?? null : null),
    [network, selection],
  )
  const closedSegmentId = result && route.simulacion ? result.segment.id : null
  const referenceDate = coverage?.reference_date ?? null
  const padding = useMemo(() => (mobile ? { left: 0, bottom: sheetOpen ? Math.round(window.innerHeight * 0.48) : 120 } : { left: 440, bottom: 0 }), [mobile, sheetOpen])

  let panel: React.ReactNode = null
  if (loadError) panel = <p className="aviso">{loadError}</p>
  else if (!network) panel = <p className="suave cargando">Cargando la red…</p>
  else if (showCoverage && coverage) panel = <CoveragePanel coverage={coverage} mode={mode} onClose={() => setShowCoverage(false)} />
  else if (segment && route.simulacion)
    panel = (
      <SimulationPanel
        segment={segment}
        referenceDate={referenceDate}
        feedStart={coverage?.feed_start ?? null}
        feedEnd={coverage?.feed_end ?? null}
        result={result}
        onResult={setResult}
        onBack={() => setRoute({ selection, simulacion: false })}
      />
    )
  else if (segment)
    panel = (
      <SegmentDetail
        key={`${segment.id}@${referenceDate}`}
        segment={segment}
        network={network}
        referenceDate={referenceDate}
        onSimulate={() => setRoute({ selection, simulacion: true })}
        onSelectNode={(id) => select({ type: 'nodo', id })}
        onBack={() => select(null)}
      />
    )
  else if (node)
    panel = (
      <NodeDetail
        key={`${node.id}@${referenceDate}`}
        node={node}
        network={network}
        referenceDate={referenceDate}
        onSelectSegment={(id) => select({ type: 'tramo', id })}
        onBack={() => select(null)}
      />
    )
  else
    panel = (
      <LineOverview
        network={network}
        coverage={coverage}
        counts={counts}
        selection={selection}
        hoverId={hoverId}
        closedSegmentId={closedSegmentId}
        onSelect={select}
        onHover={setHoverId}
        compact={mobile}
      />
    )

  const lineLabel = network?.lines[0]?.name.replace('Línea de alta velocidad ', '') ?? 'Madrid – Sevilla'

  return (
    <div className={`app ${mobile ? 'movil' : 'escritorio'} ${sheetOpen ? 'hoja-abierta' : ''}`}>
      <a className="visually-hidden" href="#panel">
        Ir al panel de la línea
      </a>
      <MapView
        network={network}
        selection={selection}
        hoverId={hoverId}
        closedSegmentId={closedSegmentId}
        onSelect={select}
        onHover={setHoverId}
        padding={padding}
      />
      <header className="cabecera">
        <div className="marca-bloque">
          <span className="marca">Oniel</span>
          <span className="lema">Cómo está conectada la red ferroviaria</span>
        </div>
        <button type="button" className="cobertura-pill" onClick={() => setShowCoverage(true)} aria-haspopup="dialog" data-testid="boton-cobertura">
          <span className="punto" aria-hidden="true" />
          <span className="pill-texto">
            <span className="solo-escritorio">Disponible: </span>
            <strong>{lineLabel}</strong>
            <span className="solo-escritorio">, alta velocidad</span>
          </span>
          {coverage && <span className="datos suave solo-escritorio"> · {Math.round(coverage.total_length_km)} km · {coverage.station_count} estaciones</span>}
          {currentMode() === 'estatico' && network && <span className="senal gris">vista estática</span>}
        </button>
      </header>
      <aside id="panel" className="panel" aria-label="Panel de la línea">
        {mobile && (
          <button type="button" className="asa" aria-label={sheetOpen ? 'Reducir el panel' : 'Ampliar el panel'} onClick={() => setSheetOpen(!sheetOpen)}>
            <span />
          </button>
        )}
        <div className="panel-contenido">{panel}</div>
      </aside>
      {!mobile && <Legend closed={closedSegmentId !== null} />}
    </div>
  )
}
