import { render, screen, within } from '@testing-library/react'
import userEvent from '@testing-library/user-event'
import { afterEach, describe, expect, it, vi } from 'vitest'
import type { AttemptView, CallStatus, ResultState, ResultView } from './api'
import { Radar } from './components/Radar'
import { ReadAloud } from './components/ReadAloud'
import { Results } from './components/Results'
import { TrustLedger } from './components/TrustLedger'
import { NOT_UNAVAILABLE, RESULT_LABEL } from './copy'
import { ledgerEntries } from './ledger'
import { radarPoint, ringLabels } from './radar'
import { speechFragments, spokenSummary } from './speech'

const ALL_STATES = Object.keys(RESULT_LABEL) as ResultState[]

function result(state: ResultState, name = 'Shop', over: Partial<ResultView> = {}): ResultView {
  const answered = state === 'REPORTED_AVAILABLE' || state === 'REPORTED_UNAVAILABLE'
  return {
    business: { id: name, name, kind: 'REAL_BUSINESS', distance_km: 1 },
    result_state: state,
    data_origin: 'LIVE_CALL',
    answer_timestamp: answered ? '2026-11-02T10:41:12Z' : null,
    freshness: {},
    reported: null,
    answer_summary: answered ? `Reported by phone: ${state === 'REPORTED_AVAILABLE' ? 'exact item available' : 'said the item is not available'}.` : null,
    evidence: null,
    verification_status: null,
    flags: [],
    note: answered ? null : `Note for ${name}. ${NOT_UNAVAILABLE}`,
    ...over,
  }
}

const claimsUnavailable = (text: string) =>
  /unavailable|out of stock|not available/i.test(text.replaceAll(NOT_UNAVAILABLE, ''))

// --- trust ledger ----------------------------------------------------------------------------

describe('trust ledger', () => {
  it('has an entry for every state that carries doubt, and none for clean answers', () => {
    expect(ledgerEntries([result('REPORTED_AVAILABLE'), result('REPORTED_UNAVAILABLE')])).toEqual([])
    for (const state of ALL_STATES.filter((s) => !s.startsWith('REPORTED'))) {
      expect(ledgerEntries([result(state)]), state).toHaveLength(1)
    }
  })

  it('never claims unavailability for silence, failure, refusal, doubt or a skipped call', () => {
    for (const state of ALL_STATES.filter((s) => s !== 'REPORTED_UNAVAILABLE')) {
      const [entry] = ledgerEntries([result(state, 'S', { flags: ['CONTRADICTORY'] })])
      if (entry) expect(claimsUnavailable(entry.text), `${state}: ${entry.text}`).toBe(false)
    }
  })

  it('explains an uncertain answer using its flags in plain language', () => {
    const [e] = ledgerEntries([result('UNCERTAIN', 'Hedger', { flags: ['EVIDENCE_NOT_FOUND', 'BUSINESS_UNSURE'] })])
    expect(e.business).toBe('Hedger')
    expect(e.text).toMatch(/could not be found in the call transcript/)
    expect(e.text).toMatch(/not sure/)
  })

  it('flags a reported-available answer that has caveats', () => {
    const [e] = ledgerEntries([result('REPORTED_AVAILABLE', 'A', { flags: ['MISSING_PRICE'] })])
    expect(e.text).toMatch(/No price was quoted/)
  })

  it('says a skipped shop was not called and why', () => {
    const [e] = ledgerEntries([result('NOT_CALLED_STOP_RULE')])
    expect(e.text).toMatch(/enough shops had already confirmed/)
  })

  it('renders nothing when there is nothing to disclose', () => {
    const { container } = render(<TrustLedger results={[result('REPORTED_AVAILABLE')]} />)
    expect(container).toBeEmptyDOMElement()
  })

  it('renders each disclosure under a heading', () => {
    render(<TrustLedger results={[result('NO_ANSWER', 'Silent'), result('UNCERTAIN', 'Hedger')]} />)
    expect(screen.getByRole('heading', { name: /chose not to claim/i })).toBeInTheDocument()
    expect(screen.getAllByRole('listitem')).toHaveLength(2)
    expect(screen.getByText(/Silent\./)).toBeInTheDocument()
  })
})

// --- radar -----------------------------------------------------------------------------------

const C = { x: 100, y: 100 }

describe('radar geometry', () => {
  it.each([
    [0, { x: 100, y: 50 }],
    [90, { x: 150, y: 100 }],
    [180, { x: 100, y: 150 }],
    [270, { x: 50, y: 100 }],
  ])('puts bearing %i degrees at the right compass point', (bearing, expected) => {
    const p = radarPoint(1, bearing, 2, 100, C) // half the radius
    expect(p.x).toBeCloseTo(expected.x, 5)
    expect(p.y).toBeCloseTo(expected.y, 5)
  })

  it('places a shop at the centre when it is at distance zero', () => {
    expect(radarPoint(0, 123, 3, 100, C)).toEqual(C)
  })

  it('pins a shop beyond the radius to the edge instead of drawing it outside', () => {
    const p = radarPoint(50, 90, 3, 100, C)
    expect(p.x).toBeCloseTo(200, 5)
  })

  it('survives a zero or negative radius and negative distances', () => {
    expect(radarPoint(1, 0, 0, 100, C)).toEqual(C)
    expect(radarPoint(-5, 0, 3, 100, C)).toEqual(C)
  })

  it('labels the three rings in kilometres', () => {
    expect(ringLabels(3)).toEqual([1, 2, 3])
    expect(ringLabels(1.5)).toEqual([0.5, 1, 1.5])
  })
})

