import { render, screen } from '@testing-library/react'
import { describe, expect, it } from 'vitest'
import type { LiveCall } from '../api'
import { TickerView } from './Ticker'

const call = (over: Partial<LiveCall> = {}): LiveCall => ({
  attempt_id: 'a1',
  business_id: 'b1',
  business_name: 'Test line',
  status: 'IN_PROGRESS',
  lines: [{ speaker: 'Shop', text: 'yes we have it' }],
  reason: null,
  updated_at: '2026-11-02T10:41:12Z',
  ...over,
})

describe('TickerView', () => {
  it('shows labelled lines in a polite live region', () => {
    const { container } = render(<TickerView calls={[call()]} />)
    expect(screen.getByText('yes we have it')).toBeInTheDocument()
    expect(container.querySelector('[aria-live="polite"]')).not.toBeNull()
  })

  it('renders markup as text', () => {
    render(<TickerView calls={[call({ lines: [{ speaker: 'Shop', text: '<img src=x onerror=alert(1)>' }] })]} />)
    expect(screen.getByText('<img src=x onerror=alert(1)>')).toBeInTheDocument()
    expect(document.querySelector('img')).toBeNull()
  })

  it('says why there is no text instead of inventing any', () => {
    render(<TickerView calls={[call({ lines: [], reason: 'not_shown' })]} />)
    expect(screen.getByText("A real shop's words are not shown live.")).toBeInTheDocument()
    render(<TickerView calls={[call({ attempt_id: 'a2', lines: [], reason: null })]} />)
    expect(screen.getByText('No live text yet.')).toBeInTheDocument()
  })

  it('renders nothing when no call is live', () => {
    const { container } = render(<TickerView calls={[]} />)
    expect(container).toBeEmptyDOMElement()
  })
})
