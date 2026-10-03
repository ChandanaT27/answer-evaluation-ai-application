import { useState } from 'react'
import api, { errorMessage } from '../api'
import { useAuth } from '../auth'
import { Alert, Pagination, Spinner, useDebounced, useLoader } from '../components/ui'

const EMPTY = { name: '', code: '', description: '', active: true }

export default function Subjects() {
  const { can } = useAuth()
  const [q, setQ] = useState('')
  const [page, setPage] = useState(0)
  const dq = useDebounced(q)
  const [form, setForm] = useState(null)
  const [msg, setMsg] = useState({})
  const { data, loading, reload } = useLoader(
    () => api.get('/subjects', { params: { q: dq, page, size: 12 } }).then((r) => r.data), [dq, page])
  const manage = can('SUBJECT_MANAGE')

  const save = async (e) => {
    e.preventDefault()
    try {
      if (form.id) await api.put(`/subjects/${form.id}`, form)
      else await api.post('/subjects', form)
      setMsg({ success: 'Subject saved.' })
      setForm(null)
      reload()
    } catch (err) { setMsg({ error: errorMessage(err) }) }
  }
  const remove = async (s) => {
    if (!window.confirm(`Delete subject ${s.name}?`)) return
    try { await api.delete(`/subjects/${s.id}`); reload() } catch (err) { setMsg({ error: errorMessage(err) }) }
  }
  const set = (k) => (e) => setForm({ ...form, [k]: e.target.value })

  return (
    <>
      <div className="d-flex justify-content-between flex-wrap gap-2 mb-3">
        <h4>Subjects</h4>
        {manage && <button className="btn btn-primary" onClick={() => setForm({ ...EMPTY })}><i className="bi bi-plus-lg me-1" />New subject</button>}
      </div>
      <Alert {...msg} onClose={() => setMsg({})} />
      {form && (
        <form className="card mb-3" onSubmit={save}><div className="card-body">
          <div className="row g-2">
            <div className="col-md-4"><input className="form-control" placeholder="Name" value={form.name} onChange={set('name')} required /></div>
            <div className="col-md-3"><input className="form-control" placeholder="Code (e.g. BIO101)" value={form.code} onChange={set('code')} required pattern="[A-Za-z0-9_-]+" /></div>
            <div className="col-md-5"><input className="form-control" placeholder="Description" value={form.description || ''} onChange={set('description')} /></div>
            <div className="col-12 form-check ms-2">
              <input id="active" type="checkbox" className="form-check-input" checked={form.active} onChange={(e) => setForm({ ...form, active: e.target.checked })} />
              <label htmlFor="active" className="form-check-label">Active</label>
            </div>
          </div>
          <div className="mt-3 d-flex gap-2">
            <button className="btn btn-primary">Save</button>
            <button type="button" className="btn btn-outline-secondary" onClick={() => setForm(null)}>Cancel</button>
          </div>
        </div></form>
      )}
      <input className="form-control mb-3" style={{ maxWidth: 320 }} placeholder="Search subjects" value={q} onChange={(e) => { setQ(e.target.value); setPage(0) }} />
      <div className="card"><div className="table-responsive">
        <table className="table table-hover align-middle mb-0">
          <thead><tr><th>Code</th><th>Name</th><th>Description</th><th>Exams</th><th>Status</th>{manage && <th />}</tr></thead>
          <tbody>
            {data?.content.map((s) => (
              <tr key={s.id}>
                <td><strong>{s.code}</strong></td><td>{s.name}</td><td className="small text-muted">{s.description}</td><td>{s.examCount}</td>
                <td>{s.active ? <span className="badge text-bg-success">Active</span> : <span className="badge text-bg-secondary">Inactive</span>}</td>
                {manage && (
                  <td className="text-end text-nowrap">
                    <button className="btn btn-sm btn-outline-primary me-1" onClick={() => setForm({ ...s })}>Edit</button>
                    <button className="btn btn-sm btn-outline-danger" onClick={() => remove(s)}>Delete</button>
                  </td>
                )}
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
