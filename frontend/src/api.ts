// Types mirror the backend schemas (Bible 20). The browser holds no provider secrets; the only
// credential is the demo access key, kept in memory and sent as X-Sonar-Key.

export type SearchStatus =
  | 'CREATED'
  | 'NEEDS_CLARIFICATION'
  | 'RUNNING'
  | 'COMPLETED'
  | 'COMPLETED_PARTIAL'
  | 'FAILED'
  | 'CANCELLED'

export type CallStatus =
  | 'PENDING'
  | 'DISPATCHING'
  | 'DISPATCH_UNKNOWN'
  | 'DIALING'
  | 'RINGING'
  | 'IN_PROGRESS'
  | 'PROCESSING'
  | 'COMPLETED'
  | 'NO_ANSWER'
  | 'BUSY'
  | 'FAILED'
  | 'ERROR'
  | 'CANCELLED'
  | 'STOPPED'
  | 'INSUFFICIENT_BALANCE'
  | 'TIMED_OUT'

export type ResultState =
  | 'REPORTED_AVAILABLE'
  | 'REPORTED_UNAVAILABLE'
  | 'ALTERNATIVE_ONLY'
  | 'UNCERTAIN'
  | 'DECLINED'
  | 'NO_ANSWER'
  | 'CALL_FAILED'
  | 'PENDING'
  | 'CANCELLED'
  | 'NOT_CALLED_STOP_RULE'

export type DataOrigin = 'LIVE_CALL' | 'CACHED_LIVE' | 'SIMULATED' | 'SHOP_SELF_REPORT'
export type BusinessKind = 'REAL_BUSINESS' | 'TEAM_TEST_LINE'

export interface BusinessRef {
  id: string
  name: string
  kind: BusinessKind
  distance_km: number | null
  address?: string | null
}

export interface PlannedTarget {
  business_id: string
  name: string
  kind: BusinessKind
  distance_km: number
}

export interface ClarificationQuestion {
  field: string
  question: string
}

export interface SearchCreated {
  search_id: string
  status: SearchStatus
  planned_targets: PlannedTarget[]
  clarification: { questions: ClarificationQuestion[] } | null
  error_code: string | null
  message: string | null
}

export interface AttemptView {
  attempt_id: string
  business: BusinessRef
  status: CallStatus
  attempt_number: number
  updated_at: string
  result_state: ResultState
}

export interface Counts {
  planned: number
  pending: number
  in_call: number
  answered: number
  no_answer: number
  failed: number
  cancelled: number
}

export type SearchMode = 'FAST' | 'THOROUGH'

export interface SearchView {
  search_id: string
  status: SearchStatus
  demo_mode: boolean
  mode?: SearchMode | null
  stopped_early?: boolean
  calls_avoided?: number
  created_at: string
  started_at: string | null
  completed_at: string | null
  deadline_at: string | null
  counts: Counts
  attempts: AttemptView[]
  error: { code: string; message: string | null } | null
}

export interface HistoryView {
  answered: number
  reported_available: number
  label: 'HISTORY'
}

export interface ResultView {
  /** Past record, shown beside a live answer and always labelled; never today's confirmation. */
  history?: HistoryView | null
  business: BusinessRef
  result_state: ResultState
  data_origin: DataOrigin
  answer_timestamp: string | null
  freshness: Record<string, 'FRESH' | 'STALE' | 'UNKNOWN'>
  reported: {
    exact_match: string
    price: { amount: number | null; currency: string | null; note: string | null } | null
    quantity: number | null
    wait_time_minutes: number | null
    open_status: string | null
  } | null
  answer_summary: string | null
  evidence: { excerpt: string | null; validated: boolean; question_asked: string | null } | null
  verification_status: string | null
  flags: string[]
  note: string | null
}

export interface ResultsView {
  search_id: string
  complete: boolean
  ranking_explanation: string
  results: ResultView[]
}

export interface CategoryPublic {
  display_name: string
  essential_attributes: string[]
  required_fields_default: string[]
}

export interface PublicConfig {
  categories: Record<string, CategoryPublic>
  min_radius_km: number
  max_radius_km: number
  max_targets_per_search: number
  simulated_banner: string
  disclaimer: string
}

export interface SearchRequest {
  query_text: string
  category: string
  item: { name: string; attributes: Record<string, string> }
  location: { lat: number; lng: number; label?: string } | null
  radius_km: number
  demo_mode: boolean
  /** FAST stops once enough shops confirm; THOROUGH ("ask everyone") calls them all. */
  mode?: SearchMode
}

export class ApiError extends Error {
  status: number
  code: string
  field: string | null

  constructor(status: number, code: string, message: string, field: string | null = null) {
    super(message)
    this.status = status
    this.code = code
    this.field = field
  }
}

const BASE: string = import.meta.env.VITE_API_BASE_URL ?? ''

async function request<T>(path: string, init: RequestInit = {}): Promise<T> {
  let response: Response
  try {
    response = await fetch(`${BASE}${path}`, init)
  } catch {
    throw new ApiError(0, 'NETWORK', 'Cannot reach the Sonar server')
  }
  const body = await response.json().catch(() => null)
  if (!response.ok) {
    const err = body?.error
    throw new ApiError(
      response.status,
      err?.code ?? 'ERROR',
      err?.message ?? `Request failed (${response.status})`,
      err?.field ?? null,
    )
  }
  return body as T
}

export const api = {
  config: () => request<PublicConfig>('/api/config/public'),
  createSearch: (body: SearchRequest, accessKey: string) =>
    request<SearchCreated>('/api/searches', {
      method: 'POST',
      headers: { 'Content-Type': 'application/json', 'X-Sonar-Key': accessKey },
      body: JSON.stringify(body),
    }),
  getSearch: (id: string) => request<SearchView>(`/api/searches/${id}`),
  getResults: (id: string) => request<ResultsView>(`/api/searches/${id}/results`),
  cancel: (id: string, accessKey: string) =>
    request<{ status: SearchStatus }>(`/api/searches/${id}/cancel`, {
      method: 'POST',
      headers: { 'X-Sonar-Key': accessKey },
    }),
}

const TERMINAL: SearchStatus[] = ['COMPLETED', 'COMPLETED_PARTIAL', 'FAILED', 'CANCELLED']
export const isTerminalSearch = (s: SearchStatus) => TERMINAL.includes(s)
