import type { AttemptView, SearchView } from '../api'
import { CALL_STATUS_LABEL } from '../copy'
import { elapsed } from '../time'

const BUSY_STATES = new Set(['DISPATCHING', 'DIALING', 'RINGING', 'IN_PROGRESS', 'PROCESSING'])

function chipClass(a: AttemptView): string {
  if (a.status === 'COMPLETED') return 'chip chip-good'
  if (BUSY_STATES.has(a.status)) return 'chip chip-info'
  if (['FAILED', 'ERROR', 'STOPPED', 'INSUFFICIENT_BALANCE', 'TIMED_OUT'].includes(a.status))
    return 'chip chip-bad'
  return 'chip'
}

function kindBadge(a: AttemptView) {
  return a.business.kind === 'TEAM_TEST_LINE' ? (
    <span className="chip chip-warn">Team test line (role-play)</span>
  ) : (
    <span className="chip">Consented</span>
  )
}

interface Props {
  search: SearchView
  running: boolean
  onCancel: () => void
}

export function Progress({ search, running, onCancel }: Props) {
  // one row per business: the latest attempt decides what to show
  const latest = new Map<string, AttemptView>()
  for (const a of search.attempts) {
    const prev = latest.get(a.business.id)
    if (!prev || a.attempt_number > prev.attempt_number) latest.set(a.business.id, a)
  }
  const rows = [...latest.values()]
  const finished = rows.filter((a) =>
    ['COMPLETED', 'NO_ANSWER', 'BUSY', 'FAILED', 'ERROR', 'CANCELLED', 'STOPPED', 'TIMED_OUT', 'INSUFFICIENT_BALANCE'].includes(a.status),
  ).length

  return (
    <section className="card p-5" aria-labelledby="progress-h">
      <div className="mb-3 flex flex-wrap items-center justify-between gap-3">
        <h2 id="progress-h" className="flex items-center gap-3 text-lg font-bold">
          {running && <span className="ping" aria-hidden="true" />}
          {running ? 'Calling now' : 'Calls finished'}
        </h2>
        <div className="flex items-center gap-3 text-sm text-[var(--muted)]">
          <span>
            {finished} of {rows.length} finished
          </span>
          {elapsed(search.started_at ?? search.created_at, search.completed_at) && (
            <span>· {elapsed(search.started_at ?? search.created_at, search.completed_at)}</span>
          )}
          {running && (
            <button className="btn" onClick={onCancel}>
              Cancel
            </button>
          )}
        </div>
      </div>
      {running && (
        <p className="mb-3 text-sm text-[var(--muted)]">
          Cancelling stops further calls. A call already in progress will finish and be recorded.
        </p>
      )}
      {search.stopped_early && (
        <p
          role="status"
          className="mb-3 rounded-xl bg-[var(--info-bg)] px-3 py-2 text-sm text-[var(--info)]"
        >
          Stopped early: enough shops had already confirmed, so {search.calls_avoided}{' '}
          {search.calls_avoided === 1 ? 'call was' : 'calls were'} not made. Skipped shops are listed
          below, and this does not mean they lack the item.
        </p>
      )}
      <ul className="grid gap-2" aria-label="Calls">
        {rows.map((a) => (
          <li
            key={a.business.id}
            className="flex flex-wrap items-center justify-between gap-2 rounded-xl bg-[var(--surface-2)] px-3 py-2"
          >
            <div className="flex flex-wrap items-center gap-2">
              <span className="font-semibold">{a.business.name}</span>
              {a.business.distance_km != null && (
                <span className="text-sm text-[var(--muted)]">{a.business.distance_km} km</span>
              )}
              {kindBadge(a)}
            </div>
            <div className="flex items-center gap-2">
              {a.attempt_number > 1 && <span className="text-sm text-[var(--muted)]">retry {a.attempt_number - 1}</span>}
              <span className={chipClass(a)}>
                {a.result_state === 'NOT_CALLED_STOP_RULE' ? 'Not called' : CALL_STATUS_LABEL[a.status]}
              </span>
            </div>
          </li>
        ))}
      </ul>
    </section>
  )
}
