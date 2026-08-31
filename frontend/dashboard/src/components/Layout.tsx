import { Link } from 'react-router-dom'
import {
  Shield,
  Menu,
  X,
  Zap,
  LogOut,
  Settings,
  LayoutDashboard,
} from 'lucide-react'
import { useState } from 'react'
import { useAppStore } from '../store'

export default function Layout({ children }: { children: React.ReactNode }) {
  const { demoMode, toggleDemoMode, user } = useAppStore()
  const [menuOpen, setMenuOpen] = useState(false)

  return (
    <div className="flex h-screen flex-col overflow-hidden bg-[#07111d]">
      <header className="flex h-16 shrink-0 items-center justify-between border-b border-slate-800/80 bg-slate-950/75 px-4 backdrop-blur-xl">
        <div className="flex items-center gap-3">
          <button
            onClick={() => setMenuOpen(!menuOpen)}
            className="rounded-xl p-1.5 text-slate-300 hover:bg-slate-800 hover:text-white lg:hidden"
          >
            {menuOpen ? <X className="h-5 w-5" /> : <Menu className="h-5 w-5" />}
          </button>

          <Link to="/" className="flex items-center gap-3">
            <div className="flex h-9 w-9 items-center justify-center rounded-xl bg-vault-500/15 text-vault-300 ring-1 ring-vault-500/30">
              <Shield className="h-4 w-4" />
            </div>
            <div className="leading-none">
              <div className="text-lg font-semibold text-white">Vault</div>
              <div className="text-[10px] uppercase tracking-[0.24em] text-slate-500">Agent</div>
            </div>
          </Link>
        </div>

        <div className="flex items-center gap-2">
          {demoMode && (
            <span className="hidden items-center gap-1 rounded-full border border-emerald-400/20 bg-emerald-500/10 px-2.5 py-1 text-[10px] font-medium uppercase tracking-[0.18em] text-emerald-300 sm:inline-flex">
              <Zap className="h-3 w-3" />
              Demo
            </span>
          )}

          <Link
            to="/dashboard"
            className="hidden rounded-xl p-2 text-slate-300 hover:bg-slate-800 hover:text-white sm:block"
            title="Dashboard"
          >
            <LayoutDashboard className="h-4 w-4" />
          </Link>
          <Link
            to="/settings"
            className="hidden rounded-xl p-2 text-slate-300 hover:bg-slate-800 hover:text-white sm:block"
            title="Settings"
          >
            <Settings className="h-4 w-4" />
          </Link>

          <button
            onClick={toggleDemoMode}
            className="rounded-xl p-2 text-slate-300 hover:bg-slate-800 hover:text-white"
            title={demoMode ? 'Disable demo mode' : 'Enable demo mode'}
          >
            <Zap className={`h-4 w-4 ${demoMode ? 'text-emerald-300' : ''}`} />
          </button>

          <div className="flex h-8 w-8 items-center justify-center rounded-full bg-vault-500/15 text-xs font-bold text-vault-200 ring-1 ring-vault-500/30">
            {user?.displayName?.charAt(0)?.toUpperCase() || 'V'}
          </div>
        </div>
      </header>

      {menuOpen && (
        <div className="absolute inset-0 z-40 bg-black/50 lg:hidden" onClick={() => setMenuOpen(false)}>
          <div className="absolute left-0 top-16 h-full w-64 border-r border-slate-800 bg-slate-950 p-4" onClick={(e) => e.stopPropagation()}>
            <nav className="space-y-1">
              {[
                { to: '/', label: 'Agent Chat' },
                { to: '/dashboard', label: 'Dashboard' },
                { to: '/subscriptions', label: 'Subscriptions' },
                { to: '/search', label: 'Search' },
                { to: '/marketplace', label: 'Marketplace' },
                { to: '/matches', label: 'Matches' },
                  { to: '/conversations', label: 'Conversations' },
                { to: '/escrow', label: 'Escrow' },
                { to: '/notifications', label: 'Notifications' },
                { to: '/settings', label: 'Settings' },
              ].map(({ to, label }) => (
                <Link
                  key={to}
                  to={to}
                  onClick={() => setMenuOpen(false)}
                  className="flex items-center gap-3 rounded-xl px-3 py-2.5 text-sm font-medium text-slate-300 hover:bg-slate-800 hover:text-white"
                >
                  {label}
                </Link>
              ))}
            </nav>
            <div className="mt-4 border-t border-slate-800 pt-4">
              <button className="flex w-full items-center gap-3 rounded-xl px-3 py-2.5 text-sm font-medium text-slate-300 hover:bg-slate-800 hover:text-white">
                <LogOut className="h-4 w-4" />
                Sign Out
              </button>
            </div>
          </div>
        </div>
      )}

      <main className="flex-1 overflow-hidden bg-[radial-gradient(circle_at_top,_rgba(14,165,233,0.12),_transparent_35%)]">
        {children}
      </main>
    </div>
  )
}
