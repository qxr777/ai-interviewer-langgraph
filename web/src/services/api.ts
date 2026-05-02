import type {
  StartInterviewRequest,
  StartInterviewResponse,
  AnswerRequest,
  AnswerResponse,
  ArbitrateRequest,
  ArbitrateResponse,
  StatusResponse,
} from '../types/generated'

const API_BASE = import.meta.env.VITE_API_URL || ''

async function request<T>(url: string, options?: RequestInit): Promise<T> {
  const res = await fetch(`${API_BASE}${url}`, {
    headers: { 'Content-Type': 'application/json', ...options?.headers },
    ...options,
  })
  if (!res.ok) {
    throw new Error(`API error: ${res.status} ${res.statusText}`)
  }
  return res.json() as Promise<T>
}

export const api = {
  startInterview: (data: StartInterviewRequest) =>
    request<StartInterviewResponse>('/interview/start', {
      method: 'POST',
      body: JSON.stringify(data),
    }),

  submitAnswer: (interviewId: string, data: AnswerRequest) =>
    request<AnswerResponse>(`/interview/${interviewId}/answer`, {
      method: 'POST',
      body: JSON.stringify(data),
    }),

  arbitrate: (interviewId: string, data: ArbitrateRequest) =>
    request<ArbitrateResponse>(`/interview/${interviewId}/arbitrate`, {
      method: 'POST',
      body: JSON.stringify(data),
    }),

  getStatus: (interviewId: string) =>
    request<StatusResponse>(`/interview/${interviewId}/status`),

  getReport: (interviewId: string) =>
    request(`/interview/${interviewId}/report`),
}
