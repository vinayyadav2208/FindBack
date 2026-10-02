import type { ReactNode } from 'react'
import { Link } from 'react-router-dom'
import { statusColor } from '../lib/types'

/** Listing card used by the Lost / Found / Search lists. */
export function ItemCard<T extends { id: number; name: string; category: string; location: string; status: string; created_at?: string }>({
  item,
  to,
  badge,
  footer,
}: {
  item: T
  to: string
  badge?: string
  footer?: ReactNode
}) {
  return (
    <Link
      to={to}
      className="card block transition hover:-translate-y-0.5 hover:shadow-md"
    >
      <div className="flex items-start justify-between gap-2">
        <h3 className="font-semibold text-slate-800">{item.name}</h3>
        <span className={`badge ${statusColor(item.status)}`}>{item.status}</span>
      </div>
      <p className="mt-1 line-clamp-2 text-sm text-slate-500">{item.location}</p>
      <div className="mt-3 flex items-center justify-between text-xs text-slate-400">
        <span className="rounded bg-slate-100 px-2 py-0.5 text-slate-600">
          {badge ?? item.category}
        </span>
        {item.created_at && <span>{new Date(item.created_at).toLocaleDateString()}</span>}
      </div>
      {footer && <div className="mt-3 border-t border-slate-100 pt-3 text-sm">{footer}</div>}
    </Link>
  )
}

/** Shared filter bar for list pages (q, category, location, status). */
export function FilterBar({
  values,
  onChange,
  showStatus = true,
  onSubmit,
}: {
  values: Record<string, string>
  onChange: (key: string, value: string) => void
  showStatus?: boolean
  onSubmit?: () => void
}) {
  return (
    <form
      className="mb-6 grid grid-cols-1 gap-3 rounded-xl border border-slate-200 bg-white p-4 sm:grid-cols-2 lg:grid-cols-4"
      onSubmit={(event) => {
        event.preventDefault()
        onSubmit?.()
      }}
    >
      <input
        className="input"
        placeholder="Search keyword…"
        value={values.q ?? ''}
        onChange={(event) => onChange('q', event.target.value)}
      />
      <input
        className="input"
        placeholder="Location…"
        value={values.location ?? ''}
        onChange={(event) => onChange('location', event.target.value)}
      />
      <select
        className="input"
        value={values.category ?? ''}
        onChange={(event) => onChange('category', event.target.value)}
      >
        <option value="">All categories</option>
        {[
          'Electronics', 'Wallet', 'Bag', 'Keys', 'Documents', 'Jewelry',
          'Clothing', 'Watch', 'Phone', 'Laptop', 'Tablet', 'Books', 'Accessories', 'Other',
        ].map((category) => (
          <option key={category} value={category}>
            {category}
          </option>
        ))}
      </select>
      {showStatus ? (
        <select
          className="input"
          value={values.status ?? ''}
          onChange={(event) => onChange('status', event.target.value)}
        >
          <option value="">Any status</option>
          <option value="ACTIVE">Active</option>
          <option value="MATCHED">Matched</option>
          <option value="CLAIMED">Claimed</option>
          <option value="RESOLVED">Resolved</option>
          <option value="RETURNED">Returned</option>
        </select>
      ) : (
        <button className="btn-primary" type="submit">
          Apply filters
        </button>
      )}
      {showStatus && (
        <button className="btn-primary sm:col-span-2 lg:col-span-4" type="submit">
          Apply filters
        </button>
      )}
    </form>
  )
}
