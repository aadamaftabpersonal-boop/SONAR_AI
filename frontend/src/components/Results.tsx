import type { ResultView } from '../api'
import { ANSWER_STATES, NOT_UNAVAILABLE, RESULT_LABEL, flagText } from '../copy'
import { clock, timeAgo, useNow } from '../time'

const LABEL_CLASS: Record<string, string> = {
  REPORTED_AVAILABLE: 'chip chip-good',
  REPORTED_UNAVAILABLE: 'chip chip-bad',
  ALTERNATIVE_ONLY: 'chip chip-warn',
  UNCERTAIN: 'chip chip-warn',
  DECLINED: 'chip',
}

function priceText(r: ResultView): string | null {
  const price = r.reported?.price
  if (!price) return r.result_state === 'REPORTED_AVAILABLE' ? 'Price not quoted' : null
  if (price.amount != null) {
    return price.currency === 'INR'
      ? `₹${price.amount}`
      : `${price.amount} (currency not stated)`
  }
  return price.note
}

function ResultCard({ r, now }: { r: ResultView; now: Date }) {
  const simulated = r.data_origin === 'SIMULATED'
  const price = priceText(r)
  return (
    <li className="card p-4">
      <div className="flex flex-wrap items-start justify-between gap-2">
        <div>
          <div className="flex flex-wrap items-center gap-2">
            <h3 className="font-bold">{r.business.name}</h3>
            {r.business.distance_km != null && (
              <span className="text-sm text-[var(--muted)]">{r.business.distance_km} km</span>
            )}
            {r.business.kind === 'TEAM_TEST_LINE' && (
              <span className="chip chip-warn">Team test line (role-play)</span>
            )}
            {simulated && <span className="chip chip-warn">SIMULATED</span>}
          </div>
          {r.answer_summary && <p className="mt-1 text-sm">{r.answer_summary}</p>}
        </div>
        <span className={LABEL_CLASS[r.result_state] ?? 'chip'}>{RESULT_LABEL[r.result_state]}</span>
      </div>

      <div className="mt-2 flex flex-wrap items-center gap-x-4 gap-y-1 text-sm text-[var(--muted)]">
        {price && <span className="font-semibold text-[var(--text)]">{price}</span>}
        {r.answer_timestamp && (
          <span>
            Answered {clock(r.answer_timestamp)} ({timeAgo(r.answer_timestamp, now)})
          </span>
        )}
        {r.freshness.availability && (
          <span>{r.freshness.availability === 'FRESH' ? 'Fresh' : r.freshness.availability === 'STALE' ? 'Stale' : 'Age unknown'}</span>
        )}
      </div>

      {r.flags.length > 0 && (
        <ul className="mt-2 ml-5 list-disc text-sm text-[var(--warn)]">
          {r.flags.map((f) => (
            <li key={f}>{flagText(f)}</li>
          ))}
        </ul>
      )}

      {r.evidence && (
        <details className="mt-3 rounded-xl bg-[var(--surface-2)] p-3 text-sm">
          <summary className="cursor-pointer font-semibold">Evidence</summary>
          <dl className="mt-2 grid gap-1">
            <div>
              <dt className="inline font-semibold">Source: </dt>
              <dd className="inline">Reported by phone, not independently verified</dd>
            </div>
            {r.evidence.excerpt ? (
              <blockquote className="my-1 border-l-4 border-[var(--accent)] pl-3">
                {/* plain text only: React escapes it, and nothing here is ever rendered as HTML */}
                {r.evidence.excerpt}
              </blockquote>
            ) : (
              <p>No quote could be validated against the call transcript.</p>
            )}
            <div>
              <dt className="inline font-semibold">Quote found in transcript: </dt>
              <dd className="inline">{r.evidence.validated ? 'yes' : 'no'}</dd>
            </div>
          </dl>
        </details>
      )}
    </li>
  )
}

export function Results({
  results,
  complete,
  explanation,
  now: nowOverride,
}: {
  results: ResultView[]
  complete: boolean
  explanation: string
  now?: Date
}) {
  const ticking = useNow()
  const now = nowOverride ?? ticking
  const answers = results.filter((r) => ANSWER_STATES.includes(r.result_state))
  const others = results.filter((r) => !ANSWER_STATES.includes(r.result_state))

  return (
    <section aria-labelledby="results-h" className="grid gap-4">
      <div>
        <h2 id="results-h" className="text-lg font-bold">
          What the shops reported
        </h2>
        <p className="text-sm text-[var(--muted)]">{explanation}</p>
      </div>

      {answers.length === 0 && (
        <p className="card p-4 text-sm text-[var(--muted)]" role="status">
          {complete
            ? 'No shop gave a usable answer this time.'
            : 'Answers will appear here as each call finishes.'}
        </p>
      )}
      <ol className="grid gap-3" aria-live="polite">
        {answers.map((r) => (
          <ResultCard key={r.business.id} r={r} now={now} />
        ))}
      </ol>

      {others.length > 0 && (
        <div className="card p-4">
          <h3 className="font-bold">No answer yet, or not completed</h3>
          <p className="mb-2 text-sm font-semibold">{NOT_UNAVAILABLE}</p>
          <ul className="grid gap-2">
            {others.map((r) => (
              <li
                key={r.business.id}
                className="flex flex-wrap items-center justify-between gap-2 rounded-xl bg-[var(--surface-2)] px-3 py-2 text-sm"
              >
                <span>
                  <span className="font-semibold">{r.business.name}</span>
                  {r.data_origin === 'SIMULATED' && (
                    <span className="chip chip-warn ml-2">SIMULATED</span>
                  )}
                  {r.note && <span className="block text-[var(--muted)]">{r.note}</span>}
                </span>
                <span className="chip">{RESULT_LABEL[r.result_state]}</span>
              </li>
            ))}
          </ul>
        </div>
      )}
    </section>
  )
}
