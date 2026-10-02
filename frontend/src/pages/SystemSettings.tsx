import { useQuery } from '@tanstack/react-query'
import { api, ms, num, pct } from '../lib/api'
import { Badge, Card, CardBody, CardHeader, ErrorState, Loading, PageHeader, Stat } from '../components/ui'

export default function SystemSettings() {
  const s = useQuery({ queryKey: ['settings'], queryFn: () => api('/settings') })
  const o = useQuery({ queryKey: ['obs'], queryFn: () => api('/observability/summary'), refetchInterval: 10_000 })
  const row = (k: string, v: any) => <div key={k} className="flex justify-between gap-4 py-2 text-sm"><span className="text-ink-mute">{k}</span><span className="text-right font-medium">{v}</span></div>
  return (
    <>
      <PageHeader title="System Settings" desc="Konfigurasi aktif dan observabilitas. Nilai API key tidak pernah ditampilkan; hanya ketersediaannya." />
      {o.data && <div className="mb-6 grid gap-4 sm:grid-cols-2 lg:grid-cols-4">
        <Stat label="Request count" value={o.data.request_count} /><Stat label="Error rate" value={pct(o.data.error_rate)} /><Stat label="Latensi p50 / p95" value={`${ms(o.data.p50_ms)} / ${ms(o.data.p95_ms)}`} /><Stat label="Token usage (estimasi)" value={o.data.token_usage.toLocaleString('id-ID')} />
        <Stat label="Retrieval quality" value={pct(o.data.retrieval_quality)} tone="brand" /><Stat label="Failure rate" value={pct(o.data.failure_rate)} /><Stat label="Hallucination rate" value={pct(o.data.hallucination_rate)} /><Stat label="Citation accuracy" value={pct(o.data.citation_accuracy)} /></div>}
      <div className="grid gap-6 lg:grid-cols-2">
        <Card><CardHeader title="Konfigurasi" />{s.error ? <ErrorState error={s.error} onRetry={s.refetch} /> : !s.data ? <Loading /> : <CardBody className="divide-y divide-line py-2">
          {row('Database', s.data.database)}{row('Embedding model', s.data.embedding_model)}{row('Reranker', s.data.reranker_model)}{row('LLM', s.data.llm_model)}{row('Qdrant', s.data.qdrant_url ?? 'tidak dipakai')}{row('MCP server', s.data.mcp_server_url)}
          {row('Autentikasi JWT', <Badge tone={s.data.auth_enabled ? 'green' : 'amber'}>{s.data.auth_enabled ? 'aktif' : 'mode demo'}</Badge>)}{row('Batas upload', `${s.data.upload_limit_mb} MB`)}{row('Tipe file', s.data.allowed_types.join(', '))}</CardBody>}</Card>
        <Card><CardHeader title="Provider LLM" desc="Tanpa API key, aplikasi memakai provider mock lokal." />{!s.data ? <Loading /> : <CardBody className="divide-y divide-line py-2">
          {row('OpenAI', <Badge tone={s.data.providers.openai ? 'green' : 'neutral'}>{s.data.providers.openai ? 'API key tersedia' : 'tidak diset'}</Badge>)}{row('Anthropic', <Badge tone={s.data.providers.anthropic ? 'green' : 'neutral'}>{s.data.providers.anthropic ? 'API key tersedia' : 'tidak diset'}</Badge>)}{row('Local mock', <Badge tone="green">selalu tersedia</Badge>)}
          {o.data && row('Versi model terlihat', o.data.model_versions.join(', '))}</CardBody>}</Card></div>
    </>
  )
}
