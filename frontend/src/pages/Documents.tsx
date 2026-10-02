import { useRef, useState } from 'react'
import { useMutation, useQuery, useQueryClient } from '@tanstack/react-query'
import { Upload } from 'lucide-react'
import { api, upload, when } from '../lib/api'
import { Badge, Button, Card, Empty, ErrorState, Field, Input, Loading, Modal, Mono, PageHeader, Table, Td, Th, useToast } from '../components/ui'

export default function Documents() {
  const toast = useToast(); const qc = useQueryClient(); const ref = useRef<HTMLInputElement>(null)
  const { data, isLoading, error, refetch } = useQuery({ queryKey: ['docs'], queryFn: () => api('/documents') })
  const [open, setOpen] = useState(false); const [file, setFile] = useState<File | null>(null); const [version, setVersion] = useState('')
  const [view, setView] = useState<string | null>(null)
  const chunks = useQuery({ queryKey: ['chunks', view], queryFn: () => api(`/documents/${view}/chunks`), enabled: !!view })
  const up = useMutation({ mutationFn: () => { const fd = new FormData(); fd.append('file', file!); if (version) fd.append('version', version); return upload('/documents/upload', fd) },
    onSuccess: (r) => { toast('ok', `${r.document_id}: ${r.chunks} chunk`); setOpen(false); setFile(null); setVersion(''); qc.invalidateQueries({ queryKey: ['docs'] }) }, onError: (e: any) => toast('err', e.message) })
  return (
    <>
      <PageHeader title="Documents" desc="Korpus yang diindeks. Versi terbaru per keluarga dokumen ditandai otomatis dan dipakai untuk evaluasi version mismatch." actions={<Button variant="primary" onClick={() => setOpen(true)}><Upload className="h-4 w-4" />Upload dokumen</Button>} />
      <Card>{error ? <ErrorState error={error} onRetry={refetch} /> : isLoading ? <Loading /> : !data?.length ? <Empty title="Belum ada dokumen" desc="Upload PDF, DOCX, TXT, atau Markdown (maks 10 MB)." /> : (
        <Table><thead><tr><Th>Document ID</Th><Th>Title</Th><Th>Version</Th><Th>Chunks</Th><Th>Source</Th><Th>Ditambahkan</Th><Th /></tr></thead>
          <tbody>{data.map((d: any) => <tr key={d.id}><Td><Mono className="text-ink">{d.document_id}</Mono></Td><Td>{d.title}</Td><Td><Badge tone={d.is_latest ? 'brand' : 'neutral'}>v{d.version}{d.is_latest ? ' terbaru' : ''}</Badge></Td><Td>{d.chunks}</Td><Td>{d.source}</Td><Td>{when(d.created_at)}</Td>
            <Td className="whitespace-nowrap"><Button size="sm" onClick={() => setView(d.document_id)}>Lihat chunk</Button></Td></tr>)}</tbody></Table>)}</Card>
      <Modal open={open} onClose={() => setOpen(false)} title="Upload dokumen">
        <div className="space-y-4">
          <input ref={ref} type="file" accept=".pdf,.docx,.txt,.md" className="hidden" onChange={(e) => setFile(e.target.files?.[0] ?? null)} />
          <button onClick={() => ref.current?.click()} className="w-full rounded-lg border border-dashed border-stone-300 px-4 py-8 text-center text-sm text-ink-soft hover:border-brand-500 hover:bg-brand-50/40">{file ? file.name : 'Pilih file PDF, DOCX, TXT, atau MD'}</button>
          <Field label="Versi dokumen" hint="Opsional bila nama file sudah berakhiran _v2, _v3, dst."><Input type="number" min={1} value={version} onChange={(e) => setVersion(e.target.value)} /></Field>
          <div className="flex justify-end gap-2"><Button onClick={() => setOpen(false)}>Batal</Button><Button variant="primary" disabled={!file} loading={up.isPending} onClick={() => up.mutate()}>Upload dan indeks</Button></div></div></Modal>
      <Modal open={!!view} onClose={() => setView(null)} title={`Chunk ${view ?? ''}`} wide>
        {chunks.isLoading ? <Loading /> : <ul className="space-y-3">{chunks.data?.map((c: any) => (<li key={c.chunk_id} className="rounded-md border border-line p-3 text-sm"><div className="mb-1 flex flex-wrap items-center gap-2"><Mono className="text-ink">{c.chunk_id}</Mono><Badge>hal. {c.page}</Badge><Badge>hash {c.content_hash.slice(0, 8)}</Badge></div><p className="text-ink-soft">{c.content}</p></li>))}</ul>}</Modal>
    </>
  )
}
