import { useState } from 'react'
import api, { errorMessage } from '../api'
import { useAuth } from '../auth'
import { Alert } from '../components/ui'

export default function Account() {
  const { user } = useAuth()
  const [form, setForm] = useState({ currentPassword: '', newPassword: '' })
  const [msg, setMsg] = useState({})

  const submit = async (e) => {
    e.preventDefault()
    try {
      await api.post('/auth/change-password', form)
      setMsg({ success: 'Password changed.' })
      setForm({ currentPassword: '', newPassword: '' })
    } catch (err) {
      setMsg({ error: errorMessage(err) })
    }
  }

  return (
    <div className="row g-3">
      <div className="col-md-6">
        <div className="card"><div className="card-body">
          <h5>Profile</h5>
          <dl className="row mb-0">
            <dt className="col-4">Name</dt><dd className="col-8">{user.fullName}</dd>
            <dt className="col-4">Username</dt><dd className="col-8">{user.username}</dd>
            <dt className="col-4">Email</dt><dd className="col-8">{user.email}</dd>
            <dt className="col-4">Role</dt><dd className="col-8">{user.role}</dd>
            {user.rollNumber && (<><dt className="col-4">Roll no.</dt><dd className="col-8">{user.rollNumber}</dd></>)}
          </dl>
        </div></div>
      </div>
      <div className="col-md-6">
        <form className="card" onSubmit={submit}><div className="card-body">
          <h5>Change password</h5>
          <Alert {...msg} onClose={() => setMsg({})} />
          <input type="password" className="form-control mb-2" placeholder="Current password" value={form.currentPassword}
            onChange={(e) => setForm({ ...form, currentPassword: e.target.value })} required />
          <input type="password" className="form-control mb-3" placeholder="New password (min 8 characters)" value={form.newPassword}
            onChange={(e) => setForm({ ...form, newPassword: e.target.value })} required minLength={8} />
          <button className="btn btn-primary">Update password</button>
        </div></form>
      </div>
    </div>
  )
}
