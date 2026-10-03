import { useEffect, useRef, useState } from 'react'
import { Link, useParams } from 'react-router-dom'
import api, { errorMessage, openFile } from '../api'
import { useAuth } from '../auth'
import { Alert, Spinner, StatusBadge, fmt, fmtDate, useDebounced, useLoader } from '../components/ui'

const ACCEPT = '.pdf,.png,.jpg,.jpeg,.tif,.tiff,.bmp,.txt'

export default function ExamDetail() {
  const { id } = useParams()
  const { can } = useAuth()
  const { data: exam, loading, error, reload } = useLoader(() => api.get(`/exams/${id}`).then((r) => r.data), [id])
  const [msg, setMsg] = useState({})
  const paperRef = useRef()

  if (loading && !exam) return <Spinner />
  if (error) return <Alert error={error} />

  const uploadPaper = async (e) => {
    const file = e.target.files[0]
    if (!file) return
    const fd = new FormData()
    fd.append('file', file)
    try { await api.post(`/exams/${id}/question-paper`, fd); setMsg({ success: 'Question paper uploaded.' }); reload() } catch (err) { setMsg({ error: errorMessage(err) }) }
    e.target.value = ''
  }

  return (
    <>
      <Link to="/teacher/exams" className="small">&larr; All exams</Link>
      <div className="d-flex justify-content-between flex-wrap align-items-start mt-1 mb-3">
        <div>
          <h4 className="mb-0">{exam.title}</h4>
          <div className="text-muted">{exam.subjectName} &middot; {exam.examDate || 'no date'} &middot; {fmt(exam.totalMarks)} marks &middot; {exam.questionCount} questions</div>
          {exam.instructions && <div className="small mt-1">{exam.instructions}</div>}
        </div>
        <div className="d-flex gap-2 align-items-center">
          {exam.hasQuestionPaper && <button className="btn btn-sm btn-outline-secondary" onClick={() => openFile(`/exams/${id}/question-paper`).catch((e) => setMsg({ error: errorMessage(e) }))}><i className="bi bi-file-earmark-text me-1" />{exam.questionPaperName}</button>}
          {can('EXAM_MANAGE') && (<>
            <input ref={paperRef} type="file" accept={ACCEPT} hidden onChange={uploadPaper} />
            <button className="btn btn-sm btn-outline-primary" onClick={() => paperRef.current.click()}><i className="bi bi-upload me-1" />{exam.hasQuestionPaper ? 'Replace' : 'Upload'} question paper</button>
          </>)}
        </div>
      </div>
      <Alert {...msg} onClose={() => setMsg({})} />
      <Questions examId={id} onChange={reload} />
      {can('SUBMISSION_UPLOAD') && <Submissions examId={id} />}
    </>
  )
}

