import { useEffect, useState } from 'react'
import { useQuery } from '@tanstack/react-query'
import { api, label, num } from '../lib/api'
import { Badge, Card, CardBody, CardHeader, Empty, ErrorState, Loading, Mono, PageHeader, Select, Table, Td, Th } from '../components/ui'
import { RankList } from '../components/Rank'
import { cn } from '../components/ui'

/** Tangga peringkat: posisi dokumen yang diharapkan vs urutan hasil retrieval. */
function Ladder({ d }: { d: any }) {
  const expectedRank = d.results.findIndex((r: any) => r.correct) + 1
  return (
    <div className="grid gap-6 p-5 md:grid-cols-[220px_1fr]">
      <div>
        <p className="mb-2 text-[13px] font-medium text-ink-soft">Expected document</p>
        <div className="rounded-md border border-line p-3"><Mono className="font-medium text-ink">{d.expected?.chunk_id ?? '-'}</Mono><p className="mt-1 text-[13px] text-ink-mute">Rank ideal: 1</p>
          <p className="mt-1 text-[13px]">Rank aktual: <b className={expectedRank === 1 ? 'text-emerald-700' : 'text-red-700'}>{expectedRank || 'tidak ditemukan'}</b></p></div>
      </div>
      <div>
        <p className="mb-2 text-[13px] font-medium text-ink-soft">Retrieved</p>
        <ol className="space-y-1.5">
          {d.results.map((r: any) => (
            <li key={r.chunk_id} className={cn('flex items-center gap-3 rounded-md border px-3 py-2 text-sm', r.correct ? 'border-emerald-200 bg-emerald-50/60' : 'border-line')}>
              <span className={cn('flex h-6 w-6 items-center justify-center rounded text-xs font-semibold', r.rank === 1 ? 'bg-ink text-white' : 'bg-stone-100')}>{r.rank}</span>
              <span className="min-w-0 flex-1 truncate">Rank {r.rank} <span className="text-ink-mute">-&gt;</span> <b className={r.correct ? 'text-emerald-700' : 'text-red-700'}>{r.correct ? 'Correct document' : 'Wrong document'}</b></span>
              <Mono className="hidden sm:block">{r.chunk_id}</Mono>
              {r.original_rank && r.original_rank !== r.rank && <Badge tone="amber">retrieval #{r.original_rank}</Badge>}
            </li>))}
        </ol>
      </div>
    </div>
  )
}

export default function RetrievalAnalysis() {
  const hist = useQuery({ queryKey: ['history'], queryFn: () => api('/rag/history', { params: { limit: 100 } }) })
  const [qid, setQid] = useState<number | null>(null)
  const items = (hist.data ?? []).filter((h: any) => h.model_version)
  useEffect(() => { if (!qid && items.length) setQid((items.find((i: any) => i.failure_type) ?? items[0]).query_id) }, [items.length])
  const det = useQuery({ queryKey: ['retrieval', qid], queryFn: () => api(`/retrieval/${qid}`), enabled: !!qid })
  const d = det.data
  return (
    <>
      <PageHeader title="Retrieval Analysis" desc="Bandingkan dokumen yang diharapkan dengan hasil retrieval, lalu baca diagnosis kegagalannya." />
      <Card className="mb-6"><CardBody>
        <label className="mb-1.5 block text-[13px] font-medium text-ink-soft">Pilih query dari riwayat</label>
        <Select value={qid ?? ''} onChange={(e) => setQid(+e.target.value)}>{items.map((h: any) => <option key={h.query_id} value={h.query_id}>{h.failure_type ? '[gagal] ' : ''}{h.query} - model {h.model_version}</option>)}</Select>
      </CardBody></Card>
      {hist.error ? <Card><ErrorState error={hist.error} onRetry={hist.refetch} /></Card> : !qid ? <Card><Empty title="Belum ada riwayat query" desc="Jalankan query di RAG Playground atau jalankan seed." /></Card> : det.isLoading || !d ? <Card><Loading /></Card> : (<>
        <Card className="mb-6"><CardHeader title={d.query} desc={`Query class ${label(d.query_class)} - model ${d.model_version}`}
          action={d.failure_type ? <Badge tone="red">{label(d.failure_type)}</Badge> : <Badge tone="green">Retrieval benar</Badge>} />
          <Ladder d={d} />
          {d.failure_type && <div className="border-t border-line px-5 py-4 text-sm"><p className="mb-2 font-medium">Diagnosis</p><div className="flex flex-wrap gap-2">
            <Badge tone="red">{label(d.failure_type)}</Badge>{d.results[0] && !d.results[0].correct && <Badge>Similarity tinggi: {num(d.results[0].similarity, 2)}</Badge>}
            {d.expected && d.results[0] && d.expected.document_id !== d.results[0].document_id && d.expected.title === d.results[0].title && <Badge tone="amber">Version mismatch v{d.results[0].version} vs v{d.expected.version}</Badge>}
            {d.expected && d.results[0] && d.expected.document_id === d.results[0].document_id && <Badge tone="amber">Wrong chunk</Badge>}</div>
            <p className="mt-2 text-ink-soft">{d.failure_reason}</p></div>}
        </Card>
        <Card className="mb-6"><CardHeader title="Perbandingan expected vs retrieved" />
          <Table><thead><tr><Th>Query</Th><Th>Expected</Th><Th>Retrieved (rank 1)</Th><Th>Similarity</Th><Th>Reranking</Th><Th>Benar</Th><Th>Failure type</Th></tr></thead>
            <tbody><tr><Td className="max-w-[220px]">{d.query}</Td><Td><Mono>{d.expected?.chunk_id}</Mono></Td><Td><Mono>{d.results[0]?.chunk_id}</Mono></Td><Td>{num(d.results[0]?.similarity)}</Td><Td>{num(d.results[0]?.reranking_score)}</Td>
              <Td>{d.results[0]?.correct ? <Badge tone="green">Correct</Badge> : <Badge tone="red">Incorrect</Badge>}</Td><Td>{label(d.failure_type)}</Td></tr></tbody></Table></Card>
        <Card><CardHeader title="Dokumen terambil" desc="Klik baris untuk melihat chunk dan metadata" /><RankList hits={d.results} /></Card>
      </>)}
    </>
  )
}
