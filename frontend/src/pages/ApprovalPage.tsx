import { useState, useEffect } from 'react'
import { useParams, useNavigate, useSearchParams } from 'react-router-dom'
import { api, ApprovalContext } from '../api/client'

// Comprehension check feedback text (spec §7.7)
const INCORRECT_FIRST = (stopValue: number) =>
  `That's not the right answer. Based on SC-01, if the portfolio falls 20% ` +
  `(to ¥${stopValue.toLocaleString()} or below), the system stops automatically and notifies you. ` +
  `You would then review the situation and decide whether to re-approve and continue. ` +
  `¥${Math.round(stopValue * 0.9875).toLocaleString()} is below ¥${stopValue.toLocaleString()} — so SC-01 would have already triggered. ` +
  `Please re-read the stop condition descriptions above before continuing.`

const INCORRECT_SECOND =
  `The system requires you to review the stop conditions before proceeding. ` +
  `Please re-read the SC-01 description above and try again.`

function DisclosureSection({ title, children }: { title: string; children: React.ReactNode }) {
  return (
    <div className="border border-gray-200 rounded-lg p-5">
      <p className="text-xs font-semibold text-gray-500 uppercase tracking-wide mb-3">{title}</p>
      <div className="text-sm text-gray-700 space-y-2">{children}</div>
    </div>
  )
}

