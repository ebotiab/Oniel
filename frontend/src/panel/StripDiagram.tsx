import type { NetworkOut, NodeOut, SegmentOut } from '../data/types'
import type { Selection } from '../app/state'
import { formatKm } from '../app/state'

interface Props {
  network: NetworkOut
  lineId: string
  selection: Selection
  hoverId: string | null
  closedSegmentId: string | null
  counts: Record<string, number> | null
  onSelect: (sel: Selection) => void
  onHover: (id: string | null) => void
  compact?: boolean
}

const X = 78

function label(n: NodeOut): string {
  return n.name
    .replace('Villanueva de Córdoba-Los Pedroches', 'Villanueva de Córdoba')
    .replace('Almuradiel-Viso del Marqués', 'Almuradiel')
    .replace('Campus Universitario de Rabanales', 'Rabanales')
    .replace('Bifurcación ', 'Bif. ')
}

/** Esquema vertical de una línea: estaciones, puestos y bifurcaciones sobre una escala de kilómetros. */
export function StripDiagram({ network, lineId, selection, hoverId, closedSegmentId, counts, onSelect, onHover, compact = false }: Props) {
  const nodes = network.nodes.filter((n) => n.line_id === lineId)
  const segments = network.segments.filter((s) => s.line_id === lineId)
  const withConnections = new Set(network.connections.map((c) => c.node_id))
  const kmMax = Math.max(...nodes.map((n) => n.km))
  const top = 22
  const principal = nodes.filter((n) => n.rank === 'principal').length
  const height = compact ? 300 : Math.max(420, principal * 52 + (nodes.length - principal) * 26)
  const y = (km: number) => top + (km / kmMax) * height
  const width = 404
  const maxCount = counts ? Math.max(0, ...Object.values(counts)) : 0
  const isSelSeg = (s: SegmentOut) => selection?.type === 'tramo' && selection.id === s.id
  const isSelNode = (n: NodeOut) => selection?.type === 'nodo' && selection.id === n.id
  const minor = (n: NodeOut) => n.kind !== 'estacion' || n.rank === 'secundario'

  return (
    <svg
      className="esquema"
      viewBox={`0 0 ${width} ${height + top + 26}`}
      width="100%"
      role="img"
      aria-label="Esquema de la línea con sus estaciones y tramos"
      data-testid="esquema"
    >
      {/* la vía: trazo grueso en vía doble, fino en vía única */}
      {segments.map((s) => (
        <line key={`via-${s.id}`} x1={X} y1={y(s.km_from)} x2={X} y2={y(s.km_to)} stroke="var(--tinta)" strokeWidth={s.tracks === 1 ? 1.5 : 3} />
      ))}
      {Array.from({ length: Math.floor(kmMax / 10) + 1 }, (_, i) => i * 10).map((km) => (
        <g key={km}>
          <line x1={X - (km % 50 ? 4 : 7)} y1={y(km)} x2={X} y2={y(km)} stroke="var(--tinta)" strokeWidth={km % 50 ? 1 : 1.5} />
          {km % 50 === 0 && (
            <text x={X - 12} y={y(km) + 3.5} textAnchor="end" fontSize={10} fill="var(--tinta-3)" className="datos">
              {km}
            </text>
          )}
        </g>
      ))}

      {segments.map((s) => {
        const y1 = y(s.km_from)
        const y2 = y(s.km_to)
        const sel = isSelSeg(s)
        const closed = closedSegmentId === s.id
        const hov = hoverId === s.id
        const color = closed ? 'var(--senal-roja)' : sel ? 'var(--senal-azul)' : 'var(--tinta)'
        const n = counts?.[s.id]
        const inset = Math.min(6, Math.max(2, (y2 - y1) / 4))
        return (
          <g
            key={s.id}
            className="esquema-tramo"
            role="button"
            tabIndex={0}
            aria-label={`Tramo ${s.from_name} – ${s.to_name}, ${formatKm(s.length_km)} km${s.tracks === 1 ? ', vía única' : ''}`}
            aria-pressed={sel}
            data-testid={`esquema-tramo-${s.seq}`}
            onClick={() => onSelect({ type: 'tramo', id: s.id })}
            onKeyDown={(e) => {
              if (e.key === 'Enter' || e.key === ' ') {
                e.preventDefault()
                onSelect({ type: 'tramo', id: s.id })
              }
            }}
            onMouseEnter={() => onHover(s.id)}
            onMouseLeave={() => onHover(null)}
            style={{ cursor: 'pointer', pointerEvents: 'all' }}
          >
            <rect x={X - 14} y={y1 + inset} width={28} height={Math.max(4, y2 - y1 - 2 * inset)} fill="transparent" pointerEvents="all" />
            {(sel || closed || hov) && (
              <line x1={X} y1={y1 + inset} x2={X} y2={y2 - inset} stroke={color} strokeWidth={sel || closed ? 7 : 5} opacity={sel || closed ? 1 : 0.35} strokeLinecap="round" />
            )}
            {!compact && n !== undefined && maxCount > 0 && y2 - y1 > 14 && (
              <g className="esquema-conteo" aria-hidden="true">
                <rect x={X + 9} y={y1 + inset + 2} width={Math.max(2, (n / maxCount) * 26)} height={Math.max(2, y2 - y1 - 2 * inset - 4)} rx={1} fill={closed ? 'var(--senal-roja)' : sel ? 'var(--senal-azul)' : 'var(--tinta)'} opacity={sel || closed ? 0.22 : 0.1} />
                <text x={X + 40} y={(y1 + y2) / 2 + 3.5} fontSize={10} fill={sel ? 'var(--senal-azul)' : 'var(--tinta-3)'} className="datos">
                  {n}
                </text>
              </g>
            )}
          </g>
        )
      })}

      {nodes.map((n, i) => {
        const yy = y(n.km)
        const prev = nodes[i - 1]
        const next = nodes[i + 1]
        const minGap = 14
        let dy = 0
        if (minor(n)) {
          if (next && y(next.km) - yy < minGap) dy = -(minGap - (y(next.km) - yy)) - 2
          else if (prev && yy - y(prev.km) < minGap) dy = minGap - (yy - y(prev.km)) + 2
        }
        const sel = isSelNode(n)
        const stroke = sel ? 'var(--senal-azul)' : 'var(--tinta)'
        const station = n.kind === 'estacion'
        const secondary = n.rank === 'secundario'
        const hideLabel = compact && secondary
        const hasStub = n.kind === 'bifurcacion' || withConnections.has(n.id)
        return (
          <g
            key={n.id}
            className="esquema-nodo"
            role="button"
            tabIndex={0}
            aria-label={`${label(n)}, kilómetro ${formatKm(n.km)}`}
            aria-pressed={sel}
            data-testid={`esquema-nodo-${n.id}`}
            onClick={() => onSelect({ type: 'nodo', id: n.id })}
            onKeyDown={(e) => {
              if (e.key === 'Enter' || e.key === ' ') {
                e.preventDefault()
                onSelect({ type: 'nodo', id: n.id })
              }
            }}
            style={{ cursor: 'pointer' }}
          >
            <rect x={X - 14} y={yy - 11} width={width - X + 14} height={22} fill="transparent" />
            {hasStub && <path d={`M${X} ${yy} l 22 -14`} stroke={sel ? 'var(--senal-azul)' : 'var(--tinta-3)'} strokeWidth={2.5} strokeDasharray="3 3" fill="none" />}
            {station ? (
              <circle cx={X} cy={yy} r={secondary ? 4.5 : 6.5} fill="var(--papel)" stroke={stroke} strokeWidth={sel ? 3.5 : secondary ? 2 : 3} />
            ) : n.kind === 'bifurcacion' ? (
              <circle cx={X} cy={yy} r={3.5} fill={stroke} />
            ) : (
              <rect x={X - 4.5} y={yy - 4.5} width={9} height={9} fill={stroke} transform={`rotate(45 ${X} ${yy})`} />
            )}
            {!hideLabel && (
              <text
                x={X + (compact ? 14 : 112)}
                y={yy + dy + (station && !secondary ? 4.5 : 4)}
                fontSize={station && !secondary ? (compact ? 12 : 13.5) : 11.5}
                fontWeight={station && !secondary ? 600 : 400}
                fill={sel ? 'var(--senal-azul)' : station && !secondary ? 'var(--tinta)' : 'var(--tinta-2)'}
              >
                {label(n)}
              </text>
            )}
            {!compact && (
              <text x={width - 6} y={yy + dy + 4} textAnchor="end" fontSize={10} fill="var(--tinta-3)" className="datos">
                km {formatKm(n.km)}
              </text>
            )}
          </g>
        )
      })}
    </svg>
  )
}
