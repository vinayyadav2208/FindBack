import { useCallback, useEffect, useState } from 'react'
import { Link, useNavigate, useParams } from 'react-router-dom'
import { ReportForm } from '../components/media'
import { ErrorBanner, Spinner, SuccessBanner } from '../components/ui'
import { useAuth } from '../context/AuthContext'
import api, { errorMessage, mediaUrl } from '../lib/api'
import type { Claim, LostItem, Match, Page } from '../lib/types'
import { claimColor, statusColor } from '../lib/types'

export default function LostDetail() {
  const { id } = useParams()
  const navigate = useNavigate()
  const { user } = useAuth()
  const [item, setItem] = useState<LostItem | null>(null)
  const [matches, setMatches] = useState<Match[]>([])
  const [claims, setClaims] = useState<Claim[]>([])
  const [error, setError] = useState<string | null>(null)
  const [notice, setNotice] = useState<string | null>(null)
  const [busy, setBusy] = useState(false)
  const [claimMessage, setClaimMessage] = useState('')

  const load = useCallback(() => {
    api
      .get<LostItem>(`/lost-items/${id}`)
      .then(({ data }) => setItem(data))
      .catch((caught) => setError(errorMessage(caught)))
    if (user) {
      api
        .get<Page<Claim>>('/claims/received', { params: { status: 'PENDING' } })
        .then(({ data }) => setClaims(data.items.filter((claim) => claim.item_type === 'LOST_ITEM' && String(claim.item_id) === String(id))))
        .catch(() => undefined)
      api
        .get<Page<Match>>('/matches')
        .then(({ data }) => setMatches(data.items.filter((match) => match.lost_item_id === Number(id))))
        .catch(() => undefined)
    }
  }, [id, user])

  useEffect(load, [load])

  const isOwner = Boolean(user && item && user.id === item.user_id)

  const submitClaim = async (event: React.FormEvent) => {
    event.preventDefault()
    setError(null)
    setBusy(true)
    try {
      await api.post(
        '/claims',
        { message: claimMessage },
        { params: { item_type: 'LOST_ITEM', item_id: id } },
      )
      setNotice('Claim submitted! The owner has been notified and will verify your message.')
      setClaimMessage('')
      load()
    } catch (caught) {
      setError(errorMessage(caught))
    } finally {
      setBusy(false)
    }
  }

  const reviewClaim = async (claimId: number, action: 'approve' | 'reject') => {
    setError(null)
    try {
      const { data } = await api.post(`/claims/${claimId}/${action}`, { note: null })
      setNotice(data.message)
      load()
    } catch (caught) {
      setError(errorMessage(caught))
    }
  }

  const remove = async () => {
    if (!window.confirm('Delete this listing? This cannot be undone.')) return
    try {
      await api.delete(`/lost-items/${id}`)
      navigate('/lost')
    } catch (caught) {
      setError(errorMessage(caught))
    }
  }

  if (error && !item) {
    return (
      <div>
        <ErrorBanner message={error} />
        <Link to="/lost" className="text-indigo-600 underline">← Back to lost items</Link>
      </div>
    )
  }
  if (!item) return <Spinner />

  return (
    <div className="mx-auto max-w-3xl">
      <Link to="/lost" className="text-sm text-indigo-600 hover:underline">← Back to lost items</Link>
      <div className="card mt-4">
        <div className="flex flex-wrap items-start justify-between gap-3">
          <div>
            <h1 className="text-2xl font-semibold text-slate-800">{item.name}</h1>
            <p className="mt-1 text-sm text-slate-500">
              {item.category} · {item.location}
              {item.created_at && ` · posted ${new Date(item.created_at).toLocaleDateString()}`}
            </p>
          </div>
          <span className={`badge ${statusColor(item.status)}`}>{item.status}</span>
        </div>

        <p className="mt-4 whitespace-pre-wrap text-slate-600">{item.description}</p>

        {item.images && item.images.length > 0 && (
          <div className="mt-4 flex flex-wrap gap-3">
            {item.images.map((url) => (
              <img
                key={url}
                src={mediaUrl(url)}
                alt={item.name}
                className="h-32 w-32 rounded-lg border border-slate-200 object-cover"
              />
            ))}
          </div>
        )}

        <div className="mt-5 flex flex-wrap items-center gap-3 border-t border-slate-100 pt-4 text-sm text-slate-500">
          <span>Posted by {item.user_name ?? 'community member'}</span>
          {isOwner && (
            <>
              <Link to={`/lost/new`} className="btn-secondary">+ New listing</Link>
              <button className="btn-danger" onClick={remove}>Delete</button>
            </>
          )}
        </div>

        {!isOwner && user && item.status === 'ACTIVE' && (
          <div className="mt-5 rounded-lg border border-emerald-200 bg-emerald-50 p-4">
            <h2 className="font-semibold text-emerald-800">I found this item</h2>
            <p className="mt-1 text-sm text-emerald-700">
              Tell the owner what you have - they will verify before approving.
            </p>
            <form className="mt-3 flex gap-2" onSubmit={submitClaim}>
              <input
                className="input flex-1"
                required
                maxLength={500}
                placeholder="e.g. Found near the metro gate, has a blue strap"
                value={claimMessage}
                onChange={(event) => setClaimMessage(event.target.value)}
              />
              <button className="btn-primary" disabled={busy} type="submit">Send to owner</button>
            </form>
          </div>
        )}

        {!user && (
          <p className="mt-4 text-sm text-slate-500">
            <Link to="/login" className="text-indigo-600 hover:underline">Log in</Link> to tell
            the owner you found this item.
          </p>
        )}

        <div className="mt-4">
          <ReportForm targetType="LOST_ITEM" targetId={item.id} />
        </div>
      </div>

      <SuccessBanner message={notice} />
      <ErrorBanner message={error} />

      {/* Owner: pending claims */}
      {isOwner && claims.length > 0 && (
        <div className="card mt-4">
          <h2 className="font-semibold text-slate-800">Claims on this listing</h2>
          {claims.map((claim) => (
            <div key={claim.id} className="mt-3 rounded-lg border border-slate-200 p-3">
              <div className="flex items-center justify-between">
                <span className="font-medium text-slate-700">{claim.claimant?.name ?? 'User'}</span>
                <span className={`badge ${claimColor(claim.status)}`}>{claim.status}</span>
              </div>
              <p className="mt-1 text-sm text-slate-600">{claim.message}</p>
              <div className="mt-3 flex gap-2">
                <button className="btn-primary" onClick={() => void reviewClaim(claim.id, 'approve')}>
                  Approve
                </button>
                <button className="btn-danger" onClick={() => void reviewClaim(claim.id, 'reject')}>
                  Reject
                </button>
              </div>
            </div>
          ))}
        </div>
      )}

      {/* AI matches for this listing */}
      {isOwner && matches.length > 0 && (
        <div className="card mt-4">
          <h2 className="font-semibold text-slate-800">Potential matches found for you</h2>
          {matches.map((match) => (
            <div key={match.id} className="mt-3 rounded-lg border border-indigo-100 bg-indigo-50/50 p-3">
              <div className="flex items-center justify-between">
                <span className="font-medium text-slate-700">{match.found_item?.name}</span>
                <span className="text-xs text-slate-500">
                  {Math.round(match.combined_score * 100)}% · {match.explanation?.confidence}
                </span>
              </div>
              <ul className="mt-1 list-inside list-disc text-sm text-slate-600">
                {match.explanation?.reasons.map((reason) => <li key={reason}>{reason}</li>)}
              </ul>
              <Link to="/matches" className="mt-2 inline-block text-sm text-indigo-600 hover:underline">
                Review all matches →
              </Link>
            </div>
          ))}
        </div>
      )}
    </div>
  )
}
