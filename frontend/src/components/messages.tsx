import { useEffect, useRef, useState } from 'react'
import type { FormEvent } from 'react'
import { useAuth } from '../context/AuthContext'
import api, { errorMessage } from '../lib/api'
import type { Message, Page } from '../lib/types'
import { ErrorBanner, Spinner } from './ui'

function formatTime(iso?: string): string {
  if (!iso) return ''
  try {
    return new Date(iso).toLocaleString([], {
      month: 'short',
      day: 'numeric',
      hour: '2-digit',
      minute: '2-digit',
    })
  } catch {
    return ''
  }
}

/**
 * Conversation between the person who lost an item and the person who found
 * it, scoped to one match. Opening the thread marks incoming messages as read;
 * sending the first message advances the match to CONTACTED (server-side).
 */
export function MatchThread({
  matchId,
  onChanged,
}: {
  matchId: number
  onChanged?: () => void
}) {
  const { user } = useAuth()
  const [messages, setMessages] = useState<Message[]>([])
  const [page, setPage] = useState(1)
  const [loading, setLoading] = useState(true)
  const [error, setError] = useState<string | null>(null)
  const [draft, setDraft] = useState('')
  const [sending, setSending] = useState(false)
  const endRef = useRef<HTMLDivElement | null>(null)

  // Load the newest messages, then mark the thread as read for this user.
  const loadLatest = async () => {
    setLoading(true)
    setError(null)
    try {
      const first = await api.get<Page<Message>>(`/matches/${matchId}/messages`, {
        params: { page: 1, limit: 100 },
      })
      const totalPages = first.data.pages || 1
      if (totalPages > 1) {
        const last = await api.get<Page<Message>>(`/matches/${matchId}/messages`, {
          params: { page: totalPages, limit: 100 },
        })
        setMessages(last.data.items)
        setPage(totalPages)
      } else {
        setMessages(first.data.items)
        setPage(1)
      }
      await api.post(`/matches/${matchId}/messages/read`)
      onChanged?.()
    } catch (caught) {
      setError(errorMessage(caught))
    } finally {
      setLoading(false)
    }
  }

  const loadEarlier = async () => {
    if (page <= 1 || loading) return
    try {
      const { data } = await api.get<Page<Message>>(`/matches/${matchId}/messages`, {
        params: { page: page - 1, limit: 100 },
      })
      setMessages((prev) => [...data.items, ...prev])
      setPage(page - 1)
    } catch (caught) {
      setError(errorMessage(caught))
    }
  }

  useEffect(() => {
    void loadLatest()
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [matchId])

  useEffect(() => {
    endRef.current?.scrollIntoView({ behavior: 'smooth', block: 'nearest' })
  }, [messages])

  const send = async (event: FormEvent) => {
    event.preventDefault()
    const body = draft.trim()
    if (!body || sending) return
    setSending(true)
    try {
      await api.post(`/matches/${matchId}/messages`, { body })
      setDraft('')
      await loadLatest()
    } catch (caught) {
      setError(errorMessage(caught))
    } finally {
      setSending(false)
    }
  }

  return (
    <div className="mt-4 border-t border-slate-200 pt-4">
      <div className="mb-2 flex flex-wrap items-center justify-between gap-2">
        <p className="text-sm font-semibold text-slate-700">💬 Conversation</p>
        <p className="text-xs text-slate-400">
          Only you, the other party and admins can read this thread.
        </p>
      </div>

      {loading ? (
        <Spinner />
      ) : (
        <>
          {page > 1 && (
            <button
              type="button"
              className="mb-2 text-xs text-indigo-600 hover:underline"
              onClick={() => void loadEarlier()}
            >
              ← Show earlier messages
            </button>
          )}
          <div className="h-64 space-y-2 overflow-y-auto rounded-lg border border-slate-200 bg-slate-50 p-3">
            {messages.length === 0 ? (
              <p className="py-8 text-center text-sm text-slate-400">
                No messages yet - introduce yourself and arrange the handover.
              </p>
            ) : (
              messages.map((message) => {
                const mine = message.sender_id === user?.id
                return (
                  <div
                    key={message.id}
                    className={`flex ${mine ? 'justify-end' : 'justify-start'}`}
                  >
                    <div
                      className={`max-w-[85%] rounded-2xl px-3 py-2 text-sm ${
                        mine
                          ? 'bg-indigo-600 text-white'
                          : 'border border-slate-200 bg-white text-slate-800'
                      }`}
                    >
                      {!mine && (
                        <p className="mb-0.5 text-xs font-semibold text-slate-500">
                          {message.sender_name ?? 'User'}
                        </p>
                      )}
                      <p className="whitespace-pre-wrap break-words">{message.body}</p>
                      <p
                        className={`mt-1 text-right text-[10px] ${
                          mine ? 'text-indigo-200' : 'text-slate-400'
                        }`}
                      >
                        {formatTime(message.created_at)}
                        {mine && message.is_read ? ' · read' : ''}
                      </p>
                    </div>
                  </div>
                )
              })
            )}
            <div ref={endRef} />
          </div>
        </>
      )}

      <ErrorBanner message={error} />

      <form onSubmit={(event) => void send(event)} className="mt-2 flex gap-2">
        <input
          className="input"
          placeholder="Write a message… (e.g. Where should we meet?)"
          value={draft}
          maxLength={2000}
          onChange={(event) => setDraft(event.target.value)}
        />
        <button
          type="submit"
          className="btn-primary shrink-0"
          disabled={sending || draft.trim().length === 0}
        >
          {sending ? 'Sending…' : 'Send'}
        </button>
      </form>
    </div>
  )
}
