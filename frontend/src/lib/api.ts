// Klien API tipis: token JWT (jika login) disimpan di localStorage.
const BASE = (import.meta as any).env?.VITE_API_URL ?? ''

export class ApiError extends Error {
  status: number
  constructor(message: string, status: number) { super(message); this.status = status }
}

export async function api<T = any>(path: string, opts: { method?: string; body?: any; params?: Record<string, any> } = {}): Promise<T> {
  const qs = opts.params
    ? '?' + new URLSearchParams(Object.entries(opts.params).filter(([, v]) => v !== '' && v != null).map(([k, v]) => [k, String(v)])).toString()
    : ''
  const token = localStorage.getItem('rr_token')
  const res = await fetch(`${BASE}/api${path}${qs}`, {
    method: opts.method ?? (opts.body ? 'POST' : 'GET'),
    headers: { 'Content-Type': 'application/json', ...(token ? { Authorization: `Bearer ${token}` } : {}) },
    body: opts.body ? JSON.stringify(opts.body) : undefined,
  })
  if (!res.ok) {
    let msg = res.statusText
    try { const j = await res.json(); msg = typeof j.detail === 'string' ? j.detail : JSON.stringify(j.detail ?? j) } catch { /* abaikan */ }
    throw new ApiError(msg, res.status)
  }
  return res.json()
}

export async function upload(path: string, form: FormData) {
  const token = localStorage.getItem('rr_token')
  const res = await fetch(`${BASE}/api${path}`, { method: 'POST', body: form, headers: token ? { Authorization: `Bearer ${token}` } : {} })
  if (!res.ok) { const j = await res.json().catch(() => ({})); throw new ApiError(j.detail ?? res.statusText, res.status) }
  return res.json()
}

export const exportUrl = (id: number, format: string) => `${BASE}/api/training/datasets/${id}/export?format=${format}`
export const pct = (v?: number | null, d = 1) => (v == null ? '-' : `${(v * 100).toFixed(d)}%`)
export const num = (v?: number | null, d = 3) => (v == null ? '-' : Number(v).toFixed(d))
export const ms = (v?: number | null) => (v == null ? '-' : `${Number(v).toFixed(v < 10 ? 2 : 0)} ms`)
export const label = (s?: string | null) => (s ? s.replace(/_/g, ' ').replace(/^\w/, (c) => c.toUpperCase()) : '-')
export const when = (s?: string | null) => (s ? new Date(s + (s.endsWith('Z') ? '' : 'Z')).toLocaleString('id-ID', { dateStyle: 'medium', timeStyle: 'short' }) : '-')
export const FAILURE_TYPES = [
  'false_positive_retrieval', 'false_negative_retrieval', 'missing_context', 'contradictory_context', 'wrong_chunk', 'document_version_mismatch',
  'low_semantic_similarity', 'poor_reranking', 'insufficient_context', 'irrelevant_context', 'citation_error', 'hallucination',
  'answer_grounding_failure', 'answer_relevance_failure', 'retrieval_latency_problem',
]
