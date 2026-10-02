import { useEffect, useState } from 'react'
import { Link, useSearchParams } from 'react-router-dom'
import { EmptyState, ErrorBanner, Spinner } from '../components/ui'
import api, { errorMessage } from '../lib/api'
import { statusColor } from '../lib/types'

interface SearchHit {
  type: 'LOST' | 'FOUND' | 'DONATION'
  id: number
  name: string
  location: string
  status: string
  category: string
}

const typeStyle: Record<string, string> = {
  LOST: 'bg-rose-100 text-rose-700',
  FOUND: 'bg-emerald-100 text-emerald-700',
  DONATION: 'bg-sky-100 text-sky-700',
}

function hitLink(hit: SearchHit): string {
  if (hit.type === 'LOST') return `/lost/${hit.id}`
  if (hit.type === 'FOUND') return `/found/${hit.id}`
  return `/donations/${hit.id}`
}

export default function SearchPage() {
  const [params, setParams] = useSearchParams()
  const [query, setQuery] = useState(params.get('q') ?? '')
  const [type, setType] = useState(params.get('type') ?? '')
  const [hits, setHits] = useState<SearchHit[]>([])
  const [total, setTotal] = useState(0)
  const [error, setError] = useState<string | null>(null)
  const [loading, setLoading] = useState(false)

  const q = params.get('q') ?? ''

  useEffect(() => {
    if (!q) {
      setHits([])
      setTotal(0)
      return
    }
    setLoading(true)
    setError(null)
    const searchParams: Record<string, string> = { q }
    if (type) searchParams.type = type
    api
      .get<{ items: SearchHit[]; total: number }>('/search', { params: searchParams })
      .then(({ data }) => {
        setHits(data.items)
        setTotal(data.total)
      })
      .catch((caught) => setError(errorMessage(caught)))
      .finally(() => setLoading(false))
  }, [q, type])

  const submit = (event: React.FormEvent) => {
    event.preventDefault()
    const next = new URLSearchParams()
    if (query.trim()) next.set('q', query.trim())
    if (type) next.set('type', type)
    setParams(next)
  }

  return (
    <div className="mx-auto max-w-3xl">
      <h1 className="text-2xl font-semibold text-slate-800">Search everything</h1>
      <p className="text-sm text-slate-500">
        One search across lost reports, found items and free donations.
      </p>

      <form className="mt-4 flex flex-col gap-2 sm:flex-row" onSubmit={submit}>
        <input
          className="input flex-1"
          placeholder="wallet, keys, phone…"
          value={query}
          onChange={(event) => setQuery(event.target.value)}
        />
        <select className="input sm:w-48" value={type} onChange={(event) => setType(event.target.value)}>
          <option value="">All types</option>
          <option value="LOST">Lost items</option>
          <option value="FOUND">Found items</option>
          <option value="DONATION">Donations</option>
        </select>
        <button className="btn-primary" type="submit">Search</button>
      </form>

      <div className="mt-6">
        <ErrorBanner message={error} />
        {loading ? (
          <Spinner />
        ) : !q ? (
          <EmptyState title="Type something to search" hint="Try a category, a place or a distinctive feature." />
        ) : hits.length === 0 ? (
          <EmptyState title={`No results for "${q}"`} hint="Try fewer words or a different type filter." />
        ) : (
          <>
            <p className="mb-3 text-sm text-slate-500">{total} result(s)</p>
            <div className="space-y-3">
              {hits.map((hit) => (
                <Link
                  key={`${hit.type}-${hit.id}`}
                  to={hitLink(hit)}
                  className="card flex items-center justify-between transition hover:shadow-md"
                >
                  <div>
                    <span className={`badge mr-2 ${typeStyle[hit.type]}`}>{hit.type}</span>
                    <span className="font-medium text-slate-800">{hit.name}</span>
                    <p className="mt-1 text-sm text-slate-500">
                      {hit.category} · {hit.location}
                    </p>
                  </div>
                  <span className={`badge ${statusColor(hit.status)}`}>{hit.status}</span>
                </Link>
              ))}
            </div>
          </>
        )}
      </div>
    </div>
  )
}
