import { useEffect, useState } from 'react'
import { Link, NavLink, useNavigate } from 'react-router-dom'
import { useAuth } from '../context/AuthContext'
import { useUnreadCount } from './ui'

const linkClass = ({ isActive }: { isActive: boolean }) =>
  `rounded-md px-3 py-2 text-sm font-medium transition-colors ${
    isActive ? 'bg-indigo-50 text-indigo-700' : 'text-slate-600 hover:bg-slate-100'
  }`

export default function Navbar() {
  const { user, logout } = useAuth()
  const navigate = useNavigate()
  const [unread] = useUnreadCount(Boolean(user))
  const [open, setOpen] = useState(false)

  useEffect(() => setOpen(false), [user, navigate])

  const handleLogout = () => {
    logout()
    navigate('/')
  }

  const navLinks = (
    <>
      <NavLink to="/" className={linkClass} end>
        Home
      </NavLink>
      <NavLink to="/lost" className={linkClass}>
        Lost Items
      </NavLink>
      <NavLink to="/found" className={linkClass}>
        Found Items
      </NavLink>
      <NavLink to="/donations" className={linkClass}>
        Donations
      </NavLink>
      <NavLink to="/search" className={linkClass}>
        Search
      </NavLink>
      {user && (
        <>
          <NavLink to="/dashboard" className={linkClass}>
            Dashboard
          </NavLink>
          <NavLink to="/matches" className={linkClass}>
            Matches
          </NavLink>
          <NavLink to="/notifications" className={linkClass} aria-label="Notifications">
            <span className="relative inline-block">
              Notifications
              {unread > 0 && (
                <span className="absolute -right-2 -top-2 rounded-full bg-rose-500 px-1.5 text-[10px] font-bold text-white">
                  {unread > 9 ? '9+' : unread}
                </span>
              )}
            </span>
          </NavLink>
        </>
      )}
      {user?.role === 'ADMIN' && (
        <NavLink to="/admin" className={linkClass}>
          Admin
        </NavLink>
      )}
    </>
  )

  return (
    <header className="sticky top-0 z-40 border-b border-slate-200 bg-white/95 backdrop-blur">
      <div className="mx-auto flex max-w-6xl items-center justify-between px-4 py-3">
        <Link to="/" className="flex items-center gap-2 text-lg font-bold text-indigo-600">
          <span className="grid h-8 w-8 place-items-center rounded-lg bg-indigo-600 text-white">F</span>
          FindBack
        </Link>

        <nav className="hidden items-center gap-1 md:flex">{navLinks}</nav>

        <div className="hidden items-center gap-2 md:flex">
          {user ? (
            <>
              <span className="text-sm text-slate-500">Hi, {user.name.split(' ')[0]}</span>
              <Link to="/profile" className="btn-secondary">
                Profile
              </Link>
              <button className="btn-primary" onClick={handleLogout}>
                Logout
              </button>
            </>
          ) : (
            <>
              <Link to="/login" className="btn-secondary">
                Login
              </Link>
              <Link to="/register" className="btn-primary">
                Sign up
              </Link>
            </>
          )}
        </div>

        <button
          className="rounded-md border border-slate-200 px-3 py-1.5 text-sm md:hidden"
          onClick={() => setOpen((value) => !value)}
          aria-label="Toggle menu"
        >
          ☰
        </button>
      </div>

      {open && (
        <div className="border-t border-slate-100 bg-white px-4 py-3 md:hidden">
          <div className="flex flex-col gap-1">{navLinks}</div>
          <div className="mt-3 flex gap-2">
            {user ? (
              <>
                <Link to="/profile" className="btn-secondary flex-1">
                  Profile
                </Link>
                <button className="btn-primary flex-1" onClick={handleLogout}>
                  Logout
                </button>
              </>
            ) : (
              <>
                <Link to="/login" className="btn-secondary flex-1">
                  Login
                </Link>
                <Link to="/register" className="btn-primary flex-1">
                  Sign up
                </Link>
              </>
            )}
          </div>
        </div>
      )}
    </header>
  )
}
