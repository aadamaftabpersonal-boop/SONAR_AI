import { render, screen } from '@testing-library/react'
import { describe, expect, it, vi } from 'vitest'
import type { AttemptView, CallStatus, SearchView } from '../api'
import { Progress } from './Progress'

function attempt(name: string, status: CallStatus, n = 1, kind: 'REAL_BUSINESS' | 'TEAM_TEST_LINE' = 'REAL_BUSINESS'): AttemptView {
  return {
    attempt_id: crypto.randomUUID(),
    business: { id: name, name, kind, distance_km: 1 },
    status,
    attempt_number: n,
    updated_at: '2026-11-02T10:00:00Z',
    result_state: 'PENDING',
  }
}

const view = (attempts: AttemptView[], over: Partial<SearchView> = {}): SearchView => ({
  search_id: 's',
  status: 'RUNNING',
  demo_mode: false,
  created_at: '2026-11-02T10:00:00Z',
  started_at: '2026-11-02T10:00:01Z',
  completed_at: null,
  deadline_at: null,
  counts: { planned: attempts.length, pending: 0, in_call: 0, answered: 0, no_answer: 0, failed: 0, cancelled: 0 },
  attempts,
  error: null,
  ...over,
})

describe('Progress', () => {
  it('shows a text label for every call status, never colour alone', () => {
    render(<Progress search={view([attempt('A', 'RINGING'), attempt('B', 'COMPLETED'), attempt('C', 'NO_ANSWER')])} running onCancel={vi.fn()} />)
    expect(screen.getByText('Ringing')).toBeInTheDocument()
    expect(screen.getByText('Done')).toBeInTheDocument()
    expect(screen.getByText('No answer')).toBeInTheDocument()
  })

  it('shows one row per shop, using the latest attempt, and marks retries', () => {
    render(<Progress search={view([attempt('A', 'NO_ANSWER', 1), attempt('A', 'PENDING', 2)])} running onCancel={vi.fn()} />)
    expect(screen.getAllByRole('listitem')).toHaveLength(1)
    expect(screen.getByText('retry 1')).toBeInTheDocument()
    expect(screen.getByText('Queued')).toBeInTheDocument()
  })

  it('labels role-played test lines so they are never mistaken for independent shops', () => {
    render(<Progress search={view([attempt('Line A', 'RINGING', 1, 'TEAM_TEST_LINE')])} running onCancel={vi.fn()} />)
    expect(screen.getByText('Team test line (role-play)')).toBeInTheDocument()
  })

  it('offers cancel only while running, with the honest consequence', () => {
    const { rerender } = render(<Progress search={view([attempt('A', 'RINGING')])} running onCancel={vi.fn()} />)
    expect(screen.getByRole('button', { name: 'Cancel' })).toBeInTheDocument()
    expect(screen.getByText(/already in progress will finish/)).toBeInTheDocument()
    rerender(<Progress search={view([attempt('A', 'COMPLETED')], { status: 'COMPLETED' })} running={false} onCancel={vi.fn()} />)
    expect(screen.queryByRole('button', { name: 'Cancel' })).not.toBeInTheDocument()
  })

  it('explains an early stop and says skipped shops are not unavailable', () => {
    render(<Progress search={view([attempt('A', 'COMPLETED')], { status: 'COMPLETED', stopped_early: true, calls_avoided: 3 })} running={false} onCancel={vi.fn()} />)
    const note = screen.getByRole('status')
    expect(note).toHaveTextContent('3 calls were not made')
    expect(note).toHaveTextContent('does not mean they lack the item')
  })

  it('shows a shop skipped by the stop rule as "Not called", not "Cancelled"', () => {
    const skipped = { ...attempt('Skipped', 'CANCELLED'), result_state: 'NOT_CALLED_STOP_RULE' as const }
    const byUser = attempt('ByUser', 'CANCELLED')
    render(<Progress search={view([skipped, byUser], { stopped_early: true, calls_avoided: 1 })} running={false} onCancel={vi.fn()} />)
    expect(screen.getByText('Not called')).toBeInTheDocument()
    expect(screen.getByText('Cancelled')).toBeInTheDocument()
  })

  it('uses the singular for one skipped call', () => {
    render(<Progress search={view([attempt('A', 'COMPLETED')], { stopped_early: true, calls_avoided: 1 })} running={false} onCancel={vi.fn()} />)
    expect(screen.getByRole('status')).toHaveTextContent('1 call was not made')
  })

  it('says nothing about stopping when the search did not stop early', () => {
    render(<Progress search={view([attempt('A', 'COMPLETED')], { stopped_early: false })} running={false} onCancel={vi.fn()} />)
    expect(screen.queryByText(/Stopped early/)).not.toBeInTheDocument()
  })
})
