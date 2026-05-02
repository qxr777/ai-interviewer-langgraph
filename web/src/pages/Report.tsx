import { useEffect } from 'react'
import { useParams, useNavigate } from 'react-router-dom'
import { useInterviewStore } from '../stores/interviewStore'

export default function ReportPage() {
  const { id: _id } = useParams<{ id: string }>() as { id: string }
  const navigate = useNavigate()
  const report = useInterviewStore((s) => s.report)
  const refreshReport = useInterviewStore((s) => s.refreshReport)

  useEffect(() => {
    refreshReport()
  }, [refreshReport])

  if (!report) {
    return (
      <div className="min-h-screen flex items-center justify-center bg-gray-50">
        <p className="text-gray-500">加载报告中...</p>
      </div>
    )
  }

  return (
    <div className="min-h-screen bg-gray-50 py-8 px-4">
      <div className="max-w-4xl mx-auto">
        <div className="bg-white rounded-2xl shadow-xl p-8">
          <div className="flex items-center justify-between mb-6">
            <h1 className="text-2xl font-bold text-gray-900">面试报告</h1>
            <button
              onClick={() => navigate('/')}
              className="text-sm text-blue-600 hover:text-blue-700"
            >
              返回首页
            </button>
          </div>

          {/* Overall Score */}
          <div className="bg-gradient-to-r from-blue-500 to-indigo-600 rounded-xl p-6 text-white mb-8">
            <p className="text-sm opacity-80">总体平均分</p>
            <p className="text-5xl font-bold mt-1">
              {report.overall_average_score ?? '--'}
            </p>
            <p className="text-sm opacity-80 mt-2">
              共 {report.total_evaluations} 次评估，{report.topics.length} 个议题
            </p>
          </div>

          {/* Topics */}
          <div className="space-y-4">
            <h2 className="text-lg font-semibold text-gray-900">各议题详情</h2>
            {report.topics.map((topic) => (
              <div key={topic.topic_id} className="border rounded-xl p-5">
                <div className="flex items-center justify-between mb-3">
                  <h3 className="font-medium text-gray-900">{topic.topic_name}</h3>
                  <span
                    className={`inline-flex items-center rounded-full px-3 py-1 text-xs font-medium ${
                      topic.status === 'completed'
                        ? 'bg-green-100 text-green-700'
                        : 'bg-gray-100 text-gray-700'
                    }`}
                  >
                    {topic.status}
                  </span>
                </div>

                {topic.scores.length > 0 && (
                  <>
                    <div className="flex items-center gap-4 mb-3">
                      <span className="text-2xl font-bold text-gray-900">
                        {topic.average_score ?? '--'}
                      </span>
                      <span className="text-sm text-gray-500">平均分</span>
                    </div>

                    {/* Score bars */}
                    <div className="flex gap-2 mb-4">
                      {topic.scores.map((score, i) => (
                        <div
                          key={i}
                          className="flex-1 h-2 bg-gray-200 rounded-full overflow-hidden"
                        >
                          <div
                            className="h-full bg-blue-500 rounded-full"
                            style={{ width: `${score}%` }}
                          />
                        </div>
                      ))}
                    </div>

                    {/* Rationales */}
                    <div className="space-y-2">
                      {topic.rationales.map((r, i) => (
                        <p key={i} className="text-sm text-gray-600 bg-gray-50 rounded-lg p-3">
                          {r}
                        </p>
                      ))}
                    </div>
                  </>
                )}
              </div>
            ))}
          </div>
        </div>
      </div>
    </div>
  )
}
