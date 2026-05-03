import { useEffect, useState } from 'react'
import { useParams, useNavigate } from 'react-router-dom'
import { useInterviewStore } from '../stores/interviewStore'
import { useUIStore } from '../stores/uiStore'
import { sseClient } from '../services/sse'
import type { EvaluationRecord, SSEEvent } from '../types/generated'

export default function InterviewerReviewPage() {
  const { id } = useParams<{ id: string }>()!
  const navigate = useNavigate()
  const refreshStatus = useInterviewStore((s) => s.refreshStatus)
  const arbitrate = useInterviewStore((s) => s.arbitrate)
  const chatHistory = useInterviewStore((s) => s.chatHistory)
  const currentTopicId = useInterviewStore((s) => s.currentTopicId)
  const interviewPlan = useInterviewStore((s) => s.interviewPlan)
  const scoresByIndex = useInterviewStore((s) => s.scoresByIndex)
  const addToast = useUIStore((s) => s.addToast)

  const [initialized, setInitialized] = useState(false)

  useEffect(() => {
    if (!id) return
    // 连接 SSE 监听实时状态变化
    sseClient.connect(id)

    // 拉取当前状态
    refreshStatus(id).then(() => setInitialized(true))

    return () => { sseClient.disconnect() }
  }, [id, refreshStatus])

  // SSE 事件处理
  useEffect(() => {
    const handler = (event: SSEEvent) => {
      if (event.type === 'status' && event.flag === 'CONTINUE') {
        // 面试官仲裁后回到面试页
        addToast('已恢复面试', 'success')
        navigate(`/interview/${id}`)
      }
      if (event.type === 'status' && event.flag === 'END') {
        addToast('面试已结束', 'info')
        navigate(`/report/${id}`)
      }
    }
    const unsub = sseClient.onEvent(handler)
    return unsub
  }, [id, navigate, addToast])

  const currentTopic = interviewPlan.find((t) => t.topic_id === currentTopicId)
  const lastCandidateMsgIdx = [...chatHistory].reverse().findIndex((m) => m.role === 'candidate')
  const lastCandidateIdx = chatHistory.length - 1 - lastCandidateMsgIdx
  const lastCandidateMessage = lastCandidateMsgIdx >= 0 ? chatHistory[lastCandidateMsgIdx] : null
  const lastAiMessage = lastCandidateIdx > 0 ? chatHistory[lastCandidateIdx - 1] : null
  const lastScores = lastCandidateIdx >= 0 ? scoresByIndex[lastCandidateIdx] : undefined

  const handleAction = async (action: 'CONTINUE' | 'SKIP' | 'END') => {
    await arbitrate(action)
    addToast(`已执行: ${action}`, 'success')
    if (action === 'END') {
      navigate(`/report/${id}`)
    } else {
      navigate(`/interview/${id}`)
    }
  }

  if (!initialized) {
    return (
      <div className="min-h-screen bg-gray-50 flex items-center justify-center">
        <div className="text-center">
          <svg className="animate-spin h-8 w-8 mx-auto text-blue-600" viewBox="0 0 24 24" fill="none">
            <circle className="opacity-25" cx="12" cy="12" r="10" stroke="currentColor" strokeWidth="4" />
            <path className="opacity-75" fill="currentColor" d="M4 12a8 8 0 018-8V0C5.373 0 0 5.373 0 12h4z" />
          </svg>
          <p className="text-gray-500 mt-4">加载面试信息...</p>
        </div>
      </div>
    )
  }

  const completedCount = interviewPlan.filter((t) => t.status === 'completed').length

  return (
    <div className="min-h-screen bg-gray-100">
      {/* Top Bar */}
      <div className="bg-white border-b px-6 py-4 flex items-center justify-between">
        <div>
          <h1 className="text-xl font-bold text-gray-900">面试官审核</h1>
          <p className="text-sm text-gray-500 mt-0.5">
            {completedCount}/{interviewPlan.length} 议题已完成
          </p>
        </div>
        <div className="flex items-center gap-2">
          <span className="inline-flex items-center rounded-full bg-yellow-100 px-3 py-1 text-xs font-medium text-yellow-700">
            待审核
          </span>
          <button
            onClick={() => navigate(`/interview/${id}`)}
            className="text-sm text-gray-500 hover:text-gray-700 underline"
          >
            返回面试页
          </button>
        </div>
      </div>

      <div className="max-w-4xl mx-auto px-4 py-6 space-y-6">
        {/* Progress Bar */}
        <div className="bg-white rounded-xl shadow-sm p-4">
          <div className="flex gap-2 mb-2">
            {interviewPlan.map((topic) => (
              <div
                key={topic.topic_id}
                className={`flex-1 h-2 rounded-full ${
                  topic.status === 'completed'
                    ? 'bg-green-500'
                    : topic.topic_id === currentTopicId
                      ? 'bg-yellow-400'
                      : 'bg-gray-200'
                }`}
                title={topic.topic_name}
              />
            ))}
          </div>
          <div className="flex justify-between text-xs text-gray-400">
            <span>{interviewPlan[0]?.topic_name}</span>
            <span>{interviewPlan[interviewPlan.length - 1]?.topic_name}</span>
          </div>
        </div>

        {/* Current Topic */}
        <div className="bg-white rounded-xl shadow-sm p-6">
          <h2 className="text-sm font-semibold text-gray-500 uppercase tracking-wide mb-3">当前议题</h2>
          <div className="bg-blue-50 rounded-lg p-4">
            <p className="text-lg font-medium text-blue-900">{currentTopic?.topic_name || '未知'}</p>
          </div>
        </div>

        {/* AI Question */}
        {lastAiMessage && (
          <div className="bg-white rounded-xl shadow-sm p-6">
            <h2 className="text-sm font-semibold text-gray-500 uppercase tracking-wide mb-3">AI 提问</h2>
            <div className="bg-gray-50 rounded-lg p-4 text-sm text-gray-800 whitespace-pre-wrap">
              {lastAiMessage.content}
            </div>
          </div>
        )}

        {/* Candidate Answer */}
        {lastCandidateMessage && (
          <div className="bg-white rounded-xl shadow-sm p-6">
            <h2 className="text-sm font-semibold text-gray-500 uppercase tracking-wide mb-3">候选人回答</h2>
            <div className="bg-white border rounded-lg p-4 text-sm text-gray-800 whitespace-pre-wrap leading-relaxed">
              {lastCandidateMessage.content}
            </div>
          </div>
        )}

        {/* Evaluator Scores */}
        {lastScores && lastScores.length > 0 && (
          <div className="bg-white rounded-xl shadow-sm p-6">
            <h2 className="text-sm font-semibold text-gray-500 uppercase tracking-wide mb-3">
              评估官评分（存在分歧）
            </h2>
            <div className="space-y-3">
              {lastScores.map((s: EvaluationRecord, i: number) => {
                const color = s.score >= 80 ? 'border-l-green-500'
                  : s.score >= 60 ? 'border-l-yellow-500'
                  : 'border-l-red-500'
                return (
                  <div key={i} className={`border rounded-lg border-l-4 ${color} p-4`}>
                    <div className="flex items-center justify-between mb-2">
                      <span className="font-semibold text-gray-900">评估官 {i + 1}</span>
                      <span className={`text-xl font-bold ${
                        s.score >= 80 ? 'text-green-600' : s.score >= 60 ? 'text-yellow-600' : 'text-red-600'
                      }`}>{s.score} 分</span>
                    </div>
                    <p className="text-sm text-gray-600">{s.rationale}</p>
                  </div>
                )
              })}
            </div>
            {lastScores.length >= 2 && (
              <div className="mt-3 text-xs text-gray-400">
                最高 {Math.max(...lastScores.map((s: EvaluationRecord) => s.score))} 分，
                最低 {Math.min(...lastScores.map((s: EvaluationRecord) => s.score))} 分
              </div>
            )}
          </div>
        )}

        {/* Action Buttons */}
        <div className="bg-white rounded-xl shadow-sm p-6">
          <h2 className="text-sm font-semibold text-gray-500 uppercase tracking-wide mb-4">仲裁操作</h2>
          <div className="grid grid-cols-3 gap-3">
            <button
              onClick={() => handleAction('CONTINUE')}
              className="bg-green-600 hover:bg-green-700 text-white font-semibold py-3 rounded-lg transition-colors"
            >
              <div className="text-base">继续</div>
              <div className="text-xs opacity-75 mt-0.5">认可该回答，继续当前议题</div>
            </button>
            <button
              onClick={() => handleAction('SKIP')}
              className="bg-yellow-500 hover:bg-yellow-600 text-white font-semibold py-3 rounded-lg transition-colors"
            >
              <div className="text-base">跳过</div>
              <div className="text-xs opacity-75 mt-0.5">进入下一议题</div>
            </button>
            <button
              onClick={() => handleAction('END')}
              className="bg-red-600 hover:bg-red-700 text-white font-semibold py-3 rounded-lg transition-colors"
            >
              <div className="text-base">结束</div>
              <div className="text-xs opacity-75 mt-0.5">终止面试，生成报告</div>
            </button>
          </div>
        </div>
      </div>
    </div>
  )
}
