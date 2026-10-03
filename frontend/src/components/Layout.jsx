import { NavLink, Outlet, useNavigate } from 'react-router-dom'
import { useAuth } from '../auth'

const NAV = {
  ADMIN: [
    ['/admin', 'bi-speedometer2', 'Dashboard'],
    ['/admin/users', 'bi-people', 'Users'],
    ['/admin/subjects', 'bi-journal-bookmark', 'Subjects'],
    ['/admin/permissions', 'bi-shield-lock', 'Permissions'],
    ['/admin/evaluations', 'bi-clipboard-data', 'Evaluations'],
    ['/admin/audit', 'bi-list-check', 'Audit logs'],
  ],
  TEACHER: [
    ['/teacher', 'bi-speedometer2', 'Dashboard'],
    ['/teacher/subjects', 'bi-journal-bookmark', 'Subjects'],
    ['/teacher/exams', 'bi-file-earmark-text', 'Exams'],
    ['/teacher/evaluations', 'bi-clipboard-check', 'Evaluations'],
  ],
  STUDENT: [
    ['/student', 'bi-graph-up', 'My performance'],
    ['/student/results', 'bi-card-checklist', 'My results'],
  ],
}

export default function Layout() {
  const { user, logout } = useAuth()
  const nav = useNavigate()
  const items = NAV[user.role] || []
  return (
    <>
      <nav className="navbar navbar-dark bg-dark px-3">
        <span className="navbar-brand brand"><i className="bi bi-pen me-2" />InkGrade AI</span>
        <div className="d-flex align-items-center text-light gap-3">
          <span className="small d-none d-sm-inline">{user.fullName} <span className="badge text-bg-secondary">{user.role}</span></span>
          <NavLink to="/account" className="btn btn-sm btn-outline-light">Account</NavLink>
          <button className="btn btn-sm btn-outline-light" onClick={() => { logout(); nav('/login') }}>Logout</button>
        </div>
      </nav>
      <div className="container-fluid">
        <div className="row">
          <aside className="col-12 col-md-3 col-lg-2 sidebar p-2">
            <ul className="nav nav-pills flex-md-column flex-row flex-wrap">
              {items.map(([to, icon, label]) => (
                <li className="nav-item" key={to}>
                  <NavLink end to={to} className="nav-link"><i className={`bi ${icon} me-2`} />{label}</NavLink>
                </li>
              ))}
            </ul>
          </aside>
          <main className="col-12 col-md-9 col-lg-10 p-3 p-md-4"><Outlet /></main>
        </div>
      </div>
    </>
  )
}
