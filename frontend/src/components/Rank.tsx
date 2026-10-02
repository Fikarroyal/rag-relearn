import { useState } from 'react'
import { CheckCircle2, ChevronDown, XCircle } from 'lucide-react'
import { Badge, cn, Mono, ScoreBar } from './ui'

export type Hit = {
  rank?: number; chunk_id: string; document_id?: string; title?: string; version?: number; section?: string; page?: number; source?: string
  content?: string; similarity?: number; reranking_score?: number; correct?: boolean; selected?: boolean; original_rank?: number
}

/** Daftar hasil retrieval berperingkat; tiap dokumen bisa dibuka untuk melihat chunk dan metadata. */
export function RankList({ hits, expected }: { hits: Hit[]; expected?: string | null }) {
  const [open, setOpen] = useState<string | null>(null)
  return (
    <ol className="divide-y divide-line">
      {hits.map((h, i) => {
        const rank = h.rank ?? i + 1
        const correct = h.correct ?? (expected ? h.chunk_id === expected : undefined)
        const isOpen = open === h.chunk_id
        return (
          <li key={h.chunk_id}>
            <button onClick={() => setOpen(isOpen ? null : h.chunk_id)} className="flex w-full items-center gap-3 px-5 py-3 text-left hover:bg-stone-50" aria-expanded={isOpen}>
              <span className={cn('flex h-8 w-8 shrink-0 items-center justify-center rounded-md text-sm font-semibold', rank === 1 ? 'bg-ink text-white' : 'bg-stone-100 text-ink-soft')}>{rank}</span>
              <div className="min-w-0 flex-1">
                <div className="flex flex-wrap items-center gap-2">
                  <Mono className="font-medium text-ink">{h.chunk_id}</Mono>
                  {h.selected && <Badge tone="brand">Dipakai di context</Badge>}
                  {correct === true && <Badge tone="green"><CheckCircle2 className="h-3 w-3" />Benar</Badge>}
                  {correct === false && <Badge tone="red"><XCircle className="h-3 w-3" />Salah</Badge>}
                </div>
                <p className="mt-0.5 truncate text-[13px] text-ink-mute">{h.title} - v{h.version} - {h.section}</p>
              </div>
              <div className="hidden shrink-0 gap-6 sm:flex">
                <div><p className="text-[11px] text-ink-mute">Similarity</p><ScoreBar value={h.similarity ?? 0} /></div>
                <div><p className="text-[11px] text-ink-mute">Rerank</p><ScoreBar value={h.reranking_score ?? 0} max={Math.max(1, h.reranking_score ?? 1)} tone="ink" /></div>
              </div>
              <ChevronDown className={cn('h-4 w-4 shrink-0 text-ink-mute transition-transform', isOpen && 'rotate-180')} />
            </button>
            {isOpen && (
              <div className="grid gap-4 bg-stone-50 px-5 py-4 text-sm md:grid-cols-[1fr_220px]">
                <div><p className="mb-1 text-[13px] font-medium text-ink-soft">Content</p><p className="leading-relaxed text-ink-soft">{h.content}</p></div>
                <dl className="space-y-1.5 text-[13px]">
                  {[['Document ID', h.document_id], ['Document title', h.title], ['Chunk ID', h.chunk_id], ['Document version', h.version != null ? `v${h.version}` : '-'],
                    ['Section', h.section], ['Page', h.page], ['Source', h.source], ['Similarity', h.similarity?.toFixed(4)], ['Reranking score', h.reranking_score?.toFixed(4)],
                    ['Rank awal', h.original_rank ?? '-']].map(([k, v]) => (
                    <div key={k as string} className="flex justify-between gap-3"><dt className="text-ink-mute">{k}</dt><dd className="break-all text-right font-medium">{v ?? '-'}</dd></div>
                  ))}
                </dl>
              </div>
            )}
          </li>
        )
      })}
    </ol>
  )
}
