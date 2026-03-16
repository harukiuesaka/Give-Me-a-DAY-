/**
 * TypeScript types matching API responses.
 * Only user-facing types — NOT the full internal schema.
 * Follows internal_schema.md §9, §10, §12, §13.
 */

// §9. CandidateCard (user-facing)
export interface CandidateCard {
  candidate_id: string
  label: 'primary' | 'alternative'
  display_name: string
  summary: string
  strategy_approach: string
  expected_return_band: {
    low_pct: number
    high_pct: number
    basis: string
    disclaimer: string
  }
  estimated_max_loss: {
    low_pct: number
    high_pct: number
    basis: string
  }
  confidence_level: 'low' | 'medium' | 'high'
  confidence_reason: string
  key_risks: string[]
  stop_conditions_headline: string
}

// §10. PresentationContext (user-facing)
export interface PresentationContext {
  run_id: string
  created_at: string
  validation_summary: string
  recommendation_expiry: string
  rejection_headline: string | null
  caveats: string[]
  candidates_evaluated: number
  candidates_rejected: number
  candidates_presented: number
}

// Run result from GET /runs/{id}/result
export interface RunResult {
  run_id: string
  candidate_cards: CandidateCard[]
  presentation_context: PresentationContext
  approval_url: string
}

// Run status from GET /runs/{id}/status
export interface RunStatus {
  run_id: string
  status: 'pending' | 'executing' | 'completed' | 'failed'
  current_step: string
  steps_completed: number
  steps_total: number
  estimated_remaining_seconds: number | null
  error: string | null
}

// Paper Run status (user-facing subset of §12)
export interface PaperRunStatus {
  status: 'running' | 'paused' | 'halted' | 're_evaluating'
  day_count: number
  current_value: number
  total_return_pct: number
  safety_status: string
  next_report: string | null
  next_re_eval: string | null
}

// §13. MonthlyReport
export interface MonthlyReport {
  report_id: string
  paper_run_id: string
  period: { start: string; end: string }
  summary: string
  numbers: {
    monthly_return_pct: number
    benchmark_return_pct: number
    cumulative_return_pct: number
    current_drawdown_pct: number
    positions_count: number
    trades_this_month: number
  }
  safety_note: string
  next: string
}
