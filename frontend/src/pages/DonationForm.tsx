import { useState } from 'react'
import { useNavigate } from 'react-router-dom'
import api, { errorMessage } from '../lib/api'
import { ImageUploader } from '../components/media'
import { ErrorBanner } from '../components/ui'
import { CATEGORIES, CONDITIONS } from '../lib/types'

export default function DonationForm() {
  const navigate = useNavigate()
  const [form, setForm] = useState({
    name: '',
    description: '',
    category: 'Other',
    condition: 'GOOD',
    location: '',
    latitude: '',
    longitude: '',
  })
  const [images, setImages] = useState<string[]>([])
  const [error, setError] = useState<string | null>(null)
  const [busy, setBusy] = useState(false)

  const set = (key: string, value: string) => setForm((prev) => ({ ...prev, [key]: value }))

  const submit = async (event: React.FormEvent) => {
    event.preventDefault()
    setError(null)
    setBusy(true)
    try {
      const payload: Record<string, unknown> = {
        name: form.name,
        description: form.description,
        category: form.category,
        condition: form.condition,
        location: form.location,
        images,
      }
      if (form.latitude !== '' && form.longitude !== '') {
        payload.latitude = Number(form.latitude)
        payload.longitude = Number(form.longitude)
      }
      const { data } = await api.post<{ donation: { id: number } }>('/donations', payload)
      navigate(`/donations/${data.donation.id}`)
    } catch (caught) {
      setError(errorMessage(caught))
    } finally {
      setBusy(false)
    }
  }

  return (
    <div className="mx-auto max-w-2xl">
      <h1 className="text-2xl font-semibold text-slate-800">Donate an item for free</h1>
      <p className="mt-1 text-sm text-slate-500">
        Working or not, someone can use it. Requests are reviewed by you.
      </p>
      <ErrorBanner message={error} />
      <form className="card mt-6 space-y-4" onSubmit={submit}>
        <div>
          <label className="label">Item name</label>
          <input
            className="input"
            required
            maxLength={255}
            placeholder="e.g. Wooden study table"
            value={form.name}
            onChange={(event) => set('name', event.target.value)}
          />
        </div>
        <div>
          <label className="label">Description</label>
          <textarea
            className="input"
            required
            rows={4}
            placeholder="Condition, size, why you are giving it away…"
            value={form.description}
            onChange={(event) => set('description', event.target.value)}
          />
        </div>
        <div className="grid gap-4 sm:grid-cols-2">
          <div>
            <label className="label">Category</label>
            <select className="input" value={form.category} onChange={(event) => set('category', event.target.value)}>
              {CATEGORIES.map((category) => (
                <option key={category} value={category}>{category}</option>
              ))}
            </select>
          </div>
          <div>
            <label className="label">Condition</label>
            <select className="input" value={form.condition} onChange={(event) => set('condition', event.target.value)}>
              {CONDITIONS.map((condition) => (
                <option key={condition} value={condition}>{condition.replace('_', ' ')}</option>
              ))}
            </select>
          </div>
        </div>
        <div>
          <label className="label">Pickup location</label>
          <input
            className="input"
            required
            placeholder="e.g. KPHB, Hyderabad"
            value={form.location}
            onChange={(event) => set('location', event.target.value)}
          />
        </div>
        <div>
          <label className="label">Approximate coordinates (optional)</label>
          <div className="flex gap-2">
            <input className="input" placeholder="Latitude" value={form.latitude} onChange={(event) => set('latitude', event.target.value)} />
            <input className="input" placeholder="Longitude" value={form.longitude} onChange={(event) => set('longitude', event.target.value)} />
          </div>
        </div>
        <div>
          <label className="label">Photos</label>
          <ImageUploader images={images} onChange={setImages} />
        </div>
        <div className="flex gap-3">
          <button className="btn-primary" disabled={busy} type="submit">
            {busy ? 'Publishing…' : 'Publish donation'}
          </button>
          <button className="btn-secondary" type="button" onClick={() => navigate(-1)}>Cancel</button>
        </div>
      </form>
    </div>
  )
}
