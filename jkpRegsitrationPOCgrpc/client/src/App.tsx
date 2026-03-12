import { BrowserRouter, Routes, Route, Navigate } from 'react-router'
import Sidebar from './components/layout/Sidebar'
import CreatePage from './pages/CreatePage'
import SearchPage from './pages/SearchPage'

export default function App() {
  return (
    <BrowserRouter>
      <div className="flex min-h-screen bg-[#f8f9fb]">
        <Sidebar />
        <div className="flex-1 flex flex-col min-w-0">
          <main className="flex-1 overflow-y-auto">
            <div className="mx-auto max-w-4xl px-4 py-6 sm:px-6 lg:px-8 lg:py-8">
              <Routes>
                <Route path="/create" element={<CreatePage />} />
                <Route path="/search" element={<SearchPage />} />
                <Route path="*" element={<Navigate to="/create" replace />} />
              </Routes>
            </div>
          </main>
        </div>
      </div>
    </BrowserRouter>
  )
}
