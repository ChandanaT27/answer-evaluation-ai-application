import axios from 'axios'

const api = axios.create({ baseURL: import.meta.env.VITE_API_URL || '/api' })

api.interceptors.request.use((cfg) => {
  const t = localStorage.getItem('token')
  if (t) cfg.headers.Authorization = `Bearer ${t}`
  return cfg
})

api.interceptors.response.use(
  (r) => r,
  (err) => {
    const onLogin = window.location.pathname === '/login'
    if (err.response?.status === 401 && !onLogin) {
      localStorage.removeItem('token')
      window.location.assign('/login')
    }
    return Promise.reject(err)
  },
)

export function errorMessage(err) {
  const d = err?.response?.data
  if (d?.fieldErrors && Object.keys(d.fieldErrors).length) {
    return Object.entries(d.fieldErrors).map(([k, v]) => `${k}: ${v}`).join('; ')
  }
  if (d?.message) return d.message
  if (err?.response) return `Request failed (${err.response.status})`
  return 'Cannot reach the server'
}

/** Fetch an authenticated file as a blob and open or download it. */
export async function openFile(url, { download = false, filename } = {}) {
  const res = await api.get(url, { responseType: 'blob' })
  const objUrl = URL.createObjectURL(res.data)
  if (download) {
    const a = document.createElement('a')
    a.href = objUrl
    a.download = filename || 'download'
    document.body.appendChild(a)
    a.click()
    a.remove()
    setTimeout(() => URL.revokeObjectURL(objUrl), 10000)
  } else {
    window.open(objUrl, '_blank')
  }
}

export default api
