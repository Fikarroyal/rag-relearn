import { useEffect, useState } from 'react'
import { useMutation, useQuery, useQueryClient } from '@tanstack/react-query'
import { BarChart3 } from 'lucide-react'
import { Bar, BarChart, CartesianGrid, Tooltip, XAxis, YAxis } from 'recharts'
import { api, label, ms, num, when } from '../lib/api'
import { Badge, Button, Card, CardBody, CardHeader, Empty, Field, Loading, Mono, PageHeader, Select, Stat, Table, Td, Th, useToast } from '../components/ui'
import { axis, C, Chart, grid, tip } from '../components/charts'

const GROUPS: Record<string, string[]> = {
  'Retrieval metrics': ['recall@1', 'recall@3', 'recall@5', 'recall@10', 'precision@k', 'mrr', 'ndcg'],
  'Generation metrics': ['faithfulness', 'answer_relevance', 'context_precision', 'context_recall', 'citation_accuracy'],
  'Failure metrics': ['hallucination_rate', 'failure_rate'],
}

export default function Evaluation() {
  const toast = useToast(); const qc = useQueryClient()
  const models = useQuery({ queryKey: ['models'], queryFn: () => api('/models') })
  const runs = useQuery({ queryKey: ['evals'], queryFn: () => api('/evaluation') })
  const [f, setF] = useState({ model_version: '', top_k: 5, reranker: '' }); const [sel, setSel] = useState<number | null>(null)
  useEffect(() => { if (!f.model_version && models.data?.length) setF((x) => ({ ...x, model_version: models.data.find((m: any) => m.status === 'production')?.version ?? models.data[0].version })) }, [models.data])
  useEffect(() => { if (!sel && runs.data?.length) setSel(runs.data[0].id) }, [runs.data])
  const det = useQuery({ queryKey: ['eval', sel], queryFn: () => api(`/evaluation/${sel}`), enabled: !!sel })
  const run = useMutation({ mutationFn: () => api('/evaluation/run', { body: { ...f, reranker: f.reranker || null } }), onSuccess: (r) => { toast('ok', 'Evaluasi batch selesai'); qc.invalidateQueries({ queryKey: ['evals'] }); setSel(r.id) }, onError: (e: any) => toast('err', e.message) })
  const m = det.data?.metrics
  return (
    <>
      <PageHeader title="Evaluation Center" desc="Evaluasi batch pada dataset berlabel: metrik retrieval, generation, latency, dan kegagalan." />
      <Card className="mb-6"><CardBody className="flex flex-wrap items-end gap-4">
        <Field label="Evaluation dataset" className="w-44"><Select disabled><option>eval_default (12 query)</option></Select></Field>
        <Field label="Model" className="w-40"><Select value={f.model_version} onChange={(e) => setF({ ...f, model_version: e.target.value })}>{models.data?.map((x: any) => <option key={x.id} value={x.version}>{x.version} ({x.status})</option>)}</Select></Field>
        <Field label="Retriever" className="w-40"><Select disabled><option>vector-cosine</option></Select></Field>
        <Field label="Reranker" className="w-48"><Select value={f.reranker} onChange={(e) => setF({ ...f, reranker: e.target.value })}><option value="">Sesuai model</option><option value="none">Tanpa reranker</option></Select></Field>
        <Field label="Top K" className="w-24"><Select value={f.top_k} onChange={(e) => setF({ ...f, top_k: +e.target.value })}>{[3, 5, 10, 20].map((k) => <option key={k}>{k}</option>)}</Select></Field>
        <Button variant="primary" loading={run.isPending} onClick={() => run.mutate()}><BarChart3 className="h-4 w-4" />Jalankan evaluasi</Button></CardBody></Card>
      {!sel ? <Card><Empty title="Belum ada evaluasi" desc="Jalankan evaluasi batch pertama." /></Card> : !m ? <Card><Loading /></Card> : (<>
        <div className="mb-2 flex items-center gap-2 text-sm text-ink-mute">Run #{det.data.id} <Badge tone="brand">{det.data.model_version}</Badge> reranker {det.data.reranker}, top K {det.data.top_k} - {when(det.data.created_at)}</div>
        <div className="mb-6 grid gap-4 sm:grid-cols-2 lg:grid-cols-4"><Stat label="Recall@1" value={num(m['recall@1'])} tone="brand" /><Stat label="MRR" value={num(m.mrr)} /><Stat label="Failure rate" value={num(m.failure_rate)} tone="red" /><Stat label="Latency rata-rata" value={ms(m.latency_ms)} /></div>
        <div className="mb-6 grid gap-6 lg:grid-cols-3">
          {Object.entries(GROUPS).map(([g, keys], i) => (
            <Card key={g}><CardHeader title={g} /><CardBody><Chart h={220}><BarChart data={keys.map((k) => ({ metric: label(k).replace('Recall@', 'R@'), value: m[k] ?? 0 }))}><CartesianGrid {...grid} /><XAxis dataKey="metric" {...axis} interval={0} angle={-25} height={60} textAnchor="end" /><YAxis {...axis} domain={[0, 1]} /><Tooltip {...tip} />
              <Bar dataKey="value" fill={[C.brand, C.ink, C.amber][i]} radius={[3, 3, 0, 0]} /></BarChart></Chart></CardBody></Card>))}</div>
        <Card><CardHeader title="Hasil per query" /><Table><thead><tr><Th>Query</Th><Th>Top-1</Th><Th>Ground truth</Th><Th>MRR</Th><Th>Failure type</Th></tr></thead>
          <tbody>{det.data.per_query.map((q: any) => <tr key={q.query}><Td className="max-w-[260px]">{q.query}</Td><Td><Mono>{q.top1}</Mono></Td><Td><Mono>{q.ground_truth}</Mono></Td><Td>{num(q.mrr, 2)}</Td><Td>{q.failure_type ? <Badge tone="red">{label(q.failure_type)}</Badge> : <Badge tone="green">Benar</Badge>}</Td></tr>)}</tbody></Table></Card></>)}
      <Card className="mt-6"><CardHeader title="Riwayat evaluasi" /><Table><thead><tr><Th>Run</Th><Th>Model</Th><Th>Reranker</Th><Th>Top K</Th><Th>Recall@1</Th><Th>MRR</Th><Th>Failure rate</Th><Th>Waktu</Th></tr></thead>
        <tbody>{runs.data?.map((r: any) => <tr key={r.id} className="cursor-pointer hover:bg-stone-50" onClick={() => setSel(r.id)}><Td>#{r.id}</Td><Td>{r.model_version}</Td><Td>{r.reranker}</Td><Td>{r.top_k}</Td><Td>{num(r.metrics['recall@1'])}</Td><Td>{num(r.metrics.mrr)}</Td><Td>{num(r.metrics.failure_rate)}</Td><Td>{when(r.created_at)}</Td></tr>)}</tbody></Table></Card>
    </>
  )
}
