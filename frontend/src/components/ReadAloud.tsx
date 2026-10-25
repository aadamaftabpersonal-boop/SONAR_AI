import { useEffect, useState } from 'react'
import type { ResultView } from '../api'
import { speechSupported, spokenSummary } from '../speech'

/** Hidden entirely in browsers without speech synthesis. Reads only what is on screen. */
export function ReadAloud({ results, explanation }: { results: ResultView[]; explanation: string }) {
  const [speaking, setSpeaking] = useState(false)
  useEffect(() => () => window.speechSynthesis?.cancel(), [])
  if (!speechSupported() || results.length === 0) return null

  const toggle = () => {
    if (speaking) {
      window.speechSynthesis.cancel()
      setSpeaking(false)
      return
    }
    const utterance = new SpeechSynthesisUtterance(spokenSummary(results, explanation))
    utterance.onend = utterance.onerror = () => setSpeaking(false)
    window.speechSynthesis.speak(utterance)
    setSpeaking(true)
  }

  return (
    <button type="button" className="btn" onClick={toggle} aria-pressed={speaking}>
      {speaking ? 'Stop reading' : 'Read results aloud'}
    </button>
  )
}
