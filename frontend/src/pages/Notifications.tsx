import { useCallback, useEffect, useState } from 'react'
import { EmptyState, ErrorBanner, Pagination, Spinner } from '../components/ui'
import api, { errorMessage } from '../lib/api'
import type { Notification, Page } from '../lib/types'

const typeDot: Record<string, string> = {
  MATCH_FOUND: 'bg-indigo-500',
  CLAIM_RECEIVED: 'bg-amber-500',
  CLAIM_APPROVED: 'bg-emerald-500',
  CLAIM_REJECTED: 'bg-rose-500',
  DONATION_CLAIMED: 'bg-sky-500',
  LISTING_REPORTED: 'bg-orange-500',
  MESSAGE_RECEIVED: 'bg-teal-500',
  SYSTEM: 'bg-slate-400',
}

export default function Notifications() {
  const [unreadOnly, setUnreadOnly] = useState(false)
  const [page, setPage] = useState(1)
  const [data, setData] = useState<Page<Notification> | null>(null)
  const [error, setError] = useState<string | null>(null)
  const [loading, setLoading] = useState(true)

  const load = useCallback(() => {
    setLoading(true)
    api
      .get<Page<Notification>>('/notifications', { params: { page, limit: 15, unread_only: unreadOnly } })
      .then(({ data: body }) => setData(body))
      .catch((caught) => setError(errorMessage(caught)))
      .finally(() => setLoading(false))
  }, [page, unreadOnly])

  useEffect(load, [load])

  const markRead = async (id: number) => {
    try {
      await api.put(`/notifications/${id}/read`)
      load()
    } catch (caught) {
      setError(errorMessage(caught))
    }
  }

  const markAll = async () => {
    try {
      await api.put('/notifications/read-all')
      load()
    } catch (caught) {
      setError(errorMessage(caught))
    }
  }

  return (
    <div className="mx-auto max-w-2xl">
      <div className="mb-6 flex flex-wrap items-center justify-between gap-3">
        <div>
          <h1 className="text-2xl font-semibold text-slate-800">Notifications</h1>
          <p className="text-sm text-slate-500">
            {data ? `${data.unread ?? 0} unread` : 'Loading…'}
          </p>
        </div>
        <div className="flex gap-2">
          <label className="flex items-center gap-2 text-sm text-slate-600">
            <input
              type="checkbox"
              checked={unreadOnly}
              onChange={(event) => {
                setUnreadOnly(event.target.checked)
                setPage(1)
              }}
            />
            Unread only
          </label>
          <button className="btn-secondary" onClick={() => void markAll()}>Mark all read</button>
        </div>
      </div>

      <ErrorBanner message={error} />

      {loading ? (
        <Spinner />
      ) : data && data.items.length === 0 ? (
        <EmptyState title={unreadOnly ? 'No unread notifications' : 'No notifications yet'} />
      ) : data ? (
        <>
          <div className="space-y-3">
            {data.items.map((notification) => (
              <div
                key={notification.id}
                className={`card flex items-start gap-3 ${notification.is_read ? 'opacity-70' : ''}`}
              >
                <span
                  className={`mt-1.5 h-2.5 w-2.5 shrink-0 rounded-full ${
                    typeDot[notification.type] ?? 'bg-slate-400'
                  }`}
                />
                <div className="min-w-0 flex-1">
                  <div className="flex flex-wrap items-center justify-between gap-2">
                    <h2 className={`text-sm ${notification.is_read ? 'text-slate-600' : 'font-semibold text-slate-800'}`}>
                      {notification.title}
                    </h2>
                    <span className="text-xs text-slate-400">
                      {notification.created_at
                        ? new Date(notification.created_at).toLocaleString()
                        : ''}
                    </span>
                  </div>
                  {notification.message && (
                    <p className="mt-1 text-sm text-slate-500">{notification.message}</p>
                  )}
                  {!notification.is_read && (
                    <button
                      className="mt-2 text-xs text-indigo-600 hover:underline"
                      onClick={() => void markRead(notification.id)}
                    >
                      Mark as read
                    </button>
                  )}
                </div>
              </div>
            ))}
          </div>
          <Pagination page={data.page} pages={data.pages} onChange={setPage} />
        </>
      ) : null}
    </div>
  )
}
