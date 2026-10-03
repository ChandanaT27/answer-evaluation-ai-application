import api from '../api'
import { Alert, Spinner, StatCard, useLoader } from '../components/ui'
import { Bar, BarChart, CartesianGrid, ResponsiveContainer, Tooltip, XAxis, YAxis } from 'recharts'

export default function AdminDashboard() {
  const { data, loading, error } = useLoader(() => api.get('/admin/stats').then((r) => r.data), [])
  if (loading) return <Spinner />
  if (error) return <Alert error={error} />
  const chart = [
    { name: 'Students', value: data.students }, { name: 'Teachers', value: data.teachers },
    { name: 'Subjects', value: data.subjects }, { name: 'Exams', value: data.exams },
    { name: 'Submissions', value: data.submissions }, { name: 'Evaluations', value: data.evaluations },
    { name: 'Finalized', value: data.finalizedEvaluations },
  ]
  return (
    <>
      <h4 className="mb-3">System overview</h4>
      <div className="row g-3 mb-4">
        <StatCard label="Students" value={data.students} icon="bi-mortarboard" />
        <StatCard label="Teachers" value={data.teachers} icon="bi-person-workspace" color="success" />
        <StatCard label="Subjects" value={data.subjects} icon="bi-journal-bookmark" color="warning" />
        <StatCard label="Exams" value={data.exams} icon="bi-file-earmark-text" color="info" />
        <StatCard label="Submissions" value={data.submissions} icon="bi-upload" />
        <StatCard label="Evaluations" value={data.evaluations} icon="bi-clipboard-data" color="success" />
        <StatCard label="Finalized" value={data.finalizedEvaluations} icon="bi-check2-circle" color="success" />
        <StatCard label="Audit events" value={data.auditEvents} icon="bi-list-check" color="secondary" />
      </div>
      <div className="card"><div className="card-body">
        <h6>Platform activity</h6>
        <div style={{ height: 280 }}>
          <ResponsiveContainer>
            <BarChart data={chart}><CartesianGrid strokeDasharray="3 3" /><XAxis dataKey="name" /><YAxis allowDecimals={false} /><Tooltip /><Bar dataKey="value" fill="#3a4180" /></BarChart>
          </ResponsiveContainer>
        </div>
      </div></div>
    </>
  )
}
