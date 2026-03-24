import { BrowserRouter, Routes, Route, Navigate } from 'react-router'
import { AuthProvider, useAuth } from './auth'
import Sidebar from './components/layout/Sidebar'
import CreatePage from './pages/CreatePage'
import SearchPage from './pages/SearchPage'
import ProfilePage from './pages/ProfilePage'
import LoginPage from './pages/LoginPage'

function ProtectedLayout() {
  const { user } = useAuth()
  if (!user) return <Navigate to="/login" replace />

  return (
    <div className="flex min-h-screen bg-[#f7f8fa]">
      <Sidebar />
      <div className="flex-1 flex flex-col min-w-0">
        <main className="flex-1 overflow-y-auto">
          <div className="mx-auto max-w-4xl px-4 py-6 sm:px-6 lg:px-8 lg:py-8">
            <Routes>
              <Route path="/search" element={<SearchPage />} />
              <Route path="/create" element={<CreatePage />} />
              <Route path="/profile/:id" element={<ProfilePage />} />
              <Route path="*" element={<Navigate to="/search" replace />} />
            </Routes>
          </div>
        </main>
      </div>
    </div>
  )
}

function AppRoutes() {
  const { user } = useAuth()

  return (
    <Routes>
      <Route path="/login" element={user ? <Navigate to="/search" replace /> : <LoginPage />} />
      <Route path="/*" element={<ProtectedLayout />} />
    </Routes>
  )
}

export default function App() {
  return (
    <AuthProvider>
      <BrowserRouter>
        <AppRoutes />
      </BrowserRouter>
    </AuthProvider>
  )
}
