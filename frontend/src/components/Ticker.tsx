// Live transcript ticker (Bible 51 tier T-1, T15.2). Shows only what the server returns: lines
// already transcribed for calls in progress, for team test lines and simulated calls. Text is
// rendered as plain text (React escapes it); nothing here is ever treated as HTML.
import { useEffect, useState } from 'react'
import { api } from '../api'
import type { LiveCall } from '../api'

const REASON_TEXT: Record<string, string> = {
  no_live_text: 'No live text yet.',
  not_shown: "A real shop's words are not shown live.",
  provider_unavailable: 'Live text is unavailable right now.',
}

export function TickerView({ calls }: { calls: LiveCall[] }) {
  if (calls.length === 0) return null
  return (
    <section className="card p-5" aria-labelledby="ticker-h">
      <h2 id="ticker-h" className="text-lg font-bold">
        Live on the call
      </h2>
      <ul className="mt-3 grid gap-3">
        {calls.map((c) => (
          <li key={c.attempt_id} className="rounded-xl bg-[var(--surface-2)] p-3 text-sm">
            <p className="font-semibold">{c.business_name}</p>
            <div aria-live="polite" className="mt-1 grid gap-1">
              {c.lines.length === 0 ? (
                <p className="text-[var(--muted)]">{REASON_TEXT[c.reason ?? 'no_live_text']}</p>
              ) : (
                c.lines.map((line, i) => (
                  <p key={i}>
                    <span className="font-semibold">{line.speaker}:</span> {line.text}
                  </p>
                ))
              )}
            </div>
          </li>
        ))}
      </ul>
    </section>
  )
}

/** Polls the ticker every 2 s while the search runs. Errors simply hide the panel. */
export function Ticker({ searchId, running }: { searchId: string; running: boolean }) {
  const [calls, setCalls] = useState<LiveCall[]>([])

  useEffect(() => {
    if (!running) {
      setCalls([])
      return
    }
    let stopped = false
    const tick = () =>
      api.getLive(searchId).then(
        (v) => !stopped && setCalls(v.calls),
        () => !stopped && setCalls([]),
      )
    tick()
    const timer = window.setInterval(tick, 2000)
    return () => {
      stopped = true
      window.clearInterval(timer)
    }
  }, [searchId, running])

  return <TickerView calls={calls} />
}
