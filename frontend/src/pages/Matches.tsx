import { useCallback, useEffect, useState } from 'react'
import { Link } from 'react-router-dom'
import { MatchThread } from '../components/messages'
import { EmptyState, ErrorBanner, Pagination, Spinner, SuccessBanner } from '../components/ui'
import api, { errorMessage } from '../lib/api'
import type { Match, Page } from '../lib/types'

const MATCH_STATUSES = ['POTENTIAL', 'VIEWED', 'CONTACTED', 'VERIFIED', 'REJECTED', 'RESOLVED']

function confidenceColor(confidence: string): string {
  if (confidence.startsWith('Strong')) return 'bg-emerald-100 text-emerald-700'
  if (confidence.startsWith('Potential')) return 'bg-amber-100 text-amber-700'
  return 'bg-slate-100 text-slate-600'
}

export default function Matches() {
  const [status, setStatus] = useState('')
  const [page, setPage] = useState(1)
  const [data, setData] = useState<Page<Match> | null>(null)
  const [error, setError] = useState<string | null>(null)
  const [notice, setNotice] = useState<string | null>(null)
  const [loading, setLoading] = useState(true)
  const [openThread, setOpenThread] = useState<number | null>(null)

  // showSpinner=true swaps the list for a spinner (filters/page changes);
  // silent refresh keeps an open conversation mounted.
  const fetchMatches = useCallback(
    (showSpinner: boolean) => {
      if (showSpinner) setLoading(true)
      const params: Record<string, string | number> = { page, limit: 10 }
      if (status) params.status = status
      api
        .get<Page<Match>>('/matches', { params })
        .then(({ data: body }) => setData(body))
        .catch((caught) => setError(errorMessage(caught)))
        .finally(() => {
          if (showSpinner) setLoading(false)
        })
    },
    [page, status],
  )

  const load = useCallback(() => fetchMatches(true), [fetchMatches])
  const refresh = useCallback(() => fetchMatches(false), [fetchMatches])

  useEffect(() => {
    load()
  }, [load])

  const updateStatus = async (matchId: number, next: string) => {
    try {
      const { data } = await api.put(`/matches/${matchId}/status`, { status: next })
      setNotice(data.message)
      refresh()
    } catch (caught) {
      setError(errorMessage(caught))
    }
  }

  return (
    <div>
      <div className="mb-6 flex flex-wrap items-center justify-between gap-3">
        <div>
          <h1 className="text-2xl font-semibold text-slate-800">AI potential matches</h1>
          <p className="text-sm text-slate-500">
            Suggestions only - always verify ownership before handing anything over.
          </p>
        </div>
        <select
          className="input w-auto"
          value={status}
          onChange={(event) => {
            setStatus(event.target.value)
            setPage(1)
          }}
        >
          <option value="">All statuses</option>
          {MATCH_STATUSES.map((option) => (
            <option key={option} value={option}>{option}</option>
          ))}
        </select>
      </div>

      <SuccessBanner message={notice} />
      <ErrorBanner message={error} />

      {loading ? (
        <Spinner />
      ) : data && data.items.length === 0 ? (
        <EmptyState
          title="No matches yet"
          hint="Report a lost item and let the community post found items - matching runs automatically."
        />
      ) : data ? (
        <>
          <div className="space-y-4">
            {data.items.map((match) => (
              <div key={match.id} className="card">
                <div className="flex flex-wrap items-start justify-between gap-3">
                  <div>
                    <h2 className="font-semibold text-slate-800">
                      Lost: {match.lost_item?.name ?? `#${match.lost_item_id}`}
                    </h2>
                    <p className="text-sm text-slate-500">
                      ↔ Found: {match.found_item?.name ?? `#${match.found_item_id}`}
                    </p>
                  </div>
                  <div className="text-right">
                    <span className={`badge ${confidenceColor(match.explanation?.confidence ?? '')}`}>
                      {match.explanation?.confidence ?? 'Possible match'}
                    </span>
                    <p className="mt-1 text-xs text-slate-400">
                      {Math.round(match.combined_score * 100)}% combined score
                    </p>
                  </div>
                </div>

                {/* Why the AI suggested this */}
                <div className="mt-3 rounded-lg bg-slate-50 p-3 text-sm">
                  <p className="font-medium text-slate-600">Why this match?</p>
                  <ul className="mt-1 list-inside list-disc text-slate-600">
                    {match.explanation?.reasons.map((reason) => <li key={reason}>{reason}</li>)}
                  </ul>
                  <div className="mt-2 grid grid-cols-2 gap-1 text-xs text-slate-500 sm:grid-cols-4">
                    <span>Text: {Math.round(match.text_score * 100)}%</span>
                    <span>Location: {Math.round(match.location_score * 100)}%</span>
                    <span>Category: {Math.round(match.category_score * 100)}%</span>
                    <span>Image: {match.image_score > 0 ? `${Math.round(match.image_score * 100)}%` : 'n/a'}</span>
                  </div>
                  <p className="mt-2 text-xs text-amber-600">{match.explanation?.confidence_note}</p>
                </div>

                <div className="mt-3 flex flex-wrap items-center justify-between gap-3">
                  <div className="flex gap-3 text-sm">
                    {match.lost_item && (
                      <Link to={`/lost/${match.lost_item_id}`} className="text-indigo-600 hover:underline">
                        View lost report
                      </Link>
                    )}
                    {match.found_item && (
                      <Link to={`/found/${match.found_item_id}`} className="text-indigo-600 hover:underline">
                        View found report
                      </Link>
                    )}
                  </div>
                  <div className="flex items-center gap-2">
                    <span className="badge bg-slate-100 text-slate-600">{match.status}</span>
                    <select
                      className="input w-auto py-1 text-xs"
                      value={match.status}
                      onChange={(event) => void updateStatus(match.id, event.target.value)}
                    >
                      {MATCH_STATUSES.map((option) => (
                        <option key={option} value={option}>{option}</option>
                      ))}
                    </select>
                  </div>
                </div>

                {/* Direct conversation between the finder and the loser */}
                <div className="mt-3">
                  <button
                    type="button"
                    className="btn-secondary"
                    onClick={() => setOpenThread(openThread === match.id ? null : match.id)}
                  >
                    💬 Conversation
                    {(match.unread_messages ?? 0) > 0 && (
                      <span className="badge bg-teal-100 text-teal-700">
                        {match.unread_messages} new
                      </span>
                    )}
                  </button>
                </div>
                {openThread === match.id && (
                  <MatchThread matchId={match.id} onChanged={refresh} />
                )}
              </div>
            ))}
          </div>
          <Pagination page={data.page} pages={data.pages} onChange={setPage} />
        </>
      ) : null}
    </div>
  )
}
