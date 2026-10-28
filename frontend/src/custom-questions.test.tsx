// D-062: the user's own questions. The builder sends only what applies, answers are shown with
// the shop's words, and nothing unanswered ever reads as "no".
import { fireEvent, render, screen, within } from '@testing-library/react'
import { useState } from 'react'
import { describe, expect, it, vi } from 'vitest'
import type { AnswerView, QuestionSpec, ResultView } from './api'
import { QuestionBuilder, cleanQuestions } from './components/QuestionBuilder'
import { Results } from './components/Results'
import { NOT_A_NO, answerText, customResultLabel, flagText } from './copy'
import { bestBusinessId, pinLabel, rankedAnswerText } from './pins'

const NOW = new Date('2026-11-02T10:45:00Z')

const answer = (over: Partial<AnswerView> = {}): AnswerView => ({
  key: 'q1',
  question: 'Are you open until 12 midnight tonight?',
  kind: 'yes_no',
  value: true,
  unit: null,
  quote: 'Yes, we are open till midnight.',
  validated: true,
  meets: true,
  flag: null,
  ...over,
})

const price = (value: number | null, over: Partial<AnswerView> = {}) =>
  answer({
    key: 'q2',
    question: 'What is the price per hour?',
    kind: 'number',
    value,
    unit: 'rupees per hour',
    quote: value == null ? null : `It is ${value} rupees.`,
    meets: null,
    ...over,
  })

function result(name: string, over: Partial<ResultView> = {}): ResultView {
  return {
    business: { id: name, name, kind: 'REAL_BUSINESS', distance_km: 1 },
    result_state: 'REPORTED_AVAILABLE',
    data_origin: 'SIMULATED',
    answer_timestamp: '2026-11-02T10:41:12Z',
    freshness: {},
    reported: null,
    answer_summary: 'Meets 1 of 1 of what you asked; answered 2 of 2.',
    evidence: null,
    verification_status: 'REPORTED_BY_PHONE',
    flags: [],
    note: null,
    answers: [answer(), price(600)],
    rank_value: 600,
    ...over,
  }
}

describe('cleanQuestions', () => {
  it('drops empty rows and options that do not fit the kind', () => {
    const rows: QuestionSpec[] = [
      { text: '  Open   till midnight? ', kind: 'yes_no', want: 'yes', unit: 'x', rank: 'lowest' },
      { text: '', kind: 'yes_no' },
      { text: 'Price per hour?', kind: 'number', want: 'yes', unit: ' rupees ', rank: 'lowest' },
      { text: 'Which sports?', kind: 'text', want: 'no', unit: 'u', rank: 'highest' },
    ]
    expect(cleanQuestions(rows)).toEqual([
      { text: 'Open till midnight?', kind: 'yes_no', want: 'yes' },
      { text: 'Price per hour?', kind: 'number', unit: 'rupees', rank: 'lowest' },
      { text: 'Which sports?', kind: 'text' },
    ])
  })
})

function Harness({ onRows }: { onRows: (rows: QuestionSpec[]) => void }) {
  const [rows, setRows] = useState<QuestionSpec[]>([])
  return (
    <QuestionBuilder
      rows={rows}
      onChange={(next) => {
        setRows(next)
        onRows(next)
      }}
      errorFor={() => null}
    />
  )
}

describe('QuestionBuilder', () => {
  it('adds free-text questions and allows only one ranking', () => {
    const onRows = vi.fn()
    render(<Harness onRows={onRows} />)
    fireEvent.click(screen.getByRole('button', { name: 'Ask your own questions' }))
    fireEvent.change(screen.getByLabelText('Question 1'), { target: { value: 'Price per hour?' } })
    fireEvent.change(screen.getByLabelText('Answer type for question 1'), { target: { value: 'number' } })
    fireEvent.change(screen.getByLabelText('Rank shops by question 1'), { target: { value: 'lowest' } })
    fireEvent.click(screen.getByRole('button', { name: 'Add a question' }))
    fireEvent.change(screen.getByLabelText('Answer type for question 2'), { target: { value: 'number' } })
    fireEvent.change(screen.getByLabelText('Rank shops by question 2'), { target: { value: 'highest' } })
    const last: QuestionSpec[] = onRows.mock.calls.at(-1)![0]
    expect(last.map((q) => q.rank)).toEqual([null, 'highest'])
  })

  it('stops at five questions', () => {
    render(<Harness onRows={() => {}} />)
    fireEvent.click(screen.getByRole('button', { name: 'Ask your own questions' }))
    for (let i = 0; i < 4; i++) fireEvent.click(screen.getByRole('button', { name: 'Add a question' }))
    expect(screen.queryByRole('button', { name: 'Add a question' })).toBeNull()
    expect(screen.getAllByRole('textbox', { name: /^Question \d$/ })).toHaveLength(5)
  })
})

