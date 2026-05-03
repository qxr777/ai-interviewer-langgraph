import { create } from 'zustand'
import type {
  ChatMessage,
  TopicItem,
  EvaluationRecord,
  RoutingFlag,
  InterviewReport,
} from '../types/generated'
import { api } from '../services/api'
import { sseClient } from '../services/sse'

interface InterviewState {
  interviewId: string | null
  candidateInfo: Record<string, unknown>
  jobDescription: string
  chatHistory: ChatMessage[]
  interviewPlan: TopicItem[]
  currentTopicId: string | null
  currentTopicIndex: number
  evaluationRecords: EvaluationRecord[]
  routingFlag: RoutingFlag | null
  report: InterviewReport | null
  loading: boolean
  error: string | null
  // Maps message index to scores for that answer
  scoresByIndex: Record<number, EvaluationRecord[]>

  setInterviewId: (id: string) => void
  setJobDescription: (jd: string) => void
  startInterview: (resumeBase64: string, jd: string) => Promise<string>
  submitAnswer: (answer: string) => Promise<void>
  arbitrate: (action: 'CONTINUE' | 'SKIP' | 'END') => Promise<void>
  refreshStatus: (overrideId?: string) => Promise<void>
  refreshReport: (overrideId?: string) => Promise<void>
  addMessage: (msg: ChatMessage) => void
  clearError: () => void
}

export const useInterviewStore = create<InterviewState>((set, get) => ({
  interviewId: null,
  candidateInfo: {},
  jobDescription: '',
  chatHistory: [],
  interviewPlan: [],
  currentTopicId: null,
  currentTopicIndex: 0,
  evaluationRecords: [],
  routingFlag: null,
  report: null,
  loading: false,
  error: null,
  scoresByIndex: {},

  setInterviewId: (id) => set({ interviewId: id }),
  setJobDescription: (jd) => set({ jobDescription: jd }),

  startInterview: async (resumeBase64, jd) => {
    set({ loading: true, jobDescription: jd, error: null })
    try {
      const res = await api.startInterview({ resume_file: resumeBase64, job_description: jd })
      const chatHistory: ChatMessage[] = res.ai_response
        ? [{ role: 'ai' as const, content: res.ai_response, topic_id: res.current_topic_id ?? null }]
        : []
      set({
        interviewId: res.interview_id,
        chatHistory,
        interviewPlan: res.interview_plan || [],
        currentTopicId: res.current_topic_id ?? null,
        currentTopicIndex: 0,
        routingFlag: 'CONTINUE',
        loading: false,
        error: null,
        scoresByIndex: {},
      })
      // 连接 SSE 用于实时推送
      sseClient.connect(res.interview_id)
      return res.interview_id
    } catch (e: unknown) {
      const msg = e instanceof Error ? e.message : '启动失败'
      set({ loading: false, error: msg })
      throw e
    }
  },

  submitAnswer: async (answer: string) => {
    const { interviewId } = get()
    if (!interviewId) {
      const msg = '面试未启动，请先启动面试'
      set({ error: msg })
      return
    }
    // 立即显示用户回答（乐观更新）
    const msgIdx = get().chatHistory.length
    set((s) => ({
      chatHistory: [
        ...s.chatHistory,
        { role: 'candidate' as const, content: answer, topic_id: null },
      ],
      loading: true,
      error: null,
    }))
    try {
      const res = await api.submitAnswer(interviewId, { answer })
      if (res.ai_response) {
        // SSE 可能已推送 AI 消息，去重：检查最后一条是否相同
        const exists = get().chatHistory.some(
          (m) => m.role === 'ai' && m.content === res.ai_response,
        )
        set((s) => ({
          chatHistory: exists
            ? s.chatHistory
            : [...s.chatHistory, { role: 'ai' as const, content: res.ai_response!, topic_id: null }],
          scoresByIndex: res.scores?.length
            ? { ...s.scoresByIndex, [msgIdx]: res.scores }
            : s.scoresByIndex,
          interviewPlan: res.interview_plan || s.interviewPlan,
          currentTopicId: res.current_topic_id ?? s.currentTopicId,
          routingFlag: res.routing_flag ?? s.routingFlag,
          loading: false,
        }))
      } else {
        set({ loading: false })
      }
    } catch (e: unknown) {
      const msg = e instanceof Error ? e.message : '提交失败'
      set({ loading: false, error: msg })
    }
  },

  arbitrate: async (action) => {
    const { interviewId } = get()
    if (!interviewId) return
    await api.arbitrate(interviewId, { action })
    set({ routingFlag: action === 'END' ? 'END' : 'CONTINUE' })
  },

  refreshStatus: async (overrideId?: string) => {
    const { interviewId, chatHistory } = get()
    const id = overrideId || interviewId
    if (!id) return
    const status = await api.getStatus(id)
    set({
      interviewId: id,
      currentTopicId: status.current_topic_id ?? null,
      currentTopicIndex: status.current_topic_index ?? 0,
      // 只在 store 为空时从后端同步 chatHistory 和 plan
      ...(chatHistory.length === 0 && status.chat_history
        ? {
            chatHistory: status.chat_history as ChatMessage[],
            interviewPlan: (status.interview_plan || []) as TopicItem[],
          }
        : {}),
    })
  },

  refreshReport: async (overrideId?: string) => {
    const { interviewId } = get()
    const id = overrideId || interviewId
    if (!id) return
    const report = await api.getReport(id) as InterviewReport
    set({ report })
  },

  addMessage: (msg) => set((s) => ({ chatHistory: [...s.chatHistory, msg] })),
  clearError: () => set({ error: null }),
  disconnectSSE: () => sseClient.disconnect(),
}))
