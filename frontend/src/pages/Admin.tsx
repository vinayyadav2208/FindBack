import { useCallback, useEffect, useState } from 'react'
import { ErrorBanner, Spinner, SuccessBanner } from '../components/ui'
import api, { errorMessage } from '../lib/api'
import type { Claim, LostItem, Page, Report, User } from '../lib/types'
import { claimColor, statusColor } from '../lib/types'

type Tab = 'stats' | 'users' | 'listings' | 'reports' | 'claims'

interface AdminStats {
  users: Record<string, number>
  listings: Record<string, number>
  matches: Record<string, number>
  claims: Record<string, number>
  reports: Record<string, number>
}

export default function Admin() {
  const [tab, setTab] = useState<Tab>('stats')
  const [stats, setStats] = useState<AdminStats | null>(null)
  const [users, setUsers] = useState<Page<User> | null>(null)
  const [listings, setListings] = useState<{ items: (LostItem & { type: string })[]; total: number } | null>(null)
  const [reports, setReports] = useState<Page<Report> | null>(null)
  const [claims, setClaims] = useState<Page<Claim> | null>(null)
  const [userQuery, setUserQuery] = useState('')
  const [listingQuery, setListingQuery] = useState('')
  const [reportFilter, setReportFilter] = useState('OPEN')
  const [error, setError] = useState<string | null>(null)
  const [notice, setNotice] = useState<string | null>(null)
  const [loading, setLoading] = useState(true)

  const load = useCallback(() => {
    setLoading(true)
    Promise.all([
      api.get<AdminStats>('/admin/stats'),
      api.get<Page<User>>('/admin/users', { params: { limit: 50, ...(userQuery ? { q: userQuery } : {}) } }),
      api.get('/admin/listings', { params: { limit: 50, ...(listingQuery ? { q: listingQuery } : {}) } }),
      api.get<Page<Report>>('/admin/reports', { params: { limit: 50, status: reportFilter } }),
      api.get<Page<Claim>>('/admin/claims', { params: { limit: 50 } }),
    ])
      .then(([statsRes, usersRes, listingsRes, reportsRes, claimsRes]) => {
        setStats(statsRes.data)
        setUsers(usersRes.data)
        setListings(listingsRes.data)
        setReports(reportsRes.data)
        setClaims(claimsRes.data)
      })
      .catch((caught) => setError(errorMessage(caught)))
      .finally(() => setLoading(false))
  }, [userQuery, listingQuery, reportFilter])

  useEffect(load, [load])

  const act = async (fn: () => Promise<{ data: { message: string } }>) => {
    setError(null)
    try {
      const { data } = await fn()
      setNotice(data.message)
      load()
    } catch (caught) {
      setError(errorMessage(caught))
    }
  }

  const setUserRole = (id: number, role: 'USER' | 'ADMIN') =>
    act(() => api.put(`/admin/users/${id}/role`, undefined, { params: { role } }))

  const toggleSuspend = (user: User) =>
    act(() =>
      api.put(`/admin/users/${user.id}/${user.is_active === false ? 'activate' : 'suspend'}`),
    )

  const removeListing = (type: string, id: number) => {
    if (!window.confirm(`Remove this ${type} listing?`)) return
    act(() => api.delete(`/admin/listings/${type}/${id}`))
  }

  const reviewReport = (id: number, status: string) =>
    act(() => api.put(`/admin/reports/${id}`, { status }))

  const rebuild = () => act(() => api.post('/admin/matches/rebuild'))

  if (loading && !stats) return <Spinner label="Loading admin data…" />

  const tabs: Tab[] = ['stats', 'users', 'listings', 'reports', 'claims']

  return (
    <div>
      <div className="mb-6 flex flex-wrap items-center justify-between gap-3">
        <div>
          <h1 className="text-2xl font-semibold text-slate-800">Admin dashboard</h1>
          <p className="text-sm text-slate-500">Moderation, user management and platform health.</p>
        </div>
        <button className="btn-secondary" onClick={rebuild}>Run global AI matching</button>
      </div>

      <SuccessBanner message={notice} />
      <ErrorBanner message={error} />

      <div className="mb-4 flex flex-wrap gap-2 border-b border-slate-200">
        {tabs.map((entry) => (
          <button
            key={entry}
            className={`-mb-px border-b-2 px-4 py-2 text-sm font-medium capitalize ${
              tab === entry
                ? 'border-indigo-600 text-indigo-600'
                : 'border-transparent text-slate-500 hover:text-slate-700'
            }`}
            onClick={() => setTab(entry)}
          >
            {entry}
          </button>
        ))}
      </div>

      {tab === 'stats' && stats && (
        <div className="grid gap-4 sm:grid-cols-2 lg:grid-cols-3">
          {[
            { title: 'Users', rows: stats.users },
            { title: 'Listings', rows: stats.listings },
            { title: 'Matches', rows: stats.matches },
            { title: 'Claims', rows: stats.claims },
            { title: 'Reports', rows: stats.reports },
          ].map((section) => (
            <div key={section.title} className="card">
              <h2 className="font-semibold text-slate-800">{section.title}</h2>
              <dl className="mt-2 space-y-1 text-sm">
                {Object.entries(section.rows).map(([key, value]) => (
                  <div key={key} className="flex justify-between">
                    <dt className="capitalize text-slate-500">{key.replace(/_/g, ' ')}</dt>
                    <dd className="font-medium text-slate-700">{value}</dd>
                  </div>
                ))}
              </dl>
            </div>
          ))}
        </div>
      )}

      {tab === 'users' && users && (
        <div>
          <form
            className="mb-3 flex gap-2"
            onSubmit={(event) => {
              event.preventDefault()
              load()
            }}
          >
            <input
              className="input max-w-sm"
              placeholder="Search name or email…"
              value={userQuery}
              onChange={(event) => setUserQuery(event.target.value)}
            />
            <button className="btn-secondary" type="submit">Search</button>
          </form>
          <div className="overflow-x-auto rounded-xl border border-slate-200 bg-white">
            <table className="w-full text-left text-sm">
              <thead className="bg-slate-50 text-slate-500">
                <tr>
                  <th className="px-4 py-3">Name</th>
                  <th className="px-4 py-3">Email</th>
                  <th className="px-4 py-3">Role</th>
                  <th className="px-4 py-3">Status</th>
                  <th className="px-4 py-3">Actions</th>
                </tr>
              </thead>
              <tbody>
                {users.items.map((entry) => (
                  <tr key={entry.id} className="border-t border-slate-100">
                    <td className="px-4 py-3 font-medium text-slate-700">{entry.name}</td>
                    <td className="px-4 py-3 text-slate-500">{entry.email}</td>
                    <td className="px-4 py-3">
                      <span className={`badge ${entry.role === 'ADMIN' ? 'bg-indigo-100 text-indigo-700' : 'bg-slate-100 text-slate-600'}`}>
                        {entry.role}
                      </span>
                    </td>
                    <td className="px-4 py-3">
                      <span className={`badge ${entry.is_active === false ? 'bg-rose-100 text-rose-700' : 'bg-emerald-100 text-emerald-700'}`}>
                        {entry.is_active === false ? 'SUSPENDED' : 'ACTIVE'}
                      </span>
                    </td>
                    <td className="px-4 py-3">
                      <div className="flex gap-2">
                        <button className="btn-secondary py-1 text-xs" onClick={() => void toggleSuspend(entry)}>
                          {entry.is_active === false ? 'Activate' : 'Suspend'}
                        </button>
                        <button
                          className="btn-secondary py-1 text-xs"
                          onClick={() => void setUserRole(entry.id, entry.role === 'ADMIN' ? 'USER' : 'ADMIN')}
                        >
                          {entry.role === 'ADMIN' ? 'Make USER' : 'Make ADMIN'}
                        </button>
                      </div>
                    </td>
                  </tr>
                ))}
              </tbody>
            </table>
          </div>
        </div>
      )}

      {tab === 'listings' && listings && (
        <div>
          <form
            className="mb-3 flex gap-2"
            onSubmit={(event) => {
              event.preventDefault()
              load()
            }}
          >
            <input
              className="input max-w-sm"
              placeholder="Search listings…"
              value={listingQuery}
              onChange={(event) => setListingQuery(event.target.value)}
            />
            <button className="btn-secondary" type="submit">Search</button>
          </form>
          <div className="space-y-3">
            {listings.items.map((item) => (
              <div key={`${item.type}-${item.id}`} className="card flex items-center justify-between">
                <div>
                  <span className="badge mr-2 bg-slate-100 text-slate-600">{item.type}</span>
                  <span className="font-medium text-slate-800">{item.name}</span>
                  <p className="text-sm text-slate-500">{item.location}</p>
                </div>
                <div className="flex items-center gap-2">
                  <span className={`badge ${statusColor(item.status)}`}>{item.status}</span>
                  <button className="btn-danger py-1 text-xs" onClick={() => removeListing(item.type, item.id)}>
                    Remove
                  </button>
                </div>
              </div>
            ))}
            {listings.items.length === 0 && <p className="text-slate-400">No listings found.</p>}
          </div>
        </div>
      )}

      {tab === 'reports' && reports && (
        <div>
          <select className="input mb-3 w-auto" value={reportFilter} onChange={(event) => setReportFilter(event.target.value)}>
            <option value="OPEN">Open</option>
            <option value="UNDER_REVIEW">Under review</option>
            <option value="RESOLVED">Resolved</option>
            <option value="DISMISSED">Dismissed</option>
          </select>
          <div className="space-y-3">
            {reports.items.map((report) => (
              <div key={report.id} className="card flex items-center justify-between">
                <div>
                  <p className="font-medium text-slate-700">
                    {report.reason.replace(/_/g, ' ')} · {report.target_type.replace('_', ' ')} #{report.target_id}
                  </p>
                  {report.description && <p className="text-sm text-slate-500">{report.description}</p>}
                  <p className="text-xs text-slate-400">
                    by user #{report.reporter_id} · {report.created_at ? new Date(report.created_at).toLocaleString() : ''}
                  </p>
                </div>
                <div className="flex items-center gap-2">
                  <span className={`badge ${report.status === 'OPEN' ? 'bg-amber-100 text-amber-700' : 'bg-slate-100 text-slate-600'}`}>
                    {report.status}
                  </span>
                  <select
                    className="input w-auto py-1 text-xs"
                    value={report.status}
                    onChange={(event) => void reviewReport(report.id, event.target.value)}
                  >
                    {['OPEN', 'UNDER_REVIEW', 'RESOLVED', 'DISMISSED'].map((option) => (
                      <option key={option} value={option}>{option}</option>
                    ))}
                  </select>
                </div>
              </div>
            ))}
            {reports.items.length === 0 && <p className="text-slate-400">No reports in this queue.</p>}
          </div>
        </div>
      )}

      {tab === 'claims' && claims && (
        <div className="space-y-3">
          {claims.items.map((claim) => (
            <div key={claim.id} className="card flex items-center justify-between">
              <div>
                <p className="font-medium text-slate-700">
                  {claim.item_type.replace('_', ' ')} #{claim.item_id} · claimant #{claim.claimant_id}
                </p>
                <p className="text-sm text-slate-500">{claim.message}</p>
              </div>
              <span className={`badge ${claimColor(claim.status)}`}>{claim.status}</span>
            </div>
          ))}
          {claims.items.length === 0 && <p className="text-slate-400">No claims yet.</p>}
        </div>
      )}
    </div>
  )
}
