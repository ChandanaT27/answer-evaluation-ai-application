import { useState } from 'react'
import { Link } from 'react-router-dom'
import api, { errorMessage } from '../api'
import { useAuth } from '../auth'
import { Alert, Pagination, Spinner, fmt, useDebounced, useLoader } from '../components/ui'

export default function Exams() {
  const { can } = useAuth()
  const [q, setQ] = useState('')
  const [subjectId, setSubjectId] = useState('')
  const [page, setPage] = useState(0)
  const dq = useDebounced(q)
  const [form, setForm] = useState(null)
  const [msg, setMsg] = useState({})
  const { data: subjects } = useLoader(() => api.get('/subjects', { params: { activeOnly: true, size: 200 } }).then((r) => r.data.content), [])
  const { data, loading, reload } = useLoader(
    () => api.get('/exams', { params: { q: dq, subjectId: subjectId || undefined, page, size: 12 } }).then((r) => r.data), [dq, subjectId, page])

  const save = async (e) => {
    e.preventDefault()
    try {
      await api.post('/exams', { ...form, subjectId: Number(form.subjectId), examDate: form.examDate || null })
      setMsg({ success: 'Exam created. Open it to add questions and blueprints.' })
      setForm(null)
      reload()
    } catch (err) { setMsg({ error: errorMessage(err) }) }
  }
  const remove = async (x) => {
    if (!window.confirm(`Delete exam "${x.title}" with all its questions, answer sheets and evaluations?`)) return
    try { await api.delete(`/exams/${x.id}`); reload() } catch (err) { setMsg({ error: errorMessage(err) }) }
  }
  const set = (k) => (e) => setForm({ ...form, [k]: e.target.value })

  return (
    <>
      <div className="d-flex justify-content-between flex-wrap gap-2 mb-3">
        <h4>Exams</h4>
        {can('EXAM_MANAGE') && <button className="btn btn-primary" onClick={() => setForm({ title: '', subjectId: subjects?.[0]?.id || '', examDate: '', instructions: '' })}><i className="bi bi-plus-lg me-1" />New exam</button>}
      </div>
      <Alert {...msg} onClose={() => setMsg({})} />
      {form && (
        <form className="card mb-3" onSubmit={save}><div className="card-body">
          <div className="row g-2">
            <div className="col-md-4"><input className="form-control" placeholder="Exam title" value={form.title} onChange={set('title')} required /></div>
            <div className="col-md-3">
              <select className="form-select" value={form.subjectId} onChange={set('subjectId')} required>
                <option value="" disabled>Select subject</option>
                {subjects?.map((s) => <option key={s.id} value={s.id}>{s.code} - {s.name}</option>)}
              </select>
            </div>
            <div className="col-md-2"><input type="date" className="form-control" value={form.examDate} onChange={set('examDate')} /></div>
            <div className="col-md-12"><input className="form-control" placeholder="Instructions (optional)" value={form.instructions} onChange={set('instructions')} /></div>
          </div>
          {subjects?.length === 0 && <div className="text-warning small mt-2">No subjects yet - create one under Subjects first.</div>}
          <div className="mt-3 d-flex gap-2">
            <button className="btn btn-primary">Create</button>
            <button type="button" className="btn btn-outline-secondary" onClick={() => setForm(null)}>Cancel</button>
          </div>
        </div></form>
      )}
      <div className="row g-2 mb-3">
        <div className="col-sm-4"><input className="form-control" placeholder="Search exams" value={q} onChange={(e) => { setQ(e.target.value); setPage(0) }} /></div>
        <div className="col-sm-3">
          <select className="form-select" value={subjectId} onChange={(e) => { setSubjectId(e.target.value); setPage(0) }}>
            <option value="">All subjects</option>
            {subjects?.map((s) => <option key={s.id} value={s.id}>{s.name}</option>)}
          </select>
        </div>
      </div>
      <div className="card"><div className="table-responsive">
        <table className="table table-hover align-middle mb-0">
          <thead><tr><th>Title</th><th>Subject</th><th>Date</th><th>Questions</th><th>Total marks</th><th /></tr></thead>
          <tbody>
            {data?.content.map((x) => (
              <tr key={x.id}>
                <td><Link to={`/teacher/exams/${x.id}`}>{x.title}</Link></td><td>{x.subjectName}</td><td>{x.examDate || '-'}</td>
                <td>{x.questionCount}</td><td>{fmt(x.totalMarks)}</td>
                <td className="text-end text-nowrap">
                  <Link className="btn btn-sm btn-outline-primary me-1" to={`/teacher/exams/${x.id}`}>Open</Link>
                  {can('EXAM_MANAGE') && <button className="btn btn-sm btn-outline-danger" onClick={() => remove(x)}>Delete</button>}
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
