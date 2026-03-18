/**
 * API client for Give Me a DAY backend.
 * Simple fetch wrapper — no external dependencies.
 */

const BASE_URL = '/api/v1'

async function request<T>(path: string, options?: RequestInit): Promise<T> {
  const response = await fetch(`${BASE_URL}${path}`, {
    headers: {
      'Content-Type': 'application/json',
    },
    ...options,
  })

  if (!response.ok) {
    const error = await response.json().catch(() => ({ detail: response.statusText }))
    throw new Error(error.detail || `Request failed: ${response.status}`)
  }

  return response.json()
}

export interface CreateRunResponse {
  run_id: string
  status_url: string
}

export interface RunStatusResponse {
  run_id: string
  status: string
  current_step: string
  steps_completed: number
  steps_total: number
  estimated_remaining_seconds: number | null
  error: string | null
}

export interface CompanionQuestion {
  id: string
  text: string
  type: string
  options: string[]
  optional: boolean
}

export interface CompanionGoalResponse {
  needs_clarification: boolean
  questions: CompanionQuestion[]
  contradictions: string[]
  inferences: Array<{ field: string; from_text: string; inferred_value: string }>
}

export interface PreflightSubmitResponse {
  refined_request: {
    goal: string
    success_criteria?: string
    risk?: string
    time_horizon?: string
    exclusions: string[]
  }
  inference_summary: Array<{ field: string; inferred_value: string; from_text: string }>
  open_uncertainties: string[]
  kpi_anchor?: string
}

export interface StopConditionTranslation {
  id: string
  plain_language: string
  virtual_capital_amount?: number
}

export interface RiskAnnotation {
  original_risk_text: string
  annotation: string
}

export interface ComprehensionCheck {
  question: string
  options: string[]
  correct_index: number
}

export interface ApprovalContext {
  run_id: string
  candidate_id: string
  authority_disclosure: string
  kpi_alignment: {
    aligned: boolean
    anchor: string
    candidate_band: string
    note: string
  }
  stop_condition_translations: StopConditionTranslation[]
  risk_annotations: RiskAnnotation[]
  data_access_disclosure: string
  paper_run_explanation: string
  comprehension_check: ComprehensionCheck
}

export const api = {
  createRun: (data: {
    goal: string
    success_criteria?: string
    risk?: string
    time_horizon?: string
    exclusions?: string[]
  }) =>
    request<CreateRunResponse>('/runs', {
      method: 'POST',
      body: JSON.stringify(data),
    }),

  getRunStatus: (runId: string) =>
    request<RunStatusResponse>(`/runs/${runId}/status`),

  getRunResult: (runId: string) =>
    request<Record<string, unknown>>(`/runs/${runId}/result`),

  getRunExport: (runId: string) =>
    fetch(`${BASE_URL}/runs/${runId}/export`).then(r => r.text()),

  approveRun: (runId: string, data: {
    candidate_id: string
    user_confirmations: Record<string, boolean>
    virtual_capital?: number
  }) =>
    request<Record<string, unknown>>(`/runs/${runId}/approve`, {
      method: 'POST',
      body: JSON.stringify(data),
    }),

  getPaperRunStatus: (prId: string) =>
    request<Record<string, unknown>>(`/paper-runs/${prId}`),

  stopPaperRun: (prId: string) =>
    request<Record<string, unknown>>(`/paper-runs/${prId}/stop`, { method: 'POST' }),

  getMonthlyReports: (prId: string) =>
    request<Record<string, unknown>[]>(`/paper-runs/${prId}/reports`),

  reApprovePaperRun: (prId: string, data: {
    candidate_id: string
    user_confirmations: Record<string, boolean>
  }) =>
    request<Record<string, unknown>>(`/paper-runs/${prId}/re-approve`, {
      method: 'POST',
      body: JSON.stringify(data),
    }),

  preflightGoal: (data: {
    goal: string
    success_criteria?: string
    risk?: string
    time_horizon?: string
    exclusions?: string[]
  }) =>
    request<CompanionGoalResponse>('/runs/preflight', {
      method: 'POST',
      body: JSON.stringify(data),
    }),

  preflightSubmit: (data: {
    original_request: {
      goal: string
      success_criteria?: string
      risk?: string
      time_horizon?: string
      exclusions?: string[]
    }
    answers: Record<string, string>
  }) =>
    request<PreflightSubmitResponse>('/runs/preflight/submit', {
      method: 'POST',
      body: JSON.stringify(data),
    }),

  getApprovalContext: (runId: string, candidateId: string, virtualCapital?: number) => {
    const params = new URLSearchParams({ candidate_id: candidateId })
    if (virtualCapital !== undefined) params.set('virtual_capital', String(virtualCapital))
    return request<ApprovalContext>(`/runs/${runId}/approval-context?${params}`)
  },
}
