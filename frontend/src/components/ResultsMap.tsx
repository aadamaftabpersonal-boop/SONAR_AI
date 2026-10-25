import { useMemo, useState } from 'react'
import type { AttemptView, SearchView } from '../api'
import { attemptStatusLabel } from '../copy'
import { destinationPoint } from '../geo'
import { MapView } from './MapView'
import type { MapPin } from './MapView'
import { Radar } from './Radar'

const color = (a: AttemptView) =>
  a.status === 'COMPLETED'
    ? '#166534'
    : ['RINGING', 'IN_PROGRESS', 'DIALING', 'DISPATCHING', 'PROCESSING'].includes(a.status)
      ? '#1e40af'
      : ['FAILED', 'ERROR', 'TIMED_OUT', 'STOPPED', 'INSUFFICIENT_BALANCE'].includes(a.status)
        ? '#991b1b'
        : '#5b6862'

/** The latest attempt per shop that has a known position. */
function latestWithPosition(attempts: AttemptView[]): AttemptView[] {
  const latest = new Map<string, AttemptView>()
  for (const a of attempts) {
    const prev = latest.get(a.business.id)
    if (!prev || a.attempt_number > prev.attempt_number) latest.set(a.business.id, a)
  }
  return [...latest.values()].filter(
    (a) => a.business.distance_km != null && a.business.bearing_deg != null,
  )
}

/** Where the shops are: a real map (OpenStreetMap) or a map-free radar that works offline. */
export function ResultsMap({ search }: { search: SearchView }) {
  const [tab, setTab] = useState<'map' | 'radar'>('map')
  const radius = search.radius_km
  const centre =
    search.center_lat != null && search.center_lng != null
      ? { lat: search.center_lat, lng: search.center_lng }
      : null

  const pins: MapPin[] = useMemo(
    () =>
      centre
        ? latestWithPosition(search.attempts).map((a) => ({
            id: a.business.id,
            name: a.business.name,
            label: attemptStatusLabel(a),
            color: color(a),
            position: destinationPoint(
              centre,
              a.business.bearing_deg as number,
              a.business.distance_km as number,
            ),
          }))
        : [],
    // eslint-disable-next-line react-hooks/exhaustive-deps
    [search.attempts, search.center_lat, search.center_lng],
  )

  if (radius == null || pins.length === 0 || !centre) return null

  return (
    <section className="card p-5" aria-labelledby="where-h">
      <div className="mb-3 flex flex-wrap items-center justify-between gap-3">
        <h2 id="where-h" className="text-lg font-bold">
          Around you
        </h2>
        <div role="tablist" aria-label="View" className="flex gap-1 rounded-full bg-[var(--surface-2)] p-1">
          {(['map', 'radar'] as const).map((t) => (
            <button
              key={t}
              role="tab"
              type="button"
              aria-selected={tab === t}
              className={`rounded-full px-4 py-1 text-sm font-semibold ${
                tab === t ? 'bg-[var(--accent)] text-[var(--accent-ink)]' : 'text-[var(--muted)]'
              }`}
              onClick={() => setTab(t)}
            >
              {t === 'map' ? 'Map' : 'Radar'}
            </button>
          ))}
        </div>
      </div>
      {tab === 'map' ? (
        <MapView
          center={centre}
          radiusKm={radius}
          pins={pins}
          ariaLabel={`Map showing ${pins.length} shops within ${radius} kilometres`}
        />
      ) : (
        <Radar attempts={search.attempts} radiusKm={radius} bare />
      )}
      <p className="mt-2 text-xs text-[var(--muted)]">
        {tab === 'map'
          ? 'Map data from OpenStreetMap contributors. Distances are in a straight line, not driving routes.'
          : 'The radar needs no network and sends nothing to any map service.'}
      </p>
    </section>
  )
}
