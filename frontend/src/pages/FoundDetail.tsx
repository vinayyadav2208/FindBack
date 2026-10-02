import { useCallback, useEffect, useState } from 'react'
import { Link, useNavigate, useParams } from 'react-router-dom'
import { ReportForm } from '../components/media'
import { ErrorBanner, Spinner, SuccessBanner } from '../components/ui'
import { useAuth } from '../context/AuthContext'
import api, { errorMessage, mediaUrl } from '../lib/api'
import type { Claim, FoundItem } from '../lib/types'
import { claimColor, statusColor } from '../lib/types'

interface QA {
  question: string
  answer: string
}

export default function FoundDetail() {
  const { id } = useParams()
  const navigate = useNavigate()
  const { user } = useAuth()
  const [item, setItem] = useState<FoundItem | null>(null)
  const [claims, setClaims] = useState<Claim[]>([])
  const [error, setError] = useState<string | null>(null)
  const [notice, setNotice] = useState<string | null>(null)
  const [busy, setBusy] = useState(false)
  const [message, setMessage] = useState('')
  const [answers, setAnswers] = useState<QA[]>([{ question: '', answer: '' }])

  const load = useCallback(() => {
    api
      .get<FoundItem>(`/found-items/${id}`)
      .then(({ data }) => setItem(data))
      .catch((caught) => setError(errorMessage(caught)))
    if (user) {
      api
        .get<{ items: Claim[] }>('/claims/received', { params: { status: 'PENDING' } })
        .then(({ data }) =>
          setClaims(
            data.items.filter(
              (claim) => claim.item_type === 'FOUND_ITEM' && String(claim.item_id) === String(id),
            ),
          ),
        )
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
      const verification_answers: Record<string, string> = {}
      for (const pair of answers) {
        if (pair.question.trim() && pair.answer.trim()) {
          verification_answers[pair.question.trim()] = pair.answer.trim()
        }
      }
      await api.post(
        '/claims',
        { message, verification_answers: Object.keys(verification_answers).length ? verification_answers : null },
        { params: { item_type: 'FOUND_ITEM', item_id: id } },
      )
      setNotice('Claim submitted for the finder to review. You will be notified of their decision.')
      setMessage('')
      setAnswers([{ question: '', answer: '' }])
      load()
    } catch (caught) {
      setError(errorMessage(caught))
    } finally {
      setBusy(false)
    }
  }

  const reviewClaim = async (claimId: number, action: 'approve' | 'reject') => {
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
      await api.delete(`/found-items/${id}`)
      navigate('/found')
    } catch (caught) {
      setError(errorMessage(caught))
    }
  }

  if (error && !item) {
    return (
      <div>
        <ErrorBanner message={error} />
        <Link to="/found" className="text-indigo-600 underline">← Back to found items</Link>
      </div>
    )
  }
  if (!item) return <Spinner />

  return (
    <div className="mx-auto max-w-3xl">
      <Link to="/found" className="text-sm text-indigo-600 hover:underline">← Back to found items</Link>

      <div className="card mt-4">
        <div className="flex flex-wrap items-start justify-between gap-3">
          <div>
            <h1 className="text-2xl font-semibold text-slate-800">{item.name}</h1>
            <p className="mt-1 text-sm text-slate-500">
              {item.category} · {item.location}
              {item.created_at && ` · found ${new Date(item.created_at).toLocaleDateString()}`}
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

        <div className="mt-5 flex flex-wrap items-center gap-3 border-t border-slate-100 pt-4 text-sm text-slate-500">
          <span>Held by {item.user_name ?? 'community member'}</span>
          {isOwner && <button className="btn-danger" onClick={remove}>Delete</button>}
        </div>

        {!isOwner && user && (item.status === 'ACTIVE' || item.status === 'MATCHED') && (
          <form className="mt-5 rounded-lg border border-indigo-200 bg-indigo-50 p-4" onSubmit={submitClaim}>
            <h2 className="font-semibold text-indigo-800">This is mine</h2>
            <p className="mt-1 text-sm text-indigo-700">
              Explain how you can prove ownership. The finder decides after reviewing your answers.
            </p>
            <textarea
              className="input mt-3"
              required
              rows={3}
              maxLength={500}
              placeholder="Describe why this item is yours…"
              value={message}
              onChange={(event) => setMessage(event.target.value)}
            />
            <div className="mt-3 space-y-2">
              <p className="text-sm font-medium text-indigo-800">Verification answers (optional)</p>
              {answers.map((pair, index) => (
                <div key={index} className="flex gap-2">
                  <input
                    className="input"
                    placeholder="Question, e.g. What is written inside?"
                    value={pair.question}
                    onChange={(event) =>
                      setAnswers((prev) =>
                        prev.map((item2, i) => (i === index ? { ...item2, question: event.target.value } : item2)),
                      )
                    }
                  />
                  <input
                    className="input"
                    placeholder="Your answer"
                    value={pair.answer}
                    onChange={(event) =>
                      setAnswers((prev) =>
                        prev.map((item2, i) => (i === index ? { ...item2, answer: event.target.value } : item2)),
                      )
                    }
                  />
                  {answers.length > 1 && (
                    <button
                      type="button"
                      className="btn-secondary"
                      onClick={() => setAnswers((prev) => prev.filter((_, i) => i !== index))}
                    >
                      ×
                    </button>
                  )}
                </div>
              ))}
              {answers.length < 4 && (
                <button
                  type="button"
                  className="text-sm text-indigo-600 hover:underline"
                  onClick={() => setAnswers((prev) => [...prev, { question: '', answer: '' }])}
                >
                  + Add another question
                </button>
              )}
            </div>
            <button className="btn-primary mt-3" disabled={busy} type="submit">
              {busy ? 'Submitting…' : 'Submit claim'}
            </button>
          </form>
        )}

        {!user && (
          <p className="mt-4 text-sm text-slate-500">
            <Link to="/login" className="text-indigo-600 hover:underline">Log in</Link> to claim this item.
          </p>
        )}

        <div className="mt-4">
          <ReportForm targetType="FOUND_ITEM" targetId={item.id} />
        </div>
      </div>

      <SuccessBanner message={notice} />
      <ErrorBanner message={error} />

      {isOwner && claims.length > 0 && (
        <div className="card mt-4">
          <h2 className="font-semibold text-slate-800">Claims waiting for your review</h2>
          <p className="text-sm text-slate-500">
            Check the answers carefully - AI never decides ownership for you.
          </p>
          {claims.map((claim) => (
            <div key={claim.id} className="mt-3 rounded-lg border border-slate-200 p-3">
              <div className="flex items-center justify-between">
                <span className="font-medium text-slate-700">{claim.claimant?.name ?? 'User'}</span>
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
              <div className="mt-3 flex gap-2">
                <button className="btn-primary" onClick={() => void reviewClaim(claim.id, 'approve')}>
                  Approve & hand over
                </button>
                <button className="btn-danger" onClick={() => void reviewClaim(claim.id, 'reject')}>
                  Reject
                </button>
              </div>
            </div>
          ))}
        </div>
      )}
    </div>
  )
}
