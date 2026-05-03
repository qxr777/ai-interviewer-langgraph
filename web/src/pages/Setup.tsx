import { useState } from 'react'
import { useNavigate } from 'react-router-dom'
import { useInterviewStore } from '../stores/interviewStore'
import { useUIStore } from '../stores/uiStore'

export default function SetupPage() {
  const navigate = useNavigate()
  const startInterview = useInterviewStore((s) => s.startInterview)
  const addToast = useUIStore((s) => s.addToast)
  const loading = useInterviewStore((s) => s.loading)

  const [jd, setJd] = useState('高级 Python 开发工程师 — 需要 5 年以上后端开发经验，精通 FastAPI 和分布式系统设计，熟悉微服务架构、云原生部署（Docker/Kubernetes）和 CI/CD 流水线。具备良好的数据库设计和性能调优能力，有带领技术团队的经验。')
  const [resumeFile, setResumeFile] = useState<File | null>(null)
  const [resumeName, setResumeName] = useState('')

  const handleFileChange = (e: React.ChangeEvent<HTMLInputElement>) => {
    const file = e.target.files?.[0]
    if (!file) return
    const ext = file.name.split('.').pop()?.toLowerCase()
    if (ext !== 'pdf' && ext !== 'docx') {
      addToast('仅支持 PDF 和 DOCX 格式', 'error')
      return
    }
    setResumeFile(file)
    setResumeName(file.name)
  }

  const handleSubmit = async (e: React.FormEvent) => {
    e.preventDefault()
    if (!resumeFile) {
      addToast('请上传简历', 'error')
      return
    }
    if (!jd.trim()) {
      addToast('请输入岗位描述', 'error')
      return
    }

    // Read file as base64
    const reader = new FileReader()
    reader.onload = async () => {
      const base64 = (reader.result as string).split(',')[1]
      try {
        const id = await startInterview(base64, jd.trim())
        addToast('面试已启动', 'success')
        navigate(`/interview/${id}`)
      } catch (err: unknown) {
        const msg = err instanceof Error ? err.message : '未知错误'
        addToast(`面试启动失败: ${msg}`, 'error')
      }
    }
    reader.onerror = () => addToast('文件读取失败', 'error')
    reader.readAsDataURL(resumeFile)
  }

  return (
    <div className="min-h-screen flex items-center justify-center bg-gradient-to-br from-blue-50 to-indigo-100">
      <div className="bg-white rounded-2xl shadow-xl p-8 w-full max-w-2xl">
        <h1 className="text-3xl font-bold text-gray-900 mb-2">AI 智能面试官</h1>
        <p className="text-gray-500 mb-8">上传简历，AI 自动生成针对性技术问题</p>

        <form onSubmit={handleSubmit} className="space-y-6">
          <div>
            <label className="block text-sm font-medium text-gray-700 mb-1">
              个人简历 <span className="text-red-500">*</span>
            </label>
            <div className="flex items-center gap-3">
              <label className="flex-1 cursor-pointer">
                <div className="border-2 border-dashed border-gray-300 rounded-lg px-4 py-8 text-center hover:border-blue-500 transition-colors">
                  {resumeName ? (
                    <div>
                      <p className="text-green-600 font-medium">{resumeName}</p>
                      <p className="text-xs text-gray-400 mt-1">点击更换</p>
                    </div>
                  ) : (
                    <div>
                      <p className="text-gray-500">点击或拖拽上传 PDF/DOCX</p>
                      <p className="text-xs text-gray-400 mt-1">支持 PDF、Word 格式</p>
                    </div>
                  )}
                </div>
                <input
                  type="file"
                  accept=".pdf,.docx"
                  onChange={handleFileChange}
                  className="hidden"
                />
              </label>
            </div>
          </div>

          <div>
            <label className="block text-sm font-medium text-gray-700 mb-1">
              岗位描述 <span className="text-red-500">*</span>
            </label>
            <textarea
              value={jd}
              onChange={(e) => setJd(e.target.value)}
              placeholder="Senior Python Developer - 需要 5 年以上后端开发经验，精通 FastAPI 和分布式系统设计。"
              rows={6}
              className="w-full rounded-lg border border-gray-300 px-4 py-2.5 focus:ring-2 focus:ring-blue-500 focus:border-transparent outline-none resize-none"
            />
          </div>

          <button
            type="submit"
            disabled={loading}
            className="w-full bg-blue-600 hover:bg-blue-700 disabled:bg-gray-400 text-white font-semibold py-3 rounded-lg transition-colors"
          >
            {loading ? '启动中...' : '启动面试'}
          </button>
        </form>
      </div>
    </div>
  )
}
