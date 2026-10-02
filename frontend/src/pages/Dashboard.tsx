import { useCallback, useEffect, useState } from 'react'
import { Link, useLocation } from 'react-router-dom'
import { Conversation } from '../components/messages'
import { EmptyState, ErrorBanner, Spinner, SuccessBanner } from '../components/ui'
import api, { errorMessage } from '../lib/api'
import type { Claim, Donation, FoundItem, LostItem, Page } from '../lib/types'
import { claimColor, statusColor } from '../lib/types'

type Tab = 'lost' | 'found' | 'donations' | 'claims'

export default function Dashboard() {
  const location = useLocation()
  // notification deep link: /dashboard?thread=8 opens that claim conversation
  const threadParam = new URLSearchParams(location.search).get('thread')
  const threadId =
    threadParam && !Number.isNaN(Number(threadParam)) ? Number(threadParam) : null
  const [tab, setTab] = useState<Tab>(threadId ? 'claims' : 'lost')
  const [openThread, setOpenThread] = useState<number | null>(threadId)
  const [lost, setLost] = useState<LostItem[]>([])
  const [found, setFound] = useState<FoundItem[]>([])
  const [donations, setDonations] = useState<Donation[]>([])
  const [myClaims, setMyClaims] = useState<Claim[]>([])
  const [received, setReceived] = useState<Claim[]>([])
  const [error, setError] = useState<string | null>(null)
  const [notice, setNotice] = useState<string | null>(null)
  const [loading, setLoading] = useState(true)

  const load = useCallback(() => {
    setLoading(true)
    Promise.all([
      api.get<Page<LostItem>>('/my-lost-items'),
      api.get<Page<FoundItem>>('/my-found-items'),
      api.get<Page<Donation>>('/my-donations'),
      api.get<{ items: Claim[] }>('/my-claims'),
      api.get<{ items: Claim[] }>('/claims/received'),
    ])
      .then(([lostRes, foundRes, donationsRes, myClaimsRes, receivedRes]) => {
        setLost(lostRes.data.items)
        setFound(foundRes.data.items)
        setDonations(donationsRes.data.items)
        setMyClaims(myClaimsRes.data.items)
        setReceived(receivedRes.data.items)
      })
      .catch((caught) => setError(errorMessage(caught)))
      .finally(() => setLoading(false))
  }, [])

  useEffect(load, [load])

  // silent claims-only refresh: keeps an open conversation mounted
  const refreshClaims = useCallback(() => {
    Promise.all([
      api.get<{ items: Claim[] }>('/my-claims'),
      api.get<{ items: Claim[] }>('/claims/received'),
    ])
      .then(([mineRes, receivedRes]) => {
        setMyClaims(mineRes.data.items)
        setReceived(receivedRes.data.items)
      })
      .catch((caught) => setError(errorMessage(caught)))
  }, [])

  const reviewClaim = async (claimId: number, action: 'approve' | 'reject') => {
    try {
      const { data } = await api.post(`/claims/${claimId}/${action}`, { note: null })
      setNotice(data.message)
      load()
    } catch (caught) {
      setError(errorMessage(caught))
    }
  }

  const cancelClaim = async (claimId: number) => {
    try {
      const { data } = await api.post(`/claims/${claimId}/cancel`)
      setNotice(data.message)
      load()
    } catch (caught) {
      setError(errorMessage(caught))
    }
  }

  const removeLost = async (id: number) => {
    if (!window.confirm('Delete this lost listing?')) return
    try {
      await api.delete(`/lost-items/${id}`)
      load()
    } catch (caught) {
      setError(errorMessage(caught))
    }
  }

  const removeFound = async (id: number) => {
    if (!window.confirm('Delete this found listing?')) return
    try {
      await api.delete(`/found-items/${id}`)
      load()
    } catch (caught) {
      setError(errorMessage(caught))
    }
  }

  const removeDonation = async (id: number) => {
    if (!window.confirm('Delete this donation?')) return
    try {
      await api.delete(`/donations/${id}`)
      load()
    } catch (caught) {
      setError(errorMessage(caught))
    }
  }

  const tabs: { id: Tab; label: string; count: number }[] = [
    { id: 'lost', label: 'My lost reports', count: lost.length },
    { id: 'found', label: 'My found reports', count: found.length },
    { id: 'donations', label: 'My donations', count: donations.length },
    { id: 'claims', label: 'Claims', count: myClaims.length + received.length },
  ]

  if (loading) return <Spinner label="Loading your dashboard…" />

  return (
    <div>
      <div className="mb-6 flex flex-wrap items-center justify-between gap-3">
        <div>
          <h1 className="text-2xl font-semibold text-slate-800">Dashboard</h1>
          <p className="text-sm text-slate-500">Everything you have posted and the claims you manage.</p>
        </div>
        <div className="flex flex-wrap gap-2">
          <Link to="/lost/new" className="btn-secondary">+ Lost</Link>
          <Link to="/found/new" className="btn-secondary">+ Found</Link>
          <Link to="/donations/new" className="btn-primary">+ Donate</Link>
        </div>
      </div>

      <SuccessBanner message={notice} />
      <ErrorBanner message={error} />

      <div className="mb-4 flex flex-wrap gap-2 border-b border-slate-200">
        {tabs.map((entry) => (
          <button
            key={entry.id}
            className={`-mb-px border-b-2 px-4 py-2 text-sm font-medium ${
              tab === entry.id
                ? 'border-indigo-600 text-indigo-600'
                : 'border-transparent text-slate-500 hover:text-slate-700'
            }`}
            onClick={() => setTab(entry.id)}
          >
            {entry.label} ({entry.count})
          </button>
        ))}
      </div>

      {tab === 'lost' &&
        (lost.length ? (
          <div className="space-y-3">
            {lost.map((item) => (
              <div key={item.id} className="card flex items-center justify-between">
                <div>
                  <Link to={`/lost/${item.id}`} className="font-medium text-slate-800 hover:underline">
                    {item.name}
                  </Link>
                  <p className="text-sm text-slate-500">{item.location}</p>
                </div>
                <div className="flex items-center gap-2">
                  <span className={`badge ${statusColor(item.status)}`}>{item.status}</span>
                  <button className="btn-danger" onClick={() => void removeLost(item.id)}>Delete</button>
                </div>
              </div>
            ))}
          </div>
        ) : (
          <EmptyState title="No lost reports yet" hint="Report an item you lost to activate AI matching." />
        ))}

      {tab === 'found' &&
        (found.length ? (
          <div className="space-y-3">
            {found.map((item) => (
              <div key={item.id} className="card flex items-center justify-between">
                <div>
                  <Link to={`/found/${item.id}`} className="font-medium text-slate-800 hover:underline">
                    {item.name}
                  </Link>
                  <p className="text-sm text-slate-500">{item.location}</p>
                </div>
                <div className="flex items-center gap-2">
                  <span className={`badge ${statusColor(item.status)}`}>{item.status}</span>
                  <button className="btn-danger" onClick={() => void removeFound(item.id)}>Delete</button>
                </div>
              </div>
            ))}
          </div>
        ) : (
          <EmptyState title="No found reports yet" />
        ))}

      {tab === 'donations' &&
        (donations.length ? (
          <div className="space-y-3">
            {donations.map((item) => (
              <div key={item.id} className="card flex items-center justify-between">
                <div>
                  <Link to={`/donations/${item.id}`} className="font-medium text-slate-800 hover:underline">
                    {item.name}
                  </Link>
                  <p className="text-sm text-slate-500">
                    {item.condition.replace('_', ' ')} · {item.location}
                  </p>
                </div>
                <div className="flex items-center gap-2">
                  <span className={`badge ${statusColor(item.status)}`}>{item.status}</span>
                  <button className="btn-danger" onClick={() => void removeDonation(item.id)}>Delete</button>
                </div>
              </div>
            ))}
          </div>
        ) : (
          <EmptyState title="No donations yet" hint="Give away something someone else needs." />
        ))}

      {tab === 'claims' && (
        <div className="grid gap-6 lg:grid-cols-2">
          <section>
            <h2 className="mb-3 font-semibold text-slate-700">Claims I submitted</h2>
            {myClaims.length ? (
              <div className="space-y-3">
                {myClaims.map((claim) => (
                  <div key={claim.id} className="card">
                    <div className="flex items-center justify-between">
                      <span className="text-sm font-medium text-slate-700">
                        {claim.item_type.replace('_', ' ')} #{claim.item_id}
                      </span>
                      <span className={`badge ${claimColor(claim.status)}`}>{claim.status}</span>
                    </div>
                    <p className="mt-1 text-sm text-slate-600">{claim.message}</p>
                    <div className="mt-2 flex flex-wrap items-center gap-2">
                      {claim.status === 'PENDING' && (
                        <button className="btn-secondary" onClick={() => void cancelClaim(claim.id)}>
                          Cancel claim
                        </button>
                      )}
                      <button
                        className="btn-secondary"
                        onClick={() => setOpenThread(openThread === claim.id ? null : claim.id)}
                      >
                        💬 Conversation
                        {(claim.unread_messages ?? 0) > 0 && (
                          <span className="badge bg-teal-100 text-teal-700">
                            {claim.unread_messages} new
                          </span>
                        )}
                      </button>
                    </div>
                    {openThread === claim.id && (
                      <Conversation path={`/claims/${claim.id}`} onChanged={refreshClaims} />
                    )}
                  </div>
                ))}
              </div>
            ) : (
              <EmptyState title="You have not submitted claims" />
            )}
          </section>

          <section>
            <h2 className="mb-3 font-semibold text-slate-700">Claims on my listings</h2>
            {received.length ? (
              <div className="space-y-3">
                {received.map((claim) => (
                  <div key={claim.id} className="card">
                    <div className="flex items-center justify-between">
                      <span className="text-sm font-medium text-slate-700">
                        {claim.claimant?.name ?? 'User'} on {claim.item_type.replace('_', ' ')} #{claim.item_id}
                      </span>
                      <span className={`badge ${claimColor(claim.status)}`}>{claim.status}</span>
                    </div>
                    <p className="mt-1 text-sm text-slate-600">{claim.message}</p>
                    {claim.verification_answers && Object.keys(claim.verification_answers).length > 0 && (
                      <dl className="mt-2 rounded bg-slate-50 p-2 text-sm">
                        {Object.entries(claim.verification_answers).map(([question, answer]) => (
                          <div key={question} className="flex gap-2">
                            <dt className="font-medium text-slate-600">{question}:</dt>
                            <dd className="text-slate-700">{answer}</dd>
                          </div>
                        ))}
                      </dl>
                    )}
                    {claim.status === 'PENDING' && (
                      <div className="mt-2 flex gap-2">
                        <button className="btn-primary" onClick={() => void reviewClaim(claim.id, 'approve')}>
                          Approve
                        </button>
                        <button className="btn-danger" onClick={() => void reviewClaim(claim.id, 'reject')}>
                          Reject
                        </button>
                      </div>
                    )}
                    <div className="mt-2">
                      <button
                        className="btn-secondary"
                        onClick={() => setOpenThread(openThread === claim.id ? null : claim.id)}
                      >
                        💬 Conversation
                        {(claim.unread_messages ?? 0) > 0 && (
                          <span className="badge bg-teal-100 text-teal-700">
                            {claim.unread_messages} new
                          </span>
                        )}
                      </button>
                    </div>
                    {openThread === claim.id && (
                      <Conversation path={`/claims/${claim.id}`} onChanged={refreshClaims} />
                    )}
                  </div>
                ))}
              </div>
            ) : (
              <EmptyState title="No claims on your listings yet" />
            )}
          </section>
        </div>
      )}
    </div>
  )
}
