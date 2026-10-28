// What each shop on the map means (user request: show which shops were approached, which said
// yes, which said no). One function decides the state; labels never imply a shop lacks the item
// unless it said so (NFR-09), and colour is never the only signal (NFR-12).
import type { AttemptView, CallStatus, NearbyBusiness, ResultState, ResultView } from './api'

export type PinState =
  | ResultState
  | 'CALLING'
  | 'JOINED_NOT_CALLED'
  | 'NOT_JOINED'

export const PIN_STYLE: Record<PinState, { label: string; color: string }> = {
  REPORTED_AVAILABLE: { label: 'Said yes', color: '#166534' },
  REPORTED_UNAVAILABLE: { label: 'Said no', color: '#991b1b' },
  ALTERNATIVE_ONLY: { label: 'Has an alternative', color: '#a16207' },
  UNCERTAIN: { label: 'Not sure', color: '#a16207' },
  DECLINED: { label: 'Declined to answer', color: '#6b21a8' },
  NO_ANSWER: { label: 'No answer', color: '#5b6862' },
  CALL_FAILED: { label: 'Call failed', color: '#5b6862' },
  PENDING: { label: 'Waiting to call', color: '#1e40af' },
  CALLING: { label: 'Calling…', color: '#1e40af' },
  CANCELLED: { label: 'Not called (cancelled)', color: '#5b6862' },
  NOT_CALLED_STOP_RULE: { label: 'Not called (enough answers)', color: '#5b6862' },
  JOINED_NOT_CALLED: { label: 'Joined Sonar, not called this time', color: '#0f766e' },
  NOT_JOINED: { label: 'Not joined yet (never called)', color: '#94a3b8' },
}

/** Order of the legend: what was learned first, then what was not. */
export const LEGEND_ORDER: PinState[] = [
  'REPORTED_AVAILABLE',
  'REPORTED_UNAVAILABLE',
  'ALTERNATIVE_ONLY',
  'UNCERTAIN',
  'DECLINED',
  'CALLING',
  'PENDING',
  'NO_ANSWER',
  'CALL_FAILED',
  'NOT_CALLED_STOP_RULE',
  'CANCELLED',
  'JOINED_NOT_CALLED',
  'NOT_JOINED',
]

const IN_CALL: CallStatus[] = ['DISPATCHING', 'DIALING', 'RINGING', 'IN_PROGRESS', 'PROCESSING']

export function pinStateForAttempt(a: Pick<AttemptView, 'status' | 'result_state'>): PinState {
  if (a.result_state === 'PENDING' && IN_CALL.includes(a.status)) return 'CALLING'
  return a.result_state
}

export interface ShopPin {
  id: string
  name: string
  state: PinState
  distance_km: number
  bearing_deg: number
  testLine: boolean
  /** first in the ranking among shops that meet everything asked (custom questions, D-062) */
  best?: boolean
  /** the shop's ranked answer, e.g. "600 rupees per hour" (custom questions only) */
  detail?: string | null
}

/** Custom-question searches (D-062) are about the user's criteria, not stock. */
export const CUSTOM_LABEL: Partial<Record<PinState, string>> = {
  REPORTED_AVAILABLE: 'Meets what you asked',
  REPORTED_UNAVAILABLE: "Doesn't meet what you asked",
  UNCERTAIN: 'Unclear answer',
}

export function stateLabel(state: PinState, custom = false): string {
  return (custom && CUSTOM_LABEL[state]) || PIN_STYLE[state].label
}

/** The top-ranked shop that meets everything, when the search ranks by a number. Results come
 *  back already ordered by the backend, so this is the first one that qualifies. */
export function bestBusinessId(results: ResultView[] | undefined | null): string | null {
  const top = (results ?? []).find(
    (r) => r.result_state === 'REPORTED_AVAILABLE' && r.rank_value != null,
  )
  return top?.business.id ?? null
}

/** One pin per shop: the shop's latest call in this search if it was called, otherwise its
 *  participation (joined or not). Shops that refused or opted out are never in `nearby`. */
export function mergePins(attempts: AttemptView[], nearby: NearbyBusiness[] = []): ShopPin[] {
  const latest = new Map<string, AttemptView>()
  for (const a of attempts) {
    const prev = latest.get(a.business.id)
    if (!prev || a.attempt_number > prev.attempt_number) latest.set(a.business.id, a)
  }
  const pins: ShopPin[] = []
  for (const a of latest.values()) {
    if (a.business.distance_km == null || a.business.bearing_deg == null) continue
    pins.push({
      id: a.business.id,
      name: a.business.name,
      state: pinStateForAttempt(a),
      distance_km: a.business.distance_km,
      bearing_deg: a.business.bearing_deg,
      testLine: a.business.kind === 'TEAM_TEST_LINE',
    })
  }
  for (const b of nearby) {
    if (latest.has(b.id)) continue
    if (b.participation_status === 'DECLINED' || b.participation_status === 'OPTED_OUT') continue
    pins.push({
      id: b.id,
      name: b.name,
      state: b.contactable ? 'JOINED_NOT_CALLED' : 'NOT_JOINED',
      distance_km: b.distance_km,
      bearing_deg: b.bearing_deg,
      testLine: b.kind === 'TEAM_TEST_LINE',
    })
  }
  return pins.sort((x, y) => x.distance_km - y.distance_km)
}

export function legendCounts(pins: ShopPin[]): { state: PinState; count: number }[] {
  const counts = new Map<PinState, number>()
  for (const p of pins) counts.set(p.state, (counts.get(p.state) ?? 0) + 1)
  return LEGEND_ORDER.filter((s) => counts.has(s)).map((s) => ({ state: s, count: counts.get(s)! }))
}

/** The ranked number a shop gave, in its unit, for the map label. Only validated answers. */
export function rankedAnswerText(r: ResultView): string | null {
  if (r.rank_value == null) return null
  const a = (r.answers ?? []).find((x) => x.kind === 'number' && x.validated && x.value === r.rank_value)
  if (!a) return null
  return a.unit ? `${a.value} ${a.unit}` : String(a.value)
}

export function pinLabel(p: ShopPin, custom = false): string {
  let base = stateLabel(p.state, custom)
  if (custom && p.detail) base += ` · ${p.detail}`
  if (p.best) base += ' · Best answer'
  return p.testLine ? `${base} · Team test line (role-play)` : base
}
