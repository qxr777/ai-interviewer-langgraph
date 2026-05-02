import { useParams, useNavigate } from 'react-router-dom'
import { useInterviewStore } from '../stores/interviewStore'
import { useUIStore } from '../stores/uiStore'
import type { EvaluationRecord } from '../types/generated'

export default function ArbitrationPage() {
  const { id } = useParams<{ id: string }>()!
  const navigate = useNavigate()
  const arbitrate = useInterviewStore((s) => s.arbitrate)
  const currentTopicId = useInterviewStore((s) => s.currentTopicId)
  const interviewPlan = useInterviewStore((s) => s.interviewPlan)
  const chatHistory = useInterviewStore((s) => s.chatHistory)
  const scoresByIndex = useInterviewStore((s) => s.scoresByIndex)
  const addToast = useUIStore((s) => s.addToast)

  const currentTopic = interviewPlan.find((t) => t.topic_id === currentTopicId)
  const lastAiMessage = [...chatHistory].reverse().find((m) => m.role === 'ai')
  const lastCandidateMsgIdx = [...chatHistory].reverse().findIndex((m) => m.role === 'candidate')
  const lastCandidateIdx = chatHistory.length - 1 - lastCandidateMsgIdx
  const lastCandidateMessage = lastCandidateMsgIdx >= 0 ? chatHistory[lastCandidateMsgIdx] : null
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

  return (
    <div className="min-h-screen bg-gray-50 py-8 px-4">
      <div className="max-w-3xl mx-auto">
        <div className="bg-white rounded-2xl shadow-xl p-8">
          <h1 className="text-2xl font-bold text-gray-900 mb-2">人工仲裁</h1>
          <p className="text-gray-500 mb-6">评估官评分分歧较大，需要人工判断</p>

          <div className="mb-6">
            <h3 className="text-sm font-medium text-gray-700 mb-2">当前议题</h3>
            <div className="bg-blue-50 rounded-lg p-4">
              <p className="font-medium text-blue-900">{currentTopic?.topic_name || '未知'}</p>
            </div>
          </div>

          {lastAiMessage && (
            <div className="mb-4">
              <h3 className="text-sm font-medium text-gray-700 mb-2">AI 提问</h3>
              <div className="bg-gray-50 rounded-lg p-4 text-sm text-gray-700">
                {lastAiMessage.content}
              </div>
            </div>
          )}

          {lastCandidateMessage && (
            <div className="mb-6">
              <h3 className="text-sm font-medium text-gray-700 mb-2">候选人回答</h3>
              <div className="bg-yellow-50 rounded-lg p-4 text-sm text-gray-700">
                {lastCandidateMessage.content}
              </div>
            </div>
          )}

          {lastScores && lastScores.length > 0 && (
            <div className="mb-6">
              <h3 className="text-sm font-medium text-gray-700 mb-2">评估官评分</h3>
              <div className="space-y-2">
                {lastScores.map((s: EvaluationRecord, i: number) => {
                  const color = s.score >= 80 ? 'bg-green-50 border-green-200'
                    : s.score >= 60 ? 'bg-yellow-50 border-yellow-200'
                    : 'bg-red-50 border-red-200'
                  return (
                    <div key={i} className={`border rounded-lg p-3 ${color}`}>
                      <div className="flex items-center justify-between">
                        <span className="font-medium">评估官 {i + 1}</span>
                        <span className="text-lg font-bold">{s.score} 分</span>
                      </div>
                      <p className="text-xs text-gray-600 mt-1">{s.rationale}</p>
                    </div>
                  )
                })}
              </div>
            </div>
          )}

          <div className="flex gap-3">
            <button
              onClick={() => handleAction('CONTINUE')}
              className="flex-1 bg-green-600 hover:bg-green-700 text-white font-semibold py-3 rounded-lg transition-colors"
            >
              继续当前议题
            </button>
            <button
              onClick={() => handleAction('SKIP')}
              className="flex-1 bg-yellow-500 hover:bg-yellow-600 text-white font-semibold py-3 rounded-lg transition-colors"
            >
              跳过此议题
            </button>
            <button
              onClick={() => handleAction('END')}
              className="flex-1 bg-red-600 hover:bg-red-700 text-white font-semibold py-3 rounded-lg transition-colors"
            >
              结束面试
            </button>
          </div>
        </div>
      </div>
    </div>
  )
}
