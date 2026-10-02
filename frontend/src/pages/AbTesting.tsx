import { useEffect, useState } from 'react'
import { useMutation, useQuery, useQueryClient } from '@tanstack/react-query'
import { FlaskConical } from 'lucide-react'
import { api, label, num } from '../lib/api'
import { Badge, Button, Card, CardBody, CardHeader, Empty, Field, Loading, PageHeader, Select, Table, Td, Th, useToast } from '../components/ui'

export function AbResult({ r }: { r: any }) {
  return (
    <Table><thead><tr><Th>Metric</Th><Th>Model {r.model_a}</Th><Th>Model {r.model_b}</Th><Th>Perbedaan</Th><Th>Arah</Th></tr></thead>
      <tbody>{r.rows.map((x: any) => (
        <tr key={x.metric}><Td className="font-medium">{label(x.metric)}</Td><Td>{num(x.a, 4)}</Td><Td>{num(x.b, 4)}</Td><Td className={x.delta === 0 ? '' : x.improved ? 'text-emerald-700' : 'text-red-700'}>{x.delta > 0 ? '+' : ''}{num(x.delta, 4)}</Td>
          <Td>{x.delta === 0 ? <Badge>Sama</Badge> : x.improved ? <Badge tone="green">Membaik</Badge> : <Badge tone="red">Memburuk</Badge>}{x.lower_is_better && <span className="ml-2 text-xs text-ink-mute">lebih rendah lebih baik</span>}</Td></tr>))}</tbody></Table>
  )
}

export default function AbTesting() {
  const toast = useToast(); const qc = useQueryClient()
  const models = useQuery({ queryKey: ['models'], queryFn: () => api('/models') })
  const tests = useQuery({ queryKey: ['abs'], queryFn: () => api('/ab-test') })
  const [a, setA] = useState(''); const [b, setB] = useState(''); const [sel, setSel] = useState<number | null>(null)
  useEffect(() => { if (models.data?.length && !a) { const v = [...models.data].reverse(); setA(v[0].version); setB(v[1]?.version ?? v[0].version) } }, [models.data])
  useEffect(() => { if (!sel && tests.data?.length) setSel(tests.data[0].id) }, [tests.data])
  const res = useQuery({ queryKey: ['ab', sel], queryFn: () => api(`/ab-test/${sel}`), enabled: !!sel })
  const run = useMutation({ mutationFn: () => api('/ab-test', { body: { model_a: a, model_b: b } }), onSuccess: (r) => { toast('ok', 'A/B test selesai'); qc.invalidateQueries({ queryKey: ['abs'] }); setSel(r.id) }, onError: (e: any) => toast('err', e.message) })
  return (
    <>
      <PageHeader title="A/B Testing" desc="Dua model dievaluasi pada dataset yang sama. Halaman ini hanya menampilkan pengukuran dan selisihnya; keputusan promosi ada pada Anda." />
      <Card className="mb-6"><CardBody className="flex flex-wrap items-end gap-4">
        <Field label="Model A" className="w-44"><Select value={a} onChange={(e) => setA(e.target.value)}>{models.data?.map((m: any) => <option key={m.id} value={m.version}>{m.version} ({m.status})</option>)}</Select></Field>
        <span className="pb-2 text-sm text-ink-mute">vs</span>
        <Field label="Model B" className="w-44"><Select value={b} onChange={(e) => setB(e.target.value)}>{models.data?.map((m: any) => <option key={m.id} value={m.version}>{m.version} ({m.status})</option>)}</Select></Field>
        <Field label="Dataset evaluasi" className="w-44"><Select disabled><option>eval_default</option></Select></Field>
        <Button variant="primary" loading={run.isPending} disabled={!a || !b || a === b} onClick={() => run.mutate()}><FlaskConical className="h-4 w-4" />Jalankan A/B test</Button></CardBody></Card>
      <div className="grid gap-6 lg:grid-cols-[1fr_260px]">
        <Card><CardHeader title={res.data ? `Hasil: ${res.data.model_a} vs ${res.data.model_b}` : 'Hasil'} desc={res.data ? `${res.data.n_queries} query, dataset ${res.data.dataset}` : undefined} />
          {!sel ? <Empty title="Belum ada A/B test" desc="Pilih dua model lalu jalankan." /> : res.isLoading || !res.data ? <Loading /> : <><AbResult r={res.data} /><p className="border-t border-line px-5 py-3 text-[13px] text-ink-mute">{res.data.note}</p></>}</Card>
        <Card className="self-start"><CardHeader title="Riwayat" /><ul className="divide-y divide-line">{tests.data?.map((t: any) => (
          <li key={t.id}><button onClick={() => setSel(t.id)} className={`w-full px-5 py-3 text-left text-sm hover:bg-stone-50 ${sel === t.id ? 'bg-brand-50' : ''}`}>#{t.id} {t.model_a} vs {t.model_b}</button></li>))}</ul></Card>
      </div>
    </>
  )
}