function attempt(name: string, status: CallStatus, distance: number | null, bearing: number | null, rs: ResultState = 'PENDING'): AttemptView {
  return {
    attempt_id: name,
    business: { id: name, name, kind: 'REAL_BUSINESS', distance_km: distance, bearing_deg: bearing },
    status,
    attempt_number: 1,
    updated_at: '2026-11-02T10:00:00Z',
    result_state: rs,
  }
}

describe('radar view', () => {
  it('writes each shop name and status as text, never colour alone', () => {
    render(<Radar radiusKm={3} attempts={[attempt('North Shop', 'RINGING', 1, 0), attempt('East Shop', 'COMPLETED', 2, 90)]} />)
    const svg = screen.getByRole('img')
    expect(within(svg).getByText('North Shop')).toBeInTheDocument()
    expect(within(svg).getByText('Ringing')).toBeInTheDocument()
    expect(within(svg).getByText('Done')).toBeInTheDocument()
    expect(svg).toHaveAccessibleName(/2 shops within 3 kilometres/)
  })

  it('labels a skipped shop "Not called", not "Cancelled"', () => {
    render(<Radar radiusKm={3} attempts={[attempt('Skipped', 'CANCELLED', 1, 45, 'NOT_CALLED_STOP_RULE')]} />)
    expect(screen.getByText('Not called')).toBeInTheDocument()
    expect(screen.queryByText('Cancelled')).not.toBeInTheDocument()
  })

  it('shows the latest attempt per shop, once', () => {
    const first = attempt('Retry Shop', 'NO_ANSWER', 1, 10)
    const second = { ...attempt('Retry Shop', 'PENDING', 1, 10), attempt_number: 2 }
    render(<Radar radiusKm={3} attempts={[first, second]} />)
    expect(screen.getAllByText('Retry Shop')).toHaveLength(1)
    expect(screen.getByText('Queued')).toBeInTheDocument()
  })

  it('draws nothing when no shop has a position', () => {
    const { container } = render(<Radar radiusKm={3} attempts={[attempt('No Pos', 'RINGING', null, null)]} />)
    expect(container).toBeEmptyDOMElement()
  })

  it('makes no network request and loads no map tiles', () => {
    const fetchSpy = vi.spyOn(globalThis, 'fetch')
    const { container } = render(<Radar radiusKm={3} attempts={[attempt('A', 'RINGING', 1, 0)]} />)
    expect(fetchSpy).not.toHaveBeenCalled()
    expect(container.querySelector('img, iframe, image')).toBeNull()
    fetchSpy.mockRestore()
  })

  it('explains that it shows straight-line distance, not driving routes', () => {
    render(<Radar radiusKm={3} attempts={[attempt('A', 'RINGING', 1, 0)]} />)
    expect(screen.getByText(/straight-line distance/)).toBeInTheDocument()
  })
})

// --- read aloud ------------------------------------------------------------------------------

describe('read aloud', () => {
  afterEach(() => {
    vi.unstubAllGlobals()
  })

  const mockSpeech = () => {
    const speak = vi.fn()
    const cancel = vi.fn()
    vi.stubGlobal('speechSynthesis', { speak, cancel })
    vi.stubGlobal('SpeechSynthesisUtterance', class { text: string; onend: unknown; onerror: unknown; constructor(t: string) { this.text = t } })
    Object.defineProperty(window, 'speechSynthesis', { configurable: true, value: { speak, cancel } })
    return { speak, cancel }
  }

  it('speaks only strings that the page also shows, for every result state', () => {
    for (const state of ALL_STATES) {
      const r = result(state, 'Fixture Shop')
      const { container, unmount } = render(
        <Results results={[r]} complete={true} explanation="Ordered by x." now={new Date('2026-11-02T10:45:00Z')} />,
      )
      const shown = container.textContent ?? ''
      for (const fragment of speechFragments([r], 'Ordered by x.')) {
        // the first fragment is the ranking explanation; the rest are name + label and the summary or note
        const parts = fragment.split('. ').map((p) => p.replace(/\.$/, ''))
        for (const part of parts) expect(shown, `${state}: "${part}"`).toContain(part)
      }
      unmount()
    }
  })

  it('never says unavailable for a state that is not an explicit unavailable answer', () => {
    for (const state of ALL_STATES.filter((s) => s !== 'REPORTED_UNAVAILABLE')) {
      expect(claimsUnavailable(spokenSummary([result(state)], 'Ordered by x.')), state).toBe(false)
    }
  })

  it('starts and stops speech from one button', async () => {
    const { speak, cancel } = mockSpeech()
    const user = userEvent.setup()
    render(<ReadAloud results={[result('REPORTED_AVAILABLE', 'Corner')]} explanation="Ordered." />)
    await user.click(screen.getByRole('button', { name: /read results aloud/i }))
    expect(speak).toHaveBeenCalledTimes(1)
    expect(speak.mock.calls[0][0].text).toContain('Corner. Reported available by phone.')
    await user.click(screen.getByRole('button', { name: /stop reading/i }))
    expect(cancel).toHaveBeenCalled()
  })

  it('is hidden when the browser cannot speak', () => {
    const { container } = render(<ReadAloud results={[result('NO_ANSWER')]} explanation="x" />)
    expect(container).toBeEmptyDOMElement()
  })

  it('is hidden when there is nothing to read', () => {
    mockSpeech()
    const { container } = render(<ReadAloud results={[]} explanation="x" />)
    expect(container).toBeEmptyDOMElement()
  })
})
