import { useEffect, useState } from 'react'
import { useParams } from 'react-router-dom'
import { api } from '../api/client'
import type { PaperRunStatus } from '../types/schema'

const ALERT_STYLES: Record<PaperRunStatus['alert_summary']['alert_type'], string> = {
  none: 'border-gray-200 bg-gray-50 text-gray-700',
  report_ready: 'border-blue-200 bg-blue-50 text-blue-900',
  halted: 'border-red-200 bg-red-50 text-red-900',
  reapproval_required: 'border-amber-200 bg-amber-50 text-amber-900',
  review_required: 'border-amber-200 bg-amber-50 text-amber-900',
}

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
  const [reApproveSubmitting, setReApproveSubmitting] = useState(false)
  const [risksReviewed, setRisksReviewed] = useState(false)
  const [stopConditionsReviewed, setStopConditionsReviewed] = useState(false)
  const [paperRunUnderstood, setPaperRunUnderstood] = useState(false)

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

  const handleReApprove = async () => {
    if (!prId || !status) return
    setReApproveSubmitting(true)
    setError(null)
    try {
      await api.reApprovePaperRun(prId, {
        candidate_id: status.pending_candidate_id ?? status.candidate_id,
        user_confirmations: {
          risks_reviewed: risksReviewed,
          stop_conditions_reviewed: stopConditionsReviewed,
          paper_run_understood: paperRunUnderstood,
        },
      })
      setRisksReviewed(false)
      setStopConditionsReviewed(false)
      setPaperRunUnderstood(false)
      await fetchStatus()
    } catch (e) {
      setError(e instanceof Error ? e.message : '再承認に失敗しました')
    } finally {
      setReApproveSubmitting(false)
    }
  }

  const reApprovalRequired = status && (
    status.status === 'halted' ||
    status.status === 'paused' ||
    (status.status === 're_evaluating' && Boolean(status.pending_candidate_id))
  )
  const allConfirmed = risksReviewed && stopConditionsReviewed && paperRunUnderstood
  const changeCandidateReview = status?.status === 're_evaluating' && Boolean(status.pending_candidate_id)
  const approvalTargetCandidate = status?.pending_candidate_id ?? status?.candidate_id

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

        {status.alert_summary.alert_type !== 'none' && (
          <div className={`mb-4 rounded-lg border px-4 py-3 text-sm ${ALERT_STYLES[status.alert_summary.alert_type]}`}>
            <p className="font-semibold">
              {status.alert_summary.alert_type === 'report_ready' && '月次レポートが利用可能です'}
              {status.alert_summary.alert_type === 'halted' && 'Paper Run は停止中です'}
              {status.alert_summary.alert_type === 'reapproval_required' && '再承認が必要です'}
              {status.alert_summary.alert_type === 'review_required' && '再評価の確認が必要です'}
            </p>
            <p className="mt-1">{status.alert_summary.message}</p>
            {status.alert_summary.timestamp && (
              <p className="mt-1 text-xs opacity-70">
                {new Date(status.alert_summary.timestamp).toLocaleString('ja-JP')}
              </p>
            )}
          </div>
        )}

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

        {status.events && status.events.length > 0 && (
          <div className="mt-4 border-t border-gray-100 pt-4">
            <p className="text-xs font-medium text-gray-700 mb-2">最近のライフサイクルイベント</p>
            <div className="space-y-2">
              {status.events.slice(0, 3).map(event => (
                <div key={event.event_id} className="rounded-md bg-gray-50 px-3 py-2 text-xs text-gray-600">
                  <div className="flex items-center justify-between gap-2">
                    <span className="font-medium text-gray-800">{event.summary}</span>
                    <span className="text-gray-400">
                      {new Date(event.timestamp).toLocaleString('ja-JP')}
                    </span>
                  </div>
                </div>
              ))}
            </div>
          </div>
        )}

        {status.status === 'running' && (
          <button
            onClick={handleStop}
            className="mt-6 w-full border border-red-300 text-red-600 py-2 px-4 rounded-lg text-sm hover:bg-red-50"
          >
            運用を停止する
          </button>
        )}

        {reApprovalRequired && (
          <div className="mt-6 border-t border-gray-100 pt-6">
            <p className="text-sm font-medium text-gray-800 mb-2">再承認して運用を再開</p>
            <p className="text-xs text-gray-500 mb-4">
              {changeCandidateReview
                ? `四半期再評価の結果、候補 ${approvalTargetCandidate} への切り替えが提案されています。適用には明示的な再承認が必要です。`
                : '停止または一時停止後の再開には、同じ候補に対して明示的な再承認が必要です。'}
            </p>
            {changeCandidateReview && status?.re_evaluation_note && (
              <p className="text-xs text-gray-500 mb-4">{status.re_evaluation_note}</p>
            )}
            <div className="space-y-3 text-sm">
              <label className="flex items-start gap-2">
                <input
                  type="checkbox"
                  checked={risksReviewed}
                  onChange={e => setRisksReviewed(e.target.checked)}
                  className="mt-1 rounded"
                />
                <span>この候補のリスクを再確認しました</span>
              </label>
              <label className="flex items-start gap-2">
                <input
                  type="checkbox"
                  checked={stopConditionsReviewed}
                  onChange={e => setStopConditionsReviewed(e.target.checked)}
                  className="mt-1 rounded"
                />
                <span>停止条件を再確認しました</span>
              </label>
              <label className="flex items-start gap-2">
                <input
                  type="checkbox"
                  checked={paperRunUnderstood}
                  onChange={e => setPaperRunUnderstood(e.target.checked)}
                  className="mt-1 rounded"
                />
                <span>Paper Run が模擬運用であり、実際のお金を使わないことを再確認しました</span>
              </label>
            </div>
            <button
              onClick={handleReApprove}
              disabled={!allConfirmed || reApproveSubmitting}
              className="mt-4 w-full bg-blue-600 text-white py-2 px-4 rounded-lg text-sm font-medium hover:bg-blue-700 disabled:opacity-50 disabled:cursor-not-allowed"
            >
              {reApproveSubmitting
                ? '再承認中...'
                : changeCandidateReview
                  ? '再承認して候補を切り替える'
                  : '再承認して再開する'}
            </button>
          </div>
        )}
      </div>
    </div>
  )
}

export default StatusPage
