import { lazy, Suspense } from 'react'
import { Routes, Route, Navigate } from 'react-router-dom'
import { useAppStore } from './store'
import Layout from './components/Layout'

const LoginPage = lazy(() => import('./pages/LoginPage'))
const ChatPage = lazy(() => import('./pages/ChatPage'))
const DashboardPage = lazy(() => import('./pages/DashboardPage'))
const SubscriptionsPage = lazy(() => import('./pages/SubscriptionsPage'))
const MarketplacePage = lazy(() => import('./pages/MarketplacePage'))
const MatchesPage = lazy(() => import('./pages/MatchesPage'))
const EscrowPage = lazy(() => import('./pages/EscrowPage'))
const ConversationsPage = lazy(() => import('./pages/ConversationsPage'))
const NotificationsPage = lazy(() => import('./pages/NotificationsPage'))
const ProfilePage = lazy(() => import('./pages/ProfilePage'))
const AdminPage = lazy(() => import('./pages/AdminPage'))
const SearchPage = lazy(() => import('./pages/SearchPage'))
const SettingsPage = lazy(() => import('./pages/SettingsPage'))

function ProtectedRoute({ children }: { children: React.ReactNode }) {
  const isAuthenticated = useAppStore((s) => s.isAuthenticated)
  const demoMode = useAppStore((s) => s.demoMode)

  // In demo mode, skip auth check
  if (!isAuthenticated && !demoMode) {
    return <Navigate to="/login" replace />
  }
  return <>{children}</>
}

export default function App() {
  return (
    <Suspense fallback={<div className="flex h-screen items-center justify-center bg-gray-950 text-gray-400">Loading…</div>}>
      <Routes>
        <Route path="/login" element={<LoginPage />} />
        <Route
          path="/*"
          element={
            <ProtectedRoute>
              <Layout>
                <Routes>
                  <Route path="/" element={<ChatPage />} />
                  <Route path="/chat" element={<ChatPage />} />
                  <Route path="/dashboard" element={<DashboardPage />} />
                  <Route path="/subscriptions" element={<SubscriptionsPage />} />
                  <Route path="/search" element={<SearchPage />} />
                  <Route path="/marketplace" element={<MarketplacePage />} />
                  <Route path="/matches" element={<MatchesPage />} />
                  <Route path="/escrow" element={<EscrowPage />} />
                  <Route path="/conversations" element={<ConversationsPage />} />
                  <Route path="/notifications" element={<NotificationsPage />} />
                  <Route path="/profile" element={<ProfilePage />} />
                  <Route path="/admin" element={<AdminPage />} />
                  <Route path="/settings" element={<SettingsPage />} />
                </Routes>
              </Layout>
            </ProtectedRoute>
          }
        />
      </Routes>
    </Suspense>
  )
}
