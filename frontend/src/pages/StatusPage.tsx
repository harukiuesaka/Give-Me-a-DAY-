import { useEffect, useState } from 'react'
import { useParams } from 'react-router-dom'
import { api } from '../api/client'
import type { PaperRunStatus } from '../types/schema'

const STATUS_ICONS: Record<string, string> = {
  running: '🟢',
  paused: '🟡',
  halted: '🔴',
  re_evaluating: '🔄',
}

function StatusPage() {
  const { prId } = useParams<{ prId: string }>()
  const [status, setStatus] = useState<PaperRunStatus | null>(null)
  const [error, setError] = useState<string | null>(null)

  const fetchStatus = async () => {
    if (!prId) return
    try {
      const data = await api.getPaperRunStatus(prId) as unknown as PaperRunStatus
      setStatus(data)
    } catch (e) {
      setError(e instanceof Error ? e.message : 'ステータスの取得に失敗しました')
    }
  }

  useEffect(() => {
    fetchStatus()
    const interval = setInterval(fetchStatus, 60000) // Poll every 60s
    return () => clearInterval(interval)
  }, [prId])

  const handleStop = async () => {
    if (!prId || !confirm('運用を停止しますか？')) return
    try {
      await api.stopPaperRun(prId)
      fetchStatus()
    } catch (e) {
      setError(e instanceof Error ? e.message : '停止に失敗しました')
    }
  }

  if (error) {
    return <div className="text-red-600">{error}</div>
  }

  if (!status) {
    return <div className="text-gray-500">読み込み中...</div>
  }

  return (
    <div className="max-w-2xl mx-auto">
      <h2 className="text-2xl font-bold mb-6">Paper Run ステータス</h2>

      <div className="bg-white border border-gray-200 rounded-lg p-6">
        <div className="flex items-center gap-3 mb-4">
          <span className="text-2xl">{STATUS_ICONS[status.status] || '⬜'}</span>
          <span className="text-lg font-semibold capitalize">{status.status}</span>
        </div>

        <div className="grid grid-cols-2 gap-4 text-sm">
          <div>
            <p className="text-gray-500">運用日数</p>
            <p className="font-medium">{status.day_count}日</p>
          </div>
          <div>
            <p className="text-gray-500">現在の資産</p>
            <p className="font-medium">¥{status.current_value.toLocaleString()}</p>
          </div>
          <div>
            <p className="text-gray-500">累積リターン</p>
            <p className={`font-medium ${status.total_return_pct >= 0 ? 'text-green-600' : 'text-red-600'}`}>
              {status.total_return_pct >= 0 ? '+' : ''}{status.total_return_pct.toFixed(2)}%
            </p>
          </div>
          <div>
            <p className="text-gray-500">安全状況</p>
            <p className="font-medium">
              {status.safety_status === 'all_clear' ? '🟢 正常' : '🔴 警告'}
            </p>
          </div>
        </div>

        {status.next_report && (
          <p className="text-xs text-gray-400 mt-4">
            次の月次レポート: {status.next_report}
          </p>
        )}
        {status.next_re_eval && (
          <p className="text-xs text-gray-400">
            次の再評価: {status.next_re_eval}
          </p>
        )}

        {status.status === 'running' && (
          <button
            onClick={handleStop}
            className="mt-6 w-full border border-red-300 text-red-600 py-2 px-4 rounded-lg text-sm hover:bg-red-50"
          >
            運用を停止する
          </button>
        )}
      </div>
    </div>
  )
}

export default StatusPage
