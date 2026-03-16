import { useState } from 'react'
import { useNavigate } from 'react-router-dom'
import { api } from '../api/client'

const RISK_OPTIONS = [
  { value: 'very_low', label: 'とても低い' },
  { value: 'low', label: '低い' },
  { value: 'medium', label: '中程度' },
  { value: 'high', label: '高い' },
]

const HORIZON_OPTIONS = [
  { value: 'fast', label: '最速' },
  { value: 'one_day', label: '1日' },
  { value: 'one_week', label: '1週間' },
  { value: 'one_month', label: '1ヶ月' },
  { value: 'quality_over_speed', label: '品質優先' },
]

const EXCLUSION_OPTIONS = [
  '特定セクターの除外',
  'レバレッジの使用禁止',
  '空売りの禁止',
  'デリバティブの使用禁止',
]

function InputPage() {
  const navigate = useNavigate()
  const [goal, setGoal] = useState('')
  const [successCriteria, setSuccessCriteria] = useState('')
  const [risk, setRisk] = useState('medium')
  const [timeHorizon, setTimeHorizon] = useState('one_week')
  const [exclusions, setExclusions] = useState<string[]>([])
  const [error, setError] = useState<string | null>(null)
  const [submitting, setSubmitting] = useState(false)

  const handleExclusionToggle = (item: string) => {
    setExclusions(prev =>
      prev.includes(item) ? prev.filter(e => e !== item) : [...prev, item]
    )
  }

  const handleSubmit = async () => {
    if (goal.length < 10) {
      setError('投資目標を10文字以上で入力してください')
      return
    }
    setError(null)
    setSubmitting(true)

    try {
      const res = await api.createRun({
        goal,
        success_criteria: successCriteria || undefined,
        risk,
        time_horizon: timeHorizon,
        exclusions,
      })
      navigate(`/runs/${res.run_id}/loading`)
    } catch (e) {
      setError(e instanceof Error ? e.message : '送信に失敗しました')
      setSubmitting(false)
    }
  }

  return (
    <div className="max-w-2xl mx-auto">
      <h2 className="text-2xl font-bold mb-2">投資戦略を検証する</h2>
      <p className="text-gray-600 mb-6">
        投資の目標を入力してください。システムが候補を生成・検証・比較し、生き残った方向を提示します。
      </p>

      <div className="space-y-6">
        {/* Goal textarea */}
        <div>
          <label className="block text-sm font-medium text-gray-700 mb-1">
            投資目標 <span className="text-red-500">*</span>
          </label>
          <textarea
            className="w-full border border-gray-300 rounded-lg p-3 min-h-[120px] focus:ring-2 focus:ring-blue-500 focus:border-blue-500"
            placeholder="例: 日本株で12ヶ月モメンタム戦略を検証したい"
            value={goal}
            onChange={e => setGoal(e.target.value)}
          />
        </div>

        {/* Success criteria */}
        <div>
          <label className="block text-sm font-medium text-gray-700 mb-1">
            成功基準（任意）
          </label>
          <input
            type="text"
            className="w-full border border-gray-300 rounded-lg p-3 focus:ring-2 focus:ring-blue-500 focus:border-blue-500"
            placeholder="例: 年率10%以上のリターン"
            value={successCriteria}
            onChange={e => setSuccessCriteria(e.target.value)}
          />
        </div>

        {/* Risk tolerance */}
        <div>
          <label className="block text-sm font-medium text-gray-700 mb-1">
            リスク許容度
          </label>
          <select
            className="w-full border border-gray-300 rounded-lg p-3"
            value={risk}
            onChange={e => setRisk(e.target.value)}
          >
            {RISK_OPTIONS.map(o => (
              <option key={o.value} value={o.value}>{o.label}</option>
            ))}
          </select>
        </div>

        {/* Time horizon */}
        <div>
          <label className="block text-sm font-medium text-gray-700 mb-1">
            検証期間
          </label>
          <select
            className="w-full border border-gray-300 rounded-lg p-3"
            value={timeHorizon}
            onChange={e => setTimeHorizon(e.target.value)}
          >
            {HORIZON_OPTIONS.map(o => (
              <option key={o.value} value={o.value}>{o.label}</option>
            ))}
          </select>
        </div>

        {/* Exclusions */}
        <div>
          <label className="block text-sm font-medium text-gray-700 mb-1">
            除外条件
          </label>
          <div className="space-y-2">
            {EXCLUSION_OPTIONS.map(item => (
              <label key={item} className="flex items-center gap-2">
                <input
                  type="checkbox"
                  checked={exclusions.includes(item)}
                  onChange={() => handleExclusionToggle(item)}
                  className="rounded"
                />
                <span className="text-sm">{item}</span>
              </label>
            ))}
          </div>
        </div>

        {/* Error */}
        {error && (
          <div className="bg-red-50 text-red-700 p-3 rounded-lg text-sm">
            {error}
          </div>
        )}

        {/* Submit */}
        <button
          onClick={handleSubmit}
          disabled={submitting || goal.length < 10}
          className="w-full bg-blue-600 text-white py-3 px-6 rounded-lg font-medium hover:bg-blue-700 disabled:opacity-50 disabled:cursor-not-allowed"
        >
          {submitting ? '送信中...' : '検証する →'}
        </button>
      </div>
    </div>
  )
}

export default InputPage
