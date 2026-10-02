import { Link } from 'react-router-dom'

export default function Footer() {
  return (
    <footer className="mt-16 border-t border-slate-200 bg-white">
      <div className="mx-auto flex max-w-6xl flex-col items-center justify-between gap-3 px-4 py-6 text-sm text-slate-500 md:flex-row">
        <p>© {new Date().getFullYear()} FindBack - Reuniting people with what they lose.</p>
        <div className="flex gap-4">
          <Link to="/lost" className="hover:text-indigo-600">
            Report lost
          </Link>
          <Link to="/found" className="hover:text-indigo-600">
            Report found
          </Link>
          <Link to="/donations" className="hover:text-indigo-600">
            Donate
          </Link>
        </div>
      </div>
    </footer>
  )
}
