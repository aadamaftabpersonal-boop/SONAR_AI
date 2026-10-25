// The trust ledger (Bible 52.4): every shop Sonar chose NOT to make a claim about, and why, in
// plain language. It is built only from fields the API already returns (state and flags), so it
// can never say more than the validator did. Wording never claims unavailability for silence,
// failure, refusal, uncertainty or a skipped call (NFR-09).
import type { ResultState, ResultView } from './api'
import { NOT_UNAVAILABLE, flagText } from './copy'

export interface LedgerEntry {
  business: string
  text: string
}

const reasons = (r: ResultView) => r.flags.map(flagText)

const BY_STATE: Record<ResultState, (r: ResultView) => string | null> = {
  REPORTED_AVAILABLE: (r) =>
    r.flags.length ? `Reported available, but note: ${reasons(r).join(' ')}` : null,
  REPORTED_UNAVAILABLE: (r) => (r.flags.length ? `Reported unavailable. ${reasons(r).join(' ')}` : null),
  ALTERNATIVE_ONLY: () =>
    'Offered something other than what you asked for, so it is not shown as having the item.',
  UNCERTAIN: (r) =>
    r.flags.length
      ? `Shown as Uncertain. ${reasons(r).join(' ')} ${NOT_UNAVAILABLE}`
      : `The shop was not sure, so Sonar makes no claim. ${NOT_UNAVAILABLE}`,
  DECLINED: () => `The shop declined to answer. ${NOT_UNAVAILABLE}`,
  NO_ANSWER: () => `Did not answer, so Sonar says nothing about it. ${NOT_UNAVAILABLE}`,
  CALL_FAILED: () => `The call could not be completed, so nothing was learned. ${NOT_UNAVAILABLE}`,
  PENDING: () => 'Still waiting for this call to finish.',
  CANCELLED: () => `The call was cancelled before an answer was recorded. ${NOT_UNAVAILABLE}`,
  NOT_CALLED_STOP_RULE: () =>
    `Not called: enough shops had already confirmed. ${NOT_UNAVAILABLE}`,
}

export function ledgerEntries(results: ResultView[]): LedgerEntry[] {
  const entries: LedgerEntry[] = []
  for (const r of results) {
    const text = BY_STATE[r.result_state](r)
    if (text) entries.push({ business: r.business.name, text })
  }
  return entries
}
