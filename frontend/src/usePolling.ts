import { useEffect, useRef, useState } from 'react'
import { ApiError, api, isTerminalSearch } from './api'
import type { ResultsView, SearchView } from './api'

export interface PollingState {
  search: SearchView | null
  results: ResultsView | null
  error: string | null
  /** true while the last poll failed; the previous good data stays on screen */
  connectionLost: boolean
}

const INITIAL: PollingState = { search: null, results: null, error: null, connectionLost: false }

/**
 * Poll a search every `intervalMs` until it reaches a terminal status.
 * A failed poll keeps the last good state visible and retries (FR-26, NFR-03).
 */
export function useSearchPolling(searchId: string | null, intervalMs = 2000): PollingState {
  // State is tagged with the search it belongs to, so switching searches never shows old data.
  const [tagged, setTagged] = useState<{ id: string | null; state: PollingState }>({
    id: null,
    state: INITIAL,
  })
  const stopped = useRef(false)
  const setState = (update: PollingState | ((prev: PollingState) => PollingState)) =>
    setTagged((prev) => {
      const base = prev.id === searchId ? prev.state : INITIAL
      return { id: searchId, state: typeof update === 'function' ? update(base) : update }
    })

  useEffect(() => {
    stopped.current = false
    if (!searchId) return
    let timer: ReturnType<typeof setTimeout> | undefined

    const tick = async () => {
      try {
        const [search, results] = await Promise.all([
          api.getSearch(searchId),
          api.getResults(searchId),
        ])
        if (stopped.current) return
        setState({ search, results, error: null, connectionLost: false })
        if (isTerminalSearch(search.status)) return
      } catch (e) {
        if (stopped.current) return
        const message = e instanceof ApiError ? e.message : 'Unexpected error'
        const notFound = e instanceof ApiError && e.status === 404
        setState((prev) => ({ ...prev, error: message, connectionLost: !notFound }))
        if (notFound) return // nothing to wait for
      }
      timer = setTimeout(tick, intervalMs)
    }
    void tick()

    return () => {
      stopped.current = true
      if (timer) clearTimeout(timer)
    }
    // eslint-disable-next-line react-hooks/exhaustive-deps -- setState only wraps setTagged
  }, [searchId, intervalMs])

  return tagged.id === searchId ? tagged.state : INITIAL
}
