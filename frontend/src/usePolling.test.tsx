import { act, renderHook, waitFor } from '@testing-library/react'
import { afterEach, beforeEach, describe, expect, it, vi } from 'vitest'
import type { ResultsView, SearchStatus, SearchView } from './api'
import { useSearchPolling } from './usePolling'

const search = (status: SearchStatus): SearchView => ({
  search_id: 's1',
  status,
  demo_mode: true,
  created_at: '2026-11-02T10:00:00Z',
  started_at: null,
  completed_at: null,
  deadline_at: null,
  counts: { planned: 1, pending: 0, in_call: 0, answered: 0, no_answer: 0, failed: 0, cancelled: 0 },
  attempts: [],
  error: null,
})
const results: ResultsView = { search_id: 's1', complete: false, ranking_explanation: '', results: [] }

function respond(handlers: Array<() => Response | Promise<Response>>) {
  let i = 0
  const calls: string[] = []
  vi.stubGlobal(
    'fetch',
    vi.fn(async (url: string) => {
      calls.push(url)
      if (url.endsWith('/results')) return Response.json(results)
      const h = handlers[Math.min(i++, handlers.length - 1)]
      return h()
    }),
  )
  return calls
}
const ok = (status: SearchStatus) => () => Response.json(search(status))
const down = () => Promise.reject(new TypeError('network'))

describe('useSearchPolling', () => {
  beforeEach(() => vi.useFakeTimers({ shouldAdvanceTime: true }))
  afterEach(() => {
    vi.useRealTimers()
    vi.unstubAllGlobals()
  })

  it('does nothing without a search id', () => {
    const calls = respond([ok('RUNNING')])
    renderHook(() => useSearchPolling(null))
    expect(calls).toEqual([])
  })

  it('polls every interval while running and stops at a terminal status', async () => {
    const calls = respond([ok('RUNNING'), ok('RUNNING'), ok('COMPLETED'), ok('COMPLETED')])
    const { result } = renderHook(() => useSearchPolling('s1', 2000))
    await waitFor(() => expect(result.current.search?.status).toBe('RUNNING'))
    await act(() => vi.advanceTimersByTimeAsync(2000))
    await act(() => vi.advanceTimersByTimeAsync(2000))
    await waitFor(() => expect(result.current.search?.status).toBe('COMPLETED'))
    const callsAtDone = calls.length
    await act(() => vi.advanceTimersByTimeAsync(20000))
    expect(calls.length).toBe(callsAtDone) // no polling after the terminal status
  })

  it('keeps the last good data and retries after a failed poll', async () => {
    respond([ok('RUNNING'), down, ok('COMPLETED')])
    const { result } = renderHook(() => useSearchPolling('s1', 2000))
    await waitFor(() => expect(result.current.search?.status).toBe('RUNNING'))
    await act(() => vi.advanceTimersByTimeAsync(2000))
    await waitFor(() => expect(result.current.connectionLost).toBe(true))
    expect(result.current.search?.status).toBe('RUNNING') // still on screen
    await act(() => vi.advanceTimersByTimeAsync(2000))
    await waitFor(() => expect(result.current.search?.status).toBe('COMPLETED'))
    expect(result.current.connectionLost).toBe(false)
  })

  it('stops on a 404 instead of polling forever', async () => {
    const calls = respond([() => Response.json({ error: { code: 'NOT_FOUND', message: 'Search not found' } }, { status: 404 })])
    const { result } = renderHook(() => useSearchPolling('nope', 2000))
    await waitFor(() => expect(result.current.error).toBe('Search not found'))
    const n = calls.length
    await act(() => vi.advanceTimersByTimeAsync(10000))
    expect(calls.length).toBe(n)
    expect(result.current.connectionLost).toBe(false)
  })

  it('stops polling when unmounted', async () => {
    const calls = respond([ok('RUNNING')])
    const { unmount, result } = renderHook(() => useSearchPolling('s1', 2000))
    await waitFor(() => expect(result.current.search).not.toBeNull())
    unmount()
    const n = calls.length
    await act(() => vi.advanceTimersByTimeAsync(10000))
    expect(calls.length).toBe(n)
  })
})
