import { useCallback, useEffect, useState } from 'react'
import { Link, useNavigate, useParams } from 'react-router-dom'
import { ReportForm } from '../components/media'
import { ErrorBanner, Spinner, SuccessBanner } from '../components/ui'
import { useAuth } from '../context/AuthContext'
import api, { errorMessage, mediaUrl } from '../lib/api'
import type { Donation } from '../lib/types'
import { statusColor } from '../lib/types'

export default function DonationDetail() {
  const { id } = useParams()
  const navigate = useNavigate()
  const { user } = useAuth()
  const [item, setItem] = useState<Donation | null>(null)
  const [error, setError] = useState<string | null>(null)
  const [notice, setNotice] = useState<string | null>(null)
  const [busy, setBusy] = useState(false)

  const load = useCallback(() => {
    api
      .get<Donation>(`/donations/${id}`)
      .then(({ data }) => setItem(data))
      .catch((caught) => setError(errorMessage(caught)))
  }, [id])

  useEffect(load, [load])

  const isOwner = Boolean(user && item && user.id === item.user_id)

  const request = async () => {
    if (!window.confirm('Send a request for this donation?')) return
    setError(null)
    setBusy(true)
    try {
      const { data } = await api.post(
        `/donations/${id}/claim`,
        { message: `${user?.name} would like to receive this donation.` },
      )
      setNotice(`Request sent (${data.status}). The donor will review it.`)
      load()
    } catch (caught) {
      setError(errorMessage(caught))
    } finally {
      setBusy(false)
    }
  }

  const remove = async () => {
    if (!window.confirm('Delete this donation?')) return
    try {
      await api.delete(`/donations/${id}`)
      navigate('/donations')
    } catch (caught) {
      setError(errorMessage(caught))
    }
  }

  if (error && !item) {
    return (
      <div>
        <ErrorBanner message={error} />
        <Link to="/donations" className="text-indigo-600 underline">← Back to donations</Link>
      </div>
    )
  }
  if (!item) return <Spinner />

  const canRequest = !isOwner && user && (item.status === 'AVAILABLE' || item.status === 'RESERVED')

  return (
    <div className="mx-auto max-w-3xl">
      <Link to="/donations" className="text-sm text-indigo-600 hover:underline">← Back to donations</Link>

      <div className="card mt-4">
        <div className="flex flex-wrap items-start justify-between gap-3">
          <div>
            <h1 className="text-2xl font-semibold text-slate-800">{item.name}</h1>
            <p className="mt-1 text-sm text-slate-500">
              {item.category} · {item.condition.replace('_', ' ')} · {item.location}
            </p>
          </div>
          <span className={`badge ${statusColor(item.status)}`}>{item.status}</span>
        </div>

        <p className="mt-4 whitespace-pre-wrap text-slate-600">{item.description}</p>

        {item.images && item.images.length > 0 && (
          <div className="mt-4 flex flex-wrap gap-3">
            {item.images.map((url) => (
              <img key={url} src={mediaUrl(url)} alt={item.name} className="h-32 w-32 rounded-lg border border-slate-200 object-cover" />
            ))}
          </div>
        )}

        <div className="mt-5 flex flex-wrap items-center gap-3 border-t border-slate-100 pt-4">
          <span className="text-sm text-slate-500">Offered by {item.user_name ?? 'community member'}</span>
          {isOwner && <button className="btn-danger" onClick={remove}>Delete</button>}
          {canRequest && (
            <button className="btn-primary" disabled={busy} onClick={() => void request()}>
              {busy ? 'Sending…' : 'Request this item'}
            </button>
          )}
          {!user && (
            <Link to="/login" className="btn-secondary">Log in to request</Link>
          )}
        </div>

        <div className="mt-4">
          <ReportForm targetType="DONATION" targetId={item.id} />
        </div>
      </div>

      <SuccessBanner message={notice} />
      <ErrorBanner message={error} />
    </div>
  )
}
