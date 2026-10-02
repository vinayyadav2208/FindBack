/**
 * Central Axios client (MASTER_README §56): one base URL, one place for the
 * auth header, one place for error messages. Components import from here only.
 */
import axios from 'axios'

export const API_BASE =
  (import.meta.env.VITE_API_BASE_URL as string | undefined) ?? 'http://127.0.0.1:8000'

export const TOKEN_KEY = 'findback_token'

const api = axios.create({ baseURL: API_BASE, timeout: 20000 })

api.interceptors.request.use((config) => {
  const token = localStorage.getItem(TOKEN_KEY)
  if (token) config.headers.Authorization = `Bearer ${token}`
  return config
})

api.interceptors.response.use(
  (response) => response,
  (error) => {
    // A stored token that the server rejects means the session is over.
    if (error.response?.status === 401 && localStorage.getItem(TOKEN_KEY)) {
      localStorage.removeItem(TOKEN_KEY)
      window.dispatchEvent(new Event('findback:logout'))
    }
    return Promise.reject(error)
  },
)

/** Resolve a backend path (e.g. /media/x.png) against the API origin. */
export function mediaUrl(url: string | null | undefined): string {
  if (!url) return ''
  if (url.startsWith('/')) return API_BASE + url
  return url
}

/** Extract a human readable message from any thrown error. */
export function errorMessage(error: unknown): string {
  if (axios.isAxiosError(error)) {
    const detail = (error.response?.data as { detail?: unknown } | undefined)?.detail
    if (typeof detail === 'string') return detail
    if (Array.isArray(detail)) {
      return detail
        .map((d) => (d as { msg?: string }).msg ?? JSON.stringify(d))
        .join('; ')
    }
    if (error.response) return `Request failed (HTTP ${error.response.status})`
    return 'Cannot reach the FindBack API - is the backend running?'
  }
  return 'Something went wrong'
}

export default api
