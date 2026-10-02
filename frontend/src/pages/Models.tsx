import { useState } from 'react'
import { useMutation, useQuery, useQueryClient } from '@tanstack/react-query'
import { Plus, Rocket } from 'lucide-react'
import { Bar, BarChart, CartesianGrid, Legend, Tooltip, XAxis, YAxis } from 'recharts'
import { api, num, when } from '../lib/api'
import { Badge, Button, Card, CardBody, CardHeader, Confirm, ErrorState, Field, Input, Loading, Modal, PageHeader, Select, StatusBadge, Table, Td, Th, useToast } from '../components/ui'
import { axis, C, Chart, grid, tip } from '../components/charts'

const METRICS = ['recall@1', 'mrr', 'ndcg', 'context_precision', 'faithfulness', 'failure_rate']

export default function Models() {
  const toast = useToast(); const qc = useQueryClient()
  const { data, isLoading, error, refetch } = useQuery({ queryKey: ['models'], queryFn: () => api('/models') })
  const [target, setTarget] = useState<{ m: any; status: string } | null>(null)
  const [reg, setReg] = useState(false); const [form, setForm] = useState({ version: '', base_model: 'linear-reranker', reranker: 'linear-reranker' })
  const refresh = () => { qc.invalidateQueries({ queryKey: ['models'] }); qc.invalidateQueries({ queryKey: ['dashboard'] }) }
  const setStatus = useMutation({ mutationFn: ({ id, status }: any) => api(`/models/${id}/status`, { body: { status } }), onSuccess: () => { toast('ok', 'Status model diperbarui'); refresh() }, onError: (e: any) => toast('err', e.message) })
  const register = useMutation({ mutationFn: () => api('/models/register', { body: form }), onSuccess: () => { toast('ok', 'Model terdaftar'); setReg(false); refresh() }, onError: (e: any) => toast('err', e.message) })
  if (error) return <Card><ErrorState error={error} onRetry={refetch} /></Card>
  const chart = METRICS.map((m) => ({ metric: m, ...Object.fromEntries((data ?? []).map((v: any) => [v.version, v.metrics?.[m] ?? 0])) }))
  return (
    <>
      <PageHeader title="Model Registry" desc="Versi model, dataset asal, metrik, dan status siklus hidup. Promosi ke production memerlukan konfirmasi." actions={<Button onClick={() => setReg(true)}><Plus className="h-4 w-4" />Daftarkan model</Button>} />
      <Card className="mb-6">{isLoading ? <Loading /> : (
        <Table><thead><tr><Th>Model name</Th><Th>Version</Th><Th>Base model</Th><Th>Embedding</Th><Th>Reranker</Th><Th>Dataset</Th><Th>Training date</Th><Th>MRR</Th><Th>Status</Th><Th>Ubah status</Th></tr></thead>
          <tbody>{data.map((m: any) => (
            <tr key={m.id}><Td>{m.name}</Td><Td><Badge tone={m.status === 'production' ? 'brand' : 'neutral'}>{m.version}</Badge></Td><Td>{m.base_model}</Td><Td>{m.embedding_model}</Td><Td>{m.reranker}</Td><Td>{m.training_dataset_id ? `#${m.training_dataset_id}` : '-'}</Td>
              <Td className="whitespace-nowrap">{when(m.trained_at)}</Td><Td>{num(m.metrics?.mrr)}</Td><Td><StatusBadge value={m.status} /></Td>
              <Td><div className="flex gap-1.5"><Select className="h-8 w-32 text-[13px]" value="" onChange={(e) => e.target.value && setTarget({ m, status: e.target.value })}><option value="">Pindah ke...</option>{['candidate', 'staging', 'production', 'archived'].filter((s) => s !== m.status).map((s) => <option key={s}>{s}</option>)}</Select>
                {m.status !== 'production' && <Button size="sm" variant="primary" onClick={() => setTarget({ m, status: 'production' })}><Rocket className="h-3.5 w-3.5" />Promote</Button>}</div></Td></tr>))}</tbody></Table>)}</Card>
      <Card><CardHeader title="Perbandingan metrik antar versi" desc="Dihitung pada dataset evaluasi yang sama" /><CardBody>
        <Chart h={300}><BarChart data={chart}><CartesianGrid {...grid} /><XAxis dataKey="metric" {...axis} /><YAxis {...axis} domain={[0, 1]} /><Tooltip {...tip} /><Legend />
          {(data ?? []).map((v: any, i: number) => <Bar key={v.version} dataKey={v.version} fill={[C.stone, C.brand, C.ink, C.amber][i % 4]} radius={[3, 3, 0, 0]} />)}</BarChart></Chart></CardBody></Card>
      <Confirm open={!!target} danger={target?.status === 'production'} title={`Pindahkan ${target?.m.version} ke ${target?.status}?`} confirmLabel="Ya, pindahkan"
        message={target?.status === 'production' ? 'Versi production saat ini akan diarsipkan dan semua query baru memakai model ini. Pastikan hasil A/B test sudah ditinjau.' : 'Status model akan diubah.'} onConfirm={() => setStatus.mutate({ id: target!.m.id, status: target!.status })} onClose={() => setTarget(null)} />
      <Modal open={reg} onClose={() => setReg(false)} title="Daftarkan model">
        <div className="space-y-3"><Field label="Version" hint="Contoh: v5"><Input value={form.version} onChange={(e) => setForm({ ...form, version: e.target.value })} /></Field>
          <Field label="Base model"><Input value={form.base_model} onChange={(e) => setForm({ ...form, base_model: e.target.value })} /></Field>
          <Field label="Reranker"><Input value={form.reranker} onChange={(e) => setForm({ ...form, reranker: e.target.value })} /></Field>
          <div className="flex justify-end gap-2 pt-2"><Button onClick={() => setReg(false)}>Batal</Button><Button variant="primary" disabled={!form.version} loading={register.isPending} onClick={() => register.mutate()}>Daftarkan</Button></div></div></Modal>
    </>
  )
}
