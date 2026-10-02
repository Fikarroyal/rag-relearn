import { useEffect, useState } from 'react'
import { useMutation, useQuery, useQueryClient } from '@tanstack/react-query'
import { FlaskConical } from 'lucide-react'
import { Bar, BarChart, CartesianGrid, Legend, Tooltip, XAxis, YAxis } from 'recharts'
import { api, label, num, when } from '../lib/api'
import { Badge, Button, Card, CardBody, CardHeader, Empty, ErrorState, Loading, PageHeader, StatusBadge, Table, Td, Th, useToast } from '../components/ui'
import { axis, C, Chart, grid, tip } from '../components/charts'

const ARMS = [['baseline', 'Baseline RAG'], ['rag_reranker', 'RAG + Reranker'], ['rag_failure_detection', 'RAG + Failure Detection'], ['rag_relearn', 'RAG-Relearn']]
const METRICS = ['recall@1', 'recall@3', 'recall@5', 'mrr', 'ndcg', 'context_precision', 'context_recall', 'faithfulness', 'answer_relevance', 'citation_accuracy', 'hallucination_rate', 'latency_ms']
const LOWER = new Set(['hallucination_rate', 'latency_ms', 'failure_rate'])

export default function Experiments() {
  const toast = useToast(); const qc = useQueryClient()
  const { data, isLoading, error, refetch } = useQuery({ queryKey: ['experiments'], queryFn: () => api('/experiments') })
  const [sel, setSel] = useState<number | null>(null)
  useEffect(() => { if (!sel && data?.length) setSel(data[0].id) }, [data])
  const run = useMutation({ mutationFn: () => api('/experiments/run', { method: 'POST', params: { epochs: 40, lr: 0.5 } }), onSuccess: (r) => { toast('ok', `${r.exp_id} selesai`); qc.invalidateQueries({ queryKey: ['experiments'] }) }, onError: (e: any) => toast('err', e.message) })
  const e = data?.find((x: any) => x.id === sel)
  const chart = e ? ['recall@1', 'mrr', 'ndcg', 'context_precision', 'faithfulness', 'answer_relevance', 'citation_accuracy'].map((m) => ({ metric: label(m), baseline: e.metrics.baseline[m], candidate: e.metrics.rag_relearn[m] })) : []
  return (
    <>
      <PageHeader title="Research Experiments" desc="Apakah closed-loop learning meningkatkan RAG? Empat konfigurasi dievaluasi pada dataset yang sama. Eksperimen lama tidak pernah dihapus."
        actions={<Button variant="primary" loading={run.isPending} onClick={() => run.mutate()}><FlaskConical className="h-4 w-4" />Jalankan eksperimen baru</Button>} />
      {error ? <Card><ErrorState error={error} onRetry={refetch} /></Card> : isLoading ? <Card><Loading /></Card> : !data?.length ? <Card><Empty title="Belum ada eksperimen" /></Card> : (<>
        <Card className="mb-6"><Table><thead><tr><Th>Experiment ID</Th><Th>Baseline</Th><Th>Candidate</Th><Th>Dataset</Th><Th>Training config</Th><Th>MRR</Th><Th>Improvement (MRR)</Th><Th>Date</Th><Th>Status</Th></tr></thead>
          <tbody>{data.map((x: any) => (
            <tr key={x.id} onClick={() => setSel(x.id)} className={`cursor-pointer hover:bg-stone-50 ${sel === x.id ? 'bg-brand-50/50' : ''}`}><Td className="font-medium">{x.exp_id}</Td><Td>{label(x.baseline)}</Td><Td>{label(x.candidate)}</Td><Td>{x.dataset}</Td>
              <Td className="text-[13px] text-ink-mute">epoch {x.config.epochs}, lr {x.config.learning_rate}, {x.config.n_samples} sampel</Td><Td>{num(x.metrics.baseline.mrr, 3)} to {num(x.metrics.rag_relearn.mrr, 3)}</Td>
              <Td className={x.improvement.mrr >= 0 ? 'text-emerald-700' : 'text-red-700'}>{x.improvement.mrr >= 0 ? '+' : ''}{num(x.improvement.mrr, 3)}</Td><Td className="whitespace-nowrap">{when(x.created_at)}</Td><Td><StatusBadge value={x.status} /></Td></tr>))}</tbody></Table></Card>
        {e && <>
          <Card className="mb-6"><CardHeader title={`${e.exp_id}: baseline vs candidate`} desc="Query training terpisah dari query evaluasi (tanpa leakage query)." /><CardBody>
            <Chart h={300}><BarChart data={chart}><CartesianGrid {...grid} /><XAxis dataKey="metric" {...axis} interval={0} angle={-20} height={60} textAnchor="end" /><YAxis {...axis} domain={[0, 1]} /><Tooltip {...tip} /><Legend />
              <Bar dataKey="baseline" name="Baseline" fill={C.stone} radius={[3, 3, 0, 0]} /><Bar dataKey="candidate" name="RAG-Relearn" fill={C.brand} radius={[3, 3, 0, 0]} /></BarChart></Chart></CardBody></Card>
          <Card><CardHeader title="Tabel perbandingan empat konfigurasi" desc="Hijau: lebih baik dari baseline. Merah: lebih buruk." />
            <Table><thead><tr><Th>Metric</Th>{ARMS.map(([k, n]) => <Th key={k}>{n}</Th>)}</tr></thead>
              <tbody>{METRICS.map((m) => (<tr key={m}><Td className="font-medium">{label(m)}</Td>{ARMS.map(([k]) => {
                const v = e.metrics[k][m], b = e.metrics.baseline[m]; const better = LOWER.has(m) ? v < b : v > b; const worse = LOWER.has(m) ? v > b : v < b
                return <Td key={k} className={k !== 'baseline' && better ? 'text-emerald-700' : k !== 'baseline' && worse ? 'text-red-700' : ''}>{num(v, m === 'latency_ms' ? 2 : 3)}</Td>})}</tr>))}</tbody></Table>
            <p className="border-t border-line px-5 py-3 text-[13px] text-ink-mute">Dataset evaluasi kecil (12 query) dan embedding hashing lokal, jadi hasil ini bukti konsep untuk pipeline, bukan klaim performa umum. Ganti dataset dan embedding untuk studi nyata.</p></Card></>}</>)}
    </>
  )
}
