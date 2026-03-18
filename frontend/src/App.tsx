import { useCallback, useEffect, useRef, useState } from 'react'
import { Link, Routes, Route, useLocation } from 'react-router-dom'
import { api } from './api/client'
import InputPage from './pages/InputPage'
import LoadingPage from './pages/LoadingPage'
import PresentationPage from './pages/PresentationPage'
import ApprovalPage from './pages/ApprovalPage'
import StatusPage from './pages/StatusPage'
import type { PaperRunStatus } from './types/schema'

const ACTIVE_PAPER_RUN_ID_KEY = 'give-me-a-day.active-paper-run-id'

const ALERT_STYLES: Record<PaperRunStatus['alert_summary']['alert_type'], string> = {
  none: 'border-gray-200 bg-gray-50 text-gray-700',
  report_ready: 'border-blue-200 bg-blue-50 text-blue-900',
  halted: 'border-red-200 bg-red-50 text-red-900',
  reapproval_required: 'border-amber-200 bg-amber-50 text-amber-900',
  review_required: 'border-amber-200 bg-amber-50 text-amber-900',
}

const ALERT_TITLES: Record<Exclude<PaperRunStatus['alert_summary']['alert_type'], 'none'>, string> = {
  report_ready: '月次レポートが利用可能です',
  halted: 'Paper Run は停止中です',
  reapproval_required: '再承認が必要です',
  review_required: '再評価の確認が必要です',
}

function getPaperRunIdFromPath(pathname: string) {
  const match = pathname.match(/^\/paper-runs\/([^/]+)/)
  return match ? match[1] : null
}

function AppShellAlertBanner({
  paperRunId,
  clearRememberedPaperRunId,
}: {
  paperRunId: string | null
  clearRememberedPaperRunId: () => void
}) {
  const location = useLocation()
  const statusPagePaperRunId = getPaperRunIdFromPath(location.pathname)
  const isStatusPage = Boolean(statusPagePaperRunId)
  const [status, setStatus] = useState<PaperRunStatus | null>(null)
  const isFetchingRef = useRef(false)

  useEffect(() => {
    if (!paperRunId || isStatusPage) {
      setStatus(null)
      return
    }

    let cancelled = false

    const loadStatus = async () => {
      if (isFetchingRef.current) {
        return
      }
      isFetchingRef.current = true
      try {
        const data = await api.getPaperRunStatus(paperRunId) as unknown as PaperRunStatus
        if (!cancelled) {
          setStatus(data)
        }
      } catch (error) {
        if (!cancelled && error instanceof Error && error.message === 'Paper Run not found') {
          setStatus(null)
          clearRememberedPaperRunId()
        }
      } finally {
        isFetchingRef.current = false
      }
    }

    loadStatus()
    const interval = window.setInterval(loadStatus, 60000)

    return () => {
      cancelled = true
      isFetchingRef.current = false
      window.clearInterval(interval)
    }
  }, [paperRunId, isStatusPage, clearRememberedPaperRunId])

  const alert = status?.alert_summary

  if (!paperRunId || isStatusPage || !alert || alert.alert_type === 'none') {
    return null
  }

  return (
    <div className="mx-auto max-w-4xl px-4 pt-4">
      <div className={`rounded-lg border px-4 py-3 text-sm ${ALERT_STYLES[alert.alert_type]}`}>
        <div className="flex items-start justify-between gap-3">
          <div>
            <p className="font-semibold">
              {ALERT_TITLES[alert.alert_type as Exclude<PaperRunStatus['alert_summary']['alert_type'], 'none'>]}
            </p>
            <p className="mt-1">{alert.message}</p>
          </div>
          {alert.timestamp && (
            <span className="text-xs opacity-70 whitespace-nowrap">
              {new Date(alert.timestamp).toLocaleString('ja-JP')}
            </span>
          )}
        </div>
        <div className="mt-3">
          <Link to={`/paper-runs/${paperRunId}`} className="text-xs font-medium underline underline-offset-2">
            Paper Run ステータスを開く
          </Link>
        </div>
      </div>
    </div>
  )
}

function App() {
  const location = useLocation()
  const [activePaperRunId, setActivePaperRunId] = useState<string | null>(() => {
    if (typeof window === 'undefined') return null
    const routePaperRunId = getPaperRunIdFromPath(window.location.pathname)
    if (routePaperRunId) {
      return routePaperRunId
    }
    return window.localStorage.getItem(ACTIVE_PAPER_RUN_ID_KEY)
  })

  useEffect(() => {
    const paperRunId = getPaperRunIdFromPath(location.pathname)
    if (!paperRunId) {
      return
    }

    setActivePaperRunId(paperRunId)
    window.localStorage.setItem(ACTIVE_PAPER_RUN_ID_KEY, paperRunId)
  }, [location.pathname])

  const clearRememberedPaperRunId = useCallback(() => {
    setActivePaperRunId(null)
    window.localStorage.removeItem(ACTIVE_PAPER_RUN_ID_KEY)
  }, [])

  return (
    <div className="min-h-screen bg-gray-50">
      <header className="bg-white border-b border-gray-200 px-6 py-4">
        <h1 className="text-xl font-semibold text-gray-900">Give Me a DAY</h1>
        <p className="text-sm text-gray-500">投資戦略の検証・比較・棄却・推奨</p>
      </header>
      <AppShellAlertBanner
        paperRunId={activePaperRunId}
        clearRememberedPaperRunId={clearRememberedPaperRunId}
      />
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
