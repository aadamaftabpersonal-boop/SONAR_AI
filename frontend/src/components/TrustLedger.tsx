import type { ResultView } from '../api'
import { ledgerEntries } from '../ledger'

export function TrustLedger({ results }: { results: ResultView[] }) {
  const entries = ledgerEntries(results)
  if (entries.length === 0) return null
  return (
    <section className="card p-5" aria-labelledby="ledger-h">
      <h2 id="ledger-h" className="text-lg font-bold">
        What Sonar chose not to claim
      </h2>
      <p className="mb-3 text-sm text-[var(--muted)]">
        Most tools hide uncertainty. Sonar lists it: each of these shops is shown exactly as
        reliable as the call allowed, and no more.
      </p>
      <ul className="grid gap-2">
        {entries.map((e) => (
          <li key={e.business} className="rounded-xl bg-[var(--surface-2)] px-3 py-2 text-sm">
            <span className="font-semibold">{e.business}.</span> {e.text}
          </li>
        ))}
      </ul>
    </section>
  )
}
