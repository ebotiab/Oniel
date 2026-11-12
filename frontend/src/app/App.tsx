import { lazy, Suspense, useCallback, useEffect, useMemo, useRef, useState } from 'react'

import { apiStatus, fetchCoverage, fetchIndex, fetchLine, onApiStatus, wakeApi, type ApiStatus, type DataMode } from '../data/api'
import { composeNetwork } from '../data/network'
import { useApiStatus } from '../data/useApiStatus'
import type { ClosureResult, CoverageOut, LineDetailOut, NetworkIndexOut } from '../data/types'
import type { Trazo } from '../map/layers'
import type { RecorridosEnMapa } from '../map/MapView'
import { buildGraph } from '../routing/graph'
import { ComparePanel } from '../panel/ComparePanel'
import { CoveragePanel } from '../panel/CoveragePanel'
import { GlossaryPanel } from '../panel/GlossaryPanel'
import { GlosarioContext } from '../panel/glosarioContexto'
import { Legend, LeyendaTrazos } from '../panel/Legend'
import { LineOverview } from '../panel/LineOverview'
import { NetworkOverview } from '../panel/NetworkOverview'
import { NodeDetail } from '../panel/NodeDetail'
import { SegmentDetail } from '../panel/SegmentDetail'
import { SimulationPanel } from '../panel/SimulationPanel'
import { SearchBox } from '../panel/SearchBox'
import { activeAnnotations, bySegment, isInterruption } from './annotations'
import { compararRecorridos } from './recorridos'
import type { SearchTarget } from './search'
import { networkCount, parseHash, toHash, todayIso, type Comparador, type Route, type Selection } from './state'
import './app.css'

