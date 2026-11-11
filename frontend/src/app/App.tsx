import { useCallback, useEffect, useMemo, useState } from 'react'

import { apiStatus, fetchCoverage, fetchNetwork, fetchSegmentCounts, onApiStatus, wakeApi, type ApiStatus, type DataMode } from '../data/api'
import { useApiStatus } from '../data/useApiStatus'
import type { ClosureResult, CoverageOut, NetworkOut } from '../data/types'
import type { Trazo } from '../map/layers'
import { MapView } from '../map/MapView'
import { CoveragePanel } from '../panel/CoveragePanel'
import { Legend } from '../panel/Legend'
import { LineOverview } from '../panel/LineOverview'
import { NetworkOverview } from '../panel/NetworkOverview'
import { NodeDetail } from '../panel/NodeDetail'
import { SegmentDetail } from '../panel/SegmentDetail'
import { SimulationPanel } from '../panel/SimulationPanel'
import { SearchBox } from '../panel/SearchBox'
import { activeInterruptions, bySegment } from './interruptions'
import type { SearchTarget } from './search'
import { networkCount, parseHash, toHash, todayIso, type Selection } from './state'
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
  const [loadError, setLoadError] = useState<string | null>(null)
  const [highlight, setHighlight] = useState<Trazo | null>(null)
  const [route, setRoute] = useState(() => parseHash(window.location.hash))
  const [hoverId, setHoverId] = useState<string | null>(null)
  const [result, setResult] = useState<ClosureResult | null>(null)
  const [showCoverage, setShowCoverage] = useState(() => Boolean(parseHash(window.location.hash).cobertura))
  const [sheetOpen, setSheetOpen] = useState(false)
  const [counts, setCounts] = useState<Record<string, number> | null>(null)
  const [activeLineId, setActiveLineId] = useState<string | null>(() => parseHash(window.location.hash).linea ?? null)
  const mobile = useMedia('(max-width: 760px)')
  const status = useApiStatus()

  // Arranque: la instantánea estática pinta la red enseguida; la API, cuando responde, la sustituye.
  useEffect(() => {
    let cancelled = false
    let fromApi = false
    let staticFailed = false
    const fail = () => setLoadError('No se ha podido cargar la red. Comprueba la conexión o el servidor de Oniel.')
    const load = async (source: DataMode) => {
      const [net, cov] = await Promise.all([fetchNetwork(source), fetchCoverage(source)])
      let counts: Record<string, number> | null = null
      try {
        counts = (await fetchSegmentCounts(cov.reference_date ?? undefined, source)).counts
      } catch {
        /* los contadores son opcionales */
      }
      return { net, cov, counts }
    }
    const apply = (d: Awaited<ReturnType<typeof load>>) => {
      setNetwork(d.net)
      setCoverage(d.cov)
      setCounts(d.counts)
      setLoadError(null)
    }
    load('estatico')
      .then((d) => {
        if (!cancelled && !fromApi) apply(d)
      })
      .catch(() => {
        staticFailed = true
        if (!cancelled && apiStatus() === 'ausente') fail()
      })
    const onStatus = (s: ApiStatus) => {
      if (cancelled) return
      if (s === 'disponible') {
        load('api')
          .then((d) => {
            if (cancelled) return
            fromApi = true
            apply(d)
          })
          .catch(() => {
            if (!cancelled && staticFailed) fail()
          })
      } else if (s === 'ausente' && staticFailed) fail()
    }
    const off = onApiStatus(onStatus)
    if (apiStatus() === 'disponible') onStatus('disponible')
    else void wakeApi()
    return () => {
      cancelled = true
      off()
    }
  }, [])

  // Sincronizar el hash con la selección
  useEffect(() => {
    const onHash = () => {
      const r = parseHash(window.location.hash)
      setRoute(r)
      setShowCoverage(Boolean(r.cobertura))
      // Sin selección manda la URL: #/ es la vista de la red. Con selección, la línea sale de lo seleccionado.
      if (!r.selection && !r.cobertura) setActiveLineId(r.linea ?? null)
    }
    window.addEventListener('hashchange', onHash)
    return () => window.removeEventListener('hashchange', onHash)
  }, [])
  // La línea a la vista y el panel de cobertura también van en la URL: toda vista se puede enlazar.
  useEffect(() => {
    const h = toHash({ ...route, linea: activeLineId, cobertura: showCoverage })
    if (window.location.hash !== h) window.history.replaceState(null, '', h)
  }, [route, activeLineId, showCoverage])

  const select = useCallback(
    (sel: Selection) => {
      setRoute({ selection: sel, simulacion: false })
      setResult(null)
      setShowCoverage(false)
        if (sel) setSheetOpen(true)
      if (sel && network) {
        const line = sel.type === 'tramo' ? network.segments.find((s) => s.id === sel.id)?.line_id : undefined
        const lines = sel.type === 'nodo' ? network.nodes.filter((n) => n.id === sel.id).map((n) => n.line_id) : []
        setActiveLineId((cur) => line ?? (lines.length ? (cur && lines.includes(cur) ? cur : lines[0]!) : cur))
      }
    },
    [network],
  )

  // El buscador lleva a un punto de la red, como al tocarlo en el mapa, o pone una línea en el panel.
  const showLine = useCallback((id: string | null) => {
    setActiveLineId(id)
    setRoute({ selection: null, simulacion: false })
    setResult(null)
    setShowCoverage(false)
    setSheetOpen(true)
  }, [])
  const pick = useCallback((target: SearchTarget) => (target.type === 'nodo' ? select(target) : showLine(target.id)), [select, showLine])

  const selection = route.selection
  const segment = useMemo(
    () => (selection?.type === 'tramo' ? network?.segments.find((s) => s.id === selection.id) ?? null : null),
    [network, selection],
  )
  const node = useMemo(
    () => (selection?.type === 'nodo' ? network?.nodes.find((n) => n.id === selection.id) ?? null : null),
    [network, selection],
  )

  // El esquema del panel sigue a la selección: un tramo o un nodo de otra línea muestran esa línea.
  // Un nodo común a varias líneas (Madrid, Córdoba) conserva la línea que ya estaba a la vista.
  const nodeLines = useMemo(() => (node && network ? network.nodes.filter((n) => n.id === node.id).map((n) => n.line_id) : []), [network, node])
  const lineId =
    segment?.line_id ??
    (nodeLines.length ? (activeLineId && nodeLines.includes(activeLineId) ? activeLineId : nodeLines[0]!) : null) ??
    (activeLineId && (!network || network.lines.some((l) => l.id === activeLineId)) ? activeLineId : null)
  const closedSegmentId = result && route.simulacion ? result.segment.id : null
  // Interrupciones vigentes hoy: se marcan en rojo en el mapa y en el esquema, y se explican en el panel.
  const today = useMemo(() => todayIso(), [])
  const interruptions = useMemo(() => activeInterruptions(network, today), [network, today])
  const interrupted = useMemo(() => bySegment(interruptions), [interruptions])
  const referenceDate = coverage?.reference_date ?? null
  const padding = useMemo(() => (mobile ? { left: 0, bottom: sheetOpen ? Math.round(window.innerHeight * 0.48) : 120 } : { left: 440, bottom: 0 }), [mobile, sheetOpen])

  // «Toda la línea» vuelve a la línea que se estaba viendo, también si se llegó por un enlace directo.
  const backToLine = () => {
    if (lineId) setActiveLineId(lineId)
    select(null)
  }

  let panel: React.ReactNode = null
  if (loadError) panel = <p className="aviso">{loadError}</p>
  else if (!network) panel = <p className="suave cargando">Cargando la red…</p>
  else if (showCoverage && coverage)
    panel = <CoveragePanel coverage={coverage} interruptions={interruptions} status={status} onClose={() => setShowCoverage(false)} />
  else if (segment && route.simulacion)
    panel = (
      <SimulationPanel
        segment={segment}
        referenceDate={referenceDate}
        feedStart={coverage?.feed_start ?? null}
        feedEnd={coverage?.feed_end ?? null}
        interruptions={interrupted.get(segment.id) ?? []}
        scenario={route.escenario}
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
        sources={coverage?.sources ?? []}
        referenceDate={referenceDate}
        interruptions={interrupted.get(segment.id) ?? []}
        onSimulate={() => setRoute({ selection, simulacion: true })}
        onSelectNode={(id) => select({ type: 'nodo', id })}
        onBack={backToLine}
      />
    )
  else if (node)
    panel = (
      <NodeDetail
        key={`${node.id}@${referenceDate}`}
        node={node}
        network={network}
        sources={coverage?.sources ?? []}
        referenceDate={referenceDate}
        interrupted={interrupted}
        onSelectSegment={(id) => select({ type: 'tramo', id })}
        onGoLine={showLine}
        onBack={backToLine}
      />
    )
  else if (!lineId)
    panel = <NetworkOverview network={network} coverage={coverage} interruptions={interruptions} onPickLine={showLine} onShowCoverage={() => setShowCoverage(true)} />
  else
    panel = (
      <LineOverview
        network={network}
        coverage={coverage}
        counts={counts}
        lineId={lineId}
        onShowNetwork={() => showLine(null)}
        selection={selection}
        hoverId={hoverId}
        closedSegmentId={closedSegmentId}
        interruptions={interruptions}
        onSelect={select}
        onHover={setHoverId}
        compact={mobile}
      />
    )

  const lines = network?.lines ?? []

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
        interrupted={interrupted}
        highlight={highlight}
        onSelect={select}
        onHover={setHoverId}
        padding={padding}
        lineId={selection ? null : lineId}
      />
      <header className="cabecera">
        <div className="cabecera-inicio">
          <div className="marca-bloque">
            <span className="marca">Oniel</span>
            <span className="lema">Cómo está conectada la red ferroviaria</span>
          </div>
          <SearchBox
            network={network}
            label="Buscar una estación o una línea"
            placeholder="Buscar estación o línea"
            onPick={pick}
            shortcut
            compact={mobile}
            testId="buscador"
          />
        </div>
        <button type="button" className="cobertura-pill" onClick={() => showLine(null)} data-testid="recuento-red">
          <span className="punto" aria-hidden="true" />
          <span className="pill-texto">
            <strong>{network ? networkCount(network.lines) : 'Oniel'}</strong>
          </span>
          {network && status === 'buscando' && <span className="senal gris">despertando el servidor…</span>}
          {network && status === 'ausente' && <span className="senal gris">vista estática</span>}
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
      {!mobile && (
        <Legend
          closed={closedSegmentId !== null}
          interrupted={interruptions.length > 0}
          lines={lines}
          singleTrack={network?.segments.some((s) => s.tracks === 1) ?? false}
          highlight={highlight}
          onHighlight={setHighlight}
        />
      )}
    </div>
  )
}
