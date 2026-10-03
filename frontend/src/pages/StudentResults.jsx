import { useEffect, useState } from 'react'
import { Link } from 'react-router-dom'
import api, { errorMessage, openFile } from '../api'
import { Alert, Spinner, StatusBadge, fmt, fmtDate, useLoader } from '../components/ui'

export default function StudentResults() {
  const [subjectId, setSubjectId] = useState('')
  const [examId, setExamId] = useState('')
  const [msg, setMsg] = useState({})
  const { data: subjects, loading } = useLoader(() => api.get('/subjects', { params: { size: 200 } }).then((r) => r.data.content), [])
  const { data: exams } = useLoader(() => (subjectId ? api.get('/exams', { params: { subjectId, size: 100 } }).then((r) => r.data.content) : Promise.resolve([])), [subjectId])
  const { data: results } = useLoader(() => (examId ? api.get('/evaluations', { params: { examId, size: 50 } }).then((r) => r.data.content) : Promise.resolve([])), [examId])

  useEffect(() => { setExamId('') }, [subjectId])

  if (loading) return <Spinner />
  return (
    <>
      <h4 className="mb-3">My results</h4>
      <Alert {...msg} onClose={() => setMsg({})} />
      <div className="row g-2 mb-3">
        <div className="col-md-4">
          <label className="form-label small mb-0">Subject</label>
          <select className="form-select" value={subjectId} onChange={(e) => setSubjectId(e.target.value)}>
            <option value="">Select subject</option>{subjects?.map((s) => <option key={s.id} value={s.id}>{s.name}</option>)}
          </select>
        </div>
        <div className="col-md-4">
          <label className="form-label small mb-0">Exam</label>
          <select className="form-select" value={examId} onChange={(e) => setExamId(e.target.value)} disabled={!subjectId}>
            <option value="">Select exam</option>{exams?.map((x) => <option key={x.id} value={x.id}>{x.title}</option>)}
          </select>
        </div>
      </div>
      {subjects?.length === 0 && <div className="text-muted">No results have been published for you yet.</div>}
      {results?.map((r) => (
        <div className="card mb-2" key={r.id}><div className="card-body d-flex justify-content-between align-items-center flex-wrap gap-2">
          <div>
            <h5 className="mb-0">{r.examTitle} <StatusBadge status={r.status} /></h5>
            <div className="text-muted small">{r.subjectName} &middot; published {fmtDate(r.finalizedAt)}</div>
          </div>
          <div className="fs-3 fw-bold">{fmt(r.finalTotal)} / {fmt(r.maxTotal)} <span className="fs-6 text-muted">({r.percentage}%)</span></div>
          <div className="d-flex gap-2">
            <Link to={`/evaluations/${r.id}`} className="btn btn-primary">Question-wise details</Link>
            <button className="btn btn-outline-danger" onClick={() => openFile(`/evaluations/${r.id}/report`, { download: true, filename: `inkgrade-report-${r.id}.pdf` }).catch((e) => setMsg({ error: errorMessage(e) }))}><i className="bi bi-file-earmark-pdf me-1" />PDF</button>
          </div>
        </div></div>
      ))}
    </>
  )
}