// MapLibre pesa tres cuartas partes del JavaScript del visor: va en un fichero aparte para que el panel
// no lo espere. index.html lo precarga (vite.config.ts), así que se descarga a la vez que el resto.
const MapView = lazy(() => import('../map/MapView').then((m) => ({ default: m.MapView })))

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
  // La red llega por partes: el índice al arrancar y el detalle de cada línea cuando hace falta.
  const [loaded, setLoaded] = useState<{ index: NetworkIndexOut; source: DataMode } | null>(null)
  const [details, setDetails] = useState<Record<string, LineDetailOut>>({})
  const [near, setNear] = useState<readonly string[]>([])
  const requested = useRef(new Set<string>())
  const [coverage, setCoverage] = useState<CoverageOut | null>(null)
  const [loadError, setLoadError] = useState<string | null>(null)
  const [highlight, setHighlight] = useState<Trazo | null>(null)
  // Trazo que la leyenda pide encuadrar en el mapa al fijarlo.
  const [frame, setFrame] = useState<{ trazo: Trazo; n: number } | null>(null)
  const pinTrazo = useCallback((trazo: Trazo) => setFrame((f) => ({ trazo, n: (f?.n ?? 0) + 1 })), [])
  const [route, setRoute] = useState(() => parseHash(window.location.hash))
  const [hoverId, setHoverId] = useState<string | null>(null)
  const [result, setResult] = useState<ClosureResult | null>(null)
  const [showCoverage, setShowCoverage] = useState(() => Boolean(parseHash(window.location.hash).cobertura))
  const [sheetOpen, setSheetOpen] = useState(() => Boolean(parseHash(window.location.hash).recorridos ?? parseHash(window.location.hash).glosario))
  const [elegidoKey, setElegidoKey] = useState<string | null>(null)
  const [activeLineId, setActiveLineId] = useState<string | null>(() => parseHash(window.location.hash).linea ?? null)
  const mobile = useMedia('(max-width: 760px)')
  const status = useApiStatus()

  // Arranque: el índice de la instantánea estática pinta la red enseguida; el de la API, cuando responde, lo sustituye.
  useEffect(() => {
    let cancelled = false
    let fromApi = false
    let staticFailed = false
    const fail = () => setLoadError('No se ha podido cargar la red. Comprueba la conexión o el servidor de Oniel.')
    const load = async (source: DataMode) => {
      const [index, cov] = await Promise.all([fetchIndex(source), fetchCoverage(source)])
      return { index, cov, source }
    }
    const apply = (d: Awaited<ReturnType<typeof load>>) => {
      setLoaded({ index: d.index, source: d.source })
      setCoverage(d.cov)
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

  const network = useMemo(() => (loaded ? composeNetwork(loaded.index, details) : null), [loaded, details])

  // Sincronizar el hash con la selección
  useEffect(() => {
    const onHash = () => {
      const r = parseHash(window.location.hash)
      setRoute(r)
      setShowCoverage(Boolean(r.cobertura))
      if (r.recorridos || r.glosario) setSheetOpen(true)
      // Sin selección manda la URL: #/ es la vista de la red. Con selección, la línea sale de lo seleccionado.
      if (!r.selection && !r.cobertura && !r.glosario) setActiveLineId(r.linea ?? null)
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
  // El glosario se abre encima de lo que se estaba viendo y «Volver» lo devuelve: la ficha de la que salió
  // el término, la línea o la vista de la red.
  const vuelta = useRef<{ route: Route; cobertura: boolean } | null>(null)
  const openGlossary = useCallback(
    (entrada: string | null) => {
      if (!route.glosario) vuelta.current = { route, cobertura: showCoverage }
      setRoute({ selection: null, simulacion: false, glosario: { entrada } })
      setShowCoverage(false)
      setSheetOpen(true)
    },
    [route, showCoverage],
  )
  const closeGlossary = () => {
    const antes = vuelta.current
    vuelta.current = null
    setRoute(antes?.route ?? { selection: null, simulacion: false })
    setShowCoverage(antes?.cobertura ?? false)
  }
  const pick = useCallback(
    (target: SearchTarget) => (target.type === 'nodo' ? select(target) : target.type === 'glosario' ? openGlossary(target.id) : showLine(target.id)),
    [select, showLine, openGlossary],
  )

  // El comparador de recorridos: abrirlo y cambiar sus estaciones son cambios de ruta.
  const compare = useCallback((next: Comparador) => {
    setRoute({ selection: null, simulacion: false, recorridos: next })
    setResult(null)
    setShowCoverage(false)
    setSheetOpen(true)
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

  // El esquema del panel sigue a la selección: un tramo o un nodo de otra línea muestran esa línea.
  // Un nodo común a varias líneas (Madrid, Córdoba) conserva la línea que ya estaba a la vista.
  const nodeLines = useMemo(() => (node && network ? network.nodes.filter((n) => n.id === node.id).map((n) => n.line_id) : []), [network, node])
  const lineId =
    segment?.line_id ??
    (nodeLines.length ? (activeLineId && nodeLines.includes(activeLineId) ? activeLineId : nodeLines[0]!) : null) ??
    (activeLineId && (!network || network.lines.some((l) => l.id === activeLineId)) ? activeLineId : null)
  // Líneas que el mapa tiene cerca: se añaden a las que ya se han pedido.
  const wantNear = useCallback((ids: string[]) => {
    setNear((cur) => {
      const extra = ids.filter((id) => !cur.includes(id))
      return extra.length ? [...cur, ...extra] : cur
    })
  }, [])

  // La línea a la vista y las que el mapa tiene cerca se cargan enteras: textos de sus nodos, geometría
  // completa y recuentos. Cada una se descarga una vez por origen: de la instantánea y, cuando responde,
  // de la API.
  useEffect(() => {
    if (!loaded) return
    const { index, source } = loaded
    for (const id of lineId ? [lineId, ...near] : near) {
      const key = `${source}:${id}`
      if (requested.current.has(key) || !index.lines.some((l) => l.id === id)) continue
      requested.current.add(key)
      fetchLine(id, source)
        .then((detail) => setDetails((cur) => ({ ...cur, [id]: detail })))
        .catch(() => {
          // Sin el detalle, la línea se queda con lo que trae el índice; se reintenta si se vuelve a pedir.
          requested.current.delete(key)
        })
    }
  }, [loaded, near, lineId])
  const lineDetail = lineId ? details[lineId] : undefined
  const closedSegmentId = result && route.simulacion ? result.segment.id : null
  // Anotaciones vigentes hoy: cada tipo se marca en el mapa y en el esquema y se explica en el panel
  // como diga su capa (annotationLayers.ts). Las interrupciones, además, cortan recorridos y avisan
  // en la simulación.
  const today = useMemo(() => todayIso(), [])
  const annotations = useMemo(() => activeAnnotations(network, today), [network, today])
  const annotated = useMemo(() => bySegment(annotations), [annotations])
  const interrupted = useMemo(() => bySegment(annotations.filter(isInterruption)), [annotations])
  const referenceDate = coverage?.reference_date ?? null

  // Comparador de recorridos. Una estación de la URL que no existe cuenta como sin elegir.
  const graph = useMemo(() => (network ? buildGraph(network) : null), [network])
  const comparador = useMemo<Comparador | null>(() => {
    if (!route.recorridos) return null
    const known = (id: string | null) => (id && (!graph || graph.nodes.has(id)) ? id : null)
    return { ...route.recorridos, from: known(route.recorridos.from), to: known(route.recorridos.to) }
  }, [route.recorridos, graph])
  const comparacion = useMemo(() => {
    if (!comparador?.from || !comparador.to || comparador.from === comparador.to || !graph || !network) return null
    return compararRecorridos(graph, network, comparador.from, comparador.to, interrupted, comparador.escenario)
  }, [comparador, graph, network, interrupted])
  const elegido = comparacion ? (comparacion.recorridos.find((r) => r.key === elegidoKey) ?? comparacion.recorridos[0] ?? null) : null
  const recorridosEnMapa = useMemo<RecorridosEnMapa | null>(() => {
    if (!comparador) return null
    return {
      todos: [...new Set(comparacion?.recorridos.flatMap((r) => r.route.segment_ids))],
      elegido: elegido?.route.segment_ids ?? [],
      extremos: [comparador.from, comparador.to].filter((id): id is string => Boolean(id)),
    }
  }, [comparador, comparacion, elegido])
  // En el comparador, tocar una estación en el mapa la pone en el extremo que falte; lo demás no hace nada.
  const pickOnMap = useCallback(
    (sel: Selection) => {
      if (!comparador || sel?.type !== 'nodo') return
      if (!comparador.from) compare({ ...comparador, from: sel.id })
      else if (!comparador.to) compare({ ...comparador, to: sel.id })
    },
    [comparador, compare],
  )
  // La hoja del móvil mide 66vh abierta y 150 px plegada (app.css): el mapa encuadra en lo que queda a la vista.
  const padding = useMemo(() => (mobile ? { left: 0, bottom: sheetOpen ? Math.round(window.innerHeight * 0.66) : 150 } : { left: 440, bottom: 0 }), [mobile, sheetOpen])

  // «Toda la línea» vuelve a la línea que se estaba viendo, también si se llegó por un enlace directo.
  const backToLine = () => {
    if (lineId) setActiveLineId(lineId)
    select(null)
  }

  // En el móvil la leyenda de los trazos va dentro del panel, sobre el esquema de la línea.
  const leyendaMovil =
    mobile && network ? (
      <LeyendaTrazos lines={network.lines} singleTrack={network.segments.some((s) => s.tracks === 1)} highlight={highlight} onHighlight={setHighlight} onPin={pinTrazo} />
    ) : null
  let panel: React.ReactNode = null
  if (loadError) panel = <p className="aviso">{loadError}</p>
  else if (!network) panel = <p className="suave cargando">Cargando la red…</p>
  else if (showCoverage && coverage)
    panel = <CoveragePanel coverage={coverage} annotations={annotations} status={status} onClose={() => setShowCoverage(false)} />
  else if (route.glosario) panel = <GlossaryPanel entrada={route.glosario.entrada} sources={coverage?.sources ?? []} onBack={closeGlossary} />
  else if (comparador)
    panel = (
      <ComparePanel
        network={network}
        comparador={comparador}
        comparacion={comparacion}
        elegido={elegido}
        sources={coverage?.sources ?? []}
        referenceDate={referenceDate}
        onChange={compare}
        onElegir={setElegidoKey}
        onBack={() => showLine(null)}
      />
    )
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
        operators={coverage?.operators ?? []}
        referenceDate={referenceDate}
        annotations={annotated.get(segment.id) ?? []}
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
        operators={coverage?.operators ?? []}
        referenceDate={referenceDate}
        annotated={annotated}
        onSelectSegment={(id) => select({ type: 'tramo', id })}
        onSelectNode={(id) => select({ type: 'nodo', id })}
        onGoLine={showLine}
        onCompare={() => compare({ from: node.id, to: null })}
        onBack={backToLine}
      />
    )
  else if (!lineId)
    panel = <NetworkOverview network={network} coverage={coverage} annotations={annotations} onPickLine={showLine} onShowCoverage={() => setShowCoverage(true)} onCompare={() => compare({ from: null, to: null })} onGlossary={() => openGlossary(null)} />
  else
    panel = (
      <LineOverview
        network={network}
        coverage={coverage}
        counts={lineDetail?.counts ?? null}
        countsMax={lineDetail?.network_max_count ?? null}
        lineId={lineId}
        onShowNetwork={() => showLine(null)}
        selection={selection}
        hoverId={hoverId}
        closedSegmentId={closedSegmentId}
        annotations={annotations}
        onSelect={select}
        onHover={setHoverId}
        compact={mobile}
        leyenda={leyendaMovil}
      />
    )

  const lines = network?.lines ?? []

  return (
    <GlosarioContext value={openGlossary}>
    <div className={`app ${mobile ? 'movil' : 'escritorio'} ${sheetOpen ? 'hoja-abierta' : ''}`}>
      <a className="visually-hidden" href="#panel">
        Ir al panel de la línea
      </a>
      <Suspense fallback={<div className="mapa" aria-hidden="true" />}>
        <MapView
          network={network}
          selection={selection}
          hoverId={hoverId}
          closedSegmentId={closedSegmentId}
          annotated={annotated}
          highlight={highlight}
          frame={frame}
          onSelect={comparador ? pickOnMap : select}
          onHover={setHoverId}
          onNearLines={wantNear}
          padding={padding}
          lineId={selection ? null : lineId}
          recorridos={recorridosEnMapa}
        />
      </Suspense>
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
        {/* en el móvil la cabecera va justa: allí al glosario se llega por el buscador y por la vista de la red */}
        {!mobile && (
          <button type="button" className="cobertura-pill glosario-boton" onClick={() => openGlossary(null)} data-testid="boton-glosario">
            Glosario
          </button>
        )}
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
          annotations={annotations}
          lines={lines}
          singleTrack={network?.segments.some((s) => s.tracks === 1) ?? false}
          highlight={highlight}
          onHighlight={setHighlight}
          onPin={pinTrazo}
        />
      )}
    </div>
    </GlosarioContext>
  )
}
