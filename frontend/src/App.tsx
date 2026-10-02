import { Route, Routes } from 'react-router-dom'
import Layout from './components/Layout'
import Dashboard from './pages/Dashboard'
import Playground from './pages/Playground'
import RetrievalAnalysis from './pages/RetrievalAnalysis'
import { FailureCases, FailureDetail } from './pages/Failures'
import HardNegatives from './pages/HardNegatives'
import TrainingDataset from './pages/TrainingDataset'
import TrainingCenter from './pages/TrainingCenter'
import Models from './pages/Models'
import AbTesting from './pages/AbTesting'
import Evaluation from './pages/Evaluation'
import Experiments from './pages/Experiments'
import Documents from './pages/Documents'
import McpTools from './pages/McpTools'
import SystemSettings from './pages/SystemSettings'

export default function App() {
  return (
    <Routes>
      <Route element={<Layout />}>
        <Route index element={<Dashboard />} />
        <Route path="playground" element={<Playground />} />
        <Route path="retrieval" element={<RetrievalAnalysis />} />
        <Route path="failures" element={<FailureCases />} />
        <Route path="failures/:id" element={<FailureDetail />} />
        <Route path="hard-negatives" element={<HardNegatives />} />
        <Route path="dataset" element={<TrainingDataset />} />
        <Route path="training" element={<TrainingCenter />} />
        <Route path="models" element={<Models />} />
        <Route path="ab-testing" element={<AbTesting />} />
        <Route path="evaluation" element={<Evaluation />} />
        <Route path="experiments" element={<Experiments />} />
        <Route path="documents" element={<Documents />} />
        <Route path="mcp" element={<McpTools />} />
        <Route path="settings" element={<SystemSettings />} />
        <Route path="*" element={<div className="p-10 text-center text-ink-mute">Halaman tidak ditemukan</div>} />
      </Route>
    </Routes>
  )
}
