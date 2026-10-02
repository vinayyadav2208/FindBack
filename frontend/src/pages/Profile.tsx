import { useEffect, useState } from 'react'
import { Link, useNavigate } from 'react-router-dom'
import { ErrorBanner, SuccessBanner } from '../components/ui'
import { useAuth } from '../context/AuthContext'
import api, { errorMessage } from '../lib/api'

export default function Profile() {
  const { user, logout } = useAuth()
  const navigate = useNavigate()
  const [reports, setReports] = useState<{ id: number; target_type: string; target_id: number; reason: string; status: string }[]>([])
  const [error, setError] = useState<string | null>(null)
  const [notice, setNotice] = useState<string | null>(null)
  const [busy, setBusy] = useState(false)

  useEffect(() => {
    api
      .get<{ items: typeof reports }>('/reports/mine')
      .then(({ data }) => setReports(data.items))
      .catch((caught) => setError(errorMessage(caught)))
  }, [])

  const markAllRead = async () => {
    try {
      const { data } = await api.put('/notifications/read-all')
      setNotice(data.message)
    } catch (caught) {
      setError(errorMessage(caught))
    }
  }

  const rebuildMatches = async () => {
    setBusy(true)
    try {
      const { data } = await api.post('/matches/rebuild')
      setNotice(`AI matching finished: ${data.new_matches} new potential match(es) found.`)
    } catch (caught) {
      setError(errorMessage(caught))
    } finally {
      setBusy(false)
    }
  }

  if (!user) return null

  return (
    <div className="mx-auto max-w-2xl space-y-6">
      <div className="card">
        <h1 className="text-xl font-semibold text-slate-800">Profile</h1>
        <dl className="mt-4 space-y-2 text-sm">
          <div className="flex justify-between border-b border-slate-100 pb-2">
            <dt className="text-slate-500">Name</dt>
            <dd className="font-medium text-slate-700">{user.name}</dd>
          </div>
          <div className="flex justify-between border-b border-slate-100 pb-2">
            <dt className="text-slate-500">Email</dt>
            <dd className="font-medium text-slate-700">{user.email}</dd>
          </div>
          <div className="flex justify-between border-b border-slate-100 pb-2">
            <dt className="text-slate-500">Role</dt>
            <dd>
              <span className="badge bg-indigo-100 text-indigo-700">{user.role}</span>
            </dd>
          </div>
          {user.created_at && (
            <div className="flex justify-between">
              <dt className="text-slate-500">Member since</dt>
              <dd className="font-medium text-slate-700">
                {new Date(user.created_at).toLocaleDateString()}
              </dd>
            </div>
          )}
        </dl>
        <div className="mt-5 flex flex-wrap gap-2">
          <Link to="/dashboard" className="btn-secondary">Go to dashboard</Link>
          <button className="btn-secondary" onClick={() => void markAllRead()}>
            Mark notifications read
          </button>
          <button className="btn-secondary" disabled={busy} onClick={() => void rebuildMatches()}>
            {busy ? 'Running AI…' : 'Re-run AI matching'}
          </button>
        </div>
      </div>

      <div className="card">
        <h2 className="font-semibold text-slate-800">My reports</h2>
        {reports.length === 0 ? (
          <p className="mt-2 text-sm text-slate-500">You have not reported anything.</p>
        ) : (
          <ul className="mt-3 space-y-2 text-sm">
            {reports.map((report) => (
              <li key={report.id} className="flex items-center justify-between rounded-lg border border-slate-200 px-3 py-2">
                <span>
                  {report.target_type.replace('_', ' ')} #{report.target_id} · {report.reason.replace(/_/g, ' ')}
                </span>
                <span className="badge bg-slate-100 text-slate-600">{report.status}</span>
              </li>
            ))}
          </ul>
        )}
      </div>

      <ErrorBanner message={error} />
      <SuccessBanner message={notice} />

      <div className="text-center">
        <button
          className="text-sm text-rose-500 hover:underline"
          onClick={() => {
            logout()
            navigate('/')
          }}
        >
          Log out of FindBack
        </button>
      </div>
    </div>
  )
}
