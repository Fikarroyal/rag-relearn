import { useState } from 'react'
import { Link, useNavigate, useParams } from 'react-router-dom'
import { useMutation, useQuery, useQueryClient } from '@tanstack/react-query'
import { ArrowLeft, CheckCheck, FilePlus2, Network, RotateCw, Search as SearchIcon } from 'lucide-react'
import { api, FAILURE_TYPES, label, num, when } from '../lib/api'
import { Badge, Button, Card, CardBody, CardHeader, Confirm, Empty, ErrorState, Input, Json, Loading, Mono, PageHeader, Pagination, Select, SortTh, StatusBadge, Table, Td, Th, useToast } from '../components/ui'
import { RankList } from '../components/Rank'

export function FailureCases() {
  const nav = useNavigate()
  const [f, setF] = useState<Record<string, any>>({ failure_type: '', model_version: '', retriever: '', reranker: '', severity: '', status: '', search: '', date_from: '' })
  const [sort, setSort] = useState('created_at'); const [order, setOrder] = useState('desc'); const [page, setPage] = useState(1)
  const pageSize = 15
  const { data, isLoading, error, refetch } = useQuery({ queryKey: ['failures', f, sort, order, page], queryFn: () => api('/failures', { params: { ...f, sort, order, page, page_size: pageSize } }), placeholderData: (p) => p })
  const set = (k: string, v: string) => { setF({ ...f, [k]: v }); setPage(1) }
  const onSort = (c: string) => { if (sort === c) setOrder(order === 'asc' ? 'desc' : 'asc'); else { setSort(c); setOrder('desc') } }
  return (
    <>
      <PageHeader title="Failure Cases" desc="Seluruh kegagalan RAG yang terdeteksi. Klik satu baris untuk membuka diagnosis lengkap." />
      <Card className="mb-6"><CardBody className="grid gap-3 sm:grid-cols-2 lg:grid-cols-4">
        <div className="relative sm:col-span-2"><SearchIcon className="pointer-events-none absolute left-3 top-2.5 h-4 w-4 text-ink-mute" /><Input className="pl-9" placeholder="Cari query atau ground truth" value={f.search} onChange={(e) => set('search', e.target.value)} /></div>
        <Select value={f.failure_type} onChange={(e) => set('failure_type', e.target.value)}><option value="">Semua failure type</option>{FAILURE_TYPES.map((t) => <option key={t} value={t}>{label(t)}</option>)}</Select>
        <Select value={f.model_version} onChange={(e) => set('model_version', e.target.value)}><option value="">Semua model version</option>{['v1', 'v2', 'v3', 'v4'].map((v) => <option key={v}>{v}</option>)}</Select>
        <Select value={f.retriever} onChange={(e) => set('retriever', e.target.value)}><option value="">Semua retriever</option><option>vector-cosine</option></Select>
        <Select value={f.reranker} onChange={(e) => set('reranker', e.target.value)}><option value="">Semua reranker</option><option>none</option><option>linear-reranker-v2</option></Select>
        <Select value={f.severity} onChange={(e) => set('severity', e.target.value)}><option value="">Semua severity</option><option>high</option><option>medium</option><option>low</option></Select>
        <Select value={f.status} onChange={(e) => set('status', e.target.value)}><option value="">Semua status</option><option>open</option><option>investigating</option><option>resolved</option></Select>
        <Input type="date" aria-label="Sejak tanggal" value={f.date_from} onChange={(e) => set('date_from', e.target.value)} />
      </CardBody></Card>
      <Card>
        {error ? <ErrorState error={error} onRetry={refetch} /> : isLoading ? <Loading rows={8} /> : !data?.items.length ? <Empty title="Tidak ada failure case" desc="Ubah filter atau jalankan query yang gagal di RAG Playground." /> : (<>
          <Table><thead><tr><SortTh col="id" sort={sort} order={order} onSort={onSort}>ID</SortTh><Th>Query</Th><Th>Failure type</Th><SortTh col="severity" sort={sort} order={order} onSort={onSort}>Severity</SortTh><Th>Model</Th><Th>Retriever</Th><Th>Reranker</Th>
            <SortTh col="similarity" sort={sort} order={order} onSort={onSort}>Similarity</SortTh><Th>Ground truth</Th><Th>Status</Th><SortTh col="created_at" sort={sort} order={order} onSort={onSort}>Created</SortTh></tr></thead>
            <tbody>{data.items.map((r: any) => (
              <tr key={r.id} onClick={() => nav(`/failures/${r.id}`)} className="cursor-pointer hover:bg-stone-50">
                <Td>#{r.id}</Td><Td className="max-w-[260px]"><span className="line-clamp-2">{r.query}</span></Td><Td><Badge tone="brand">{label(r.failure_type)}</Badge></Td><Td><StatusBadge value={r.severity} /></Td>
                <Td>{r.model_version}</Td><Td>{r.retriever}</Td><Td>{r.reranker}</Td><Td>{num(r.similarity, 2)}</Td><Td><Mono>{r.ground_truth}</Mono></Td><Td><StatusBadge value={r.status} /></Td><Td className="whitespace-nowrap text-ink-mute">{when(r.created_at)}</Td></tr>))}</tbody></Table>
          <Pagination page={page} pageSize={pageSize} total={data.total} onPage={setPage} /></>)}
      </Card>
    </>
  )
}

