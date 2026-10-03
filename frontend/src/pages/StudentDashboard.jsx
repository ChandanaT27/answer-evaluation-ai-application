import { Link } from 'react-router-dom'
import { Bar, BarChart, CartesianGrid, Legend, Line, LineChart, ResponsiveContainer, Tooltip, XAxis, YAxis } from 'recharts'
import api from '../api'
import { Alert, Spinner, StatCard, fmt, fmtDate, useLoader } from '../components/ui'

export default function StudentDashboard() {
  const { data, loading, error } = useLoader(() => api.get('/student/performance').then((r) => r.data), [])
  if (loading) return <Spinner />
  if (error) return <Alert error={error} />
  const trend = data.exams.map((e) => ({ name: e.examTitle, Percentage: e.percentage }))
  return (
    <>
      <h4 className="mb-3">My performance</h4>
      {data.exams.length === 0 ? (
        <div className="card"><div className="card-body text-muted">No published results yet. Results appear here once your teacher finalizes the evaluation.</div></div>
      ) : (
        <>
          <div className="row g-3 mb-3">
            <StatCard label="Overall average" value={`${data.overallPercentage}%`} icon="bi-graph-up" color="success" />
            <StatCard label="Exams evaluated" value={data.exams.length} icon="bi-card-checklist" />
            <StatCard label="Subjects" value={data.subjects.length} icon="bi-journal-bookmark" color="warning" />
          </div>
          <div className="row g-3 mb-3">
            <div className="col-lg-7"><div className="card h-100"><div className="card-body">
              <h6>Score trend</h6>
              <div style={{ height: 260 }}><ResponsiveContainer><LineChart data={trend}><CartesianGrid strokeDasharray="3 3" /><XAxis dataKey="name" /><YAxis domain={[0, 100]} /><Tooltip /><Line type="monotone" dataKey="Percentage" stroke="#3a4180" strokeWidth={2} /></LineChart></ResponsiveContainer></div>
            </div></div></div>
            <div className="col-lg-5"><div className="card h-100"><div className="card-body">
              <h6>Subject averages</h6>
              <div style={{ height: 260 }}><ResponsiveContainer><BarChart data={data.subjects}><CartesianGrid strokeDasharray="3 3" /><XAxis dataKey="subjectName" /><YAxis domain={[0, 100]} /><Tooltip /><Legend /><Bar dataKey="averagePercentage" name="Average %" fill="#2ea05a" /></BarChart></ResponsiveContainer></div>
            </div></div></div>
          </div>
          <div className="card"><div className="table-responsive">
            <table className="table table-hover align-middle mb-0">
              <thead><tr><th>Exam</th><th>Subject</th><th>Marks</th><th>%</th><th>Published</th><th /></tr></thead>
              <tbody>{data.exams.map((e) => (
                <tr key={e.evaluationId}><td>{e.examTitle}</td><td>{e.subjectName}</td><td>{fmt(e.marks)} / {fmt(e.maxMarks)}</td><td>{e.percentage}%</td><td className="small">{fmtDate(e.date)}</td>
                  <td className="text-end"><Link className="btn btn-sm btn-outline-primary" to={`/evaluations/${e.evaluationId}`}>View details</Link></td></tr>
              ))}</tbody>
            </table>
          </div></div>
        </>
      )}
    </>
  )
}
