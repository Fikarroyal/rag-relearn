import { useState } from 'react'
import { NavLink, Outlet } from 'react-router-dom'
import { useQuery } from '@tanstack/react-query'
import {
  Activity, BarChart3, Boxes, Database, FileText, FlaskConical, GitCompareArrows, LayoutDashboard, Layers, Menu, Network, Search, Settings,
  ShieldAlert, SlidersHorizontal, Terminal, User, Workflow, X,
} from 'lucide-react'
import { api } from '../lib/api'
import { Badge, Button, cn, Field, Input, Modal, useToast } from './ui'

const NAV = [
  { to: '/', label: 'Dashboard', icon: LayoutDashboard },
  { to: '/playground', label: 'RAG Playground', icon: Terminal },
  { to: '/retrieval', label: 'Retrieval Analysis', icon: Search },
  { to: '/failures', label: 'Failure Cases', icon: ShieldAlert },
  { to: '/hard-negatives', label: 'Hard Negatives', icon: Network },
  { to: '/dataset', label: 'Training Dataset', icon: Database },
  { to: '/training', label: 'Training Center', icon: SlidersHorizontal },
  { to: '/models', label: 'Models', icon: Boxes },
  { to: '/ab-testing', label: 'A/B Testing', icon: GitCompareArrows },
  { to: '/evaluation', label: 'Evaluation', icon: BarChart3 },
  { to: '/experiments', label: 'Experiments', icon: FlaskConical },
  { to: '/documents', label: 'Documents', icon: FileText },
  { to: '/mcp', label: 'MCP Tools', icon: Layers },
  { to: '/settings', label: 'System Settings', icon: Settings },
]

function LoginModal({ open, onClose }: { open: boolean; onClose: () => void }) {
  const toast = useToast()
  const [u, setU] = useState('researcher')
  const [p, setP] = useState('')
  const role = localStorage.getItem('rr_role')
  const login = async () => {
    try {
      const r = await api('/auth/login', { body: { username: u, password: p } })
      localStorage.setItem('rr_token', r.access_token); localStorage.setItem('rr_role', r.role)
      toast('ok', `Masuk sebagai ${u} (${r.role})`); onClose()
    } catch (e: any) { toast('err', e.message) }
  }
  return (
    <Modal open={open} onClose={onClose} title="Profil dan akses">
      <p className="mb-4 text-sm text-ink-mute">{role ? `Sesi aktif dengan role ${role}.` : 'Mode demo berjalan tanpa login. Masuk bila AUTH_ENABLED=true di backend.'}</p>
      <div className="space-y-3">
        <Field label="Username"><Input value={u} onChange={(e) => setU(e.target.value)} /></Field>
        <Field label="Password"><Input type="password" value={p} onChange={(e) => setP(e.target.value)} placeholder="Akun demo ada di README" /></Field>
      </div>
      <div className="mt-5 flex justify-between">
        <Button variant="ghost" onClick={() => { localStorage.removeItem('rr_token'); localStorage.removeItem('rr_role'); onClose() }}>Keluar</Button>
        <Button variant="primary" onClick={login}>Masuk</Button>
      </div>
    </Modal>
  )
}

export default function Layout() {
  const [open, setOpen] = useState(false)
  const [profile, setProfile] = useState(false)
  const health = useQuery({ queryKey: ['health'], queryFn: () => api('/health'), refetchInterval: 20_000, retry: 0 })
  const dash = useQuery({ queryKey: ['dashboard'], queryFn: () => api('/dashboard/metrics') })
  const ok = health.isSuccess
  return (
    <div className="flex h-full">
      {open && <div className="fixed inset-0 z-30 bg-ink/40 lg:hidden" onClick={() => setOpen(false)} />}
      <aside className={cn('fixed inset-y-0 left-0 z-40 flex w-60 flex-col border-r border-line bg-white transition-transform lg:static lg:translate-x-0', open ? 'translate-x-0' : '-translate-x-full')}>
        <div className="flex h-14 items-center justify-between border-b border-line px-5">
          <div className="flex items-center gap-2.5">
            <span className="flex h-7 w-7 items-center justify-center rounded-md bg-brand-600 text-white"><Workflow className="h-4 w-4" /></span>
            <span className="font-semibold tracking-tight">RAG-Relearn</span>
          </div>
          <button className="lg:hidden" onClick={() => setOpen(false)} aria-label="Tutup menu"><X className="h-5 w-5" /></button>
        </div>
        <nav className="flex-1 space-y-0.5 overflow-y-auto p-3">
          {NAV.map(({ to, label, icon: Icon }) => (
            <NavLink key={to} to={to} end={to === '/'} onClick={() => setOpen(false)}
              className={({ isActive }) => cn('flex items-center gap-2.5 rounded-md px-3 py-2 text-sm transition-colors', isActive ? 'bg-brand-50 font-medium text-brand-700' : 'text-ink-soft hover:bg-stone-100')}>
              <Icon className="h-4 w-4 shrink-0" />{label}
            </NavLink>
          ))}
        </nav>
        <p className="border-t border-line px-5 py-3 text-xs text-ink-mute">Retrieval Failure Analysis and Continuous RAG Improvement</p>
      </aside>

      <div className="flex min-w-0 flex-1 flex-col">
        <header className="flex h-14 shrink-0 items-center gap-3 border-b border-line bg-white px-4 sm:px-6">
          <button className="rounded-md p-1.5 hover:bg-stone-100 lg:hidden" onClick={() => setOpen(true)} aria-label="Buka menu"><Menu className="h-5 w-5" /></button>
          <span className="hidden font-medium sm:block">RAG-Relearn</span>
          <Badge className="hidden sm:inline-flex">local</Badge>
          <div className="ml-auto flex items-center gap-2 sm:gap-4">
            <span className="hidden items-center gap-1.5 text-[13px] text-ink-soft md:flex">Model <Badge tone="brand">{dash.data?.kpis.current_model ?? '-'}</Badge></span>
            <span className="flex items-center gap-1.5 text-[13px] text-ink-soft" title={ok ? 'Backend terhubung' : 'Backend tidak terjangkau'}>
              <Activity className={cn('h-4 w-4', ok ? 'text-emerald-600' : 'text-red-500')} />{ok ? 'Sistem normal' : 'Backend mati'}
            </span>
            <Button variant="ghost" size="sm" onClick={() => setProfile(true)} aria-label="Profil"><User className="h-4 w-4" /></Button>
          </div>
        </header>
        <main className="flex-1 overflow-y-auto"><div className="mx-auto max-w-[1280px] p-4 sm:p-6 lg:p-8"><Outlet /></div></main>
      </div>
      <LoginModal open={profile} onClose={() => setProfile(false)} />
    </div>
  )
}