describe('custom wording', () => {
  it('labels by what was asked, not by stock', () => {
    expect(customResultLabel(result('A'))).toBe('Meets what you asked')
    expect(customResultLabel(result('A', { answers: [price(600)] }))).toBe('Answered')
    expect(customResultLabel(result('A', { result_state: 'REPORTED_UNAVAILABLE' }))).toBe(
      "Doesn't meet what you asked",
    )
    expect(customResultLabel(result('A', { result_state: 'UNCERTAIN' }))).toBe('Unclear answer')
  })

  it('never shows an unanswered or unchecked answer as no', () => {
    expect(answerText(answer({ value: null }))).toBe('Not clearly answered')
    expect(answerText(answer({ value: false, validated: false }))).toBe('Not clearly answered')
    expect(answerText(answer({ value: false }))).toBe('No')
    expect(answerText(price(600))).toBe('600 rupees per hour')
  })

  it('has plain text for every new flag', () => {
    for (const f of ['NOT_ANSWERED', 'NOT_A_YES_OR_NO', 'NOT_A_NUMBER', 'NUMBER_NOT_HEARD', 'ANSWERS_UNREADABLE']) {
      expect(flagText(f)).not.toContain('_')
    }
  })
})

describe('map pins for custom questions', () => {
  it('marks the top-ranked shop that meets everything, with its answer', () => {
    const results = [
      result('Cheap'),
      result('Dear', { rank_value: 900, answers: [answer(), price(900)] }),
      result('Closed', { result_state: 'REPORTED_UNAVAILABLE', rank_value: 300 }),
    ]
    expect(bestBusinessId(results)).toBe('Cheap')
    expect(bestBusinessId([results[2]])).toBeNull()
    expect(rankedAnswerText(results[0])).toBe('600 rupees per hour')
    const pin = {
      id: 'Cheap', name: 'Cheap', state: 'REPORTED_AVAILABLE' as const, distance_km: 1,
      bearing_deg: 0, testLine: false, best: true, detail: '600 rupees per hour',
    }
    expect(pinLabel(pin, true)).toBe('Meets what you asked · 600 rupees per hour · Best answer')
    expect(pinLabel(pin, false)).toBe('Said yes · Best answer')
  })

  it('does not show a ranked number that was not validated', () => {
    expect(rankedAnswerText(result('A', { answers: [price(600, { validated: false })] }))).toBeNull()
  })
})

describe('Results with custom questions', () => {
  it('shows each answer with the shop words and whether it matches', () => {
    render(
      <Results
        results={[
          result('Turf A'),
          result('Turf B', {
            result_state: 'REPORTED_UNAVAILABLE',
            answers: [answer({ value: false, meets: false, quote: 'No, we close at ten.' }), price(null, { flag: 'NOT_ANSWERED', validated: false })],
            rank_value: null,
          }),
          result('Turf C', { result_state: 'NO_ANSWER', answers: null, note: 'Call was not answered.' }),
        ]}
        complete
        custom
        explanation="Ordered by: shops that meet everything you asked first."
        now={NOW}
      />,
    )
    expect(screen.getByText('What each place answered')).toBeInTheDocument()
    const a = screen.getByText('Turf A').closest('li')!
    expect(within(a).getByText('Meets what you asked')).toBeInTheDocument()
    expect(within(a).getByText('600 rupees per hour')).toBeInTheDocument()
    expect(within(a).getByText('Yes, we are open till midnight.')).toBeInTheDocument()
    expect(within(a).queryByText('Price not quoted')).toBeNull()

    const b = screen.getByText('Turf B').closest('li')!
    expect(within(b).getByText("Doesn't meet what you asked")).toBeInTheDocument()
    expect(within(b).getByText('Does not match')).toBeInTheDocument()
    expect(within(b).getByText('Not clearly answered')).toBeInTheDocument()
    expect(within(b).getByText(flagText('NOT_ANSWERED'))).toBeInTheDocument()

    expect(screen.getByText(NOT_A_NO)).toBeInTheDocument()
  })
})
