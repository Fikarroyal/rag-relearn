import { useEffect, useState } from 'react'
import { useMutation, useQuery } from '@tanstack/react-query'
import { Play } from 'lucide-react'
import { api } from '../lib/api'
import { Button, Card, CardBody, CardHeader, ErrorState, Json, Loading, Mono, PageHeader, Textarea, cn, useToast } from '../components/ui'

const EXAMPLES: Record<string, any> = {
  evaluate_rag: { query: 'Bagaimana prosedur backup server?', model_version: 'v1' }, inspect_retrieval: { query: 'Bagaimana prosedur backup server?' }, get_failure_cases: { filters: { failure_type: 'document_version_mismatch', page_size: 3 } },
  get_failure_case: { failure_id: 1 }, generate_hard_negatives: { query: 'Bagaimana prosedur backup server?' }, run_ab_test: { model_a: 'v1', model_b: 'v2' }, compare_models: { model_a: 'v1', model_b: 'v2' },
  get_model_metrics: { model_version: 'v2' }, trigger_retraining: { dataset_id: 1 }, get_training_status: { job_id: 1 },
}
const CONFIG = `{
  "mcpServers": {
    "rag-relearn": {
      "command": "python",
      "args": ["mcp-server/server.py"],
      "env": { "BACKEND_URL": "http://localhost:8000" }
    }
  }
}`

export default function McpTools() {
  const toast = useToast()
  const tools = useQuery({ queryKey: ['mcp'], queryFn: () => api('/mcp/tools') })
  const [sel, setSel] = useState('inspect_retrieval'); const [args, setArgs] = useState('{}'); const [out, setOut] = useState<any>(null)
  useEffect(() => setArgs(JSON.stringify(EXAMPLES[sel] ?? {}, null, 2)), [sel])
  const run = useMutation({ mutationFn: () => api('/mcp/invoke', { body: { tool: sel, arguments: JSON.parse(args) } }), onSuccess: setOut, onError: (e: any) => toast('err', e.message) })
  const tool = tools.data?.find((t: any) => t.name === sel)
  return (
    <>
      <PageHeader title="MCP Tools" desc="Tool yang dapat dipakai agen AI untuk mengamati dan mengevaluasi sistem RAG. Server MCP dan halaman ini memakai implementasi yang sama." />
      {tools.error ? <Card><ErrorState error={tools.error} onRetry={tools.refetch} /></Card> : tools.isLoading ? <Card><Loading /></Card> : (
        <div className="grid gap-6 lg:grid-cols-[300px_1fr]">
          <Card className="self-start"><CardHeader title={`${tools.data.length} tools`} /><ul className="divide-y divide-line">{tools.data.map((t: any) => (
            <li key={t.name}><button onClick={() => { setSel(t.name); setOut(null) }} className={cn('w-full px-5 py-3 text-left hover:bg-stone-50', sel === t.name && 'bg-brand-50')}><Mono className="font-medium text-ink">{t.name}</Mono><p className="mt-0.5 text-[13px] text-ink-mute">{t.description}</p></button></li>))}</ul></Card>
          <div className="min-w-0 space-y-6">
            <Card><CardHeader title={sel} desc={tool?.description} action={<Button variant="primary" loading={run.isPending} onClick={() => { try { JSON.parse(args); run.mutate() } catch { toast('err', 'Argumen bukan JSON valid') } }}><Play className="h-4 w-4" />Jalankan</Button>} />
              <CardBody className="space-y-3"><div><p className="mb-1.5 text-[13px] font-medium text-ink-soft">Parameter: {Object.entries(tool?.params ?? {}).map(([k, v]) => `${k} (${v})`).join(', ') || 'tidak ada'}</p>
                <Textarea rows={6} className="font-mono text-[12.5px]" value={args} onChange={(e) => setArgs(e.target.value)} spellCheck={false} /></div>
                {out && <div><p className="mb-1.5 text-[13px] font-medium text-ink-soft">Hasil</p><Json data={out} /></div>}</CardBody></Card>
            <Card><CardHeader title="Menyambungkan agen (stdio)" desc="Tambahkan ke konfigurasi klien MCP, setelah pip install -r mcp-server/requirements.txt" /><CardBody><pre className="overflow-auto rounded-md bg-ink p-4 font-mono text-xs text-stone-100">{CONFIG}</pre></CardBody></Card></div></div>)}
    </>
  )
}
