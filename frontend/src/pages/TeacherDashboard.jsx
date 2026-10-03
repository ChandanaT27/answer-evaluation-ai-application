import { Link } from 'react-router-dom'
import api from '../api'
import { Alert, Spinner, StatCard, useLoader } from '../components/ui'

export default function TeacherDashboard() {
  const { data, loading, error } = useLoader(() => api.get('/teacher/stats').then((r) => r.data), [])
  if (loading) return <Spinner />
  if (error) return <Alert error={error} />
  return (
    <>
      <h4 className="mb-3">Teacher dashboard</h4>
      <div className="row g-3 mb-4">
        <StatCard label="My exams" value={data.exams} icon="bi-file-earmark-text" />
        <StatCard label="Answer sheets" value={data.submissions} icon="bi-upload" color="info" />
        <StatCard label="Pending review" value={data.pendingReview} icon="bi-hourglass-split" color="warning" />
        <StatCard label="Finalized" value={data.finalized} icon="bi-check2-circle" color="success" />
      </div>
      <div className="card"><div className="card-body">
        <p className="mb-1">Average score across your evaluations: <strong>{data.averagePercentage}%</strong></p>
        <Link to="/teacher/exams" className="btn btn-primary btn-sm me-2">Manage exams</Link>
        <Link to="/teacher/evaluations" className="btn btn-outline-primary btn-sm">Review evaluations</Link>
      </div></div>
    </>
  )
}
