import { useRef, useState } from 'react'
import api, { errorMessage, mediaUrl } from '../lib/api'
import { REPORT_REASONS } from '../lib/types'

/** Upload images via POST /uploads; returns stored /media URLs. */
export function ImageUploader({
  images,
  onChange,
  max = 4,
}: {
  images: string[]
  onChange: (images: string[]) => void
  max?: number
}) {
  const [busy, setBusy] = useState(false)
  const [error, setError] = useState<string | null>(null)
  const inputRef = useRef<HTMLInputElement>(null)

  const upload = async (files: FileList | null) => {
    if (!files?.length) return
    setError(null)
    setBusy(true)
    try {
      const urls = [...images]
      for (const file of Array.from(files)) {
        if (urls.length >= max) break
        const form = new FormData()
        form.append('file', file)
        const { data } = await api.post('/uploads', form)
        urls.push(data.url)
      }
      onChange(urls)
    } catch (caught) {
      setError(errorMessage(caught))
    } finally {
      setBusy(false)
      if (inputRef.current) inputRef.current.value = ''
    }
  }

  return (
    <div>
      <div className="flex flex-wrap gap-3">
        {images.map((url) => (
          <div key={url} className="relative">
            <img
              src={mediaUrl(url)}
              alt="upload"
              className="h-20 w-20 rounded-lg border border-slate-200 object-cover"
            />
            <button
              type="button"
              className="absolute -right-2 -top-2 grid h-5 w-5 place-items-center rounded-full bg-rose-500 text-xs text-white"
              onClick={() => onChange(images.filter((image) => image !== url))}
              aria-label="Remove image"
            >
              ×
            </button>
          </div>
        ))}
        {images.length < max && (
          <button
            type="button"
            className="grid h-20 w-20 place-items-center rounded-lg border-2 border-dashed border-slate-300 text-2xl text-slate-400 hover:border-indigo-400 hover:text-indigo-500"
            onClick={() => inputRef.current?.click()}
            disabled={busy}
          >
            {busy ? '…' : '+'}
          </button>
        )}
      </div>
      <input
        ref={inputRef}
        type="file"
        accept="image/jpeg,image/png,image/webp"
        multiple
        className="hidden"
        onChange={(event) => void upload(event.target.files)}
      />
      {error && <p className="mt-2 text-sm text-rose-600">{error}</p>}
      <p className="mt-1 text-xs text-slate-400">JPEG, PNG or WEBP · up to {max} images</p>
    </div>
  )
}

/** Inline "Report this listing" form used on detail pages. */
export function ReportForm({
  targetType,
  targetId,
  onDone,
}: {
  targetType: 'LOST_ITEM' | 'FOUND_ITEM' | 'DONATION' | 'USER'
  targetId: number
  onDone?: () => void
}) {
  const [open, setOpen] = useState(false)
  const [reason, setReason] = useState<string>(REPORT_REASONS[0])
  const [description, setDescription] = useState('')
  const [message, setMessage] = useState<string | null>(null)
  const [error, setError] = useState<string | null>(null)

  const submit = async (event: React.FormEvent) => {
    event.preventDefault()
    setError(null)
    setMessage(null)
    try {
      const { data } = await api.post('/reports', {
        target_type: targetType,
        target_id: targetId,
        reason,
        description: description || null,
      })
      setMessage(data.message)
      setOpen(false)
      onDone?.()
    } catch (caught) {
      setError(errorMessage(caught))
    }
  }

  return (
    <div className="text-sm">
      <button
        type="button"
        className="text-rose-500 hover:underline"
        onClick={() => setOpen((value) => !value)}
      >
        Report this listing
      </button>
      {message && <p className="mt-2 text-emerald-600">{message}</p>}
      {error && <p className="mt-2 text-rose-600">{error}</p>}
      {open && (
        <form className="mt-3 space-y-3 rounded-lg border border-slate-200 p-3" onSubmit={submit}>
          <div>
            <label className="label">Reason</label>
            <select className="input" value={reason} onChange={(event) => setReason(event.target.value)}>
              {REPORT_REASONS.map((option) => (
                <option key={option} value={option}>
                  {option.replace(/_/g, ' ')}
                </option>
              ))}
            </select>
          </div>
          <div>
            <label className="label">Details (optional)</label>
            <textarea
              className="input"
              rows={2}
              value={description}
              onChange={(event) => setDescription(event.target.value)}
            />
          </div>
          <button className="btn-danger" type="submit">
            Submit report
          </button>
        </form>
      )}
    </div>
  )
}
