// Auto-generated TypeScript types aligned with backend Pydantic models
// Source: src/state.py

export type RoutingFlag = 'CONTINUE' | 'RETRY' | 'ESCALATE' | 'END'

export interface TopicItem {
  topic_id: string
  topic_name: string
  status: 'pending' | 'in_progress' | 'completed'
}

export interface ChatMessage {
  role: 'system' | 'ai' | 'candidate'
  content: string
  topic_id: string | null
}

export interface EvaluationRecord {
  score: number
  topic_id: string
  rationale: string
}

export interface InterviewState {
  candidate_info: Record<string, unknown>
  interview_plan: TopicItem[]
  chat_history: ChatMessage[]
  current_topic_id: string | null
  current_topic_index: number
  evaluation_records: EvaluationRecord[]
  routing_flag: RoutingFlag
  report: InterviewReport | null
  next_node: string
  human_intervened: boolean
}

export interface InterviewReport {
  status: string
  overall_average_score: number | null
  topics: ReportTopic[]
  total_evaluations: number
  generated_at: string
}

export interface ReportTopic {
  topic_id: string
  topic_name: string
  status: string
  average_score: number | null
  scores: number[]
  rationales: string[]
}

// API request/response types
export interface StartInterviewRequest {
  resume_file: string  // base64 encoded PDF/DOCX
  job_description: string
}

export interface StartInterviewResponse {
  interview_id: string
  status: string
  ai_response: string | null
  interview_plan: TopicItem[]
  current_topic_id: string | null
}

export interface AnswerRequest {
  answer: string
}

export interface AnswerResponse {
  ai_response: string | null
  scores: EvaluationRecord[]
  interview_plan: TopicItem[]
  current_topic_id: string | null
  routing_flag: RoutingFlag | null
  status: string
}

export interface ArbitrateRequest {
  action: 'CONTINUE' | 'SKIP' | 'END'
}

export interface ArbitrateResponse {
  status: string
  action: string
}

export interface StatusResponse {
  routing_flag: RoutingFlag
  current_topic_id: string | null
  current_topic_index?: number
  chat_history?: ChatMessage[]
  interview_plan?: TopicItem[]
  chat_count: number
}

// SSE event types
export interface SSEEvent {
  type: 'status' | 'message' | 'heartbeat'
  flag?: RoutingFlag
  role?: string
  content?: string
  topic_id?: string | null
}
