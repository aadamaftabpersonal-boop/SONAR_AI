import { describe, expect, it } from 'vitest'
import type { ResultState } from './api'
import { CALL_STATUS_LABEL, FLAG_TEXT, NOT_UNAVAILABLE, RESULT_LABEL, flagText } from './copy'

// NFR-09: only an explicit, validated "not available" may ever read as unavailable.
const MUST_NOT_CLAIM: ResultState[] = [
  'NO_ANSWER',
  'CALL_FAILED',
  'DECLINED',
  'PENDING',
  'CANCELLED',
  'UNCERTAIN',
  'ALTERNATIVE_ONLY',
  'NOT_CALLED_STOP_RULE',
  'REPORTED_AVAILABLE',
]

const claimsUnavailable = (text: string) =>
  /unavailable|out of stock|not available/i.test(text.replaceAll(NOT_UNAVAILABLE, ''))

describe('result wording', () => {
  it.each(MUST_NOT_CLAIM)('%s never claims unavailability', (state) => {
    expect(claimsUnavailable(RESULT_LABEL[state])).toBe(false)
  })

  it('only REPORTED_UNAVAILABLE reads as unavailable', () => {
    expect(RESULT_LABEL.REPORTED_UNAVAILABLE).toMatch(/unavailable/i)
    const others = Object.entries(RESULT_LABEL).filter(([k]) => k !== 'REPORTED_UNAVAILABLE')
    for (const [, label] of others) expect(claimsUnavailable(label)).toBe(false)
  })

  it('no call status label mentions unavailability', () => {
    for (const label of Object.values(CALL_STATUS_LABEL)) expect(claimsUnavailable(label)).toBe(false)
  })

  it('no flag text claims unavailability', () => {
    for (const text of Object.values(FLAG_TEXT)) expect(claimsUnavailable(text)).toBe(false)
  })

  it('unknown flags fall back to readable text, never a raw code dump', () => {
    expect(flagText('SOMETHING_NEW')).toBe('something new')
  })

  it('every backend call status has a label', () => {
    expect(Object.keys(CALL_STATUS_LABEL)).toHaveLength(16)
  })
})
