import { useEffect, useState } from 'react'
import api, { errorMessage } from '../api'
import { Alert, Spinner, useLoader } from '../components/ui'

const DESCRIPTIONS = {
  EXAM_MANAGE: 'Create/edit exams, questions and blueprints',
  SUBJECT_MANAGE: 'Create/edit subjects',
  SUBMISSION_UPLOAD: 'Upload and manage answer sheets',
  EVALUATION_RUN: 'Start AI evaluation',
  EVALUATION_REVIEW: 'Review, override marks and finalize',
  EVALUATION_DELETE: 'Delete evaluations',
  REPORT_DOWNLOAD: 'Download PDF reports',
}

export default function AdminPermissions() {
  const { data: perms } = useLoader(() => api.get('/admin/permissions').then((r) => r.data), [])
  const { data: roles, loading, reload } = useLoader(() => api.get('/admin/roles').then((r) => r.data), [])
  const [selected, setSelected] = useState({})
  const [msg, setMsg] = useState({})

  useEffect(() => {
    if (roles) setSelected(Object.fromEntries(roles.map((r) => [r.id, new Set(r.permissions)])))
  }, [roles])

  if (loading || !perms) return <Spinner />

  const toggle = (id, p) => {
    const s = new Set(selected[id])
    s.has(p) ? s.delete(p) : s.add(p)
    setSelected({ ...selected, [id]: s })
  }
  const save = async (role) => {
    try {
      await api.put(`/admin/roles/${role.id}/permissions`, { permissions: [...selected[role.id]] })
      setMsg({ success: `${role.name} permissions saved. Changes apply to the next request of each user.` })
      reload()
    } catch (e) {
      setMsg({ error: errorMessage(e) })
    }
  }
  return (
    <>
      <h4 className="mb-3">Roles &amp; permissions</h4>
      <Alert {...msg} onClose={() => setMsg({})} />
      <div className="row g-3">
        {roles.map((r) => {
          const editable = r.name === 'TEACHER'
          return (
            <div className="col-lg-4" key={r.id}>
              <div className="card h-100"><div className="card-body">
                <h5>{r.name}</h5>
                {r.name === 'STUDENT' && <p className="text-muted small">Students can only view their own published results.</p>}
                {r.name === 'ADMIN' && <p className="text-muted small">Administrators always hold every permission.</p>}
                {(editable || r.name === 'ADMIN') && [...perms].sort().map((p) => (
                  <div className="form-check" key={p}>
                    <input className="form-check-input" type="checkbox" id={`${r.id}-${p}`} disabled={!editable}
                      checked={selected[r.id]?.has(p) || false} onChange={() => toggle(r.id, p)} />
                    <label className="form-check-label" htmlFor={`${r.id}-${p}`}>
                      <strong>{p}</strong><br /><small className="text-muted">{DESCRIPTIONS[p]}</small>
                    </label>
                  </div>
                ))}
                {editable && <button className="btn btn-primary btn-sm mt-3" onClick={() => save(r)}>Save permissions</button>}
              </div></div>
            </div>
          )
        })}
      </div>
    </>
  )
}
