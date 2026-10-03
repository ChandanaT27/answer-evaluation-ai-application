import { useState } from 'react'
import api, { errorMessage } from '../api'
import { Alert, Pagination, Spinner, useDebounced, useLoader } from '../components/ui'

const EMPTY = { username: '', email: '', fullName: '', password: '', role: 'STUDENT', rollNumber: '', className: '', employeeId: '', department: '' }

export default function AdminUsers() {
  const [role, setRole] = useState('')
  const [q, setQ] = useState('')
  const [page, setPage] = useState(0)
  const dq = useDebounced(q)
  const [form, setForm] = useState(null) // null = closed; object = create/edit
  const [msg, setMsg] = useState({})
  const { data, loading, reload } = useLoader(
    () => api.get('/admin/users', { params: { role: role || undefined, q: dq, page, size: 15 } }).then((r) => r.data), [role, dq, page])

  const save = async (e) => {
    e.preventDefault()
    try {
      if (form.id) await api.put(`/admin/users/${form.id}`, form)
      else await api.post('/admin/users', form)
      setMsg({ success: form.id ? 'User updated.' : 'User created.' })
      setForm(null)
      reload()
    } catch (err) {
      setMsg({ error: errorMessage(err) })
    }
  }
  const toggle = async (u) => {
    try { await api.put(`/admin/users/${u.id}`, { ...u, enabled: !u.enabled }); reload() } catch (err) { setMsg({ error: errorMessage(err) }) }
  }
  const remove = async (u) => {
    if (!window.confirm(`Delete user ${u.username}? This cannot be undone.`)) return
    try { await api.delete(`/admin/users/${u.id}`); setMsg({ success: 'User deleted.' }); reload() } catch (err) { setMsg({ error: errorMessage(err) }) }
  }
  const reset = async (u) => {
    const pw = window.prompt(`New password for ${u.username} (min 8 characters):`)
    if (!pw) return
    try { await api.post(`/admin/users/${u.id}/reset-password`, { newPassword: pw }); setMsg({ success: 'Password reset.' }) } catch (err) { setMsg({ error: errorMessage(err) }) }
  }
  const set = (k) => (e) => setForm({ ...form, [k]: e.target.value })

  return (
    <>
      <div className="d-flex justify-content-between flex-wrap gap-2 mb-3">
        <h4>Students &amp; teachers</h4>
        <button className="btn btn-primary" onClick={() => setForm({ ...EMPTY })}><i className="bi bi-plus-lg me-1" />New user</button>
      </div>
      <Alert {...msg} onClose={() => setMsg({})} />
      {form && (
        <form className="card mb-3" onSubmit={save}><div className="card-body">
          <h6>{form.id ? `Edit ${form.username}` : 'Create user'}</h6>
          <div className="row g-2">
            {!form.id && <div className="col-md-4"><input className="form-control" placeholder="Username" value={form.username} onChange={set('username')} required minLength={3} /></div>}
            <div className="col-md-4"><input className="form-control" placeholder="Full name" value={form.fullName} onChange={set('fullName')} required /></div>
            <div className="col-md-4"><input type="email" className="form-control" placeholder="Email" value={form.email} onChange={set('email')} required /></div>
            {!form.id && <div className="col-md-4"><input type="password" className="form-control" placeholder="Password (min 8)" value={form.password} onChange={set('password')} required minLength={8} /></div>}
            {!form.id && (
              <div className="col-md-4">
                <select className="form-select" value={form.role} onChange={set('role')}>
                  <option value="STUDENT">Student</option><option value="TEACHER">Teacher</option><option value="ADMIN">Administrator</option>
                </select>
              </div>
            )}
            {form.role === 'STUDENT' && (<>
              <div className="col-md-4"><input className="form-control" placeholder="Roll number" value={form.rollNumber || ''} onChange={set('rollNumber')} required /></div>
              <div className="col-md-4"><input className="form-control" placeholder="Class" value={form.className || ''} onChange={set('className')} /></div>
            </>)}
            {form.role === 'TEACHER' && (<>
              <div className="col-md-4"><input className="form-control" placeholder="Employee ID" value={form.employeeId || ''} onChange={set('employeeId')} /></div>
              <div className="col-md-4"><input className="form-control" placeholder="Department" value={form.department || ''} onChange={set('department')} /></div>
            </>)}
          </div>
          <div className="mt-3 d-flex gap-2">
            <button className="btn btn-primary">Save</button>
            <button type="button" className="btn btn-outline-secondary" onClick={() => setForm(null)}>Cancel</button>
          </div>
        </div></form>
      )}
      <div className="row g-2 mb-3">
        <div className="col-sm-4"><input className="form-control" placeholder="Search name / username / email" value={q} onChange={(e) => { setQ(e.target.value); setPage(0) }} /></div>
        <div className="col-sm-3">
          <select className="form-select" value={role} onChange={(e) => { setRole(e.target.value); setPage(0) }}>
            <option value="">All roles</option><option value="STUDENT">Students</option><option value="TEACHER">Teachers</option><option value="ADMIN">Admins</option>
          </select>
        </div>
      </div>
      <div className="card"><div className="table-responsive">
        <table className="table table-hover align-middle mb-0">
          <thead><tr><th>Name</th><th>Username</th><th>Role</th><th>Details</th><th>Status</th><th className="text-end">Actions</th></tr></thead>
          <tbody>
            {data?.content.map((u) => (
              <tr key={u.id}>
                <td>{u.fullName}<div className="small text-muted">{u.email}</div></td>
                <td>{u.username}</td><td><span className="badge text-bg-secondary">{u.role}</span></td>
                <td className="small">{u.rollNumber ? `Roll ${u.rollNumber} ${u.className || ''}` : [u.employeeId, u.department].filter(Boolean).join(' / ')}</td>
                <td>{u.enabled ? <span className="badge text-bg-success">Active</span> : <span className="badge text-bg-danger">Disabled</span>}</td>
                <td className="text-end text-nowrap">
                  <button className="btn btn-sm btn-outline-primary me-1" onClick={() => setForm({ ...u })}>Edit</button>
                  <button className="btn btn-sm btn-outline-secondary me-1" onClick={() => toggle(u)}>{u.enabled ? 'Disable' : 'Enable'}</button>
                  <button className="btn btn-sm btn-outline-secondary me-1" onClick={() => reset(u)}>Reset pw</button>
                  <button className="btn btn-sm btn-outline-danger" onClick={() => remove(u)}>Delete</button>
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
