import { useState, useEffect, useRef } from 'react'
import { useParams, useNavigate, useLocation } from 'react-router-dom'
import { useInterviewStore } from '../stores/interviewStore'
import { useUIStore } from '../stores/uiStore'
import { sseClient } from '../services/sse'
import type { EvaluationRecord, TopicItem, SSEEvent } from '../types/generated'

function ScoreCard({ scores }: { scores: EvaluationRecord[] }) {
  const [expanded, setExpanded] = useState(false)
  const avg = Math.round(scores.reduce((sum, s) => sum + s.score, 0) / scores.length)
  const color = avg >= 80 ? 'bg-green-50 border-green-200 text-green-800'
    : avg >= 60 ? 'bg-yellow-50 border-yellow-200 text-yellow-800'
    : 'bg-red-50 border-red-200 text-red-800'

  return (
    <div className={`border rounded-lg p-3 ${color} text-sm`}>
      <div
        className="flex items-center justify-between cursor-pointer"
        onClick={() => setExpanded(!expanded)}
      >
        <span className="font-medium">评分：{avg} 分（{scores.length} 位评估官）</span>
        <span className="text-xs">{expanded ? '收起 ▲' : '展开 ▼'}</span>
      </div>
      {expanded && (
        <div className="mt-3 space-y-2 border-t pt-3">
          {scores.map((s, i) => (
            <div key={i} className="bg-white/60 rounded p-2">
              <div className="flex items-center gap-2">
                <span className="font-semibold">评估官 {i + 1}</span>
                <span className="text-xs bg-gray-100 px-2 py-0.5 rounded">{s.score} 分</span>
              </div>
              <p className="mt-1 text-xs text-gray-600">{s.rationale}</p>
            </div>
          ))}
        </div>
      )}
    </div>
  )
}

function TopicSidebar({ plan, currentTopicId }: { plan: TopicItem[]; currentTopicId: string | null }) {
  return (
    <div className="w-64 bg-white border-r flex-shrink-0 overflow-y-auto">
      <div className="px-4 py-3 border-b">
        <h3 className="text-sm font-semibold text-gray-700">面试议题</h3>
        <p className="text-xs text-gray-400 mt-1">{plan.length} 个议题</p>
      </div>
      <div className="p-3 space-y-2">
        {plan.map((topic, i) => {
          const isActive = topic.topic_id === currentTopicId
          const isCompleted = topic.status === 'completed'
          return (
            <div
              key={topic.topic_id}
              className={`rounded-lg px-3 py-2.5 text-sm transition-colors ${
                isActive
                  ? 'bg-blue-50 border border-blue-200 text-blue-800'
                  : isCompleted
                    ? 'bg-gray-50 text-gray-500'
                    : 'text-gray-600'
              }`}
            >
              <div className="flex items-center gap-2">
                <span className={`w-5 h-5 rounded-full flex items-center justify-center text-xs font-medium ${
                  isActive
                    ? 'bg-blue-500 text-white'
                    : isCompleted
                      ? 'bg-green-500 text-white'
                      : 'bg-gray-200 text-gray-500'
                }`}>
                  {isCompleted ? '✓' : i + 1}
                </span>
                <span className="truncate">{topic.topic_name}</span>
              </div>
              <p className="text-xs mt-1 ml-7 text-gray-400">
                {isActive ? '进行中' : isCompleted ? '已完成' : '待进行'}
              </p>
            </div>
          )
        })}
        {plan.length === 0 && (
          <div className="text-center text-gray-400 py-8 text-sm">
            议题加载中...
          </div>
        )}
      </div>
    </div>
  )
}

