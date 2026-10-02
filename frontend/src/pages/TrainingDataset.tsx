import { useEffect, useState } from 'react'
import { useMutation, useQuery, useQueryClient } from '@tanstack/react-query'
import { Download, Plus } from 'lucide-react'
import { Bar, BarChart, CartesianGrid, Tooltip, XAxis, YAxis } from 'recharts'
import { api, exportUrl, label, num } from '../lib/api'
import { Badge, Button, Card, CardBody, CardHeader, Empty, ErrorState, Json, Loading, Mono, PageHeader, Select, Stat, Table, Td, Th, useToast } from '../components/ui'
import { axis, C, Chart, grid, tip } from '../components/charts'

export default function TrainingDataset() {
  const toast = useToast(); const qc = useQueryClient()
  const list = useQuery({ queryKey: ['datasets'], queryFn: () => api('/training/datasets') })
  const [id, setId] = useState<number | null>(null)
  const [split, setSplit] = useState('')
  useEffect(() => { if (!id && list.data?.length) setId(list.data[0].id) }, [list.data])
  const det = useQuery({ queryKey: ['dataset', id, split], queryFn: () => api(`/training/datasets/${id}`, { params: { split, page_size: 100 } }), enabled: !!id })
  const create = useMutation({ mutationFn: () => api('/training/dataset', { body: { name: `dataset-${new Date().toISOString().replace(/\D/g, '').slice(0, 12)}` } }),
    onSuccess: (r) => { toast('ok', `Dataset #${r.id} dibuat: ${r.stats.n_samples} sampel`); qc.invalidateQueries({ queryKey: ['datasets'] }); setId(r.id) }, onError: (e: any) => toast('err', e.message) })
  const d = det.data; const s = d?.stats
  return (
    <>
      <PageHeader title="Training Dataset" desc="Dataset query - positive - hard negative dari failure case yang disetujui, lengkap dengan validasi kualitas." actions={<Button variant="primary" loading={create.isPending} onClick={() => create.mutate()}><Plus className="h-4 w-4" />Generate dataset baru</Button>} />
      {list.error ? <Card><ErrorState error={list.error} onRetry={list.refetch} /></Card> : list.isLoading ? <Card><Loading /></Card> : !list.data?.length ? <Card><Empty title="Belum ada dataset" desc="Setujui hard negative lalu generate dataset." /></Card> : (<>
        <div className="mb-6 flex flex-wrap items-center gap-3">
          <Select className="w-72" value={id ?? ''} onChange={(e) => setId(+e.target.value)}>{list.data.map((x: any) => <option key={x.id} value={x.id}>#{x.id} {x.name}</option>)}</Select>
          {id && ['json', 'jsonl', 'csv'].map((f) => <a key={f} href={exportUrl(id, f)} download><Button><Download className="h-4 w-4" />{f.toUpperCase()}</Button></a>)}
        </div>
        {!d ? <Card><Loading /></Card> : (<>
          <div className="mb-6 grid gap-4 sm:grid-cols-2 lg:grid-cols-5">
            <Stat label="Jumlah sampel" value={s.n_samples} /><Stat label="Train / Val / Test" value={`${s.split.train ?? 0} / ${s.split.validation ?? 0} / ${s.split.test ?? 0}`} />
            <Stat label="Duplikat" value={s.duplicates} tone={s.duplicates ? 'red' : undefined} /><Stat label="Quality score" value={num(s.quality_score, 2)} tone="brand" /><Stat label="Leakage train/test" value={d.validation.train_test_leakage ?? 0} />
          </div>
          <div className="mb-6 grid gap-6 lg:grid-cols-2">
            <Card><CardHeader title="Failure distribution" /><CardBody><Chart h={200}><BarChart data={Object.entries(s.failure_distribution).map(([k, v]) => ({ type: label(k), count: v }))}><CartesianGrid {...grid} /><XAxis dataKey="type" {...axis} /><YAxis {...axis} /><Tooltip {...tip} /><Bar dataKey="count" fill={C.brand} radius={[4, 4, 0, 0]} /></BarChart></Chart></CardBody></Card>
            <Card><CardHeader title="Quality validation" action={<Badge tone={d.validation.ok ? 'green' : 'amber'}>{d.validation.ok ? 'Lolos' : `${d.validation.issues.length} isu`}</Badge>} />
              <CardBody className="text-sm text-ink-soft">{d.validation.ok ? 'Tidak ada field kosong, duplikat, dokumen tidak valid, label kontradiktif, negatif berkualitas rendah, maupun leakage train/test.' :
                <ul className="space-y-1">{d.validation.issues.slice(0, 8).map((i: any, n: number) => <li key={n}><Badge tone="amber">{label(i.issue)}</Badge> <span className="ml-1">{Array.isArray(i.detail) ? i.detail.join(', ') : i.detail}</span></li>)}</ul>}</CardBody></Card>
          </div>
          <Card className="mb-6"><CardHeader title="Contoh format sampel" /><CardBody><Json data={d.samples[0] ? { query: d.samples[0].query, positive: d.samples[0].positive, hard_negative: d.samples[0].hard_negative, reason: d.samples[0].reason, failure_type: d.samples[0].failure_type } : {}} /></CardBody></Card>
          <Card><CardHeader title="Sampel" action={<Select className="w-36" value={split} onChange={(e) => setSplit(e.target.value)}><option value="">Semua split</option><option>train</option><option>validation</option><option>test</option></Select>} />
            <Table><thead><tr><Th>Query</Th><Th>Positive</Th><Th>Hard negative</Th><Th>Reason</Th><Th>Failure type</Th><Th>Split</Th><Th>Quality</Th></tr></thead>
              <tbody>{d.samples.map((x: any, i: number) => <tr key={i}><Td className="max-w-[220px]">{x.query}</Td><Td><Mono>{x.positive}</Mono></Td><Td><Mono>{x.hard_negative}</Mono></Td><Td>{x.reason}</Td><Td>{label(x.failure_type)}</Td><Td><Badge>{x.split}</Badge></Td><Td>{num(x.quality_score, 2)}</Td></tr>)}</tbody></Table></Card>
        </>)}</>)}
    </>
  )
}
