import { useEffect, useState } from 'react'
import { Link, useNavigate } from 'react-router-dom'
import api from '../lib/api'
import type { LostItem, Stats } from '../lib/types'
import { ItemCard } from '../components/items'
import { Spinner } from '../components/ui'

export default function Home() {
  const navigate = useNavigate()
  const [stats, setStats] = useState<Stats | null>(null)
  const [recent, setRecent] = useState<LostItem[]>([])
  const [query, setQuery] = useState('')

  useEffect(() => {
    api.get<Stats>('/stats').then(({ data }) => setStats(data)).catch(() => undefined)
    api
      .get('/lost-items', { params: { status: 'ACTIVE', limit: 3 } })
      .then(({ data }) => setRecent(data.items))
      .catch(() => undefined)
  }, [])

  const submitSearch = (event: React.FormEvent) => {
    event.preventDefault()
    if (query.trim()) navigate(`/search?q=${encodeURIComponent(query.trim())}`)
  }

  return (
    <div className="space-y-12">
      {/* Hero */}
      <section className="rounded-2xl bg-gradient-to-br from-indigo-600 to-sky-500 px-6 py-14 text-center text-white">
        <h1 className="text-3xl font-bold md:text-4xl">Lost something? Find it faster.</h1>
        <p className="mx-auto mt-3 max-w-2xl text-indigo-100">
          FindBack combines community listings with AI-powered matching to reconnect
          lost items with their owners - and gives away what nobody is missing.
        </p>
        <form className="mx-auto mt-6 flex max-w-xl gap-2" onSubmit={submitSearch}>
          <input
            className="w-full rounded-lg px-4 py-3 text-slate-800 outline-none"
            placeholder="Search: wallet, keys, phone…"
            value={query}
            onChange={(event) => setQuery(event.target.value)}
          />
          <button className="rounded-lg bg-slate-900 px-5 py-3 font-medium hover:bg-slate-800" type="submit">
            Search
          </button>
        </form>
        <div className="mt-6 flex flex-wrap justify-center gap-3">
          <Link to="/lost/new" className="rounded-lg bg-white px-4 py-2 text-sm font-semibold text-indigo-700">
            I lost an item
          </Link>
          <Link to="/found/new" className="rounded-lg bg-white/15 px-4 py-2 text-sm font-semibold text-white ring-1 ring-white/40">
            I found an item
          </Link>
          <Link to="/donations/new" className="rounded-lg bg-white/15 px-4 py-2 text-sm font-semibold text-white ring-1 ring-white/40">
            Donate an item
          </Link>
        </div>
      </section>

      {/* Stats */}
      <section>
        <h2 className="mb-4 text-xl font-semibold text-slate-800">Platform activity</h2>
        {stats ? (
          <div className="grid grid-cols-2 gap-4 md:grid-cols-4">
            {[
              { label: 'Lost reports', value: stats.lost_items },
              { label: 'Found reports', value: stats.found_items },
              { label: 'Items reunited', value: stats.lost_resolved + stats.found_returned },
              { label: 'Free donations', value: stats.donations },
            ].map((stat) => (
              <div key={stat.label} className="card text-center">
                <p className="text-3xl font-bold text-indigo-600">{stat.value}</p>
                <p className="mt-1 text-sm text-slate-500">{stat.label}</p>
              </div>
            ))}
          </div>
        ) : (
          <Spinner label="Loading statistics…" />
        )}
      </section>

      {/* Recent listings */}
      <section>
        <div className="mb-4 flex items-center justify-between">
          <h2 className="text-xl font-semibold text-slate-800">Recent lost reports</h2>
          <Link to="/lost" className="text-sm font-medium text-indigo-600 hover:underline">
            View all →
          </Link>
        </div>
        <div className="grid gap-4 md:grid-cols-3">
          {recent.map((item) => (
            <ItemCard key={item.id} item={item} to={`/lost/${item.id}`} />
          ))}
          {recent.length === 0 && <p className="text-slate-400">No listings yet.</p>}
        </div>
      </section>

      {/* How it works */}
      <section className="grid gap-4 md:grid-cols-3">
        {[
          { title: '1. Report', text: 'Describe what you lost or found. Photos and location make matches stronger.' },
          { title: '2. AI matches', text: 'Our engine compares wording, category, location and photos to suggest potential matches.' },
          { title: '3. Verify & reunite', text: 'Owners review claims and verification answers. Humans always make the final call.' },
        ].map((step) => (
          <div key={step.title} className="card">
            <h3 className="font-semibold text-slate-800">{step.title}</h3>
            <p className="mt-2 text-sm text-slate-500">{step.text}</p>
          </div>
        ))}
      </section>
    </div>
  )
}