export default function InterviewPage() {
  const { id } = useParams<{ id: string }>() as { id: string }
  const navigate = useNavigate()
  const location = useLocation()
  const chatHistory = useInterviewStore((s) => s.chatHistory)
  const currentTopicId = useInterviewStore((s) => s.currentTopicId)
  const routingFlag = useInterviewStore((s) => s.routingFlag)
  const isEscalated = useInterviewStore((s) => s.isEscalated)
  const loading = useInterviewStore((s) => s.loading)
  const error = useInterviewStore((s) => s.error)
  const clearError = useInterviewStore((s) => s.clearError)
  const submitAnswer = useInterviewStore((s) => s.submitAnswer)
  const interviewPlan = useInterviewStore((s) => s.interviewPlan)
  const refreshStatus = useInterviewStore((s) => s.refreshStatus)
  const scoresByIndex = useInterviewStore((s) => s.scoresByIndex)
  const addToast = useUIStore((s) => s.addToast)

  const [input, setInput] = useState('')
  const messagesEnd = useRef<HTMLDivElement>(null)

  useEffect(() => {
    messagesEnd.current?.scrollIntoView({ behavior: 'smooth' })
  }, [chatHistory])

  useEffect(() => {
    if (routingFlag === 'ESCALATE' && !isEscalated) {
      useInterviewStore.setState({ isEscalated: true })
      addToast('评分分歧过大，等待面试官审核', 'info')
    }
    if (routingFlag === 'END') {
      addToast('面试已结束', 'info')
      navigate(`/report/${id}`)
    }
  }, [routingFlag, isEscalated, id, navigate, addToast])

  // 立即同步 + 定期同步后端状态
  useEffect(() => {
    refreshStatus(id)
    const timer = setInterval(() => refreshStatus(id), 5000)
    return () => clearInterval(timer)
  }, [refreshStatus, id])

  // 路由变化时重新同步（如从仲裁页面返回）
  useEffect(() => {
    refreshStatus(id)
  }, [location.pathname, refreshStatus, id])

  // 当 interviewId 存在时连接 SSE（非 startInterview 路径进入时）
  useEffect(() => {
    if (id && !sseClient.isConnected()) {
      sseClient.connect(id)
    }
  }, [id])

  // SSE 事件处理
  useEffect(() => {
    const handler = (event: SSEEvent) => {
      if (event.type === 'message' && event.role === 'ai' && event.content) {
        // SSE 推送的 AI 消息 — 去重后追加
        useInterviewStore.setState((s) => {
          const exists = s.chatHistory.some(
            (m) => m.role === 'ai' && m.content === event.content,
          )
          if (exists) return {}
          return {
            chatHistory: [...s.chatHistory, { role: 'ai' as const, content: event.content!, topic_id: null }],
            loading: false,
            interviewPlan: event.topic_id
              ? s.interviewPlan.map((t) =>
                  t.topic_id === event.topic_id ? { ...t, status: 'completed' as const } : t,
                )
              : s.interviewPlan,
          }
        })
      }
      if (event.type === 'status' && event.flag) {
        // 只在用户未干预时更新 routingFlag
        useInterviewStore.setState((s) => {
          if (s.routingFlag !== null) return {}
          if (event.flag === 'ESCALATE') return { routingFlag: 'ESCALATE' as const }
          if (event.flag === 'END') return { routingFlag: 'END' as const }
          // 面试官仲裁后恢复
          if (event.flag === 'CONTINUE') return { isEscalated: false, loading: false }
          return {}
        })
      }
    }
    const unsub = sseClient.onEvent(handler)
    return unsub
  }, [])

  const handleSubmit = async (e: React.FormEvent) => {
    e.preventDefault()
    const answer = input.trim()
    if (!answer || loading) return
    setInput('')
    await submitAnswer(answer)
  }

  const currentTopic = interviewPlan.find((t) => t.topic_id === currentTopicId)
  const completedCount = interviewPlan.filter((t) =>
    t.status === 'completed'
  ).length

  return (
    <div className="flex h-screen bg-gray-50">
      {/* Sidebar: Topic List */}
      <TopicSidebar plan={interviewPlan} currentTopicId={currentTopicId} />

      {/* Main: Chat Area */}
      <div className="flex-1 flex flex-col min-w-0">
        {/* Header */}
        <div className="bg-white border-b px-6 py-4 flex items-center justify-between">
          <div>
            <h2 className="text-lg font-semibold text-gray-900">AI 面试中</h2>
            {currentTopic && (
              <p className="text-sm text-gray-500">当前议题: {currentTopic.topic_name}</p>
            )}
          </div>
          <div className="flex gap-2">
            <span className="inline-flex items-center rounded-full bg-blue-100 px-3 py-1 text-xs font-medium text-blue-700">
              {completedCount} / {interviewPlan.length} 已完成
            </span>
          </div>
        </div>

        {/* Messages */}
        <div className="flex-1 overflow-y-auto px-6 py-4 space-y-4">
          {error && (
            <div className="bg-red-50 border border-red-200 rounded-lg p-3 text-sm text-red-700 flex justify-between items-center">
              <span>{error}</span>
              <button onClick={clearError} className="text-red-500 hover:text-red-700 ml-4">x</button>
            </div>
          )}
          {chatHistory.length === 0 && !error && (
            <div className="text-center text-gray-400 py-12">
              <p className="text-lg">等待 AI 提问...</p>
            </div>
          )}
          {chatHistory.map((msg, i) => {
            const scores = msg.role === 'candidate' ? scoresByIndex[i] : undefined
            const isLatestCandidate = msg.role === 'candidate' && i === chatHistory.length - 1 && loading
            return (
              <div key={i}>
                <div
                  className={`flex ${msg.role === 'candidate' ? 'justify-end' : 'justify-start'}`}
                >
                  <div
                    className={`max-w-[75%] rounded-2xl px-4 py-3 ${
                      msg.role === 'candidate'
                        ? 'bg-blue-600 text-white rounded-br-sm'
                        : 'bg-white text-gray-900 shadow-sm rounded-bl-sm'
                    }`}
                  >
                    <p className="text-sm whitespace-pre-wrap">{msg.content}</p>
                    {isLatestCandidate && (
                      <div className="mt-2 flex items-center gap-1 text-blue-200 text-xs">
                        <svg className="animate-spin h-3 w-3" viewBox="0 0 24 24" fill="none">
                          <circle className="opacity-25" cx="12" cy="12" r="10" stroke="currentColor" strokeWidth="4" />
                          <path className="opacity-75" fill="currentColor" d="M4 12a8 8 0 018-8V0C5.373 0 0 5.373 0 12h4z" />
                        </svg>
                        AI 思考中...
                      </div>
                    )}
                  </div>
                </div>
                {scores && scores.length > 0 && (
                  <div className="max-w-[75%] ml-auto mt-1">
                    <ScoreCard scores={scores} />
                  </div>
                )}
              </div>
            )
          })}
          <div ref={messagesEnd} />
        </div>

        {/* Escalation Overlay */}
        {isEscalated && (
          <div className="absolute inset-0 bg-white/80 backdrop-blur-sm flex items-center justify-center z-50">
            <div className="bg-white rounded-2xl shadow-2xl p-8 max-w-md mx-4 text-center">
              <div className="w-16 h-16 rounded-full bg-yellow-100 flex items-center justify-center mx-auto mb-4">
                <svg className="w-8 h-8 text-yellow-600" fill="none" viewBox="0 0 24 24" stroke="currentColor" strokeWidth={2}>
                  <path strokeLinecap="round" strokeLinejoin="round" d="M12 9v3.75m-9.303 3.376c-.866 1.5.217 3.374 1.948 3.374h14.71c1.73 0 2.813-1.874 1.948-3.374L13.949 3.378c-.866-1.5-3.032-1.5-3.898 0L2.697 16.126zM12 15.75h.007v.008H12v-.008z" />
                </svg>
              </div>
              <h3 className="text-lg font-semibold text-gray-900 mb-2">等待面试官审核</h3>
              <p className="text-sm text-gray-500 mb-4">
                评估官对您的回答评分存在较大分歧，面试官正在审核当前回答，请稍候...
              </p>
              <div className="flex items-center justify-center gap-2 text-yellow-600">
                <svg className="animate-spin h-4 w-4" viewBox="0 0 24 24" fill="none">
                  <circle className="opacity-25" cx="12" cy="12" r="10" stroke="currentColor" strokeWidth="4" />
                  <path className="opacity-75" fill="currentColor" d="M4 12a8 8 0 018-8V0C5.373 0 0 5.373 0 12h4z" />
                </svg>
                <span className="text-sm font-medium">审核中</span>
              </div>
            </div>
          </div>
        )}

        {/* Input */}
        <div className="bg-white border-t px-6 py-4">
          <form onSubmit={handleSubmit} className="flex gap-3">
            <input
              type="text"
              value={input}
              onChange={(e) => setInput(e.target.value)}
              placeholder="输入你的回答..."
              disabled={loading}
              className="flex-1 rounded-lg border border-gray-300 px-4 py-2.5 focus:ring-2 focus:ring-blue-500 focus:border-transparent outline-none disabled:bg-gray-100"
            />
            <button
              type="submit"
              disabled={loading || !input.trim()}
              className="bg-blue-600 hover:bg-blue-700 disabled:bg-gray-300 text-white font-semibold px-6 py-2.5 rounded-lg transition-colors"
            >
              {loading ? '...' : '提交'}
            </button>
          </form>
        </div>
      </div>
    </div>
  )
}
