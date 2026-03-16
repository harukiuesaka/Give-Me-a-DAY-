import { useState } from 'react'
import { useParams, useNavigate, useSearchParams } from 'react-router-dom'
import { api } from '../api/client'

function ApprovalPage() {
  const { runId } = useParams<{ runId: string }>()
  const [searchParams] = useSearchParams()
  const candidateId = searchParams.get('candidate') || ''
  const navigate = useNavigate()

  const [confirmed, setConfirmed] = useState(false)
  const [virtualCapital, setVirtualCapital] = useState(1000000)
  const [submitting, setSubmitting] = useState(false)
  const [error, setError] = useState<string | null>(null)

  const handleApprove = async () => {
    if (!runId || !candidateId) return
    setSubmitting(true)
    setError(null)

    try {
      const res = await api.approveRun(runId, {
        candidate_id: candidateId,
        user_confirmations: {
          risks_reviewed: true,
          stop_conditions_reviewed: true,
          paper_run_understood: true,
        },
        virtual_capital: virtualCapital,
      })
      const prId = (res as Record<string, string>).paper_run_id
      navigate(`/paper-runs/${prId}`)
    } catch (e) {
      setError(e instanceof Error ? e.message : '承認に失敗しました')
      setSubmitting(false)
    }
  }

  return (
    <div className="max-w-2xl mx-auto">
      <h2 className="text-2xl font-bold mb-6">承認確認</h2>

      <div className="bg-white border border-gray-200 rounded-lg p-6 space-y-6">
        {/* Paper Run notice */}
        <div className="bg-blue-50 border border-blue-200 rounded-lg p-4">
          <p className="text-sm text-blue-800 font-medium">
            Paper Run: 実際のお金は使いません
          </p>
          <p className="text-xs text-blue-600 mt-1">
            模擬運用（シミュレーション）として実行されます。
          </p>
        </div>

        {/* Stop conditions */}
        <div>
          <h3 className="text-sm font-medium text-gray-700 mb-2">停止条件</h3>
          <ul className="text-sm text-gray-600 space-y-1">
            <li>• 損失が -20% に達した場合、自動停止</li>
            <li>• 3ヶ月連続でベンチマークを下回った場合、自動停止</li>
            <li>• シグナルが3σ以上の異常を示した場合、一時停止</li>
            <li>• データ取得が3日連続で失敗した場合、一時停止</li>
          </ul>
        </div>

        {/* Virtual capital */}
        <div>
          <label className="block text-sm font-medium text-gray-700 mb-1">
            仮想資金
          </label>
          <input
            type="number"
            value={virtualCapital}
            onChange={e => setVirtualCapital(Number(e.target.value))}
            className="w-full border border-gray-300 rounded-lg p-3"
          />
          <p className="text-xs text-gray-400 mt-1">デフォルト: ¥1,000,000</p>
        </div>

        {/* Confirmation checkbox */}
        <label className="flex items-start gap-3">
          <input
            type="checkbox"
            checked={confirmed}
            onChange={e => setConfirmed(e.target.checked)}
            className="mt-1 rounded"
          />
          <span className="text-sm text-gray-700">
            上記のリスクと停止条件を確認しました
          </span>
        </label>

        {error && (
          <div className="bg-red-50 text-red-700 p-3 rounded-lg text-sm">
            {error}
          </div>
        )}

        {/* Approve button */}
        <button
          onClick={handleApprove}
          disabled={!confirmed || submitting}
          className="w-full bg-blue-600 text-white py-3 px-6 rounded-lg font-medium hover:bg-blue-700 disabled:opacity-50 disabled:cursor-not-allowed"
        >
          {submitting ? '処理中...' : 'この方向で模擬運用を開始 →'}
        </button>

        <button
          onClick={() => navigate(`/runs/${runId}/result`)}
          className="w-full text-center text-sm text-gray-500 underline"
        >
          やめて戻る
        </button>
      </div>
    </div>
  )
}

export default ApprovalPage
