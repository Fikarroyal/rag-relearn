import { useState } from 'react'
import { Link } from 'react-router-dom'
import { useMutation, useQuery, useQueryClient } from '@tanstack/react-query'
import { ClipboardCheck, GitCompareArrows, Play, ShieldAlert, Stethoscope } from 'lucide-react'
import { api, FAILURE_TYPES, label, ms } from '../lib/api'
import { Badge, Button, Card, CardBody, CardHeader, Empty, Field, Input, Json, Modal, Mono, PageHeader, Select, Textarea, useToast } from '../components/ui'
import { RankList } from '../components/Rank'

export default function Playground() {
  const toast = useToast()
  const qc = useQueryClient()
  const models = useQuery({ queryKey: ['models'], queryFn: () => api('/models') })
  const [f, setF] = useState({ query: 'Bagaimana prosedur backup server?', top_k: 5, threshold: 0, reranker: 'model', llm: 'mock', embedding_model: 'hashing-512-local', model_version: '' })
  const [res, setRes] = useState<any>(null)
  const [markOpen, setMarkOpen] = useState(false)
  const [cmp, setCmp] = useState<any>(null)
  const [mark, setMark] = useState({ failure_type: 'answer_relevance_failure', reason: '' })
  const set = (k: string, v: any) => setF((x) => ({ ...x, [k]: v }))
  const body = () => ({ query: f.query, top_k: f.top_k, threshold: f.threshold, reranker: f.reranker === 'none' ? 'none' : null, llm: f.llm, model_version: f.model_version || null })

  const run = useMutation({ mutationFn: () => api('/rag/query', { body: body() }), onSuccess: (r) => { setRes(r); qc.invalidateQueries({ queryKey: ['dashboard'] }) }, onError: (e: any) => toast('err', e.message) })
  const evaluate = useMutation({ mutationFn: () => api('/rag/evaluate', { body: body() }), onSuccess: (r) => { setRes(r); toast('ok', r.diagnosis ? `Kegagalan terdeteksi: ${label(r.diagnosis.failure_type)}` : 'Evaluasi selesai: jawaban benar') }, onError: (e: any) => toast('err', e.message) })
  const markFail = useMutation({
    mutationFn: () => api('/failures/mark', { body: { evaluation_id: res.evaluation_id, ...mark } }),
    onSuccess: (r) => { toast('ok', `Failure case #${r.failure_id} dibuat`); setMarkOpen(false); setRes({ ...res, failure_id: r.failure_id }) }, onError: (e: any) => toast('err', e.message),
  })
  const compare = useMutation({
    mutationFn: async () => {
      const [a, b] = await Promise.all([api('/rag/query', { body: { ...body(), reranker: 'none', persist: false } }), api('/rag/query', { body: { ...body(), reranker: null, persist: false } })])
      return { a, b }
    }, onSuccess: setCmp, onError: (e: any) => toast('err', e.message),
  })

  return (
    <>
      <PageHeader title="RAG Playground" desc="Jalankan query langsung dan periksa setiap tahap: retrieval, reranking, context, dan jawaban bersitasi." />
      <div className="grid gap-6 lg:grid-cols-[360px_1fr]">
        <Card className="self-start">
          <CardHeader title="Konfigurasi" />
          <CardBody className="space-y-4">
            <Field label="Question"><Textarea rows={3} value={f.query} onChange={(e) => set('query', e.target.value)} /></Field>
            <div className="grid grid-cols-2 gap-3">
              <Field label="Top K"><Input type="number" min={1} max={20} value={f.top_k} onChange={(e) => set('top_k', +e.target.value)} /></Field>
              <Field label="Similarity threshold"><Input type="number" min={0} max={1} step={0.05} value={f.threshold} onChange={(e) => set('threshold', +e.target.value)} /></Field>
            </div>
            <Field label="Reranker"><Select value={f.reranker} onChange={(e) => set('reranker', e.target.value)}><option value="model">Sesuai model version</option><option value="none">Tanpa reranker</option></Select></Field>
            <Field label="LLM model" hint="Tanpa API key otomatis memakai provider mock."><Select value={f.llm} onChange={(e) => set('llm', e.target.value)}><option value="mock">Mock extractive (lokal)</option><option value="anthropic">Anthropic</option><option value="openai">OpenAI</option></Select></Field>
            <Field label="Embedding model"><Select value={f.embedding_model} onChange={(e) => set('embedding_model', e.target.value)}><option value="hashing-512-local">hashing-512-local</option></Select></Field>
            <Field label="Model version"><Select value={f.model_version} onChange={(e) => set('model_version', e.target.value)}><option value="">Production saat ini</option>{models.data?.map((m: any) => <option key={m.id} value={m.version}>{m.version} ({m.status})</option>)}</Select></Field>
            <Button variant="primary" className="w-full" loading={run.isPending} disabled={f.query.trim().length < 3} onClick={() => run.mutate()}><Play className="h-4 w-4" />Jalankan query</Button>
          </CardBody>
        </Card>

        <div className="min-w-0 space-y-6">
          {!res ? <Card><Empty title="Belum ada hasil" desc="Jalankan query untuk melihat jawaban, ranking dokumen, dan context window." /></Card> : (<>
            <Card>
              <CardHeader title="Generated answer" desc={`Query class: ${label(res.query_class.type)} - model ${res.model_version}`}
                action={res.diagnosis ? <Badge tone="red">{label(res.diagnosis.failure_type)}</Badge> : res.ground_truth_chunk ? <Badge tone="green">Sesuai ground truth</Badge> : <Badge>Tanpa ground truth</Badge>} />
              <CardBody>
                <p className="leading-relaxed">{res.answer.replace(/\[[^\]]+\]/g, '')}</p>
                <div className="mt-3 flex flex-wrap items-center gap-2"><span className="text-[13px] text-ink-mute">Citation</span>{res.citations.map((c: string) => <Mono key={c} className="rounded bg-stone-100 px-1.5 py-0.5">{c}</Mono>)}</div>
                <div className="mt-4 grid grid-cols-2 gap-3 text-[13px] sm:grid-cols-5">
                  {[['Embedding', res.metrics.embedding_ms], ['Retrieval', res.metrics.retrieval_ms], ['Reranking', res.metrics.reranking_ms], ['Generation', res.metrics.generation_ms], ['Total', res.metrics.total_ms]].map(([k, v]: any) => (
                    <div key={k} className="rounded-md bg-stone-50 px-3 py-2"><p className="text-ink-mute">{k}</p><p className="font-medium">{ms(v)}</p></div>))}
                </div>
                <div className="mt-5 flex flex-wrap gap-2">
                  <Button onClick={() => evaluate.mutate()} loading={evaluate.isPending}><ClipboardCheck className="h-4 w-4" />Evaluate answer</Button>
                  <Button onClick={() => setMarkOpen(true)}><ShieldAlert className="h-4 w-4" />Mark as failure</Button>
                  {res.failure_id ? <Link to={`/failures/${res.failure_id}`}><Button variant="primary"><Stethoscope className="h-4 w-4" />View failure analysis</Button></Link>
                    : <Button disabled title="Belum ada failure untuk query ini"><Stethoscope className="h-4 w-4" />View failure analysis</Button>}
                  <Button onClick={() => compare.mutate()} loading={compare.isPending}><GitCompareArrows className="h-4 w-4" />Compare retrieval</Button>
                </div>
                {res.diagnosis && <div className="mt-4 rounded-md border border-red-100 bg-red-50/60 p-3 text-sm"><p className="font-medium text-red-800">{res.diagnosis.root_cause}</p><p className="mt-1 text-red-900/80">{res.diagnosis.evidence.join(' - ')}</p></div>}
              </CardBody>
            </Card>
            <Card><CardHeader title="Retrieved documents" desc={`Peringkat setelah reranking (${res.reranked.length} chunk). Klik baris untuk detail.`} />
              <RankList hits={res.reranked.map((h: any) => ({ ...h, selected: res.selected.some((s: any) => s.chunk_id === h.chunk_id) }))} expected={res.ground_truth_chunk} /></Card>
            <Card><CardHeader title="Context window" desc="Chunk yang dikirim ke LLM" />
              <CardBody className="space-y-3">{res.selected.map((c: any, i: number) => (
                <div key={c.chunk_id} className="rounded-md border border-line p-3 text-sm"><div className="mb-1 flex items-center gap-2"><Badge>#{i + 1}</Badge><Mono>{c.chunk_id}</Mono></div><p className="text-ink-soft">{c.content}</p></div>))}</CardBody></Card>
          </>)}
        </div>
      </div>

      <Modal open={markOpen} onClose={() => setMarkOpen(false)} title="Tandai sebagai failure">
        <div className="space-y-4">
          <Field label="Failure type"><Select value={mark.failure_type} onChange={(e) => setMark({ ...mark, failure_type: e.target.value })}>{FAILURE_TYPES.map((t) => <option key={t} value={t}>{label(t)}</option>)}</Select></Field>
          <Field label="Alasan"><Textarea rows={3} value={mark.reason} onChange={(e) => setMark({ ...mark, reason: e.target.value })} placeholder="Mengapa jawaban ini salah?" /></Field>
          <div className="flex justify-end gap-2"><Button onClick={() => setMarkOpen(false)}>Batal</Button><Button variant="primary" loading={markFail.isPending} onClick={() => markFail.mutate()}>Buat failure case</Button></div>
        </div>
      </Modal>
      <Modal open={!!cmp} onClose={() => setCmp(null)} title="Compare retrieval" wide>
        {cmp && <div className="grid gap-4 md:grid-cols-2">
          {[['Tanpa reranker', cmp.a], ['Dengan reranker model', cmp.b]].map(([t, r]: any) => (
            <div key={t}><p className="mb-2 text-sm font-medium">{t}</p><ol className="space-y-1.5">{r.reranked.map((h: any, i: number) => (
              <li key={h.chunk_id} className="flex items-center justify-between rounded-md border border-line px-3 py-2 text-[13px]"><span><b className="mr-2">{i + 1}</b><Mono>{h.chunk_id}</Mono></span>
                {h.chunk_id === r.ground_truth_chunk && <Badge tone="green">Benar</Badge>}</li>))}</ol></div>))}</div>}
      </Modal>
    </>
  )
}
