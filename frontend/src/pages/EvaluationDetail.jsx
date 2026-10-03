import { useEffect, useState } from 'react'
import { useNavigate } from 'react-router-dom'
import { useParams } from 'react-router-dom'
import { Bar, BarChart, CartesianGrid, Legend, ResponsiveContainer, Tooltip, XAxis, YAxis } from 'recharts'
import api, { errorMessage, openFile } from '../api'
import { useAuth } from '../auth'
import Highlight, { HighlightLegend } from '../components/Highlight'
import { Alert, Spinner, StatusBadge, fmt, fmtDate, useLoader } from '../components/ui'

export default function EvaluationDetail() {
  const { id } = useParams()
  const { user, can } = useAuth()
  const nav = useNavigate()
  const staff = user.role !== 'STUDENT'
  const { data, loading, error, setData } = useLoader(() => api.get(`/evaluations/${id}`).then((r) => r.data), [id])
  const [msg, setMsg] = useState({})
  const [history, setHistory] = useState(null)

  if (loading && !data) return <Spinner />
  if (error) return <Alert error={error} />
  const s = data.summary
  const canReview = staff && can('EVALUATION_REVIEW')

  const act = async (fn, ok) => {
    try { const r = await fn(); if (r?.data?.summary) setData(r.data); setMsg({ success: ok }); if (history) loadHistory() } catch (e) { setMsg({ error: errorMessage(e) }) }
  }
  const loadHistory = () => api.get(`/evaluations/${id}/history`).then((r) => setHistory(r.data)).catch((e) => setMsg({ error: errorMessage(e) }))
  const chart = data.questions.map((q) => ({ name: `Q${q.questionNumber}`, Awarded: q.effectiveMarks, Maximum: q.maxMarks }))
  const remove = async () => {
    if (!window.confirm('Delete this evaluation? The answer sheet is kept so it can be re-evaluated.')) return
    try { await api.delete(`/evaluations/${id}`); nav(-1) } catch (e) { setMsg({ error: errorMessage(e) }) }
  }

  return (
    <>
      <div className="d-flex justify-content-between flex-wrap gap-2 mb-3">
        <div>
          <h4 className="mb-0">{s.examTitle} <StatusBadge status={s.status} /></h4>
          <div className="text-muted">{s.subjectName} &middot; {s.studentName} ({s.rollNumber}) &middot; evaluated {fmtDate(s.evaluatedAt)}</div>
        </div>
        <div className="d-flex gap-2 flex-wrap align-items-start">
          <button className="btn btn-sm btn-outline-secondary" onClick={() => openFile(`/submissions/${s.submissionId}/file`).catch((e) => setMsg({ error: errorMessage(e) }))}><i className="bi bi-image me-1" />Answer sheet</button>
          {(!staff || can('REPORT_DOWNLOAD')) && <button className="btn btn-sm btn-outline-danger" onClick={() => openFile(`/evaluations/${id}/report`, { download: true, filename: `inkgrade-report-${id}.pdf` }).catch((e) => setMsg({ error: errorMessage(e) }))}><i className="bi bi-file-earmark-pdf me-1" />PDF report</button>}
          {staff && <button className="btn btn-sm btn-outline-secondary" onClick={loadHistory}><i className="bi bi-clock-history me-1" />History</button>}
          {canReview && s.status !== 'FINALIZED' && <button className="btn btn-sm btn-success" onClick={() => act(() => api.post(`/evaluations/${id}/finalize`), 'Evaluation finalized and published to the student.')}><i className="bi bi-check2-circle me-1" />Finalize &amp; publish</button>}
          {canReview && s.status === 'FINALIZED' && <button className="btn btn-sm btn-warning" onClick={() => act(() => api.post(`/evaluations/${id}/reopen`), 'Evaluation reopened (hidden from student until finalized).')}>Reopen</button>}
          {staff && can('EVALUATION_DELETE') && <button className="btn btn-sm btn-danger" onClick={remove}>Delete</button>}
        </div>
      </div>
      <Alert {...msg} onClose={() => setMsg({})} />

      <div className="row g-3 mb-3">
        <div className="col-md-4">
          <div className="card h-100"><div className="card-body text-center">
            <div className="text-muted">Total marks</div>
            <div className="display-4 fw-bold">{fmt(s.finalTotal)}<span className="fs-4 text-muted"> / {fmt(s.maxTotal)}</span></div>
            <div className="fs-5">{s.percentage}%</div>
            {staff && <div className="small text-muted mt-1">AI suggested: {fmt(s.aiTotal)} &middot; engine: {data.embeddingBackend}</div>}
            {data.reviewedBy && <div className="small text-muted">Reviewed by {data.reviewedBy}</div>}
          </div></div>
        </div>
        <div className="col-md-8">
          <div className="card h-100"><div className="card-body">
            <h6>Question-wise performance</h6>
            <div style={{ height: 220 }}>
              <ResponsiveContainer>
                <BarChart data={chart}><CartesianGrid strokeDasharray="3 3" /><XAxis dataKey="name" /><YAxis /><Tooltip /><Legend />
                  <Bar dataKey="Awarded" fill="#2ea05a" /><Bar dataKey="Maximum" fill="#c9cff0" /></BarChart>
              </ResponsiveContainer>
            </div>
          </div></div>
        </div>
      </div>

      {history && (
        <div className="card mb-3"><div className="card-body">
          <h6>Evaluation history</h6>
          <div className="table-responsive"><table className="table table-sm mb-0">
            <thead><tr><th>When</th><th>Action</th><th>Q</th><th>Old</th><th>New</th><th>By</th><th>Note</th></tr></thead>
            <tbody>{history.map((h) => (<tr key={h.id}><td>{fmtDate(h.changedAt)}</td><td>{h.action}</td><td>{h.questionNumber ?? '-'}</td><td>{fmt(h.oldMarks)}</td><td>{fmt(h.newMarks)}</td><td>{h.changedBy}</td><td className="small">{h.note}</td></tr>))}</tbody>
          </table></div>
        </div></div>
      )}

      <HighlightLegend />
      {data.questions.map((q) => (
        <QuestionCard key={q.id} q={q} staff={staff} canReview={canReview}
          onSave={(body) => act(() => api.put(`/evaluations/${id}/questions/${q.id}`, body), `Question ${q.questionNumber} updated.`)} />
      ))}
    </>
  )
}

