import { createContext, useCallback, useContext, useEffect, useState, type ReactNode } from 'react'
import clsx from 'clsx'
import { AlertTriangle, CheckCircle2, ChevronLeft, ChevronRight, ChevronDown, ChevronUp, Inbox, Loader2, X, XCircle } from 'lucide-react'

export const cn = clsx

/* ---------- Button ---------- */
type BtnProps = React.ButtonHTMLAttributes<HTMLButtonElement> & { variant?: 'primary' | 'secondary' | 'ghost' | 'danger'; size?: 'sm' | 'md'; loading?: boolean }
export function Button({ variant = 'secondary', size = 'md', loading, className, children, disabled, ...p }: BtnProps) {
  return (
    <button
      disabled={disabled || loading}
      className={cn(
        'inline-flex shrink-0 items-center justify-center gap-2 whitespace-nowrap rounded-md border font-medium leading-none transition-colors disabled:cursor-not-allowed disabled:opacity-50',
        size === 'sm' ? 'h-8 px-3.5 text-xs' : 'h-9 px-4 text-sm',
        variant === 'primary' && 'border-brand-600 bg-brand-600 text-white hover:border-brand-700 hover:bg-brand-700',
        variant === 'secondary' && 'border-stone-300 bg-white text-ink hover:bg-stone-50',
        variant === 'ghost' && 'border-transparent text-ink-soft hover:bg-stone-100',
        variant === 'danger' && 'border-red-300 bg-white text-red-700 hover:bg-red-50',
        className,
      )}
      {...p}
    >
      {loading && <Loader2 className="h-4 w-4 animate-spin" />}
      {children}
    </button>
  )
}

/* ---------- Card ---------- */
export function Card({ className, children }: { className?: string; children: ReactNode }) {
  return <section className={cn('rounded-lg border border-line bg-white', className)}>{children}</section>
}
export function CardHeader({ title, desc, action }: { title: ReactNode; desc?: ReactNode; action?: ReactNode }) {
  return (
    <div className="flex items-start justify-between gap-3 border-b border-line px-5 py-4">
      <div className="min-w-0">
        <h2>{title}</h2>
        {desc && <p className="mt-0.5 text-[13px] text-ink-mute">{desc}</p>}
      </div>
      {action}
    </div>
  )
}
export const CardBody = ({ className, children }: { className?: string; children: ReactNode }) => <div className={cn('p-5', className)}>{children}</div>

export function PageHeader({ title, desc, actions }: { title: string; desc?: string; actions?: ReactNode }) {
  return (
    <div className="mb-6 flex flex-wrap items-end justify-between gap-3">
      <div>
        <h1>{title}</h1>
        {desc && <p className="mt-1 max-w-2xl text-sm text-ink-mute">{desc}</p>}
      </div>
      {actions && <div className="flex flex-wrap gap-2">{actions}</div>}
    </div>
  )
}

/* ---------- Badge ---------- */
const TONES: Record<string, string> = {
  neutral: 'bg-stone-100 text-ink-soft', brand: 'bg-brand-50 text-brand-700', green: 'bg-emerald-50 text-emerald-700',
  red: 'bg-red-50 text-red-700', amber: 'bg-amber-50 text-amber-800', dark: 'bg-ink text-white',
}
export function Badge({ tone = 'neutral', children, className }: { tone?: keyof typeof TONES | string; children: ReactNode; className?: string }) {
  return <span className={cn('inline-flex items-center gap-1 whitespace-nowrap rounded-md px-2 py-0.5 text-xs font-medium', TONES[tone] ?? TONES.neutral, className)}>{children}</span>
}
const STATUS_TONE: Record<string, string> = {
  open: 'red', investigating: 'amber', resolved: 'green', pending: 'amber', approved: 'green', rejected: 'neutral', production: 'brand', staging: 'amber',
  candidate: 'neutral', archived: 'neutral', training: 'amber', completed: 'green', running: 'amber', queued: 'neutral', failed: 'red',
  high: 'red', medium: 'amber', low: 'neutral', critical: 'red',
}
export const StatusBadge = ({ value }: { value?: string | null }) => <Badge tone={STATUS_TONE[value ?? ''] ?? 'neutral'}>{value ?? '-'}</Badge>

/* ---------- Form ---------- */
const field = 'w-full rounded-md border border-line bg-white px-3 text-sm text-ink placeholder:text-ink-mute focus:border-brand-500 focus:outline-none focus:ring-2 focus:ring-brand-100'
export const Input = (p: React.InputHTMLAttributes<HTMLInputElement>) => <input {...p} className={cn(field, 'h-9', p.className)} />
export const Textarea = (p: React.TextareaHTMLAttributes<HTMLTextAreaElement>) => <textarea {...p} className={cn(field, 'py-2', p.className)} />
export const Select = ({ className, children, ...p }: React.SelectHTMLAttributes<HTMLSelectElement>) => (
  <select {...p} className={cn(field, 'h-9 pr-10', className)}>{children}</select>
)
export function Field({ label, hint, children, className }: { label: string; hint?: string; children: ReactNode; className?: string }) {
  return (
    <label className={cn('block', className)}>
      <span className="mb-1.5 block text-[13px] font-medium text-ink-soft">{label}</span>
      {children}
      {hint && <span className="mt-1 block text-xs text-ink-mute">{hint}</span>}
    </label>
  )
}