function ApprovalPage() {
  const { runId } = useParams<{ runId: string }>()
  const [searchParams] = useSearchParams()
  const candidateId = searchParams.get('candidate') || ''
  const navigate = useNavigate()

  // Companion context
  const [context, setContext] = useState<ApprovalContext | null>(null)
  const [contextLoading, setContextLoading] = useState(true)

  // Comprehension check
  const [selectedAnswer, setSelectedAnswer] = useState<number | null>(null)
  const [checkAttempts, setCheckAttempts] = useState(0)
  const [checkPassed, setCheckPassed] = useState(false)
  const [checkFeedback, setCheckFeedback] = useState<string | null>(null)

  // Approval fields
  const [risksReviewed, setRisksReviewed] = useState(false)
  const [stopConditionsReviewed, setStopConditionsReviewed] = useState(false)
  const [paperRunUnderstood, setPaperRunUnderstood] = useState(false)
  const [virtualCapital, setVirtualCapital] = useState(1000000)
  const [submitting, setSubmitting] = useState(false)
  const [error, setError] = useState<string | null>(null)

  const allConfirmed = risksReviewed && stopConditionsReviewed && paperRunUnderstood && checkPassed

  // Load approval context on mount
  useEffect(() => {
    if (!runId || !candidateId) return
    setContextLoading(true)
    api.getApprovalContext(runId, candidateId, virtualCapital)
      .then(ctx => { setContext(ctx); setContextLoading(false) })
      .catch(() => { setContextLoading(false) })
      // Context failure is non-fatal — approval still works, just without companion disclosure
  }, [runId, candidateId]) // virtualCapital intentionally not in deps (context loaded once at mount)

  const handleCheckAnswer = () => {
    if (selectedAnswer === null || !context) return
    const newAttempts = checkAttempts + 1
    setCheckAttempts(newAttempts)
    if (selectedAnswer === context.comprehension_check.correct_index) {
      setCheckPassed(true)
      setCheckFeedback(null)
    } else {
      setCheckFeedback(newAttempts === 1
        ? INCORRECT_FIRST(virtualCapital * 0.80)
        : INCORRECT_SECOND)
      setSelectedAnswer(null)
    }
  }

  const handleApprove = async () => {
    if (!runId || !candidateId || !allConfirmed) return
    setSubmitting(true)
    setError(null)
    try {
      const res = await api.approveRun(runId, {
        candidate_id: candidateId,
        user_confirmations: {
          risks_reviewed: risksReviewed,
          stop_conditions_reviewed: stopConditionsReviewed,
          paper_run_understood: paperRunUnderstood,
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

  // Fallback stop condition list (used if context unavailable)
  const fallbackStopConditions = [
    '損失が -20% に達した場合、自動停止',
    '3ヶ月連続でベンチマークを下回った場合、自動停止',
    'シグナルが3σ以上の異常を示した場合、一時停止',
    'データ取得が3日連続で失敗した場合、一時停止',
  ]

  return (
    <div className="max-w-2xl mx-auto">
      <h2 className="text-2xl font-bold mb-6">承認確認</h2>

      {contextLoading && (
        <div className="text-sm text-gray-400 mb-4">開示内容を読み込み中...</div>
      )}

      <div className="space-y-5">

        {/* ── WHAT YOU ARE AUTHORIZING ── */}
        {context && (
          <DisclosureSection title="あなたが承認する内容">
            <pre className="whitespace-pre-wrap font-sans text-sm text-gray-700">
              {context.authority_disclosure}
            </pre>
          </DisclosureSection>
        )}

        {/* ── YOUR GOAL VS THIS CANDIDATE ── */}
        {context && (
          <DisclosureSection title="あなたの目標とこの候補">
            <p className={context.kpi_alignment.aligned ? 'text-gray-700' : 'text-amber-700 font-medium'}>
              {context.kpi_alignment.note}
            </p>
            {!context.kpi_alignment.aligned && (
              <p className="text-xs text-amber-600 mt-1">
                この候補のリターン範囲があなたの目標と乖離している可能性があります。
              </p>
            )}
          </DisclosureSection>
        )}

        {/* ── WHAT COULD GO WRONG ── */}
        <DisclosureSection title="リスクと停止条件">
          {context ? (
            <>
              {context.risk_annotations.length > 0 && (
                <div className="space-y-3 mb-4">
                  {context.risk_annotations.map((ra, i) => (
                    <div key={i} className="bg-gray-50 rounded p-3">
                      <p className="font-medium text-gray-800 text-xs mb-1">{ra.original_risk_text}</p>
                      <p className="text-gray-600 text-xs">{ra.annotation}</p>
                    </div>
                  ))}
                </div>
              )}
              <div className="space-y-3">
                {context.stop_condition_translations.map(sc => (
                  <div key={sc.id} className="bg-red-50 rounded p-3">
                    <pre className="whitespace-pre-wrap font-sans text-xs text-red-800">
                      {sc.plain_language}
                    </pre>
                  </div>
                ))}
              </div>
              <p className="text-xs text-gray-500 mt-3 italic">
                これら4つの停止条件はシステムによって設定されています。v1ではしきい値を変更できません。すべて自動で発動します。
              </p>
            </>
          ) : (
            <ul className="space-y-1">
              {fallbackStopConditions.map((c, i) => (
                <li key={i}>• {c}</li>
              ))}
            </ul>
          )}
        </DisclosureSection>

        {/* ── DATA ACCESS ── */}
        {context && (
          <DisclosureSection title="使用するデータ">
            <pre className="whitespace-pre-wrap font-sans text-sm text-gray-700">
              {context.data_access_disclosure}
            </pre>
          </DisclosureSection>
        )}

        {/* ── PAPER RUN EXPLANATION ── */}
        <DisclosureSection title="Paper Runとは">
          {context ? (
            <pre className="whitespace-pre-wrap font-sans text-sm text-gray-700">
              {context.paper_run_explanation}
            </pre>
          ) : (
            <>
              <p className="font-medium text-blue-800">Paper Run: 実際のお金は使いません</p>
              <p className="text-blue-600">模擬運用（シミュレーション）として実行されます。</p>
            </>
          )}
        </DisclosureSection>

        {/* ── VIRTUAL CAPITAL ── */}
        <DisclosureSection title="仮想資金">
          <input
            type="number"
            value={virtualCapital}
            onChange={e => setVirtualCapital(Number(e.target.value))}
            className="w-full border border-gray-300 rounded-lg p-3 text-sm"
          />
          <p className="text-xs text-gray-400 mt-1">デフォルト: ¥1,000,000 — 実際のお金は使用されません</p>
        </DisclosureSection>

        {/* ── COMPREHENSION CHECK ── */}
        {context && !checkPassed && (
          <DisclosureSection title="確認テスト（チェックボックスを有効にするために必要）">
            <pre className="whitespace-pre-wrap font-sans text-sm text-gray-800 mb-3">
              {context.comprehension_check.question}
            </pre>
            <div className="space-y-2">
              {context.comprehension_check.options.map((opt, i) => (
                <label key={i} className="flex items-start gap-2 cursor-pointer">
                  <input
                    type="radio"
                    name="comprehension"
                    checked={selectedAnswer === i}
                    onChange={() => setSelectedAnswer(i)}
                    className="mt-0.5"
                  />
                  <span className="text-sm text-gray-700">{opt}</span>
                </label>
              ))}
            </div>
            {checkFeedback && (
              <div className="bg-amber-50 border border-amber-200 rounded p-3 mt-3">
                <p className="text-xs text-amber-800 whitespace-pre-wrap">{checkFeedback}</p>
              </div>
            )}
            <button
              onClick={handleCheckAnswer}
              disabled={selectedAnswer === null}
              className="mt-3 px-4 py-2 text-sm bg-gray-800 text-white rounded-lg hover:bg-gray-700 disabled:opacity-40 disabled:cursor-not-allowed"
            >
              回答を確認する
            </button>
          </DisclosureSection>
        )}

        {context && checkPassed && (
          <div className="bg-green-50 border border-green-200 rounded-lg p-3 text-sm text-green-800">
            ✓ 確認テスト通過 — チェックボックスが有効になりました
          </div>
        )}

        {/* ── TRIPLE CONFIRMATION GATE ── */}
        <DisclosureSection title="承認チェック（すべて必須）">
          <div className="space-y-3">
            <label className={`flex items-start gap-3 ${!checkPassed && context ? 'opacity-40 cursor-not-allowed' : ''}`}>
              <input
                type="checkbox"
                checked={risksReviewed}
                onChange={e => setRisksReviewed(e.target.checked)}
                disabled={!checkPassed && !!context}
                className="mt-1 rounded"
              />
              <span className="text-sm text-gray-700">この戦略のリスクを確認し、理解しました</span>
            </label>
            <label className={`flex items-start gap-3 ${!checkPassed && context ? 'opacity-40 cursor-not-allowed' : ''}`}>
              <input
                type="checkbox"
                checked={stopConditionsReviewed}
                onChange={e => setStopConditionsReviewed(e.target.checked)}
                disabled={!checkPassed && !!context}
                className="mt-1 rounded"
              />
              <span className="text-sm text-gray-700">停止条件を確認し、自動停止に同意します</span>
            </label>
            <label className={`flex items-start gap-3 ${!checkPassed && context ? 'opacity-40 cursor-not-allowed' : ''}`}>
              <input
                type="checkbox"
                checked={paperRunUnderstood}
                onChange={e => setPaperRunUnderstood(e.target.checked)}
                disabled={!checkPassed && !!context}
                className="mt-1 rounded"
              />
              <span className="text-sm text-gray-700">
                これはPaper Run（模擬運用）であり、実際のお金は使われないことを理解しました
              </span>
            </label>
          </div>
        </DisclosureSection>

        {error && (
          <div className="bg-red-50 text-red-700 p-3 rounded-lg text-sm">{error}</div>
        )}

        <button
          onClick={handleApprove}
          disabled={!allConfirmed || submitting}
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