function QuestionCard({ q, staff, canReview, onSave }) {
  const [marks, setMarks] = useState(q.effectiveMarks)
  const [comment, setComment] = useState('')
  useEffect(() => setMarks(q.effectiveMarks), [q.effectiveMarks])
  const overridden = q.finalMarks != null && q.finalMarks !== q.aiMarks
  const lang = q.mistakes
  return (
    <div className="card mb-3"><div className="card-body">
      <div className="d-flex justify-content-between flex-wrap gap-2">
        <h6 className="mb-1">Q{q.questionNumber}. {q.questionText}</h6>
        <div>
          <span className="badge text-bg-success fs-6">{fmt(q.effectiveMarks)} / {fmt(q.maxMarks)}</span>
          {staff && <span className="badge text-bg-light border ms-1" title="Marks suggested by AI">AI {fmt(q.aiMarks)}</span>}
          {overridden && <span className="badge text-bg-warning ms-1">teacher override</span>}
        </div>
      </div>
      {staff && (
        <div className="small text-muted mb-2">
          AI confidence {Math.round(q.confidence * 100)}%
          <div className="progress mt-1" style={{ height: 6, maxWidth: 220 }}><div className={`progress-bar ${q.confidence < 0.5 ? 'bg-danger' : q.confidence < 0.75 ? 'bg-warning' : 'bg-success'}`} style={{ width: `${q.confidence * 100}%` }} /></div>
          {q.confidence < 0.5 && <span className="text-danger">Low confidence - please review manually.</span>}
        </div>
      )}
      <div className="row g-3">
        <div className="col-lg-7">
          <div className="fw-semibold small mb-1">{staff ? 'Student answer (recognised text)' : 'Your answer'}</div>
          <Highlight text={q.answerText} mistakes={q.mistakes} />
        </div>
        <div className="col-lg-5">
          {q.matchedConcepts.length > 0 && <div className="mb-2"><div className="fw-semibold small">Concepts covered</div>{q.matchedConcepts.map((c) => <span key={c} className="badge text-bg-success me-1">{c}</span>)}</div>}
          {q.missingConcepts.length > 0 && <div className="mb-2"><div className="fw-semibold small">Missing concepts</div>{q.missingConcepts.map((c) => <span key={c} className="badge text-bg-danger me-1">{c}</span>)}</div>}
          {lang.length > 0 && (
            <div className="mb-2"><div className="fw-semibold small">Detected mistakes ({lang.length})</div>
              <ul className="small ps-3 mb-0">{lang.map((m) => <li key={m.id}><mark className={`m-${m.type}`}>{m.type.replace('_', ' ').toLowerCase()}</mark> {m.description}{m.suggestion && <> &rarr; <em>{m.suggestion}</em></>}</li>)}</ul>
            </div>
          )}
          {q.feedback.length > 0 && (
            <div className="mb-2"><div className="fw-semibold small">Feedback</div>
              {q.feedback.map((f) => <div key={f.id} className={`small p-2 mb-1 rounded ${f.source === 'TEACHER' ? 'bg-warning-subtle' : 'bg-primary-subtle'}`}><strong>{f.source === 'TEACHER' ? 'Teacher' : 'AI'}:</strong> {f.text}</div>)}
            </div>
          )}
        </div>
      </div>
      {canReview && (
        <form className="row g-2 mt-2 border-top pt-3" onSubmit={(e) => { e.preventDefault(); onSave({ finalMarks: Number(marks), comment: comment || null }); setComment('') }}>
          <div className="col-6 col-md-2">
            <label className="form-label small mb-0">Final marks (max {fmt(q.maxMarks)})</label>
            <input type="number" className="form-control" min="0" max={q.maxMarks} step="0.5" value={marks} onChange={(e) => setMarks(e.target.value)} required />
          </div>
          <div className="col-12 col-md-8">
            <label className="form-label small mb-0">Teacher comment (optional)</label>
            <input className="form-control" value={comment} onChange={(e) => setComment(e.target.value)} maxLength={2000} />
          </div>
          <div className="col-6 col-md-2 d-flex align-items-end"><button className="btn btn-primary w-100">Save review</button></div>
        </form>
      )}
    </div></div>
  )
}
