import { useState } from 'react'
import { Navigate, useNavigate } from 'react-router-dom'
import { useAuth } from '../auth'
import { errorMessage } from '../api'
import { Alert } from '../components/ui'

export default function Login() {
  const { user, login } = useAuth()
  const nav = useNavigate()
  const [username, setUsername] = useState('')
  const [password, setPassword] = useState('')
  const [error, setError] = useState('')
  const [busy, setBusy] = useState(false)

  if (user) return <Navigate to="/" replace />

  const submit = async (e) => {
    e.preventDefault()
    setBusy(true)
    setError('')
    try {
      await login(username.trim(), password)
      nav('/')
    } catch (err) {
      setError(errorMessage(err))
    } finally {
      setBusy(false)
    }
  }

  return (
    <div className="min-vh-100 d-flex align-items-center justify-content-center" style={{ background: 'linear-gradient(135deg,#1f2547,#3a4180)' }}>
      <form className="card p-4" style={{ width: 380, maxWidth: '92vw' }} onSubmit={submit}>
        <h3 className="brand text-center mb-1"><i className="bi bi-pen me-2" />InkGrade AI</h3>
        <p className="text-center text-muted small mb-4">AI handwritten answer evaluation</p>
        <Alert error={error} />
        <label className="form-label" htmlFor="username">Username</label>
        <input id="username" className="form-control mb-3" value={username} onChange={(e) => setUsername(e.target.value)} autoFocus required />
        <label className="form-label" htmlFor="password">Password</label>
        <input id="password" type="password" className="form-control mb-4" value={password} onChange={(e) => setPassword(e.target.value)} required />
        <button className="btn btn-primary w-100" disabled={busy}>{busy ? 'Signing in...' : 'Sign in'}</button>
      </form>
    </div>
  )
}
