import { useState } from 'react'
import api from '../api'
import { Alert, Pagination, Spinner, fmtDate, useDebounced, useLoader } from '../components/ui'

export default function AdminAudit() {
  const [q, setQ] = useState('')
  const [page, setPage] = useState(0)
  const dq = useDebounced(q)
  const { data, loading, error } = useLoader(
    () => api.get('/admin/audit-logs', { params: { q: dq, page, size: 25 } }).then((r) => r.data), [dq, page])
  return (
    <>
      <div className="d-flex justify-content-between flex-wrap gap-2 mb-3">
        <h4>Audit logs</h4>
        <input className="form-control" style={{ maxWidth: 280 }} placeholder="Search user / action / entity" value={q}
          onChange={(e) => { setQ(e.target.value); setPage(0) }} />
      </div>
      <Alert error={error} />
      <div className="card"><div className="table-responsive">
        <table className="table table-sm table-hover mb-0">
          <thead><tr><th>Time</th><th>User</th><th>Action</th><th>Entity</th><th>Details</th><th>IP</th></tr></thead>
          <tbody>
            {data?.content.map((a) => (
              <tr key={a.id}><td className="text-nowrap">{fmtDate(a.createdAt)}</td><td>{a.username || '-'}</td>
                <td><span className="badge text-bg-light border">{a.action}</span></td>
                <td>{a.entityType}{a.entityId ? ` #${a.entityId}` : ''}</td><td className="small">{a.details}</td><td className="small">{a.ipAddress}</td></tr>
            ))}
          </tbody>
        </table>
      </div></div>
      {loading && <Spinner />}
      <div className="mt-3"><Pagination page={page} totalPages={data?.totalPages} onChange={setPage} /></div>
    </>
  )
}
