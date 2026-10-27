import { render, screen, within } from '@testing-library/react'
import userEvent from '@testing-library/user-event'
import { describe, expect, it } from 'vitest'
import type { AttemptView, CallStatus, NearbyBusiness, ResultState, SearchView } from './api'
import { MapView } from './components/MapView'
import { ResultsMap } from './components/ResultsMap'
import { destinationPoint, distanceKm } from './geo'
import { TILE_URL } from './tiles'

// --- geography ---------------------------------------------------------------------------------

describe('destinationPoint', () => {
  const origin = { lat: 12.9716, lng: 77.5946 }

  it.each([0, 45, 90, 135, 180, 225, 270, 315])(
    'lands exactly the requested distance away at bearing %i',
    (bearing) => {
      const p = destinationPoint(origin, bearing, 2.5)
      expect(distanceKm(origin, p)).toBeCloseTo(2.5, 3)
    },
  )

  it('goes north for 0 degrees and east for 90 degrees', () => {
    const north = destinationPoint(origin, 0, 1)
    expect(north.lat).toBeGreaterThan(origin.lat)
    expect(north.lng).toBeCloseTo(origin.lng, 6)
    const east = destinationPoint(origin, 90, 1)
    expect(east.lng).toBeGreaterThan(origin.lng)
    expect(east.lat).toBeCloseTo(origin.lat, 3)
  })

  it('stays put for zero distance and keeps longitude in range across the date line', () => {
    const same = destinationPoint(origin, 123, 0)
    expect(same.lat).toBeCloseTo(origin.lat, 9)
    expect(same.lng).toBeCloseTo(origin.lng, 9)
    const p = destinationPoint({ lat: 0, lng: 179.9 }, 90, 50)
    expect(p.lng).toBeGreaterThanOrEqual(-180)
    expect(p.lng).toBeLessThanOrEqual(180)
  })
})

// --- the map -----------------------------------------------------------------------------------

describe('MapView', () => {
  it('uses the HTTPS OpenStreetMap tile URL by default', () => {
    expect(TILE_URL).toBe('https://tile.openstreetmap.org/{z}/{x}/{y}.png')
    expect(TILE_URL.startsWith('https://')).toBe(true)
  })

  it('shows the OpenStreetMap attribution, as the tile policy requires', () => {
    render(<MapView center={{ lat: 12.97, lng: 77.59 }} radiusKm={3} ariaLabel="test map" />)
    const link = screen.getByRole('link', { name: 'OpenStreetMap' })
    expect(link).toHaveAttribute('href', 'https://www.openstreetmap.org/copyright')
    expect(screen.getByRole('application', { name: 'test map' })).toBeInTheDocument()
  })

  it('writes every shop name and status as text on the map, not colour alone', () => {
    render(
      <MapView
        center={{ lat: 12.97, lng: 77.59 }}
        radiusKm={3}
        ariaLabel="m"
        pins={[
          { id: '1', name: 'Corner Pharmacy', label: 'Ringing', color: '#1e40af', position: { lat: 12.975, lng: 77.595 } },
          { id: '2', name: 'Far Shop', label: 'Not called', color: '#5b6862', position: { lat: 12.96, lng: 77.58 } },
        ]}
      />,
    )
    expect(screen.getByText('Corner Pharmacy · Ringing')).toBeInTheDocument()
    expect(screen.getByText('Far Shop · Not called')).toBeInTheDocument()
  })

  it('labels the centre and a picked spot', () => {
    render(
      <MapView center={{ lat: 12.97, lng: 77.59 }} radiusKm={3} ariaLabel="m" picked={{ lat: 12.98, lng: 77.6 }} />,
    )
    expect(screen.getByText('You')).toBeInTheDocument()
    expect(screen.getByText('Search here')).toBeInTheDocument()
  })

  it('redraws when the pins change instead of stacking old ones', () => {
    const pin = (name: string) => ({ id: name, name, label: 'Done', color: '#166534', position: { lat: 12.97, lng: 77.59 } })
    const { rerender } = render(
      <MapView center={{ lat: 12.97, lng: 77.59 }} radiusKm={3} ariaLabel="m" pins={[pin('First')]} />,
    )
    rerender(<MapView center={{ lat: 12.97, lng: 77.59 }} radiusKm={3} ariaLabel="m" pins={[pin('Second')]} />)
    expect(screen.queryByText('First · Done')).not.toBeInTheDocument()
    expect(screen.getByText('Second · Done')).toBeInTheDocument()
  })

  it('cleans up on unmount without throwing', () => {
    const { unmount } = render(<MapView center={{ lat: 12.97, lng: 77.59 }} radiusKm={3} ariaLabel="m" />)
    expect(() => unmount()).not.toThrow()
  })
})

