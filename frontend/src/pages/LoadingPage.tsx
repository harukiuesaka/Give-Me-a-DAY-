import { useEffect, useState } from 'react'
import { useParams, useNavigate } from 'react-router-dom'
import { api } from '../api/client'
import type { RunStatus } from '../types/schema'

const STEPS = [
  'ゴールを分析中',
  '投資ドメインを分析中',
  'リサーチ仕様を策定中',
  '候補戦略を生成中',
  'エビデンス計画を作成中',
  '検証計画を作成中',
  'データを取得中',
  'バックテストを実行中',
  '統計検定を実行中',
  '候補を比較中',
  '推奨パッケージを作成中',
  '結果を整理中',
]

function LoadingPage() {
  const { runId } = useParams<{ runId: string }>()
  const navigate = useNavigate()
  const [status, setStatus] = useState<RunStatus | null>(null)
  const [error, setError] = useState<string | null>(null)

  useEffect(() => {
    if (!runId) return

    const poll = setInterval(async () => {
      try {
        const data = await api.getRunStatus(runId) as unknown as RunStatus
        setStatus(data)

        if (data.status === 'completed') {
          clearInterval(poll)
          navigate(`/runs/${runId}/result`)
        } else if (data.status === 'failed') {
          clearInterval(poll)
          setError(data.error || 'パイプラインが失敗しました')
        }
      } catch {
        // Polling error — will retry
      }
    }, 3000)

    return () => clearInterval(poll)
  }, [runId, navigate])

  return (
    <div className="max-w-2xl mx-auto">
      <h2 className="text-2xl font-bold mb-6">検証を実行中...</h2>

      <div className="bg-white rounded-lg border border-gray-200 p-6">
        <div className="space-y-3">
          {STEPS.map((step, i) => {
            const completed = status ? i < status.steps_completed : false
            const active = status ? i === status.steps_completed && status.status === 'executing' : false

            return (
              <div key={step} className="flex items-center gap-3">
                <span className="text-lg">
                  {completed ? '✅' : active ? '🔄' : '⬜'}
                </span>
                <span className={`text-sm ${completed ? 'text-gray-500' : active ? 'text-blue-600 font-medium' : 'text-gray-400'}`}>
                  {step}
                </span>
              </div>
            )
          })}
        </div>

        {status?.estimated_remaining_seconds != null && (
          <p className="mt-4 text-sm text-gray-500">
            残り約 {Math.ceil(status.estimated_remaining_seconds / 60)} 分
          </p>
        )}
      </div>

      {error && (
        <div className="mt-6 bg-red-50 text-red-700 p-4 rounded-lg">
          <p className="font-medium">エラーが発生しました</p>
          <p className="text-sm mt-1">{error}</p>
          <button
            onClick={() => navigate('/')}
            className="mt-3 text-sm text-red-600 underline"
          >
            もう一度やる
          </button>
        </div>
      )}
    </div>
  )
}

export default LoadingPage