function Questions({ examId, onChange }) {
  const { can } = useAuth()
  const { data: questions, loading, reload } = useLoader(() => api.get(`/exams/${examId}/questions`).then((r) => r.data), [examId])
  const [form, setForm] = useState(null)
  const [openBp, setOpenBp] = useState(null)
  const [msg, setMsg] = useState({})
  const manage = can('EXAM_MANAGE')

  const save = async (e) => {
    e.preventDefault()
    const body = { number: form.number ? Number(form.number) : null, text: form.text, maxMarks: Number(form.maxMarks) }
    try {
      if (form.id) await api.put(`/questions/${form.id}`, body)
      else await api.post(`/exams/${examId}/questions`, body)
      setForm(null)
      reload(); onChange()
    } catch (err) { setMsg({ error: errorMessage(err) }) }
  }
  const remove = async (q) => {
    if (!window.confirm(`Delete question ${q.number}?`)) return
    try { await api.delete(`/questions/${q.id}`); reload(); onChange() } catch (err) { setMsg({ error: errorMessage(err) }) }
  }
  const set = (k) => (e) => setForm({ ...form, [k]: e.target.value })

  return (
    <div className="card mb-4"><div className="card-body">
      <div className="d-flex justify-content-between mb-2">
        <h5 className="mb-0">Questions &amp; blueprints</h5>
        {manage && <button className="btn btn-sm btn-primary" onClick={() => setForm({ number: '', text: '', maxMarks: '' })}><i className="bi bi-plus-lg me-1" />Add question</button>}
      </div>
      <Alert {...msg} onClose={() => setMsg({})} />
      {form && (
        <form className="border rounded p-3 mb-3 bg-light" onSubmit={save}>
          <div className="row g-2">
            <div className="col-md-2"><input type="number" min="1" className="form-control" placeholder="Q no. (auto)" value={form.number} onChange={set('number')} /></div>
            <div className="col-md-2"><input type="number" step="0.5" min="0.5" className="form-control" placeholder="Max marks" value={form.maxMarks} onChange={set('maxMarks')} required /></div>
            <div className="col-md-8"><textarea className="form-control" rows={2} placeholder="Question text" value={form.text} onChange={set('text')} required /></div>
          </div>
          <div className="mt-2 d-flex gap-2">
            <button className="btn btn-primary btn-sm">Save</button>
            <button type="button" className="btn btn-outline-secondary btn-sm" onClick={() => setForm(null)}>Cancel</button>
          </div>
        </form>
      )}
      {loading && !questions && <Spinner />}
      {questions?.length === 0 && <div className="text-muted">No questions yet. Add the exam's questions with their marks.</div>}
      {questions?.map((q) => (
        <div key={q.id} className="border rounded mb-2">
          <div className="d-flex justify-content-between align-items-start p-2 gap-2 flex-wrap">
            <div><strong>Q{q.number}.</strong> {q.text} <span className="badge text-bg-info ms-1">{fmt(q.maxMarks)} marks</span>
              {q.hasBlueprint ? <span className="badge text-bg-success ms-1">blueprint ready</span> : <span className="badge text-bg-warning ms-1">no blueprint</span>}</div>
            <div className="text-nowrap">
              <button className="btn btn-sm btn-outline-primary me-1" onClick={() => setOpenBp(openBp === q.id ? null : q.id)}>Blueprint</button>
              {manage && <button className="btn btn-sm btn-outline-secondary me-1" onClick={() => setForm({ id: q.id, number: q.number, text: q.text, maxMarks: q.maxMarks })}>Edit</button>}
              {manage && <button className="btn btn-sm btn-outline-danger" onClick={() => remove(q)}>Delete</button>}
            </div>
          </div>
          {openBp === q.id && <BlueprintEditor questionId={q.id} onSaved={reload} />}
        </div>
      ))}
    </div></div>
  )
}

function BlueprintEditor({ questionId, onSaved }) {
  const { data, loading } = useLoader(() => api.get(`/questions/${questionId}/blueprint`).then((r) => r.data), [questionId])
  const [model, setModel] = useState('')
  const [concepts, setConcepts] = useState([])
  const [msg, setMsg] = useState({})
  const [busy, setBusy] = useState(false)
  const fileRef = useRef()

  useEffect(() => {
    if (data) {
      setModel(data.modelAnswer || '')
      setConcepts(data.concepts.map((c) => ({ name: c.name, keywords: c.keywords.join(', '), weight: c.weight })))
    }
  }, [data])

  const apply = (bp) => {
    setModel(bp.modelAnswer || '')
    setConcepts(bp.concepts.map((c) => ({ name: c.name, keywords: c.keywords.join(', '), weight: c.weight })))
  }
  const upload = async (e) => {
    const file = e.target.files[0]
    if (!file) return
    const fd = new FormData()
    fd.append('file', file)
    setBusy(true)
    try {
      const r = await api.post(`/questions/${questionId}/blueprint/upload`, fd)
      apply(r.data)
      setMsg({ success: 'Text extracted from the file and saved as the model answer. Add concepts below for better evaluation.' })
      onSaved()
    } catch (err) { setMsg({ error: errorMessage(err) }) } finally { setBusy(false); e.target.value = '' }
  }
  const save = async () => {
    const body = {
      modelAnswer: model,
      concepts: concepts.filter((c) => c.name.trim()).map((c) => ({
        name: c.name.trim(), keywords: c.keywords.split(',').map((k) => k.trim()).filter(Boolean), weight: Number(c.weight) || 1,
      })),
    }
    setBusy(true)
    try { const r = await api.put(`/questions/${questionId}/blueprint`, body); apply(r.data); setMsg({ success: 'Blueprint saved.' }); onSaved() } catch (err) { setMsg({ error: errorMessage(err) }) } finally { setBusy(false) }
  }
  const upd = (i, k, v) => setConcepts(concepts.map((c, j) => (j === i ? { ...c, [k]: v } : c)))

  if (loading) return <div className="p-2"><Spinner /></div>
  return (
    <div className="border-top p-3 bg-light">
      <Alert {...msg} onClose={() => setMsg({})} />
      <div className="d-flex justify-content-between mb-1">
        <label className="form-label fw-semibold mb-0">Model answer</label>
        <div>
          <input ref={fileRef} type="file" accept={ACCEPT} hidden onChange={upload} />
          <button className="btn btn-sm btn-outline-secondary" disabled={busy} onClick={() => fileRef.current.click()}><i className="bi bi-upload me-1" />Upload model answer file (OCR)</button>
        </div>
      </div>
      <textarea className="form-control mb-3" rows={4} value={model} onChange={(e) => setModel(e.target.value)} placeholder="Type or upload the ideal answer" />
      <label className="form-label fw-semibold">Key concepts <span className="text-muted fw-normal small">(name, synonyms/alternative phrasing, weight)</span></label>
      {concepts.map((c, i) => (
        <div className="row g-2 mb-2" key={i}>
          <div className="col-md-3"><input className="form-control form-control-sm" placeholder="Concept" value={c.name} onChange={(e) => upd(i, 'name', e.target.value)} /></div>
          <div className="col-md-6"><input className="form-control form-control-sm" placeholder="Synonyms, comma separated" value={c.keywords} onChange={(e) => upd(i, 'keywords', e.target.value)} /></div>
          <div className="col-6 col-md-1"><input type="number" min="0.1" step="0.1" className="form-control form-control-sm" value={c.weight} onChange={(e) => upd(i, 'weight', e.target.value)} /></div>
          <div className="col-6 col-md-2"><button className="btn btn-sm btn-outline-danger" onClick={() => setConcepts(concepts.filter((_, j) => j !== i))}>Remove</button></div>
        </div>
      ))}
      <div className="d-flex gap-2">
        <button className="btn btn-sm btn-outline-primary" onClick={() => setConcepts([...concepts, { name: '', keywords: '', weight: 1 }])}>+ Add concept</button>
        <button className="btn btn-sm btn-primary" disabled={busy} onClick={save}>Save blueprint</button>
      </div>
    </div>
  )
}

function Submissions({ examId }) {
  const { can } = useAuth()
  const { data: subs, reload } = useLoader(() => api.get(`/exams/${examId}/submissions`).then((r) => r.data), [examId])
  const [q, setQ] = useState('')
  const dq = useDebounced(q)
  const { data: students } = useLoader(() => api.get('/students', { params: { q: dq, size: 20 } }).then((r) => r.data.content), [dq])
  const [studentId, setStudentId] = useState('')
  const [file, setFile] = useState(null)
  const [msg, setMsg] = useState({})
  const [busy, setBusy] = useState(false)
  const fileRef = useRef()

  // poll while something is being evaluated
  useEffect(() => {
    if (!subs?.some((s) => s.status === 'EVALUATING')) return undefined
    const t = setInterval(reload, 2500)
    return () => clearInterval(t)
  }, [subs])

  const upload = async (e) => {
    e.preventDefault()
    const fd = new FormData()
    fd.append('studentId', studentId)
    fd.append('file', file)
    setBusy(true)
    try {
      await api.post(`/exams/${examId}/submissions`, fd)
      setMsg({ success: 'Answer sheet uploaded.' })
      setFile(null); setStudentId(''); fileRef.current.value = ''
      reload()
    } catch (err) { setMsg({ error: errorMessage(err) }) } finally { setBusy(false) }
  }
  const evaluate = async (s) => {
    try { await api.post(`/submissions/${s.id}/evaluate`); setMsg({ success: 'AI evaluation started.' }); reload() } catch (err) { setMsg({ error: errorMessage(err) }) }
  }
  const remove = async (s) => {
    if (!window.confirm(`Delete the answer sheet of ${s.studentName} (and its evaluation)?`)) return
    try { await api.delete(`/submissions/${s.id}`); reload() } catch (err) { setMsg({ error: errorMessage(err) }) }
  }

  return (
    <div className="card"><div className="card-body">
      <h5>Student answer sheets</h5>
      <Alert {...msg} onClose={() => setMsg({})} />
      <form className="row g-2 mb-3" onSubmit={upload}>
        <div className="col-md-3"><input className="form-control" placeholder="Find student (name / roll no.)" value={q} onChange={(e) => setQ(e.target.value)} /></div>
        <div className="col-md-3">
          <select className="form-select" value={studentId} onChange={(e) => setStudentId(e.target.value)} required>
            <option value="" disabled>Select student</option>
            {students?.map((s) => <option key={s.id} value={s.id}>{s.rollNumber} - {s.fullName}</option>)}
          </select>
        </div>
        <div className="col-md-4"><input ref={fileRef} type="file" className="form-control" accept={ACCEPT} onChange={(e) => setFile(e.target.files[0])} required /></div>
        <div className="col-md-2"><button className="btn btn-primary w-100" disabled={busy || !file || !studentId}>{busy ? 'Uploading...' : 'Upload'}</button></div>
      </form>
      <div className="table-responsive">
        <table className="table align-middle">
          <thead><tr><th>Student</th><th>File</th><th>Uploaded</th><th>Status</th><th className="text-end">Actions</th></tr></thead>
          <tbody>
            {subs?.length === 0 && <tr><td colSpan={5} className="text-muted">No answer sheets uploaded yet.</td></tr>}
            {subs?.map((s) => (
              <tr key={s.id}>
                <td>{s.studentName}<div className="small text-muted">{s.rollNumber}</div></td>
                <td className="small">{s.fileName}</td><td className="small">{fmtDate(s.uploadedAt)}</td>
                <td><StatusBadge status={s.status} />{s.errorMessage && <div className="small text-danger">{s.errorMessage}</div>}</td>
                <td className="text-end text-nowrap">
                  <button className="btn btn-sm btn-outline-secondary me-1" onClick={() => openFile(`/submissions/${s.id}/file`).catch((e) => setMsg({ error: errorMessage(e) }))}>View sheet</button>
                  {can('EVALUATION_RUN') && (
                    <button className="btn btn-sm btn-primary me-1" disabled={s.status === 'EVALUATING'} onClick={() => evaluate(s)}>
                      {s.status === 'EVALUATING' ? 'Evaluating...' : s.evaluationId ? 'Re-evaluate' : 'Start AI evaluation'}
                    </button>
                  )}
                  {s.evaluationId && <Link className="btn btn-sm btn-outline-success me-1" to={`/evaluations/${s.evaluationId}`}>Review</Link>}
                  <button className="btn btn-sm btn-outline-danger" onClick={() => remove(s)}>Delete</button>
                </td>
              </tr>
            ))}
          </tbody>
        </table>
      </div>
    </div></div>
  )
}
