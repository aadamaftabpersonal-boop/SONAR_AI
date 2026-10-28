import { MAX_QUESTIONS } from '../api'
import type { QuestionKind, QuestionSpec } from '../api'

/** The user's own questions (D-062). Nothing is predefined: whatever they type is what every
 *  shop is asked. The server checks each question before any call is made. */

export const EMPTY_QUESTION: QuestionSpec = { text: '', kind: 'yes_no', want: null, unit: null, rank: null }

const KIND_LABEL: Record<QuestionKind, string> = {
  yes_no: 'Yes or no',
  number: 'A number',
  text: 'Anything',
}

/** Drops empty rows and fields that do not apply to the row's kind, so the request is clean. */
export function cleanQuestions(rows: QuestionSpec[]): QuestionSpec[] {
  return rows
    .map((q) => ({ ...q, text: q.text.replace(/\s+/g, ' ').trim() }))
    .filter((q) => q.text !== '')
    .map((q) => {
      const out: QuestionSpec = { text: q.text, kind: q.kind }
      if (q.kind === 'yes_no' && q.want) out.want = q.want
      if (q.kind === 'number') {
        if (q.unit?.trim()) out.unit = q.unit.trim()
        if (q.rank) out.rank = q.rank
      }
      return out
    })
}

interface Props {
  rows: QuestionSpec[]
  onChange: (rows: QuestionSpec[]) => void
  errorFor: (field: string) => string | null
}

export function QuestionBuilder({ rows, onChange, errorFor }: Props) {
  const set = (i: number, patch: Partial<QuestionSpec>) =>
    onChange(rows.map((q, j) => (j === i ? { ...q, ...patch } : q)))
  const setRank = (i: number, rank: QuestionSpec['rank']) =>
    // only one question can rank shops, so choosing one clears the others
    onChange(rows.map((q, j) => (j === i ? { ...q, rank } : { ...q, rank: rank ? null : q.rank })))
  const remove = (i: number) => onChange(rows.filter((_, j) => j !== i))
  const listError = errorFor('questions')

  return (
    <fieldset className="grid gap-3">
      <legend className="text-sm font-semibold">What should Sonar ask each place?</legend>
      <p className="text-sm text-[var(--muted)]">
        Write the questions in your own words, for example "Are you open until midnight tonight?"
        or "What is the price per hour?". Every place is asked the same questions, and every answer
        is checked against what they actually said.
      </p>
      <ol className="grid gap-3">
        {rows.map((q, i) => {
          const fieldErr = errorFor(`questions.${i}`) ?? errorFor(`questions.${i}.text`)
          return (
            <li key={i} className="grid gap-2 rounded-xl bg-[var(--surface-2)] p-3">
              <div className="flex gap-2">
                <input
                  className="field flex-1"
                  maxLength={140}
                  value={q.text}
                  onChange={(e) => set(i, { text: e.target.value })}
                  placeholder={i === 0 ? 'e.g. Are you open until 12 midnight tonight?' : 'Another question'}
                  aria-label={`Question ${i + 1}`}
                  aria-invalid={!!fieldErr}
                />
                <button type="button" className="btn" onClick={() => remove(i)} aria-label={`Remove question ${i + 1}`}>
                  Remove
                </button>
              </div>
              <div className="flex flex-wrap items-center gap-3 text-sm">
                <label className="flex items-center gap-2">
                  <span>Answer is</span>
                  <select
                    className="field py-1"
                    value={q.kind}
                    onChange={(e) =>
                      set(i, { kind: e.target.value as QuestionKind, want: null, unit: null, rank: null })
                    }
                    aria-label={`Answer type for question ${i + 1}`}
                  >
                    {(Object.keys(KIND_LABEL) as QuestionKind[]).map((k) => (
                      <option key={k} value={k}>
                        {KIND_LABEL[k]}
                      </option>
                    ))}
                  </select>
                </label>
                {q.kind === 'yes_no' && (
                  <label className="flex items-center gap-2">
                    <span>I need</span>
                    <select
                      className="field py-1"
                      value={q.want ?? ''}
                      onChange={(e) => set(i, { want: (e.target.value || null) as QuestionSpec['want'] })}
                      aria-label={`Answer you need for question ${i + 1}`}
                    >
                      <option value="">Just tell me</option>
                      <option value="yes">Yes</option>
                      <option value="no">No</option>
                    </select>
                  </label>
                )}
                {q.kind === 'number' && (
                  <>
                    <input
                      className="field w-40 py-1"
                      maxLength={30}
                      value={q.unit ?? ''}
                      onChange={(e) => set(i, { unit: e.target.value })}
                      placeholder="unit, e.g. rupees per hour"
                      aria-label={`Unit for question ${i + 1}`}
                    />
                    <label className="flex items-center gap-2">
                      <span>Rank by</span>
                      <select
                        className="field py-1"
                        value={q.rank ?? ''}
                        onChange={(e) => setRank(i, (e.target.value || null) as QuestionSpec['rank'])}
                        aria-label={`Rank shops by question ${i + 1}`}
                      >
                        <option value="">Don't rank</option>
                        <option value="lowest">Lowest first</option>
                        <option value="highest">Highest first</option>
                      </select>
                    </label>
                  </>
                )}
              </div>
              {fieldErr && <span className="text-sm text-[var(--bad)]">{fieldErr}</span>}
            </li>
          )
        })}
      </ol>
      {rows.length < MAX_QUESTIONS && (
        <button
          type="button"
          className="btn justify-self-start"
          onClick={() => onChange([...rows, { ...EMPTY_QUESTION }])}
        >
          {rows.length === 0 ? 'Ask your own questions' : 'Add a question'}
        </button>
      )}
      {listError && <span className="text-sm text-[var(--bad)]">{listError}</span>}
    </fieldset>
  )
}
