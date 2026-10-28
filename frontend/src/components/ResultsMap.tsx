import { useMemo, useState } from 'react'
import type { NearbyBusiness, ResultView, SearchView } from '../api'
import { destinationPoint } from '../geo'
import { PIN_STYLE, bestBusinessId, rankedAnswerText, legendCounts, mergePins, pinLabel, stateLabel } from '../pins'
import type { PinState } from '../pins'
import { MapView } from './MapView'
import type { MapPin } from './MapView'
import { Radar } from './Radar'

/** Where the shops are and what each one said: a real map (OpenStreetMap) or a map-free radar.
 *  Shops near the search that have not joined Sonar are shown too, and are never called. */
export function ResultsMap({
  search,
  nearby = [],
  results,
}: {
  search: SearchView
  nearby?: NearbyBusiness[]
  results?: ResultView[]
}) {
  const custom = !!search.custom_questions
  const [tab, setTab] = useState<'map' | 'radar'>('map')
  const [hidden, setHidden] = useState<Set<PinState>>(new Set())
  const radius = search.radius_km
  const centre =
    search.center_lat != null && search.center_lng != null
      ? { lat: search.center_lat, lng: search.center_lng }
      : null

  const best = bestBusinessId(results)
  const details = useMemo(
    () => new Map((results ?? []).map((r) => [r.business.id, rankedAnswerText(r)])),
    [results],
  )
  const shops = useMemo(
    () =>
      mergePins(search.attempts, nearby).map((p) => ({
        ...p,
        best: p.id === best,
        detail: details.get(p.id) ?? null,
      })),
    [search.attempts, nearby, best, details],
  )
  const legend = useMemo(() => legendCounts(shops), [shops])
  const pins: MapPin[] = useMemo(
    () =>
      centre
        ? shops
            .filter((p) => !hidden.has(p.state))
            .map((p) => ({
              id: p.id,
              name: p.name,
              label: pinLabel(p, custom),
              color: PIN_STYLE[p.state].color,
              position: destinationPoint(centre, p.bearing_deg, p.distance_km),
            }))
        : [],
    // eslint-disable-next-line react-hooks/exhaustive-deps
    [shops, hidden, custom, search.center_lat, search.center_lng],
  )

  const toggle = (state: PinState) =>
    setHidden((prev) => {
      const next = new Set(prev)
      if (next.has(state)) next.delete(state)
      else next.add(state)
      return next
    })

  if (radius == null || shops.length === 0 || !centre) return null

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
          ariaLabel={`Map showing ${pins.length} of ${shops.length} shops within ${radius} kilometres`}
        />
      ) : (
        <Radar attempts={search.attempts} radiusKm={radius} bare />
      )}
      <p className="mt-2 text-xs text-[var(--muted)]">
        {tab === 'map'
          ? 'Map data from OpenStreetMap contributors. Distances are in a straight line, not driving routes.'
          : 'The radar needs no network and sends nothing to any map service.'}
      </p>
      <fieldset className="mt-3">
        <legend className="text-sm font-semibold">What each shop said (tap to hide or show)</legend>
        <ul className="mt-2 flex flex-wrap gap-2" aria-label="Map legend">
          {legend.map(({ state, count }) => (
            <li key={state}>
              <button
                type="button"
                aria-pressed={!hidden.has(state)}
                onClick={() => toggle(state)}
                className={`chip cursor-pointer ${hidden.has(state) ? 'opacity-50' : ''}`}
              >
                <span
                  aria-hidden="true"
                  className="mr-1 inline-block size-3 rounded-full"
                  style={{ background: PIN_STYLE[state].color }}
                />
                {stateLabel(state, custom)}: {count}
              </button>
            </li>
          ))}
        </ul>
      </fieldset>
      {shops.some((p) => p.state === 'NOT_JOINED') && (
        <p className="mt-2 text-xs text-[var(--muted)]">
          Sonar only calls shops that joined themselves. Shops marked "Not joined yet" were found on
          OpenStreetMap and have never been called.
        </p>
      )}
      <details className="mt-3 text-sm">
        <summary className="cursor-pointer font-semibold">All shops as a list</summary>
        <ul className="mt-2 grid gap-1">
          {shops.map((p) => (
            <li key={p.id}>
              {p.name}, {p.distance_km} km: {pinLabel(p, custom)}
            </li>
          ))}
        </ul>
      </details>
    </section>
  )
}
