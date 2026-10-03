import { Navigate, Route, Routes } from 'react-router-dom'
import { useAuth } from './auth'
import Layout from './components/Layout'
import { Spinner } from './components/ui'
import Login from './pages/Login'
import Account from './pages/Account'
import AdminDashboard from './pages/AdminDashboard'
import AdminUsers from './pages/AdminUsers'
import AdminPermissions from './pages/AdminPermissions'
import AdminAudit from './pages/AdminAudit'
import Subjects from './pages/Subjects'
import TeacherDashboard from './pages/TeacherDashboard'
import Exams from './pages/Exams'
import ExamDetail from './pages/ExamDetail'
import Evaluations from './pages/Evaluations'
import EvaluationDetail from './pages/EvaluationDetail'
import StudentDashboard from './pages/StudentDashboard'
import StudentResults from './pages/StudentResults'

const HOME = { ADMIN: '/admin', TEACHER: '/teacher', STUDENT: '/student' }

function Protected({ roles, children }) {
  const { user, loading } = useAuth()
  if (loading) return <Spinner />
  if (!user) return <Navigate to="/login" replace />
  if (roles && !roles.includes(user.role)) return <Navigate to={HOME[user.role]} replace />
  return children
}

function Home() {
  const { user, loading } = useAuth()
  if (loading) return <Spinner />
  return <Navigate to={user ? HOME[user.role] : '/login'} replace />
}

export default function App() {
  return (
    <Routes>
      <Route path="/login" element={<Login />} />
      <Route path="/" element={<Home />} />
      <Route element={<Protected><Layout /></Protected>}>
        <Route path="/account" element={<Account />} />
        <Route path="/evaluations/:id" element={<EvaluationDetail />} />

        <Route path="/admin" element={<Protected roles={['ADMIN']}><AdminDashboard /></Protected>} />
        <Route path="/admin/users" element={<Protected roles={['ADMIN']}><AdminUsers /></Protected>} />
        <Route path="/admin/subjects" element={<Protected roles={['ADMIN']}><Subjects /></Protected>} />
        <Route path="/admin/permissions" element={<Protected roles={['ADMIN']}><AdminPermissions /></Protected>} />
        <Route path="/admin/evaluations" element={<Protected roles={['ADMIN']}><Evaluations /></Protected>} />
        <Route path="/admin/audit" element={<Protected roles={['ADMIN']}><AdminAudit /></Protected>} />

        <Route path="/teacher" element={<Protected roles={['TEACHER']}><TeacherDashboard /></Protected>} />
        <Route path="/teacher/subjects" element={<Protected roles={['TEACHER']}><Subjects /></Protected>} />
        <Route path="/teacher/exams" element={<Protected roles={['TEACHER']}><Exams /></Protected>} />
        <Route path="/teacher/exams/:id" element={<Protected roles={['TEACHER']}><ExamDetail /></Protected>} />
        <Route path="/teacher/evaluations" element={<Protected roles={['TEACHER']}><Evaluations /></Protected>} />

        <Route path="/student" element={<Protected roles={['STUDENT']}><StudentDashboard /></Protected>} />
        <Route path="/student/results" element={<Protected roles={['STUDENT']}><StudentResults /></Protected>} />
      </Route>
      <Route path="*" element={<Home />} />
    </Routes>
  )
}