/* ---------- Tabs ---------- */
export function Tabs({ tabs, value, onChange }: { tabs: { id: string; label: string }[]; value: string; onChange: (id: string) => void }) {
  return (
    <div className="flex gap-1 border-b border-line" role="tablist">
      {tabs.map((t) => (
        <button key={t.id} role="tab" aria-selected={value === t.id} onClick={() => onChange(t.id)}
          className={cn('-mb-px border-b-2 px-3 py-2 text-sm font-medium transition-colors', value === t.id ? 'border-brand-600 text-ink' : 'border-transparent text-ink-mute hover:text-ink')}>
          {t.label}
        </button>
      ))}
    </div>
  )
}

/* ---------- Modal & Confirm ---------- */
export function Modal({ open, onClose, title, children, wide }: { open: boolean; onClose: () => void; title: string; children: ReactNode; wide?: boolean }) {
  useEffect(() => {
    if (!open) return
    const h = (e: KeyboardEvent) => e.key === 'Escape' && onClose()
    window.addEventListener('keydown', h)
    return () => window.removeEventListener('keydown', h)
  }, [open, onClose])
  if (!open) return null
  return (
    <div className="fixed inset-0 z-50 flex items-start justify-center overflow-y-auto bg-ink/40 p-4 sm:p-10" onMouseDown={onClose}>
      <div role="dialog" aria-modal="true" aria-label={title} onMouseDown={(e) => e.stopPropagation()}
        className={cn('w-full rounded-lg border border-line bg-white shadow-xl', wide ? 'max-w-3xl' : 'max-w-lg')}>
        <div className="flex items-center justify-between border-b border-line px-5 py-3.5">
          <h2>{title}</h2>
          <button onClick={onClose} aria-label="Tutup" className="rounded-md p-1 text-ink-mute hover:bg-stone-100"><X className="h-4 w-4" /></button>
        </div>
        <div className="p-5">{children}</div>
      </div>
    </div>
  )
}
export function Confirm({ open, title, message, confirmLabel = 'Lanjutkan', danger, onConfirm, onClose }:
  { open: boolean; title: string; message: string; confirmLabel?: string; danger?: boolean; onConfirm: () => void; onClose: () => void }) {
  return (
    <Modal open={open} onClose={onClose} title={title}>
      <p className="text-sm text-ink-soft">{message}</p>
      <div className="mt-5 flex justify-end gap-2">
        <Button onClick={onClose}>Batal</Button>
        <Button variant={danger ? 'danger' : 'primary'} onClick={() => { onConfirm(); onClose() }}>{confirmLabel}</Button>
      </div>
    </Modal>
  )
}

/* ---------- Toast ---------- */
type Toast = { id: number; kind: 'ok' | 'err'; text: string }
const ToastCtx = createContext<(kind: 'ok' | 'err', text: string) => void>(() => {})
export const useToast = () => useContext(ToastCtx)
export function ToastProvider({ children }: { children: ReactNode }) {
  const [items, setItems] = useState<Toast[]>([])
  const push = useCallback((kind: 'ok' | 'err', text: string) => {
    const id = Date.now() + Math.random()
    setItems((x) => [...x, { id, kind, text }])
    setTimeout(() => setItems((x) => x.filter((t) => t.id !== id)), 4500)
  }, [])
  return (
    <ToastCtx.Provider value={push}>
      {children}
      <div className="fixed bottom-4 right-4 z-[60] flex w-80 max-w-[calc(100vw-2rem)] flex-col gap-2" aria-live="polite">
        {items.map((t) => (
          <div key={t.id} className="flex items-start gap-2 rounded-lg border border-line bg-white p-3 text-sm shadow-lg">
            {t.kind === 'ok' ? <CheckCircle2 className="mt-0.5 h-4 w-4 shrink-0 text-emerald-600" /> : <XCircle className="mt-0.5 h-4 w-4 shrink-0 text-red-600" />}
            <span>{t.text}</span>
          </div>
        ))}
      </div>
    </ToastCtx.Provider>
  )
}

