// All user-facing wording for states lives here so it can be reviewed in one place.
// Rule (NFR-09): only an explicit, validated "not available" answer may read as unavailable.
// Silence, failure, refusal, uncertainty and skipped calls never do.
import type { CallStatus, ResultState } from './api'

export const NOT_UNAVAILABLE = 'This does not mean the item is unavailable.'

export const RESULT_LABEL: Record<ResultState, string> = {
  REPORTED_AVAILABLE: 'Reported available by phone',
  REPORTED_UNAVAILABLE: 'Reported unavailable by phone',
  ALTERNATIVE_ONLY: 'Alternative only',
  UNCERTAIN: 'Uncertain',
  DECLINED: 'Declined to answer',
  NO_ANSWER: 'No answer',
  CALL_FAILED: 'Call failed',
  PENDING: 'Pending',
  CANCELLED: 'Cancelled',
  NOT_CALLED_STOP_RULE: 'Not called (enough answers)',
}

// States that carry an answer; everything else is a "no answer" outcome shown below the list.
export const ANSWER_STATES: ResultState[] = [
  'REPORTED_AVAILABLE',
  'ALTERNATIVE_ONLY',
  'UNCERTAIN',
  'REPORTED_UNAVAILABLE',
  'DECLINED',
]

export const CALL_STATUS_LABEL: Record<CallStatus, string> = {
  PENDING: 'Queued',
  DISPATCHING: 'Dialing',
  DISPATCH_UNKNOWN: 'Status unknown',
  DIALING: 'Dialing',
  RINGING: 'Ringing',
  IN_PROGRESS: 'In call',
  PROCESSING: 'Processing',
  COMPLETED: 'Done',
  NO_ANSWER: 'No answer',
  BUSY: 'No answer',
  FAILED: 'Failed',
  ERROR: 'Failed',
  CANCELLED: 'Cancelled',
  STOPPED: 'Failed',
  INSUFFICIENT_BALANCE: 'Failed',
  TIMED_OUT: 'Timed out',
}

export const FLAG_TEXT: Record<string, string> = {
  EVIDENCE_NOT_FOUND: 'The quoted answer could not be found in the call transcript.',
  CONTRADICTORY: 'What the shop said contradicted itself, so Sonar did not pick a side.',
  EXACT_MATCH_UNKNOWN: 'It was not confirmed that this is exactly the requested item.',
  EXACT_MATCH_NOT_CONFIRMED: 'The shop said it is not exactly the requested item.',
  BUSINESS_UNSURE: 'The shop was not sure.',
  MISSING_PRICE: 'No price was quoted.',
  PRICE_NOT_IN_TRANSCRIPT: 'A price was reported but not heard in the call, so it was dropped.',
  PRICE_CURRENCY_UNSTATED: 'The currency was not stated.',
  PRICE_NOT_EXACT_ITEM: 'The price was for a different item.',
  PRICE_IMPLAUSIBLE: 'The price looked implausible, so it was dropped.',
  NO_EXTRACTION: 'No structured answer was captured.',
  INVALID_AVAILABILITY: 'The captured answer was not in a recognised form.',
  OPT_OUT_REQUESTED: 'The business asked not to be called again. Sonar will not call them again.',
}

export function flagText(flag: string): string {
  return FLAG_TEXT[flag] ?? flag.toLowerCase().replaceAll('_', ' ')
}
