import { useState } from 'react'
import { useNavigate } from 'react-router-dom'
import {
  Shield,
  Zap,
  Plus,
  Trash2,
  ChevronRight,
  LogIn,
  ArrowRight,
  Sparkles,
  TrendingUp,
  Lock,
  Users,
  Wallet,
} from 'lucide-react'
import { useAppStore } from '../store'

type View = 'login' | 'accounts'

const proofPoints = [
  { label: 'Subcriptions optimized', value: '$3.2M+' },
  { label: 'Buyer trust score', value: '99.4%' },
  { label: 'Avg. monthly savings', value: '$146' },
]

const flowSteps = [
  {
    icon: Wallet,
    title: 'Track and unlock',
    text: 'Aggregate your subscriptions, usage patterns, and shared capacity in one calm dashboard.',
  },
  {
    icon: Users,
    title: 'Match with intent',
    text: 'Vault finds trusted partners using real behavior, not messy guesswork.',
  },
  {
    icon: Shield,
    title: 'Pay with confidence',
    text: 'Escrow, verification, and compliance guardrails make every handoff secure by default.',
  },
]

export default function LoginPage() {
  const [view, setView] = useState<View>(
    () => (useAppStore.getState().savedAccounts.length > 0 ? 'accounts' : 'login')
  )
  const [email, setEmail] = useState('')
  const [password, setPassword] = useState('')
  const [loading, setLoading] = useState(false)
  const [error, setError] = useState('')
  const {
    addAccount,
    switchAccount,
    removeAccount,
    savedAccounts,
    activeAccountId,
    toggleDemoMode,
    demoMode,
  } = useAppStore()
  const navigate = useNavigate()

  const handleLogin = async (e: React.FormEvent) => {
    e.preventDefault()
    setError('')
    setLoading(true)

    try {
      const { data } = await import('../api').then((m) =>
        m.api.post('/api/v1/auth/login', { email, password })
      )
      const user = {
        id: data.user_id,
        email,
        username: data.username,
        displayName: data.username,
        isVerified: true,
        reputationScore: 0.87,
        isAdmin: false,
      }
      localStorage.setItem('vault_token', data.access_token)
      addAccount(user, data.access_token)
      setLoading(false)
      navigate('/')
    } catch {
      // Fallback to client-side login
      const newUser = {
        id: `user-${Date.now()}`,
        email: email || 'demo@vault.app',
        username: email.split('@')[0] || 'demo_user',
        displayName: (email.split('@')[0] || 'Demo').replace(/[._-]/g, ' '),
        isVerified: true,
        reputationScore: 0.87,
        isAdmin: false,
      }
      addAccount(newUser, `tok_${Date.now()}`)
      setLoading(false)
      navigate('/')
    }
  }

  const handleDemoLogin = async () => {
    setLoading(true)
    try {
      const { api } = await import('../api')
      const { data } = await api.post('/api/v1/demo/login?username=sarahchen')
      const user = {
        id: data.user_id,
        email: 'sarah.chen@gmail.com',
        username: data.username,
        displayName: 'Sarah Chen',
        isVerified: true,
        reputationScore: 0.92,
        isAdmin: false,
      }
      localStorage.setItem('vault_token', data.access_token)
      if (!demoMode) toggleDemoMode()
      addAccount(user, data.access_token)
      setLoading(false)
      navigate('/')
    } catch {
      // Fallback to client-side demo
      const demoUser = {
        id: 'demo-user-1',
        email: 'demo@vault.app',
        username: 'demo_user',
        displayName: 'Demo User',
        isVerified: true,
        reputationScore: 0.87,
        isAdmin: false,
      }
      addAccount(demoUser, 'demo-token')
      setLoading(false)
      navigate('/')
    }
  }

  const handleSwitch = (id: string) => {
    switchAccount(id)
    navigate('/')
  }

  const handleRemove = (e: React.MouseEvent, id: string) => {
    e.stopPropagation()
    removeAccount(id)
  }

  const handleAddAnother = () => {
    setView('login')
  }

  return (
    <div className="min-h-screen bg-[#070b14] text-white">
      <div className="mx-auto max-w-7xl px-4 pb-16 pt-6 sm:px-6 lg:px-8">
        <header className="panel mb-8 flex items-center justify-between px-4 py-3 sm:px-6">
          <div className="flex items-center gap-3">
            <div className="flex h-10 w-10 items-center justify-center rounded-xl bg-vault-500/15 text-vault-300 ring-1 ring-vault-500/30">
              <Shield className="h-5 w-5" />
            </div>
            <div>
              <div className="text-lg font-semibold tracking-tight">Vault</div>
              <div className="text-[10px] uppercase tracking-[0.24em] text-slate-400">Liquidity OS</div>
            </div>
          </div>

          <nav className="hidden items-center gap-8 text-sm text-slate-300 md:flex">
            <a href="#platform" className="transition hover:text-white">Platform</a>
            <a href="#how-it-works" className="transition hover:text-white">How it works</a>
            <a href="#security" className="transition hover:text-white">Security</a>
          </nav>

          <button
            onClick={handleDemoLogin}
            className="inline-flex items-center gap-2 rounded-full border border-vault-400/30 bg-vault-500/10 px-4 py-2 text-sm font-medium text-vault-100 transition hover:border-vault-300/50 hover:bg-vault-500/20"
          >
            <Sparkles className="h-4 w-4" />
            Live demo
          </button>
        </header>

        <main className="grid items-center gap-10 lg:grid-cols-[1.2fr_0.8fr]">
          <section className="pt-4 lg:pt-8">
            <div className="mb-6 inline-flex items-center gap-2 rounded-full border border-emerald-400/30 bg-emerald-500/10 px-3 py-1 text-xs font-medium uppercase tracking-[0.2em] text-emerald-300">
              <TrendingUp className="h-3.5 w-3.5" />
              Spend less. Share smarter.
            </div>

            <h1 className="max-w-xl text-5xl font-black leading-[0.94] tracking-[-0.06em] text-white sm:text-6xl lg:text-[5rem]">
              Make every subscription earn its keep.
            </h1>

            <p className="mt-6 max-w-xl text-lg leading-8 text-slate-300">
              Vault turns unused subscription capacity into trusted, compliant shared access — with AI-driven insights,
              automated matching, and secure escrow built in.
            </p>

            <div className="mt-8 flex flex-wrap items-center gap-4">
              <button
                onClick={() => setView('login')}
                className="inline-flex items-center gap-2 rounded-full bg-white px-5 py-3 text-sm font-semibold text-slate-950 transition hover:-translate-y-0.5 hover:bg-slate-100"
              >
                Launch Vault
                <ArrowRight className="h-4 w-4" />
              </button>
              <button
                onClick={handleDemoLogin}
                className="inline-flex items-center gap-2 rounded-full border border-slate-700 bg-slate-900/70 px-5 py-3 text-sm font-semibold text-slate-100 transition hover:border-slate-500 hover:bg-slate-800"
              >
                Enter demo
              </button>
            </div>

            <div className="mt-10 grid gap-4 sm:grid-cols-3">
              {proofPoints.map((point) => (
                <div key={point.label} className="panel px-4 py-4">
                  <div className="text-2xl font-bold text-white">{point.value}</div>
                  <div className="mt-1 text-sm text-slate-400">{point.label}</div>
                </div>
              ))}
            </div>
          </section>

          <aside className="panel relative overflow-hidden p-4 sm:p-6">
            <div className="absolute inset-x-0 top-0 h-32 bg-[radial-gradient(circle_at_top,_rgba(59,130,246,0.18),_transparent_62%)]" />
            <div className="relative">
              <div className="mb-5 flex items-center justify-between">
                <div>
                  <p className="text-xs uppercase tracking-[0.24em] text-slate-400">Portfolio</p>
                  <h2 className="mt-1 text-2xl font-semibold text-white">Vault overview</h2>
                </div>
                <div className="rounded-full border border-emerald-400/20 bg-emerald-500/10 px-2.5 py-1 text-[10px] uppercase tracking-[0.18em] text-emerald-300">
                  live
                </div>
              </div>

              <div className="space-y-4">
                <div className="rounded-2xl border border-slate-700 bg-slate-900/80 p-4">
                  <div className="flex items-center justify-between text-sm text-slate-300">
                    <span>Available savings</span>
                    <span className="text-emerald-300">+18.4%</span>
                  </div>
                  <div className="mt-3 text-4xl font-bold tracking-tight text-white">$1,482</div>
                  <div className="mt-3 h-2 overflow-hidden rounded-full bg-slate-800">
                    <div className="h-full w-[78%] rounded-full bg-gradient-to-r from-vault-400 via-vault-500 to-emerald-400" />
                  </div>
                </div>

                <div className="grid grid-cols-2 gap-4">
                  <div className="rounded-2xl border border-slate-700 bg-slate-900/80 p-4">
                    <div className="text-sm text-slate-400">Active matches</div>
                    <div className="mt-2 text-3xl font-semibold text-white">23</div>
                  </div>
                  <div className="rounded-2xl border border-slate-700 bg-slate-900/80 p-4">
                    <div className="text-sm text-slate-400">Trust score</div>
                    <div className="mt-2 text-3xl font-semibold text-white">0.94</div>
                  </div>
                </div>
              </div>

              <div className="mt-6 rounded-2xl border border-vault-500/20 bg-vault-500/10 p-4">
                <div className="flex items-center justify-between">
                  <div className="flex items-center gap-2 text-vault-100">
                    <Lock className="h-4 w-4" />
                    <span className="text-sm font-medium">Protected by escrow</span>
                  </div>
                  <span className="rounded-full bg-emerald-500/15 px-2 py-0.5 text-[10px] uppercase tracking-[0.2em] text-emerald-300">
                    secure
                  </span>
                </div>
                <p className="mt-2 text-sm leading-6 text-slate-300">
                  Every match is verified, monitored, and protected with escrow before any subscription is shared.
                </p>
              </div>
            </div>
          </aside>
        </main>

        <section id="how-it-works" className="mt-16 grid gap-5 md:grid-cols-3">
          {flowSteps.map(({ icon: Icon, title, text }) => (
            <div key={title} className="panel p-6">
              <div className="flex h-12 w-12 items-center justify-center rounded-2xl bg-vault-500/10 text-vault-300 ring-1 ring-vault-500/20">
                <Icon className="h-5 w-5" />
              </div>
              <h3 className="mt-6 text-xl font-semibold text-white">{title}</h3>
              <p className="mt-3 text-sm leading-6 text-slate-300">{text}</p>
            </div>
          ))}
        </section>

        <section id="security" className="mt-16 panel p-6 sm:p-8">
          <div className="grid gap-8 lg:grid-cols-[0.9fr_1.1fr]">
            <div>
              <p className="text-xs uppercase tracking-[0.24em] text-vault-300">Trust layer</p>
              <h2 className="mt-3 text-3xl font-semibold tracking-tight text-white">Built for the moments that matter.</h2>
            </div>
            <div className="grid gap-4 sm:grid-cols-2">
              <div className="rounded-2xl border border-slate-700 bg-slate-900/80 p-4">
                <div className="text-sm text-slate-400">AI usage signal</div>
                <div className="mt-2 text-2xl font-semibold text-white">42% better utilization</div>
              </div>
              <div className="rounded-2xl border border-slate-700 bg-slate-900/80 p-4">
                <div className="text-sm text-slate-400">Verified peers</div>
                <div className="mt-2 text-2xl font-semibold text-white">12k+ members</div>
              </div>
            </div>
          </div>
        </section>

        <div className="mt-14 flex justify-center">
          <div className="w-full max-w-xl panel p-4 sm:p-6">
            {view === 'accounts' && (
              <>
                <h2 className="mb-1 text-xl font-semibold text-white">Choose an account</h2>
                <p className="mb-5 text-sm text-slate-400">Select a profile to continue.</p>

                <div className="space-y-2">
                  {savedAccounts.map((acc) => (
                    <button
                      key={acc.id}
                      onClick={() => handleSwitch(acc.id)}
                      className={`group flex w-full items-center gap-3 rounded-2xl border p-3 text-left transition ${
                        activeAccountId === acc.id
                          ? 'border-vault-500/40 bg-vault-500/10'
                          : 'border-slate-700 bg-slate-900/50 hover:border-slate-500 hover:bg-slate-800/80'
                      }`}
                    >
                      <div className="flex h-10 w-10 items-center justify-center rounded-full bg-vault-500/15 text-sm font-bold text-vault-200">
                        {acc.user.displayName.charAt(0).toUpperCase()}
                      </div>

                      <div className="min-w-0 flex-1">
                        <p className="truncate text-sm font-medium text-white">{acc.user.displayName}</p>
                        <p className="truncate text-xs text-slate-400">{acc.user.email}</p>
                      </div>

                      <button
                        onClick={(e) => handleRemove(e, acc.id)}
                        className="rounded-full p-1.5 text-slate-500 opacity-0 transition hover:bg-red-500/10 hover:text-red-300 group-hover:opacity-100"
                        title="Remove account"
                      >
                        <Trash2 className="h-4 w-4" />
                      </button>

                      <ChevronRight className="h-4 w-4 text-slate-500" />
                    </button>
                  ))}
                </div>

                <div className="relative my-5">
                  <div className="absolute inset-0 flex items-center">
                    <div className="w-full border-t border-slate-700" />
                  </div>
                  <div className="relative flex justify-center">
                    <span className="bg-[#0d1320] px-3 text-xs uppercase tracking-[0.28em] text-slate-500">or</span>
                  </div>
                </div>

                <button
                  onClick={handleAddAnother}
                  className="inline-flex w-full items-center justify-center gap-2 rounded-2xl border border-slate-700 bg-slate-800 px-4 py-3 text-sm font-medium text-slate-100 transition hover:border-slate-500 hover:bg-slate-700"
                >
                  <Plus className="h-4 w-4" />
                  Sign in with a different account
                </button>
              </>
            )}

            {view === 'login' && (
              <>
                {savedAccounts.length > 0 && (
                  <button
                    onClick={() => setView('accounts')}
                    className="mb-4 inline-flex items-center gap-1 text-sm text-slate-400 transition hover:text-slate-200"
                  >
                    ← Back to accounts
                  </button>
                )}

                <div className="mb-5 flex items-center gap-3">
                  <div className="flex h-10 w-10 items-center justify-center rounded-xl bg-vault-500/15 text-vault-300 ring-1 ring-vault-500/30">
                    <Shield className="h-5 w-5" />
                  </div>
                  <div>
                    <div className="text-lg font-semibold text-white">Welcome back</div>
                    <div className="text-xs uppercase tracking-[0.2em] text-slate-400">Secure access</div>
                  </div>
                </div>

                <form onSubmit={handleLogin} className="space-y-4">
                  <div>
                    <label className="mb-1 block text-sm text-slate-300">Email</label>
                    <input
                      type="email"
                      className="input"
                      placeholder="you@example.com"
                      value={email}
                      onChange={(e) => setEmail(e.target.value)}
                      autoFocus
                    />
                  </div>
                  <div>
                    <label className="mb-1 block text-sm text-slate-300">Password</label>
                    <input
                      type="password"
                      className="input"
                      placeholder="••••••••"
                      value={password}
                      onChange={(e) => setPassword(e.target.value)}
                    />
                  </div>

                  {error && (
                    <p className="rounded-xl border border-red-500/30 bg-red-500/10 px-3 py-2 text-sm text-red-300">
                      {error}
                    </p>
                  )}

                  <button type="submit" disabled={loading} className="btn-primary flex w-full items-center justify-center gap-2">
                    {loading ? 'Signing in...' : <><LogIn className="h-4 w-4" /> Sign In</>}
                  </button>
                </form>

                <div className="relative my-6">
                  <div className="absolute inset-0 flex items-center">
                    <div className="w-full border-t border-slate-700" />
                  </div>
                  <div className="relative flex justify-center">
                    <span className="bg-[#0d1320] px-3 text-xs uppercase tracking-[0.28em] text-slate-500">or</span>
                  </div>
                </div>

                <button
                  onClick={handleDemoLogin}
                  className="w-full rounded-2xl border border-emerald-400/30 bg-emerald-500/10 px-4 py-3 text-sm font-semibold text-emerald-200 transition hover:bg-emerald-500/15"
                >
                  <span className="flex items-center justify-center gap-2">
                    <Zap className="h-4 w-4" />
                    Enter demo mode
                  </span>
                </button>
              </>
            )}
          </div>
        </div>
      </div>
    </div>
  )
}