/* ---------- States ---------- */
export const Skeleton = ({ className }: { className?: string }) => <div className={cn('animate-pulse rounded-md bg-stone-200/70', className)} />
export function Empty({ title, desc, action }: { title: string; desc?: string; action?: ReactNode }) {
  return (
    <div className="flex flex-col items-center px-6 py-12 text-center">
      <Inbox className="mb-3 h-8 w-8 text-stone-300" />
      <p className="font-medium">{title}</p>
      {desc && <p className="mt-1 max-w-sm text-sm text-ink-mute">{desc}</p>}
      {action && <div className="mt-4">{action}</div>}
    </div>
  )
}
export function ErrorState({ error, onRetry }: { error: unknown; onRetry?: () => void }) {
  return (
    <div className="flex flex-col items-center px-6 py-10 text-center">
      <AlertTriangle className="mb-3 h-8 w-8 text-red-400" />
      <p className="font-medium">Data gagal dimuat</p>
      <p className="mt-1 max-w-md text-sm text-ink-mute">{(error as Error)?.message ?? 'Terjadi kesalahan'}. Pastikan backend berjalan di port 8000.</p>
      {onRetry && <Button className="mt-4" onClick={onRetry}>Coba lagi</Button>}
    </div>
  )
}
export function Loading({ rows = 4 }: { rows?: number }) {
  return <div className="space-y-2.5 p-5">{Array.from({ length: rows }).map((_, i) => <Skeleton key={i} className="h-8" />)}</div>
}

/* ---------- Table helpers ---------- */
export const Table = ({ children }: { children: ReactNode }) => <div className="overflow-x-auto"><table className="w-full min-w-[640px] text-left text-sm">{children}</table></div>
export const Th = ({ children, className }: { children?: ReactNode; className?: string }) => (
  <th className={cn('whitespace-nowrap border-b border-line bg-stone-50/70 px-4 py-2.5 text-[13px] font-medium text-ink-mute', className)}>{children}</th>
)
export function SortTh({ children, col, sort, order, onSort }: { children: ReactNode; col: string; sort: string; order: string; onSort: (c: string) => void }) {
  const active = sort === col
  return (
    <Th>
      <button onClick={() => onSort(col)} className={cn('inline-flex items-center gap-1 hover:text-ink', active && 'text-ink')}>
        {children}{active && (order === 'asc' ? <ChevronUp className="h-3.5 w-3.5" /> : <ChevronDown className="h-3.5 w-3.5" />)}
      </button>
    </Th>
  )
}
export const Td = ({ children, className, ...p }: React.TdHTMLAttributes<HTMLTableCellElement>) => <td className={cn('border-b border-line/70 px-4 py-3 align-top', className)} {...p}>{children}</td>

export function Pagination({ page, pageSize, total, onPage }: { page: number; pageSize: number; total: number; onPage: (p: number) => void }) {
  const pages = Math.max(1, Math.ceil(total / pageSize))
  return (
    <div className="flex items-center justify-between px-4 py-3 text-[13px] text-ink-mute">
      <span>{total === 0 ? '0 data' : `${(page - 1) * pageSize + 1}-${Math.min(page * pageSize, total)} dari ${total}`}</span>
      <div className="flex items-center gap-1">
        <Button size="sm" variant="ghost" disabled={page <= 1} onClick={() => onPage(page - 1)} aria-label="Halaman sebelumnya"><ChevronLeft className="h-4 w-4" /></Button>
        <span className="px-2">{page} / {pages}</span>
        <Button size="sm" variant="ghost" disabled={page >= pages} onClick={() => onPage(page + 1)} aria-label="Halaman berikutnya"><ChevronRight className="h-4 w-4" /></Button>
      </div>
    </div>
  )
}

export function Stat({ label, value, hint, tone }: { label: string; value: ReactNode; hint?: string; tone?: 'brand' | 'red' }) {
  return (
    <div className="rounded-lg border border-line bg-white p-4">
      <p className="text-[13px] text-ink-mute">{label}</p>
      <p className={cn('mt-1.5 text-2xl font-semibold tracking-tight', tone === 'brand' && 'text-brand-600', tone === 'red' && 'text-red-600')}>{value}</p>
      {hint && <p className="mt-0.5 text-xs text-ink-mute">{hint}</p>}
    </div>
  )
}
export const Mono = ({ children, className }: { children: ReactNode; className?: string }) => <code className={cn('font-mono text-[12.5px] text-ink-soft', className)}>{children}</code>
export const Json = ({ data }: { data: any }) => <pre className="max-h-80 overflow-auto rounded-md bg-ink p-4 font-mono text-xs leading-relaxed text-stone-100">{JSON.stringify(data, null, 2)}</pre>
export function ScoreBar({ value, max = 1, tone = 'brand' }: { value: number; max?: number; tone?: 'brand' | 'ink' }) {
  const w = Math.max(0, Math.min(100, (value / max) * 100))
  return (
    <div className="flex items-center gap-2">
      <div className="h-1.5 w-20 overflow-hidden rounded-full bg-stone-200"><div className={cn('h-full', tone === 'brand' ? 'bg-brand-500' : 'bg-ink')} style={{ width: `${w}%` }} /></div>
      <span className="tabular-nums text-[13px]">{value.toFixed(3)}</span>
    </div>
  )
}
