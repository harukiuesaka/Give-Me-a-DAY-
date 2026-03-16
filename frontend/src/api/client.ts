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
}
