import { useEffect, useState } from 'react'
import { useParams, useNavigate } from 'react-router-dom'
import { api } from '../api/client'
import type { RunResult, CandidateCard } from '../types/schema'

function CandidateCardView({ card }: { card: CandidateCard }) {
  const labelText = card.label === 'primary' ? '推奨' : '代替案'
  const labelColor = card.label === 'primary' ? 'bg-blue-100 text-blue-800' : 'bg-gray-100 text-gray-800'

  return (
    <div className="bg-white border border-gray-200 rounded-lg p-6">
      <div className="flex items-center gap-2 mb-3">
        <span className={`text-xs px-2 py-1 rounded-full font-medium ${labelColor}`}>
          {labelText}
        </span>
        <span className={`text-xs px-2 py-1 rounded-full ${
          card.confidence_level === 'high' ? 'bg-green-100 text-green-800' :
          card.confidence_level === 'medium' ? 'bg-yellow-100 text-yellow-800' :
          'bg-red-100 text-red-800'
        }`}>
          信頼度: {card.confidence_level}
        </span>
      </div>

      <h3 className="text-lg font-semibold mb-2">{card.display_name}</h3>
      <p className="text-sm text-gray-600 mb-4">{card.summary}</p>

      <div className="grid grid-cols-2 gap-4 mb-4 text-sm">
        <div>
          <p className="text-gray-500">期待リターン</p>
          <p className="font-medium">{card.expected_return_band.low_pct}% 〜 {card.expected_return_band.high_pct}%</p>
          <p className="text-xs text-gray-400">{card.expected_return_band.disclaimer}</p>
        </div>
        <div>
          <p className="text-gray-500">推定最大損失</p>
          <p className="font-medium">{card.estimated_max_loss.low_pct}% 〜 {card.estimated_max_loss.high_pct}%</p>
        </div>
      </div>

      <div className="mb-4">
        <p className="text-sm text-gray-500 mb-1">主なリスク</p>
        <ul className="text-sm space-y-1">
          {card.key_risks.map((risk, i) => (
            <li key={i} className="text-gray-700">• {risk}</li>
          ))}
        </ul>
      </div>

      <p className="text-xs text-gray-400">{card.stop_conditions_headline}</p>
    </div>
  )
}

function PresentationPage() {
  const { runId } = useParams<{ runId: string }>()
  const navigate = useNavigate()
  const [result, setResult] = useState<RunResult | null>(null)
  const [error, setError] = useState<string | null>(null)

  useEffect(() => {
    if (!runId) return
    api.getRunResult(runId)
      .then(data => setResult(data as unknown as RunResult))
      .catch(e => setError(e instanceof Error ? e.message : 'Failed to load'))
  }, [runId])

  if (error) {
    return <div className="text-red-600">{error}</div>
  }

  if (!result) {
    return <div className="text-gray-500">読み込み中...</div>
  }

  const { candidate_cards: cards, presentation_context: ctx } = result

  return (
    <div className="max-w-3xl mx-auto">
      <h2 className="text-2xl font-bold mb-2">検証結果</h2>
      <p className="text-sm text-gray-600 mb-6">{ctx.validation_summary}</p>

      {cards.length === 0 ? (
        <div className="bg-yellow-50 border border-yellow-200 rounded-lg p-6">
          <p className="font-medium text-yellow-800">
            すべての候補が棄却されました
          </p>
          {ctx.rejection_headline && (
            <p className="text-sm text-yellow-700 mt-2">{ctx.rejection_headline}</p>
          )}
          <button
            onClick={() => navigate('/')}
            className="mt-4 text-sm text-blue-600 underline"
          >
            別のアイデアで検証する →
          </button>
        </div>
      ) : (
        <div className="grid grid-cols-1 md:grid-cols-2 gap-6 mb-6">
          {cards.map(card => (
            <div key={card.candidate_id}>
              <CandidateCardView card={card} />
              <button
                onClick={() => navigate(`/runs/${runId}/approve?candidate=${card.candidate_id}`)}
                className="w-full mt-3 bg-blue-600 text-white py-2 px-4 rounded-lg text-sm font-medium hover:bg-blue-700"
              >
                この方向で進める →
              </button>
            </div>
          ))}
        </div>
      )}

      {ctx.caveats.length > 0 && (
        <div className="mt-4 text-xs text-gray-500">
          <p className="font-medium mb-1">注意事項:</p>
          <ul>
            {ctx.caveats.map((c, i) => <li key={i}>• {c}</li>)}
          </ul>
        </div>
      )}

      <p className="text-xs text-gray-400 mt-4">
        推奨有効期限: {ctx.recommendation_expiry}
      </p>
    </div>
  )
}

export default PresentationPage
