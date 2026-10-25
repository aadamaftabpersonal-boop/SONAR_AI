import type { AttemptView } from '../api'
import { attemptStatusLabel } from '../copy'
import { radarPoint, ringLabels } from '../radar'

const SIZE = 130
const CENTRE = { x: 160, y: 150 }

const fill = (a: AttemptView) =>
  a.status === 'COMPLETED'
    ? 'var(--good)'
    : ['RINGING', 'IN_PROGRESS', 'DIALING', 'DISPATCHING', 'PROCESSING'].includes(a.status)
      ? 'var(--info)'
      : ['FAILED', 'ERROR', 'TIMED_OUT', 'STOPPED', 'INSUFFICIENT_BALANCE'].includes(a.status)
        ? 'var(--bad)'
        : 'var(--muted)'

/**
 * A map-free radar: you at the centre, each shop at its real bearing and distance. Status is
 * always written as text beside the pin (never colour alone), and the list above stays the
 * accessible source of truth.
 */
export function Radar({
  attempts,
  radiusKm,
  bare = false,
}: {
  attempts: AttemptView[]
  radiusKm: number
  /** draw just the picture, for use inside another card */
  bare?: boolean
}) {
  const latest = new Map<string, AttemptView>()
  for (const a of attempts) {
    const prev = latest.get(a.business.id)
    if (!prev || a.attempt_number > prev.attempt_number) latest.set(a.business.id, a)
  }
  const pins = [...latest.values()].filter(
    (a) => a.business.distance_km != null && a.business.bearing_deg != null,
  )
  if (pins.length === 0) return null

  const picture = (
    <>
      <svg
        viewBox="0 0 320 300"
        role="img"
        aria-label={`Radar showing ${pins.length} shops within ${radiusKm} kilometres`}
        className="mx-auto w-full max-w-md"
      >
        {ringLabels(radiusKm).map((km, i) => (
          <g key={km}>
            <circle
              cx={CENTRE.x}
              cy={CENTRE.y}
              r={((i + 1) / 3) * SIZE}
              fill="none"
              stroke="var(--border)"
              strokeDasharray="3 4"
            />
            <text
              x={CENTRE.x + 4}
              y={CENTRE.y - ((i + 1) / 3) * SIZE + 11}
              fontSize="9"
              fill="var(--muted)"
            >
              {km} km
            </text>
          </g>
        ))}
        <text x={CENTRE.x} y={CENTRE.y - SIZE - 6} fontSize="10" textAnchor="middle" fill="var(--muted)">
          N
        </text>
        <circle cx={CENTRE.x} cy={CENTRE.y} r="6" fill="var(--accent)" />
        <text x={CENTRE.x} y={CENTRE.y + 18} fontSize="9" textAnchor="middle" fill="var(--muted)">
          you
        </text>
        {pins.map((a) => {
          const p = radarPoint(
            a.business.distance_km as number,
            a.business.bearing_deg as number,
            radiusKm,
            SIZE,
            CENTRE,
          )
          const right = p.x <= CENTRE.x + 40
          return (
            <g key={a.business.id}>
              <title>{`${a.business.name}: ${attemptStatusLabel(a)}, ${a.business.distance_km} km`}</title>
              <circle cx={p.x} cy={p.y} r="6" fill={fill(a)} stroke="var(--surface)" strokeWidth="2" />
              <text x={p.x + (right ? 10 : -10)} y={p.y - 1} fontSize="10" textAnchor={right ? 'start' : 'end'} fill="var(--text)">
                {a.business.name.slice(0, 22)}
              </text>
              <text x={p.x + (right ? 10 : -10)} y={p.y + 10} fontSize="9" textAnchor={right ? 'start' : 'end'} fill="var(--muted)">
                {attemptStatusLabel(a)}
              </text>
            </g>
          )
        })}
      </svg>
      <p className="text-xs text-[var(--muted)]">
        Positions are straight-line distance and compass direction from your search point, not
        driving routes.
      </p>
    </>
  )

  if (bare) return picture
  return (
    <section className="card p-5" aria-labelledby="radar-h">
      <h2 id="radar-h" className="text-lg font-bold">
        Around you
      </h2>
      {picture}
    </section>
  )
}
