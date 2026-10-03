import { useState } from 'react'
import { Link } from 'react-router-dom'
import api, { errorMessage, openFile } from '../api'
import { useAuth } from '../auth'
import { Alert, Pagination, Spinner, StatusBadge, fmt, fmtDate, useDebounced, useLoader } from '../components/ui'

export default function Evaluations() {
  const { can } = useAuth()
  const [f, setF] = useState({ q: '', status: '', subjectId: '', examId: '', from: '', to: '' })
  const [page, setPage] = useState(0)
  const [msg, setMsg] = useState({})
  const dq = useDebounced(f.q)
  const { data: subjects } = useLoader(() => api.get('/subjects', { params: { size: 200 } }).then((r) => r.data.content), [])
  const { data: exams } = useLoader(() => api.get('/exams', { params: { subjectId: f.subjectId || undefined, size: 100 } }).then((r) => r.data.content), [f.subjectId])
  const { data, loading, reload } = useLoader(
    () => api.get('/evaluations', {
      params: {
        q: dq, status: f.status || undefined, subjectId: f.subjectId || undefined, examId: f.examId || undefined,
        from: f.from || undefined, to: f.to || undefined, page, size: 15,
      },
    }).then((r) => r.data), [dq, f.status, f.subjectId, f.examId, f.from, f.to, page])
  const set = (k) => (e) => { setF({ ...f, [k]: e.target.value, ...(k === 'subjectId' ? { examId: '' } : {}) }); setPage(0) }

  const remove = async (ev) => {
    if (!window.confirm(`Delete the evaluation of ${ev.studentName} for "${ev.examTitle}"? The answer sheet is kept and can be re-evaluated.`)) return
    try { await api.delete(`/evaluations/${ev.id}`); setMsg({ success: 'Evaluation deleted.' }); reload() } catch (err) { setMsg({ error: errorMessage(err) }) }
  }
  const report = (ev) => openFile(`/evaluations/${ev.id}/report`, { download: true, filename: `report-${ev.id}.pdf` }).catch((e) => setMsg({ error: errorMessage(e) }))

  return (
    <>
      <h4 className="mb-3">Evaluation history</h4>
      <Alert {...msg} onClose={() => setMsg({})} />
      <div className="row g-2 mb-3">
        <div className="col-md-3"><input className="form-control" placeholder="Search student / roll / exam" value={f.q} onChange={set('q')} /></div>
        <div className="col-md-2">
          <select className="form-select" value={f.status} onChange={set('status')}>
            <option value="">Any status</option><option value="AI_COMPLETED">AI completed</option><option value="UNDER_REVIEW">Under review</option><option value="FINALIZED">Finalized</option>
          </select>
        </div>
        <div className="col-md-2">
          <select className="form-select" value={f.subjectId} onChange={set('subjectId')}>
            <option value="">All subjects</option>{subjects?.map((s) => <option key={s.id} value={s.id}>{s.name}</option>)}
          </select>
        </div>
        <div className="col-md-2">
          <select className="form-select" value={f.examId} onChange={set('examId')}>
            <option value="">All exams</option>{exams?.map((x) => <option key={x.id} value={x.id}>{x.title}</option>)}
          </select>
        </div>
        <div className="col-6 col-md-1"><input type="date" className="form-control" value={f.from} onChange={set('from')} title="From" /></div>
        <div className="col-6 col-md-2"><input type="date" className="form-control" value={f.to} onChange={set('to')} title="To" /></div>
      </div>
      <div className="card"><div className="table-responsive">
        <table className="table table-hover align-middle mb-0">
          <thead><tr><th>Student</th><th>Exam</th><th>Subject</th><th>AI total</th><th>Final</th><th>%</th><th>Status</th><th>Evaluated</th><th /></tr></thead>
          <tbody>
            {data?.content.length === 0 && <tr><td colSpan={9} className="text-muted">No evaluations match.</td></tr>}
            {data?.content.map((e) => (
              <tr key={e.id}>
                <td>{e.studentName}<div className="small text-muted">{e.rollNumber}</div></td>
                <td>{e.examTitle}</td><td>{e.subjectName}</td>
                <td>{fmt(e.aiTotal)} / {fmt(e.maxTotal)}</td><td><strong>{fmt(e.finalTotal)}</strong></td><td>{e.percentage}%</td>
                <td><StatusBadge status={e.status} /></td><td className="small">{fmtDate(e.evaluatedAt)}</td>
                <td className="text-end text-nowrap">
                  <Link className="btn btn-sm btn-outline-primary me-1" to={`/evaluations/${e.id}`}>Open</Link>
                  {can('REPORT_DOWNLOAD') && <button className="btn btn-sm btn-outline-secondary me-1" onClick={() => report(e)} title="Download PDF"><i className="bi bi-file-earmark-pdf" /></button>}
                  {can('EVALUATION_DELETE') && <button className="btn btn-sm btn-outline-danger" onClick={() => remove(e)} title="Delete"><i className="bi bi-trash" /></button>}
                </td>
              </tr>
            ))}
          </tbody>
        </table>
      </div></div>
      {loading && <Spinner />}
      <div className="mt-3"><Pagination page={page} totalPages={data?.totalPages} onChange={setPage} /></div>
    </>
  )
}
