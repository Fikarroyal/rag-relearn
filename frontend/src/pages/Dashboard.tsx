import { Link } from 'react-router-dom'
import { useQuery } from '@tanstack/react-query'
import { Bar, BarChart, CartesianGrid, Legend, Line, LineChart, Tooltip, XAxis, YAxis } from 'recharts'
import { ArrowRight } from 'lucide-react'
import { api, label, ms, num, pct, when } from '../lib/api'
import { Badge, Card, CardBody, CardHeader, ErrorState, Loading, PageHeader, Skeleton, Stat, StatusBadge, Empty } from '../components/ui'
import { axis, C, Chart, grid, tip } from '../components/charts'

function LoopStrip({ k }: { k: any }) {
  const ds = useQuery({ queryKey: ['datasets'], queryFn: () => api('/training/datasets') })
  const models = useQuery({ queryKey: ['models'], queryFn: () => api('/models') })
  const ab = useQuery({ queryKey: ['abs'], queryFn: () => api('/ab-test') })
  const steps = [
    { to: '/failures', name: 'Failure cases', v: k.total_failures },
    { to: '/hard-negatives', name: 'Hard negatives', v: k.hard_negatives },
    { to: '/dataset', name: 'Dataset', v: ds.data?.length },
    { to: '/models', name: 'Model versions', v: models.data?.length },
    { to: '/ab-testing', name: 'A/B tests', v: ab.data?.length },
    { to: '/models', name: 'Production', v: k.current_model },
  ]
  return (
    <Card className="mb-6">
      <CardHeader title="Siklus closed-loop" desc="Dari kegagalan retrieval sampai model produksi" />
      <div className="grid grid-cols-2 divide-x divide-y divide-line sm:grid-cols-3 lg:grid-cols-6 lg:divide-y-0">
        {steps.map((s, i) => (
          <Link key={s.name} to={s.to} className="group flex items-center justify-between gap-2 px-5 py-4 hover:bg-stone-50">
            <div><p className="text-xl font-semibold">{s.v ?? '-'}</p><p className="text-[13px] text-ink-mute">{s.name}</p></div>
            {i < steps.length - 1 && <ArrowRight className="hidden h-4 w-4 text-stone-300 group-hover:text-brand-600 lg:block" />}
          </Link>
        ))}
      </div>
    </Card>
  )
}

