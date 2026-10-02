import { useEffect, useState } from 'react'
import { Link } from 'react-router-dom'
import { FilterBar, ItemCard } from '../components/items'
import { EmptyState, ErrorBanner, Pagination, Spinner } from '../components/ui'
import api, { errorMessage } from '../lib/api'
import type { FoundItem, Page } from '../lib/types'

export default function FoundList() {
  const [filters, setFilters] = useState<Record<string, string>>({
    q: '',
    location: '',
    category: '',
    status: '',
  })
  const [page, setPage] = useState(1)
  const [data, setData] = useState<Page<FoundItem> | null>(null)
  const [error, setError] = useState<string | null>(null)
  const [loading, setLoading] = useState(true)

  useEffect(() => {
    setLoading(true)
    const params: Record<string, string | number> = { page, limit: 12 }
    for (const [key, value] of Object.entries(filters)) {
      if (value) params[key] = value
    }
    api
      .get<Page<FoundItem>>('/found-items', { params })
      .then(({ data: body }) => setData(body))
      .catch((caught) => setError(errorMessage(caught)))
      .finally(() => setLoading(false))
  }, [filters, page])

  const changeFilter = (key: string, value: string) => {
    setFilters((previous) => ({ ...previous, [key]: value }))
    setPage(1)
  }

  return (
    <div>
      <div className="mb-6 flex items-center justify-between">
        <div>
          <h1 className="text-2xl font-semibold text-slate-800">Found items</h1>
          <p className="text-sm text-slate-500">Help return these to their owners.</p>
        </div>
        <Link to="/found/new" className="btn-primary">
          + Report found item
        </Link>
      </div>

      <FilterBar values={filters} onChange={changeFilter} onSubmit={() => setPage(1)} />
      <ErrorBanner message={error} />

      {loading ? (
        <Spinner />
      ) : data && data.items.length > 0 ? (
        <>
          <div className="grid gap-4 sm:grid-cols-2 lg:grid-cols-3">
            {data.items.map((item) => (
              <ItemCard key={item.id} item={item} to={`/found/${item.id}`} />
            ))}
          </div>
          <Pagination page={data.page} pages={data.pages} onChange={setPage} />
        </>
      ) : (
        <EmptyState title="No found items match these filters" hint="Report an item you found to get started." />
      )}
    </div>
  )
}
