import type { NetworkOut, NodeOut, SegmentOut } from '../data/types'
import type { Selection } from '../app/state'
import { formatKm } from '../app/state'

interface Props {
  network: NetworkOut
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
  return n.name.replace('Villanueva de Córdoba-Los Pedroches', 'Villanueva de Córdoba').replace('Bifurcación ', 'Bif. ')
}

/** Esquema vertical de la línea: estaciones, puestos y bifurcaciones sobre una escala de kilómetros. */
export function StripDiagram({ network, selection, hoverId, closedSegmentId, counts, onSelect, onHover, compact = false }: Props) {
  const nodes = network.nodes
  const segments = network.segments
  const kmMax = Math.max(...nodes.map((n) => n.km))
  const top = 22
  const height = compact ? 300 : Math.max(420, nodes.length * 52)
  const y = (km: number) => top + (km / kmMax) * height
  const width = 404
  const maxCount = counts ? Math.max(0, ...Object.values(counts)) : 0
  const isSelSeg = (s: SegmentOut) => selection?.type === 'tramo' && selection.id === s.id
  const isSelNode = (n: NodeOut) => selection?.type === 'nodo' && selection.id === n.id

  return (
    <svg
      className="esquema"
      viewBox={`0 0 ${width} ${height + top + 26}`}
      width="100%"
      role="img"
      aria-label="Esquema de la línea con sus estaciones y tramos"
      data-testid="esquema"
    >
      <line x1={X} y1={top} x2={X} y2={top + height} stroke="var(--tinta)" strokeWidth={3} />
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
        return (
          <g
            key={s.id}
            className="esquema-tramo"
            role="button"
            tabIndex={0}
            aria-label={`Tramo ${s.from_name} – ${s.to_name}, ${formatKm(s.length_km)} km`}
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
            <rect x={X - 14} y={y1 + 7} width={28} height={Math.max(4, y2 - y1 - 14)} fill="transparent" pointerEvents="all" />
            {(sel || closed || hov) && (
              <line x1={X} y1={y1 + 6} x2={X} y2={y2 - 6} stroke={color} strokeWidth={sel || closed ? 7 : 5} opacity={sel || closed ? 1 : 0.35} strokeLinecap="round" />
            )}
            {!compact && n !== undefined && maxCount > 0 && (
              <g className="esquema-conteo" aria-hidden="true">
                <rect x={X + 9} y={y1 + 9} width={Math.max(2, (n / maxCount) * 26)} height={Math.max(2, y2 - y1 - 18)} rx={1} fill={closed ? 'var(--senal-roja)' : sel ? 'var(--senal-azul)' : 'var(--tinta)'} opacity={sel || closed ? 0.22 : 0.1} />
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
        const minGap = 15
        let dy = 0
        if (n.kind !== 'estacion') {
          if (next && y(next.km) - yy < minGap) dy = -(minGap - (y(next.km) - yy)) - 2
          else if (prev && yy - y(prev.km) < minGap) dy = minGap - (yy - y(prev.km)) + 2
        }
        const sel = isSelNode(n)
        const stroke = sel ? 'var(--senal-azul)' : 'var(--tinta)'
        const station = n.kind === 'estacion'
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
            {station ? (
              <circle cx={X} cy={yy} r={6.5} fill="var(--papel)" stroke={stroke} strokeWidth={sel ? 3.5 : 3} />
            ) : n.kind === 'bifurcacion' ? (
              <>
                <path d={`M${X} ${yy} l 22 -14`} stroke={sel ? 'var(--senal-azul)' : 'var(--tinta-3)'} strokeWidth={2.5} strokeDasharray="3 3" fill="none" />
                <circle cx={X} cy={yy} r={3.5} fill={stroke} />
              </>
            ) : (
              <rect x={X - 4.5} y={yy - 4.5} width={9} height={9} fill={stroke} transform={`rotate(45 ${X} ${yy})`} />
            )}
            <text
              x={X + (compact ? 14 : 112)}
              y={yy + dy + (station ? 4.5 : 4)}
              fontSize={station ? (compact ? 12 : 13.5) : 11.5}
              fontWeight={station ? 600 : 400}
              fill={sel ? 'var(--senal-azul)' : station ? 'var(--tinta)' : 'var(--tinta-2)'}
            >
              {label(n)}
            </text>
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
