import { Routes, Route } from 'react-router-dom'
import SetupPage from './pages/Setup'
import InterviewPage from './pages/Interview'
import ArbitrationPage from './pages/Arbitration'
import InterviewerReviewPage from './pages/InterviewerReview'
import ReportPage from './pages/Report'
import ToastContainer from './components/ToastContainer'

export default function App() {
  return (
    <>
      <Routes>
        <Route path="/" element={<SetupPage />} />
        <Route path="/interview/:id" element={<InterviewPage />} />
        <Route path="/interviewer/:id" element={<InterviewerReviewPage />} />
        <Route path="/arbitration/:id" element={<ArbitrationPage />} />
        <Route path="/report/:id" element={<ReportPage />} />
      </Routes>
      <ToastContainer />
    </>
  )
}