export default function Dashboard() {
  const { data, isLoading, error, refetch } = useQuery({ queryKey: ['dashboard'], queryFn: () => api('/dashboard/metrics') })
  if (error) return <Card><ErrorState error={error} onRetry={refetch} /></Card>
  if (isLoading || !data) return (<><PageHeader title="Dashboard" /><div className="grid gap-4 sm:grid-cols-2 lg:grid-cols-5">{Array.from({ length: 10 }).map((_, i) => <Skeleton key={i} className="h-24" />)}</div></>)
  const k = data.kpis
  const trend = data.success_trend.map((d: any) => ({ ...d, date: d.date.slice(5), success: +(d.success_rate * 100).toFixed(1), failure: +(d.failure_rate * 100).toFixed(1) }))
  const scores = ['faithfulness', 'answer_relevance', 'context_precision', 'citation_accuracy']
  return (
    <>
      <PageHeader title="Dashboard" desc="Kesehatan retrieval dan generation RAG, diagnosis kegagalan, dan status model produksi." />
      <LoopStrip k={k} />
      <div className="mb-6 grid gap-4 sm:grid-cols-2 lg:grid-cols-5">
        <Stat label="Total queries" value={k.total_queries} />
        <Stat label="Successful retrieval" value={pct(k.successful_retrieval)} hint="Dokumen benar di rank 1" tone="brand" />
        <Stat label="Retrieval failure rate" value={pct(k.retrieval_failure_rate)} tone="red" />
        <Stat label="Answer grounding" value={num(k.answer_grounding, 2)} hint="Faithfulness rata-rata" />
        <Stat label="Answer relevance" value={num(k.answer_relevance, 2)} />
        <Stat label="Avg retrieval latency" value={ms(k.avg_retrieval_ms)} />
        <Stat label="Avg generation latency" value={ms(k.avg_generation_ms)} />
        <Stat label="Total failure cases" value={k.total_failures} />
        <Stat label="Hard negatives" value={k.hard_negatives} />
        <Stat label="Current model" value={k.current_model ?? '-'} tone="brand" />
      </div>

      <div className="mb-6 grid gap-6 lg:grid-cols-2">
        <Card><CardHeader title="Retrieval success rate" desc="Persentase query dengan dokumen benar di rank 1, per hari" />
          <CardBody><Chart><LineChart data={trend}><CartesianGrid {...grid} /><XAxis dataKey="date" {...axis} /><YAxis {...axis} unit="%" domain={[0, 100]} /><Tooltip {...tip} /><Legend />
            <Line name="Success" dataKey="success" stroke={C.brand} strokeWidth={2.5} dot={false} /><Line name="Failure" dataKey="failure" stroke={C.ink} strokeWidth={2} dot={false} /></LineChart></Chart></CardBody></Card>
        <Card><CardHeader title="Failure type distribution" />
          <CardBody>{data.failure_distribution.length === 0 ? <Empty title="Belum ada kegagalan" /> :
            <Chart><BarChart layout="vertical" data={data.failure_distribution.map((d: any) => ({ ...d, type: label(d.type) }))} margin={{ left: 40 }}><CartesianGrid {...grid} horizontal={false} vertical />
              <XAxis type="number" {...axis} /><YAxis type="category" dataKey="type" width={170} {...axis} /><Tooltip {...tip} /><Bar dataKey="count" fill={C.brand} radius={[0, 4, 4, 0]} /></BarChart></Chart>}</CardBody></Card>
        <Card><CardHeader title="Retrieval score distribution" desc="Similarity dokumen rank 1" />
          <CardBody><Chart><BarChart data={data.score_distribution}><CartesianGrid {...grid} /><XAxis dataKey="bucket" {...axis} /><YAxis {...axis} /><Tooltip {...tip} /><Bar dataKey="count" fill={C.ink} radius={[4, 4, 0, 0]} /></BarChart></Chart></CardBody></Card>
        <Card><CardHeader title="Latency trend" desc="Rata-rata per hari (ms)" />
          <CardBody><Chart><LineChart data={trend}><CartesianGrid {...grid} /><XAxis dataKey="date" {...axis} /><YAxis {...axis} /><Tooltip {...tip} /><Legend />
            <Line name="Retrieval + rerank" dataKey="retrieval_ms" stroke={C.brand} strokeWidth={2.5} dot={false} /><Line name="Generation" dataKey="generation_ms" stroke={C.ink} strokeWidth={2} dot={false} /></LineChart></Chart></CardBody></Card>
        <Card><CardHeader title="RAG evaluation score" desc="Per versi model" />
          <CardBody><Chart><BarChart data={data.eval_scores}><CartesianGrid {...grid} /><XAxis dataKey="model_version" {...axis} /><YAxis {...axis} domain={[0, 1]} /><Tooltip {...tip} /><Legend />
            {scores.map((s, i) => <Bar key={s} dataKey={s} name={label(s)} fill={[C.brand, C.ink, C.amber, C.stone][i]} radius={[3, 3, 0, 0]} />)}</BarChart></Chart></CardBody></Card>
        <Card><CardHeader title="Model performance comparison" desc="Evaluasi pada dataset yang sama" />
          <CardBody><Chart><BarChart data={data.model_comparison}><CartesianGrid {...grid} /><XAxis dataKey="version" {...axis} /><YAxis {...axis} domain={[0, 1]} /><Tooltip {...tip} /><Legend />
            <Bar dataKey="recall@1" name="Recall@1" fill={C.brand} radius={[3, 3, 0, 0]} /><Bar dataKey="mrr" name="MRR" fill={C.ink} radius={[3, 3, 0, 0]} /><Bar dataKey="ndcg" name="NDCG" fill={C.amber} radius={[3, 3, 0, 0]} /></BarChart></Chart></CardBody></Card>
      </div>

      <div className="grid gap-6 lg:grid-cols-3">
        <Card className="lg:col-span-2"><CardHeader title="Recent failure cases" action={<Link to="/failures" className="text-[13px] font-medium text-brand-700 hover:underline">Lihat semua</Link>} />
          {data.recent_failures.length === 0 ? <Empty title="Tidak ada failure case" /> : (
            <ul className="divide-y divide-line">{data.recent_failures.map((f: any) => (
              <li key={f.id}><Link to={`/failures/${f.id}`} className="flex items-center justify-between gap-3 px-5 py-3 hover:bg-stone-50">
                <div className="min-w-0"><p className="truncate text-sm font-medium">{f.query}</p><p className="text-xs text-ink-mute">{when(f.created_at)} - model {f.model_version}</p></div>
                <div className="flex shrink-0 gap-2"><Badge tone="brand">{label(f.failure_type)}</Badge><StatusBadge value={f.severity} /></div></Link></li>))}</ul>)}
        </Card>
        <div className="space-y-6">
          <Card><CardHeader title="Current production model" />
            <CardBody className="space-y-2 text-sm">{data.production_model ? (<>
              <div className="flex justify-between"><span className="text-ink-mute">Versi</span><Badge tone="brand">{data.production_model.version}</Badge></div>
              <div className="flex justify-between"><span className="text-ink-mute">Reranker</span><span>{data.production_model.reranker}</span></div>
              <div className="flex justify-between"><span className="text-ink-mute">MRR</span><span>{num(data.production_model.metrics?.mrr)}</span></div>
              <div className="flex justify-between"><span className="text-ink-mute">Recall@1</span><span>{num(data.production_model.metrics?.['recall@1'])}</span></div></>) : <p className="text-ink-mute">Belum ada model production.</p>}</CardBody></Card>
          <Card><CardHeader title="Training pipeline status" />
            <CardBody className="text-sm">{data.training_status ? (<div className="space-y-2">
              <div className="flex justify-between"><span className="text-ink-mute">Job terakhir</span><span>#{data.training_status.id}</span></div>
              <div className="flex justify-between"><span className="text-ink-mute">Status</span><StatusBadge value={data.training_status.status} /></div>
              <div className="flex justify-between"><span className="text-ink-mute">Epoch</span><span>{data.training_status.epochs_done} / {data.training_status.epochs_total}</span></div>
              <div className="flex justify-between"><span className="text-ink-mute">Hasil model</span><span>{data.training_status.model_version ?? '-'}</span></div></div>) : <p className="text-ink-mute">Belum ada job training.</p>}</CardBody></Card>
        </div>
      </div>

      <Card className="mt-6"><CardHeader title="Recent evaluation" />
        {isLoading ? <Loading /> : (
          <ul className="divide-y divide-line">{data.recent_evaluations.map((e: any) => (
            <li key={e.id} className="flex flex-wrap items-center justify-between gap-2 px-5 py-3 text-sm">
              <span className="min-w-0 flex-1 truncate">{e.query}</span>
              <span className="flex items-center gap-2"><Badge>{e.model_version}</Badge>{e.failure_type ? <Badge tone="red">{label(e.failure_type)}</Badge> : <Badge tone="green">Benar</Badge>}<span className="w-20 text-right text-ink-mute">{ms(e.latency_ms)}</span></span></li>))}</ul>)}
      </Card>
    </>
  )
}
