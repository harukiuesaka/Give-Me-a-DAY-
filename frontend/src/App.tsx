import { Routes, Route } from 'react-router-dom'
import InputPage from './pages/InputPage'
import LoadingPage from './pages/LoadingPage'
import PresentationPage from './pages/PresentationPage'
import ApprovalPage from './pages/ApprovalPage'
import StatusPage from './pages/StatusPage'

function App() {
  return (
    <div className="min-h-screen bg-gray-50">
      <header className="bg-white border-b border-gray-200 px-6 py-4">
        <h1 className="text-xl font-semibold text-gray-900">Give Me a DAY</h1>
        <p className="text-sm text-gray-500">投資戦略の検証・比較・棄却・推奨</p>
      </header>
      <main className="max-w-4xl mx-auto px-4 py-8">
        <Routes>
          <Route path="/" element={<InputPage />} />
          <Route path="/runs/:runId/loading" element={<LoadingPage />} />
          <Route path="/runs/:runId/result" element={<PresentationPage />} />
          <Route path="/runs/:runId/approve" element={<ApprovalPage />} />
          <Route path="/paper-runs/:prId" element={<StatusPage />} />
        </Routes>
      </main>
    </div>
  )
}

export default App
