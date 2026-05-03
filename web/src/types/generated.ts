// Auto-generated TypeScript types aligned with backend Pydantic models
// Source: src/state.py
// Do not edit manually — run `python scripts/generate_ts_types.py` to regenerate.

export type RoutingFlag = 'CONTINUE' | 'RETRY' | 'ESCALATE' | 'END'

export interface TopicItem {
  topic_id: string
  topic_name: string
  status: string
}

export interface ChatMessage {
  role: string
  content: string
  topic_id: string | null
}

export interface EvaluationRecord {
  score: number
  topic_id: string
  rationale: string
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

export interface InterviewState {
  candidate_info: Record<string, unknown>
  interview_plan: TopicItem[] | null
  chat_history: ChatMessage[] | null
  current_topic_id: string | null
  current_topic_index: number
  evaluation_records: EvaluationRecord[] | null
  routing_flag: RoutingFlag
  report: Record<string, unknown> | null
  next_node: string
  human_intervened: boolean
}

export interface StartInterviewRequest {
  resume_file: string
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
  scores: EvaluationRecord[] | null
  interview_plan: TopicItem[] | null
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
  current_topic_index: number | null
  chat_history: ChatMessage[] | null
  interview_plan: TopicItem[] | null
  chat_count: number
}

export interface SSEEvent {
  type: 'status' | 'message' | 'heartbeat'
  flag: RoutingFlag | null
  role: string | null
  content: string | null
  topic_id: string | null
}
