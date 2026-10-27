import { describe, expect, it } from 'vitest'
import type { AttemptView, NearbyBusiness, ResultState } from './api'
import { LEGEND_ORDER, PIN_STYLE, legendCounts, mergePins, pinLabel, pinStateForAttempt } from './pins'

const attempt = (id: string, over: Partial<AttemptView> = {}): AttemptView => ({
  attempt_id: `a-${id}`,
  business: { id, name: `Shop ${id}`, kind: 'REAL_BUSINESS', distance_km: 1, bearing_deg: 90 },
  status: 'COMPLETED',
  attempt_number: 1,
  updated_at: '2026-11-02T10:41:12Z',
  result_state: 'REPORTED_AVAILABLE',
  ...over,
})

const near = (id: string, over: Partial<NearbyBusiness> = {}): NearbyBusiness => ({
  id,
  name: `Near ${id}`,
  kind: 'REAL_BUSINESS',
  participation_status: 'INVITED',
  contactable: false,
  distance_km: 2,
  bearing_deg: 180,
  address: null,
  source: 'osm',
  ...over,
})

const claimsUnavailable = (t: string) => /unavailable|out of stock|not available|don't have/i.test(t)

describe('pins', () => {
  it('every state has a label and a colour, and every state is in the legend order', () => {
    for (const [state, style] of Object.entries(PIN_STYLE)) {
      expect(style.label.length).toBeGreaterThan(0)
      expect(style.color).toMatch(/^#/)
      expect(LEGEND_ORDER).toContain(state)
    }
  })

  it('only "Said no" reads as a negative answer', () => {
    for (const [state, style] of Object.entries(PIN_STYLE)) {
      if (state !== 'REPORTED_UNAVAILABLE') expect(claimsUnavailable(style.label)).toBe(false)
    }
    expect(PIN_STYLE.REPORTED_UNAVAILABLE.label).toBe('Said no')
  })

  it('a pending call that is ringing shows as calling', () => {
    expect(pinStateForAttempt({ status: 'RINGING', result_state: 'PENDING' })).toBe('CALLING')
    expect(pinStateForAttempt({ status: 'PENDING', result_state: 'PENDING' })).toBe('PENDING')
    const states: ResultState[] = ['NO_ANSWER', 'REPORTED_UNAVAILABLE', 'NOT_CALLED_STOP_RULE']
    for (const s of states) expect(pinStateForAttempt({ status: 'COMPLETED', result_state: s })).toBe(s)
  })

  it('merges called shops with nearby shops, the call winning', () => {
    const pins = mergePins(
      [attempt('1'), attempt('1', { attempt_number: 2, result_state: 'NO_ANSWER' })],
      [near('1'), near('2'), near('3', { participation_status: 'CONSENTED', contactable: true })],
    )
    expect(pins.map((p) => [p.id, p.state])).toEqual([
      ['1', 'NO_ANSWER'],
      ['2', 'NOT_JOINED'],
      ['3', 'JOINED_NOT_CALLED'],
    ])
  })

  it('never shows shops that said no to joining or opted out', () => {
    const pins = mergePins([], [
      near('x', { participation_status: 'DECLINED' }),
      near('y', { participation_status: 'OPTED_OUT' }),
    ])
    expect(pins).toEqual([])
  })

  it('skips called shops without a position', () => {
    const a = attempt('1')
    a.business.bearing_deg = null
    expect(mergePins([a])).toEqual([])
  })

  it('counts the legend in a fixed order', () => {
    const pins = mergePins([attempt('1'), attempt('2', { result_state: 'NO_ANSWER' })], [near('3')])
    expect(legendCounts(pins)).toEqual([
      { state: 'REPORTED_AVAILABLE', count: 1 },
      { state: 'NO_ANSWER', count: 1 },
      { state: 'NOT_JOINED', count: 1 },
    ])
  })

  it('labels test lines as role-play', () => {
    const [p] = mergePins([attempt('1', { business: { id: '1', name: 'T', kind: 'TEAM_TEST_LINE', distance_km: 1, bearing_deg: 0 } })])
    expect(pinLabel(p)).toBe('Said yes · Team test line (role-play)')
  })
})
