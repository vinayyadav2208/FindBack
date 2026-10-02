import { StrictMode } from 'react'
import { createRoot } from 'react-dom/client'
import { BrowserRouter, Route, Routes } from 'react-router-dom'
import './index.css'
import App from './App'
import { AdminRoute, ProtectedRoute } from './components/ui'
import { AuthProvider } from './context/AuthContext'
import AdminPage from './pages/Admin'
import Dashboard from './pages/Dashboard'
import DonationDetail from './pages/DonationDetail'
import DonationForm from './pages/DonationForm'
import Donations from './pages/Donations'
import FoundDetail from './pages/FoundDetail'
import FoundForm from './pages/FoundForm'
import FoundList from './pages/FoundList'
import Home from './pages/Home'
import Login from './pages/Login'
import LostDetail from './pages/LostDetail'
import LostForm from './pages/LostForm'
import LostList from './pages/LostList'
import Matches from './pages/Matches'
import NotFound from './pages/NotFound'
import Notifications from './pages/Notifications'
import Profile from './pages/Profile'
import Register from './pages/Register'
import SearchPage from './pages/SearchPage'

createRoot(document.getElementById('root')!).render(
  <StrictMode>
    <AuthProvider>
      <BrowserRouter>
        <Routes>
          <Route element={<App />}>
            <Route path="/" element={<Home />} />
            <Route path="/login" element={<Login />} />
            <Route path="/register" element={<Register />} />
            <Route path="/lost" element={<LostList />} />
            <Route path="/lost/:id" element={<LostDetail />} />
            <Route path="/found" element={<FoundList />} />
            <Route path="/found/:id" element={<FoundDetail />} />
            <Route path="/search" element={<SearchPage />} />
            <Route path="/donations" element={<Donations />} />
            <Route path="/donations/:id" element={<DonationDetail />} />

            <Route
              path="/lost/new"
              element={
                <ProtectedRoute>
                  <LostForm />
                </ProtectedRoute>
              }
            />
            <Route
              path="/found/new"
              element={
                <ProtectedRoute>
                  <FoundForm />
                </ProtectedRoute>
              }
            />
            <Route
              path="/donations/new"
              element={
                <ProtectedRoute>
                  <DonationForm />
                </ProtectedRoute>
              }
            />
            <Route
              path="/dashboard"
              element={
                <ProtectedRoute>
                  <Dashboard />
                </ProtectedRoute>
              }
            />
            <Route
              path="/profile"
              element={
                <ProtectedRoute>
                  <Profile />
                </ProtectedRoute>
              }
            />
            <Route
              path="/matches"
              element={
                <ProtectedRoute>
                  <Matches />
                </ProtectedRoute>
              }
            />
            <Route
              path="/notifications"
              element={
                <ProtectedRoute>
                  <Notifications />
                </ProtectedRoute>
              }
            />
            <Route
              path="/admin"
              element={
                <AdminRoute>
                  <AdminPage />
                </AdminRoute>
              }
            />
            <Route path="*" element={<NotFound />} />
          </Route>
        </Routes>
      </BrowserRouter>
    </AuthProvider>
  </StrictMode>,
)
