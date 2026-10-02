import { useEffect, useState } from 'react'
import { useMutation, useQuery, useQueryClient } from '@tanstack/react-query'
import { Play } from 'lucide-react'
import { CartesianGrid, Legend, Line, LineChart, Tooltip, XAxis, YAxis } from 'recharts'
import { api, num, when } from '../lib/api'
import { Badge, Button, Card, CardBody, CardHeader, Empty, Field, Input, Json, Loading, PageHeader, Select, Stat, StatusBadge, Table, Td, Th, useToast } from '../components/ui'
import { axis, C, Chart, grid, tip } from '../components/charts'

export default function TrainingCenter() {
  const toast = useToast(); const qc = useQueryClient()
  const datasets = useQuery({ queryKey: ['datasets'], queryFn: () => api('/training/datasets') })
  const jobs = useQuery({ queryKey: ['jobs'], queryFn: () => api('/training/jobs'), refetchInterval: 4000 })
  const [jobId, setJobId] = useState<number | null>(null)
  const [c, setC] = useState({ dataset_id: 0, base_model: 'linear-reranker', epochs: 30, learning_rate: 0.5, batch_size: 8, max_seq_length: 256, lora_rank: 8, lora_alpha: 16, warmup_steps: 0, mode: 'lightweight' })
  const set = (k: string, v: any) => setC((x) => ({ ...x, [k]: v }))
  useEffect(() => { if (!c.dataset_id && datasets.data?.length) set('dataset_id', datasets.data[0].id) }, [datasets.data])
  useEffect(() => { if (!jobId && jobs.data?.length) setJobId(jobs.data[0].id) }, [jobs.data])
  const job = useQuery({ queryKey: ['job', jobId], queryFn: () => api(`/training/${jobId}`), enabled: !!jobId, refetchInterval: (q) => (['queued', 'running'].includes(q.state.data?.status) ? 700 : false) })
  const start = useMutation({ mutationFn: () => api('/training/start', { body: c }), onSuccess: (r) => { toast('ok', `Job #${r.job_id} dimulai`); setJobId(r.job_id); qc.invalidateQueries({ queryKey: ['jobs'] }) }, onError: (e: any) => toast('err', e.message) })
  const j = job.data; const last = j?.history?.at(-1)
  useEffect(() => { if (j?.status === 'completed') { qc.invalidateQueries({ queryKey: ['models'] }); qc.invalidateQueries({ queryKey: ['dashboard'] }) } }, [j?.status])
  return (
    <>
      <PageHeader title="Training Center" desc="Latih reranker dari hard negative. Mode lightweight berjalan di CPU; mode HF memakai Transformers + PEFT/LoRA bila terpasang." />
      <div className="grid gap-6 lg:grid-cols-[360px_1fr]">
        <Card className="self-start"><CardHeader title="Konfigurasi" /><CardBody className="space-y-3.5">
          <Field label="Training dataset"><Select value={c.dataset_id} onChange={(e) => set('dataset_id', +e.target.value)}>{datasets.data?.map((d: any) => <option key={d.id} value={d.id}>#{d.id} {d.name} ({d.stats.n_samples})</option>)}</Select></Field>
          <Field label="Base model"><Input value={c.base_model} onChange={(e) => set('base_model', e.target.value)} /></Field>
          <Field label="Mode"><Select value={c.mode} onChange={(e) => set('mode', e.target.value)}><option value="lightweight">Lightweight / mock (CPU)</option><option value="hf">Hugging Face + PEFT LoRA</option></Select></Field>
          <div className="grid grid-cols-2 gap-3">
            <Field label="Epoch"><Input type="number" min={1} value={c.epochs} onChange={(e) => set('epochs', +e.target.value)} /></Field>
            <Field label="Learning rate"><Input type="number" step={0.01} value={c.learning_rate} onChange={(e) => set('learning_rate', +e.target.value)} /></Field>
            <Field label="Batch size"><Input type="number" min={1} value={c.batch_size} onChange={(e) => set('batch_size', +e.target.value)} /></Field>
            <Field label="Max seq. length"><Input type="number" value={c.max_seq_length} onChange={(e) => set('max_seq_length', +e.target.value)} /></Field>
            <Field label="LoRA rank"><Input type="number" value={c.lora_rank} onChange={(e) => set('lora_rank', +e.target.value)} /></Field>
            <Field label="LoRA alpha"><Input type="number" value={c.lora_alpha} onChange={(e) => set('lora_alpha', +e.target.value)} /></Field>
            <Field label="Warmup steps"><Input type="number" value={c.warmup_steps} onChange={(e) => set('warmup_steps', +e.target.value)} /></Field></div>
          <Button variant="primary" className="w-full" loading={start.isPending} disabled={!c.dataset_id} onClick={() => start.mutate()}><Play className="h-4 w-4" />Mulai training</Button></CardBody></Card>

        <div className="min-w-0 space-y-6">
          {!j ? <Card><Empty title="Belum ada job" desc="Pilih dataset lalu mulai training." /></Card> : (<>
            <div className="grid gap-4 sm:grid-cols-2 lg:grid-cols-5">
              <Stat label="Status" value={<StatusBadge value={j.status} />} /><Stat label="Epoch" value={`${j.history.length} / ${j.config.epochs}`} /><Stat label="Loss" value={num(last?.loss, 4)} tone="brand" />
              <Stat label="Validation loss" value={num(last?.val_loss, 4)} /><Stat label="GPU memory" value={`${last?.gpu_memory_mb ?? 0} MB`} hint="0 = CPU" /></div>
            <Card><CardHeader title="Progres training" desc={`Job #${j.id} - ${when(j.created_at)}${j.mode_used ? ` - mode: ${j.mode_used}` : ''}`}
              action={j.model_version ? <Badge tone="brand">Menghasilkan {j.model_version}</Badge> : undefined} />
              <CardBody>{j.history.length === 0 ? <Loading rows={3} /> : <Chart><LineChart data={j.history}><CartesianGrid {...grid} /><XAxis dataKey="epoch" {...axis} /><YAxis {...axis} /><Tooltip {...tip} /><Legend />
                <Line name="Loss" dataKey="loss" stroke={C.brand} strokeWidth={2.5} dot={false} isAnimationActive={false} /><Line name="Validation loss" dataKey="val_loss" stroke={C.ink} strokeWidth={2} dot={false} isAnimationActive={false} /></LineChart></Chart>}
                {j.error && <p className="mt-3 rounded-md bg-red-50 p-3 text-sm text-red-800">{j.error}</p>}</CardBody></Card>
            <Card><CardHeader title="Detail epoch" /><div className="max-h-64 overflow-y-auto"><Table><thead><tr><Th>Epoch</Th><Th>Loss</Th><Th>Val loss</Th><Th>Learning rate</Th><Th>GPU mem</Th><Th>Waktu</Th></tr></thead>
              <tbody>{[...j.history].reverse().map((h: any) => <tr key={h.epoch}><Td>{h.epoch}</Td><Td>{num(h.loss, 4)}</Td><Td>{num(h.val_loss, 4)}</Td><Td>{h.learning_rate}</Td><Td>{h.gpu_memory_mb} MB</Td><Td>{h.elapsed_s}s</Td></tr>)}</tbody></Table></div></Card>
            {j.weights && <Card><CardHeader title="Bobot reranker hasil training" desc="Bobot is_latest dan section_match yang naik menunjukkan reranker belajar menghindari versi lama dan section salah." /><CardBody><Json data={j.weights} /></CardBody></Card>}</>)}
          <Card><CardHeader title="Riwayat job" /><Table><thead><tr><Th>Job</Th><Th>Status</Th><Th>Dataset</Th><Th>Epoch</Th><Th>Model</Th><Th>Dibuat</Th></tr></thead>
            <tbody>{jobs.data?.map((x: any) => <tr key={x.id} className="cursor-pointer hover:bg-stone-50" onClick={() => setJobId(x.id)}><Td>#{x.id}</Td><Td><StatusBadge value={x.status} /></Td><Td>#{x.dataset_id}</Td><Td>{x.epochs_done}</Td><Td>{x.model_version ?? '-'}</Td><Td>{when(x.created_at)}</Td></tr>)}</tbody></Table></Card>
        </div>
      </div>
    </>
  )
}