export function FailureDetail() {
  const { id } = useParams(); const toast = useToast(); const qc = useQueryClient()
  const [confirm, setConfirm] = useState(false)
  const [rerun, setRerun] = useState<any>(null)
  const { data: d, isLoading, error, refetch } = useQuery({ queryKey: ['failure', id], queryFn: () => api(`/failures/${id}`) })
  const refresh = () => { qc.invalidateQueries({ queryKey: ['failure', id] }); qc.invalidateQueries({ queryKey: ['failures'] }); qc.invalidateQueries({ queryKey: ['dashboard'] }) }
  const act = (fn: () => Promise<any>, ok: (r: any) => string) => ({ mutationFn: fn, onSuccess: (r: any) => { toast('ok', ok(r)); refresh() }, onError: (e: any) => toast('err', e.message) })
  const gen = useMutation(act(() => api(`/failures/${id}/hard-negative`, { method: 'POST' }), (r) => `${r.generated.length} hard negative baru dibuat`))
  const add = useMutation(act(() => api(`/failures/${id}/add-to-dataset`, { method: 'POST' }), (r) => `${r.approved} hard negative disetujui untuk dataset`))
  const resolve = useMutation(act(() => api(`/failures/${id}/status`, { body: { status: 'resolved' } }), () => 'Ditandai resolved'))
  const rr = useMutation({ mutationFn: () => api(`/failures/${id}/rerun`, { method: 'POST' }), onSuccess: (r) => { setRerun(r); refresh() }, onError: (e: any) => toast('err', e.message) })
  if (error) return <Card><ErrorState error={error} onRetry={refetch} /></Card>
  if (isLoading || !d) return <Card><Loading rows={8} /></Card>
  const dg = d.diagnosis
  return (
    <>
      <Link to="/failures" className="mb-3 inline-flex items-center gap-1 text-[13px] text-ink-mute hover:text-ink"><ArrowLeft className="h-4 w-4" />Semua failure case</Link>
      <PageHeader title={`Failure #${d.id}`} desc={d.query} actions={<>
        <Button onClick={() => gen.mutate()} loading={gen.isPending}><Network className="h-4 w-4" />Generate hard negative</Button>
        <Button onClick={() => add.mutate()} loading={add.isPending}><FilePlus2 className="h-4 w-4" />Add to training dataset</Button>
        <Button onClick={() => rr.mutate()} loading={rr.isPending}><RotateCw className="h-4 w-4" />Re-run evaluation</Button>
        <Button variant="primary" disabled={d.status === 'resolved'} onClick={() => setConfirm(true)}><CheckCheck className="h-4 w-4" />Mark resolved</Button></>} />
      {rerun && <Card className="mb-6"><CardBody className="flex flex-wrap items-center gap-3 text-sm">
        <Badge tone={rerun.still_failing ? 'red' : 'green'}>{rerun.still_failing ? 'Masih gagal' : 'Sudah benar'}</Badge>
        <span>Model {rerun.model_version} memilih <Mono>{rerun.top1}</Mono></span>{rerun.diagnosis && <span className="text-ink-mute">{label(rerun.diagnosis.failure_type)}</span>}</CardBody></Card>}
      <div className="mb-6 grid gap-6 lg:grid-cols-3">
        <Card className="lg:col-span-2"><CardHeader title="Failure diagnosis" action={<div className="flex gap-2"><StatusBadge value={d.severity} /><StatusBadge value={d.status} /></div>} />
          <CardBody className="space-y-4 text-sm">
            <div className="flex flex-wrap items-center gap-2"><Badge tone="brand">{label(dg.failure_type)}</Badge><span className="text-ink-mute">confidence {num(dg.confidence, 2)} - model {d.model_version} - {when(d.created_at)}</span></div>
            <div><p className="mb-1 text-[13px] font-medium text-ink-soft">Failure explanation</p><ul className="list-disc space-y-1 pl-5 text-ink-soft">{dg.evidence.map((e: string) => <li key={e}>{e}</li>)}</ul></div>
            <div><p className="mb-1 text-[13px] font-medium text-ink-soft">Root cause</p><p>{dg.root_cause}</p></div>
            <div><p className="mb-1 text-[13px] font-medium text-ink-soft">Recommended action</p><p>{dg.recommended_action}</p></div></CardBody></Card>
        <Card><CardHeader title="Jawaban dan ground truth" /><CardBody className="space-y-3 text-sm">
          <div><p className="text-[13px] text-ink-mute">Generated answer</p><p className="mt-1">{d.answer.replace(/\[[^\]]+\]/g, '')}</p></div>
          <div><p className="text-[13px] text-ink-mute">Citation</p><div className="mt-1 flex flex-wrap gap-1">{d.citations.map((c: string) => <Mono key={c} className="rounded bg-stone-100 px-1.5 py-0.5">{c}</Mono>)}</div></div>
          <div><p className="text-[13px] text-ink-mute">Ground truth</p><Mono className="mt-1 block text-ink">{d.ground_truth}</Mono></div></CardBody></Card>
      </div>
      <Card className="mb-6"><CardHeader title="Retrieved documents" desc="Similarity dan reranking score per chunk; hijau = dokumen yang diharapkan" /><RankList hits={d.retrieved} expected={d.ground_truth} /></Card>
      <div className="grid gap-6 lg:grid-cols-2">
        <Card><CardHeader title="Expected document" /><CardBody className="text-sm">{d.expected ? (<><Mono className="text-ink">{d.expected.chunk_id}</Mono><p className="mt-1 text-[13px] text-ink-mute">{d.expected.title} - v{d.expected.version} - {d.expected.section}</p><p className="mt-3 text-ink-soft">{d.expected.content}</p></>) : <p className="text-ink-mute">-</p>}</CardBody></Card>
        <Card><CardHeader title="Hard negative candidates" desc={`${d.hard_negatives.length} kandidat`} />
          {d.hard_negatives.length === 0 ? <Empty title="Belum ada kandidat" desc="Klik Generate hard negative." /> : <ul className="divide-y divide-line">{d.hard_negatives.map((h: any) => (
            <li key={h.id} className="flex items-center justify-between gap-3 px-5 py-3 text-sm"><div className="min-w-0"><Mono className="text-ink">{h.hard_negative}</Mono><p className="text-[13px] text-ink-mute">{h.reason} - sim {num(h.similarity, 2)}</p></div><StatusBadge value={h.status} /></li>))}</ul>}</Card>
      </div>
      <Card className="mt-6"><CardHeader title="Training dataset entry" />{d.training_entry ? <CardBody><Json data={d.training_entry} /></CardBody> : <Empty title="Belum ada entri" desc="Entri dibuat setelah hard negative tersedia." />}</Card>
      <Confirm open={confirm} title="Tandai resolved?" message="Failure case ini akan ditandai sudah selesai. Jalankan Re-run evaluation lebih dulu bila ingin memastikan model sudah benar." confirmLabel="Tandai resolved" onConfirm={() => resolve.mutate()} onClose={() => setConfirm(false)} />
    </>
  )
}