// --- map or radar -------------------------------------------------------------------------------

function attempt(name: string, status: CallStatus, bearing: number, km: number, rs: ResultState = 'PENDING'): AttemptView {
  return {
    attempt_id: name,
    business: { id: name, name, kind: 'REAL_BUSINESS', distance_km: km, bearing_deg: bearing },
    status,
    attempt_number: 1,
    updated_at: '2026-11-02T10:00:00Z',
    result_state: rs,
  }
}

const search = (over: Partial<SearchView> = {}): SearchView => ({
  search_id: 's',
  status: 'RUNNING',
  demo_mode: false,
  created_at: '2026-11-02T10:00:00Z',
  started_at: null,
  completed_at: null,
  deadline_at: null,
  counts: { planned: 2, pending: 0, in_call: 0, answered: 0, no_answer: 0, failed: 0, cancelled: 0 },
  attempts: [attempt('North Shop', 'RINGING', 0, 1), attempt('East Shop', 'COMPLETED', 90, 2, 'REPORTED_AVAILABLE')],
  error: null,
  radius_km: 3,
  center_lat: 12.9716,
  center_lng: 77.5946,
  ...over,
})

describe('ResultsMap', () => {
  it('shows the map first, with each shop as text, and says where the data comes from', () => {
    render(<ResultsMap search={search()} />)
    expect(screen.getByRole('tab', { name: 'Map', selected: true })).toBeInTheDocument()
    expect(screen.getByText('North Shop · Calling…')).toBeInTheDocument()
    expect(screen.getByText('East Shop · Said yes')).toBeInTheDocument()
    expect(screen.getByText(/Map data from OpenStreetMap contributors/)).toBeInTheDocument()
  })

  it('switches to the radar, which sends nothing to any map service', async () => {
    const user = userEvent.setup()
    render(<ResultsMap search={search()} />)
    await user.click(screen.getByRole('tab', { name: 'Radar' }))
    expect(screen.getByRole('img', { name: /Radar showing 2 shops/ })).toBeInTheDocument()
    expect(screen.getByText(/needs no network/)).toBeInTheDocument()
    expect(screen.queryByRole('application')).not.toBeInTheDocument()
    await user.click(screen.getByRole('tab', { name: 'Map' }))
    expect(screen.getByRole('application')).toBeInTheDocument()
  })

  it('labels a skipped shop "Not called"', () => {
    const skipped = { ...attempt('Skipped', 'CANCELLED', 180, 1), result_state: 'NOT_CALLED_STOP_RULE' as const }
    render(<ResultsMap search={search({ attempts: [skipped] })} />)
    expect(screen.getByText('Skipped · Not called (enough answers)')).toBeInTheDocument()
  })

  it('adds nearby shops that have not joined, and never calls them', () => {
    const nearby: NearbyBusiness[] = [
      { id: 'n1', name: 'Corner Chemist', kind: 'REAL_BUSINESS', participation_status: 'INVITED', contactable: false, distance_km: 1.5, bearing_deg: 200, address: null, source: 'osm' },
    ]
    render(<ResultsMap search={search()} nearby={nearby} />)
    expect(screen.getByText('Corner Chemist · Not joined yet (never called)')).toBeInTheDocument()
    expect(screen.getByText(/Sonar only calls shops that joined themselves/)).toBeInTheDocument()
  })

  it('shows a legend with counts that hides and shows each kind of shop', async () => {
    const user = userEvent.setup()
    render(<ResultsMap search={search()} />)
    const yes = screen.getByRole('button', { name: /Said yes: 1/ })
    expect(yes).toHaveAttribute('aria-pressed', 'true')
    await user.click(yes)
    expect(yes).toHaveAttribute('aria-pressed', 'false')
    expect(screen.queryByText('East Shop · Said yes')).not.toBeInTheDocument()
    expect(screen.getByText('East Shop, 2 km: Said yes')).toBeInTheDocument() // list keeps everyone
  })

  it('draws nothing without a centre, a radius or any positioned shop', () => {
    for (const s of [search({ center_lat: null }), search({ radius_km: null }), search({ attempts: [] })]) {
      const { container, unmount } = render(<ResultsMap search={s} />)
      expect(container).toBeEmptyDOMElement()
      unmount()
    }
  })
})

describe('map and the privacy of a result view', () => {
  it('a shop card never reveals more than distance and direction', () => {
    const { container } = render(<ResultsMap search={search()} />)
    expect(within(container).queryByText(/\+91/)).toBeNull()
  })
})

