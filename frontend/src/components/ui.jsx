import { useEffect, useState, useCallback } from 'react'

export function Alert({ error, success, onClose }) {
  const msg = error || success
  if (!msg) return null
  return (
    <div className={`alert alert-${error ? 'danger' : 'success'} alert-dismissible`} role="alert">
      {msg}
      {onClose && <button type="button" className="btn-close" onClick={onClose} aria-label="Close" />}
    </div>
  )
}

export function Spinner({ text = 'Loading...' }) {
  return (
    <div className="text-center text-muted py-4">
      <div className="spinner-border spinner-border-sm me-2" role="status" />
      {text}
    </div>
  )
}

export function Pagination({ page, totalPages, onChange }) {
  if (!totalPages || totalPages <= 1) return null
  const start = Math.max(0, Math.min(page - 2, totalPages - 5))
  const pages = []
  for (let i = start; i < Math.min(totalPages, start + 5); i++) pages.push(i)
  return (
    <nav aria-label="Pagination">
      <ul className="pagination pagination-sm justify-content-center mb-0">
        <li className={`page-item ${page === 0 ? 'disabled' : ''}`}>
          <button className="page-link" onClick={() => onChange(page - 1)}>&laquo;</button>
        </li>
        {pages.map((p) => (
          <li key={p} className={`page-item ${p === page ? 'active' : ''}`}>
            <button className="page-link" onClick={() => onChange(p)}>{p + 1}</button>
          </li>
        ))}
        <li className={`page-item ${page >= totalPages - 1 ? 'disabled' : ''}`}>
          <button className="page-link" onClick={() => onChange(page + 1)}>&raquo;</button>
        </li>
      </ul>
    </nav>
  )
}

export function useDebounced(value, ms = 350) {
  const [v, setV] = useState(value)
  useEffect(() => {
    const t = setTimeout(() => setV(value), ms)
    return () => clearTimeout(t)
  }, [value, ms])
  return v
}

/** Runs an async loader whenever deps change; exposes reload(). */
export function useLoader(loader, deps) {
  const [data, setData] = useState(null)
  const [error, setError] = useState('')
  const [loading, setLoading] = useState(true)
  const [tick, setTick] = useState(0)
  // eslint-disable-next-line react-hooks/exhaustive-deps
  const stable = useCallback(loader, deps)
  useEffect(() => {
    let alive = true
    setLoading(true)
    stable()
      .then((d) => alive && (setData(d), setError('')))
      .catch((e) => alive && setError(e.message || 'Failed to load'))
      .finally(() => alive && setLoading(false))
    return () => { alive = false }
  }, [stable, tick])
  return { data, error, loading, reload: () => setTick((t) => t + 1), setData }
}

export function StatCard({ label, value, icon, color = 'primary' }) {
  return (
    <div className="col-6 col-lg-3">
      <div className="card stat-card h-100">
        <div className="card-body d-flex justify-content-between align-items-center">
          <div>
            <div className="text-muted small">{label}</div>
            <div className="display-6">{value ?? '-'}</div>
          </div>
          <i className={`bi ${icon} fs-1 text-${color} opacity-75`} />
        </div>
      </div>
    </div>
  )
}

const STATUS_COLORS = {
  UPLOADED: 'secondary', EVALUATING: 'info', EVALUATED: 'primary', FAILED: 'danger',
  AI_COMPLETED: 'primary', UNDER_REVIEW: 'warning', FINALIZED: 'success',
}
export function StatusBadge({ status }) {
  return <span className={`badge text-bg-${STATUS_COLORS[status] || 'secondary'}`}>{status?.replace('_', ' ')}</span>
}

export const fmt = (n) => (n == null ? '-' : Number.isInteger(n) ? String(n) : Number(n).toFixed(2).replace(/\.?0+$/, ''))
export const fmtDate = (s) => (s ? new Date(s).toLocaleString() : '-')
