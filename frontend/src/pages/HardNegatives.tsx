import { useState } from 'react'
import { useMutation, useQuery, useQueryClient } from '@tanstack/react-query'
import { Check, RefreshCw, X } from 'lucide-react'
import { api, label, num } from '../lib/api'
import { Badge, Button, Card, CardHeader, Empty, ErrorState, Loading, Mono, PageHeader, Pagination, Select, StatusBadge, Table, Td, Th, useToast } from '../components/ui'

export default function HardNegatives() {
  const toast = useToast(); const qc = useQueryClient()
  const [status, setStatus] = useState(''); const [type, setType] = useState(''); const [page, setPage] = useState(1)
  const size = 12
  const { data, isLoading, error, refetch } = useQuery({ queryKey: ['hn', status, type, page], queryFn: () => api('/hard-negatives', { params: { status, negative_type: type, page, page_size: size } }), placeholderData: (p) => p })
  const act = useMutation({
    mutationFn: ({ id, a }: { id: number; a: string }) => api(`/hard-negatives/${id}/${a}`, { method: 'POST' }),
    onSuccess: (r, v) => { toast('ok', v.a === 'regenerate' ? `Negatif baru: ${r.hard_negative}` : v.a === 'approve' ? 'Disetujui' : 'Ditolak'); qc.invalidateQueries({ queryKey: ['hn'] }); qc.invalidateQueries({ queryKey: ['dashboard'] }) },
    onError: (e: any) => toast('err', e.message),
  })
  return (
    <>
      <PageHeader title="Hard Negative Mining" desc="Negatif sulit hasil mining dari kegagalan. Hanya yang disetujui masuk ke training dataset." />
      <Card>
        <CardHeader title="Kandidat negatif" action={<div className="flex gap-2">
          <Select value={status} onChange={(e) => { setStatus(e.target.value); setPage(1) }} className="w-36"><option value="">Semua status</option><option>pending</option><option>approved</option><option>rejected</option></Select>
          <Select value={type} onChange={(e) => { setType(e.target.value); setPage(1) }} className="w-44"><option value="">Semua tipe</option><option value="wrong_version">Wrong version</option><option value="wrong_section">Wrong section</option><option value="keyword_overlap">Keyword overlap</option><option value="topical">Topical</option></Select></div>} />
        {error ? <ErrorState error={error} onRetry={refetch} /> : isLoading ? <Loading rows={8} /> : !data?.items.length ? <Empty title="Tidak ada hard negative" desc="Buka failure case lalu klik Generate hard negative." /> : (<>
          <Table><thead><tr><Th>Query</Th><Th>Positive document</Th><Th>Candidate negative</Th><Th>Similarity</Th><Th>Negative type</Th><Th>Reason</Th><Th>Confidence</Th><Th>Status</Th><Th /></tr></thead>
            <tbody>{data.items.map((h: any) => (
              <tr key={h.id}><Td className="max-w-[220px]">{h.query}</Td><Td><Mono className="text-emerald-700">{h.positive}</Mono></Td><Td><Mono className="text-red-700">{h.hard_negative}</Mono></Td><Td>{num(h.similarity, 2)}</Td>
                <Td><Badge tone="brand">{label(h.negative_type)}</Badge></Td><Td className="max-w-[200px] text-ink-soft">{h.reason}</Td><Td>{num(h.confidence, 2)}</Td><Td><StatusBadge value={h.status} /></Td>
                <Td><div className="flex gap-1.5"><Button size="sm" variant="primary" disabled={h.status === 'approved'} onClick={() => act.mutate({ id: h.id, a: 'approve' })}><Check className="h-3.5 w-3.5" />Approve</Button>
                  <Button size="sm" disabled={h.status === 'rejected'} onClick={() => act.mutate({ id: h.id, a: 'reject' })}><X className="h-3.5 w-3.5" />Reject</Button>
                  <Button size="sm" variant="ghost" onClick={() => act.mutate({ id: h.id, a: 'regenerate' })}><RefreshCw className="h-3.5 w-3.5" />Regenerate</Button></div></Td></tr>))}</tbody></Table>
          <Pagination page={page} pageSize={size} total={data.total} onPage={setPage} /></>)}
      </Card>
    </>
  )
}
