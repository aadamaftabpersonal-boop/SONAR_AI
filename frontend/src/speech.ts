// Read-aloud (Bible 52.1, NFR-18). The spoken text is assembled ONLY from strings the page already
// shows: the shop's name, its state label, and the templated summary or note. No free prose is
// generated for speech, so what is heard is what is displayed.
import type { ResultView } from './api'
import { RESULT_LABEL } from './copy'

export function speechFragments(results: ResultView[], explanation: string): string[] {
  const parts = [explanation]
  for (const r of results) {
    parts.push(`${r.business.name}. ${RESULT_LABEL[r.result_state]}.`)
    // both are shown on the card, so both are spoken: nothing is heard that is not also read
    if (r.answer_summary) parts.push(r.answer_summary)
    if (r.note) parts.push(r.note)
  }
  return parts
}

export const spokenSummary = (results: ResultView[], explanation: string) =>
  speechFragments(results, explanation).join(' ')

export const speechSupported = () =>
  typeof window !== 'undefined' &&
  'speechSynthesis' in window &&
  typeof SpeechSynthesisUtterance !== 'undefined'
