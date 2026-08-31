import { create } from 'zustand'

export interface User {
  id: string
  email: string
  username: string
  displayName: string
  avatarUrl?: string
  isVerified: boolean
  reputationScore?: number
  isAdmin?: boolean
}

export interface SavedAccount {
  id: string
  user: User
  token: string
}

// --- Chat Types ---

export interface ResultCard {
  type: 'subscription' | 'listing' | 'match' | 'escrow' | 'stats' | 'action'
  title: string
  subtitle?: string
  data: Record<string, unknown>
  actions?: { label: string; variant?: string }[]
}

export interface ChatMessage {
  id: string
  role: 'user' | 'assistant'
  content: string
  timestamp: string
  cards?: ResultCard[]
  suggestions?: string[]
  loading?: boolean
}

interface AppState {
  // Auth — active user
  user: User | null
  token: string | null
  isAuthenticated: boolean
  _authReady: boolean

  // Multi-account
  savedAccounts: SavedAccount[]
  activeAccountId: string | null
  addAccount: (user: User, token: string) => void
  removeAccount: (accountId: string) => void
  switchAccount: (accountId: string) => void

  // Demo mode
  demoMode: boolean
  toggleDemoMode: () => void

  // UI
  sidebarOpen: boolean
  toggleSidebar: () => void

  // Chat
  messages: ChatMessage[]
  chatLoading: boolean
  addMessage: (msg: ChatMessage) => void
  updateMessage: (id: string, update: Partial<ChatMessage>) => void
  setChatLoading: (loading: boolean) => void
  clearChat: () => void

  // Actions
  setUser: (user: User | null) => void
  setToken: (token: string | null) => void
  logout: () => void
}

function loadSavedAccounts(): SavedAccount[] {
  try {
    const raw = localStorage.getItem('vault_saved_accounts')
    return raw ? JSON.parse(raw) : []
  } catch {
    return []
  }
}

function persistSavedAccounts(accounts: SavedAccount[]) {
  localStorage.setItem('vault_saved_accounts', JSON.stringify(accounts))
}

/**
 * Decode a JWT payload and return its claims, or null if invalid/expired.
 * We only decode the payload (no signature verification) — this is safe
 * for client-side expiry checks because:
 *  1. The backend still verifies signatures on every API request.
 *  2. A tampered exp claim would only let the user see stale UI briefly
 *     before API calls fail with 401.
 */
function decodeJwtPayload(token: string): Record<string, unknown> | null {
  try {
    const parts = token.split('.')
    if (parts.length !== 3) return null
    // base64url → base64
    const base64 = parts[1].replace(/-/g, '+').replace(/_/g, '/')
    const padded = base64 + '='.repeat((4 - (base64.length % 4)) % 4)
    const json = atob(padded)
    return JSON.parse(json) as Record<string, unknown>
  } catch {
    return null
  }
}

/** Check whether a JWT token is expired (or about to expire within grace seconds). */
function isTokenExpired(token: string, graceSeconds = 60): boolean {
  const payload = decodeJwtPayload(token)
  if (!payload) return true // unparseable = treat as expired
  const exp = payload.exp
  if (typeof exp !== 'number') return false // no exp claim = don't expire
  const nowSec = Math.floor(Date.now() / 1000)
  return nowSec > exp - graceSeconds
}

/** Filter out expired accounts and clean up their tokens. */
function filterExpiredAccounts(accounts: SavedAccount[]): SavedAccount[] {
  const valid: SavedAccount[] = []
  for (const acc of accounts) {
    if (isTokenExpired(acc.token)) {
      console.warn(
        `[Vault] Clearing expired session for ${acc.user.username} (token expired)`
      )
      continue
    }
    valid.push(acc)
  }
  return valid
}

export const useAppStore = create<AppState>((set, get) => {
  let savedAccounts = loadSavedAccounts()

  // Strip out any accounts with expired JWTs
  const beforeCount = savedAccounts.length
  savedAccounts = filterExpiredAccounts(savedAccounts)
  if (savedAccounts.length !== beforeCount) {
    persistSavedAccounts(savedAccounts) // persist the cleaned list
  }

  const activeId = savedAccounts.length > 0 ? savedAccounts[0].id : null
  const active = savedAccounts.find((a) => a.id === activeId) || null

  // Sync the active account token to the key the API interceptor reads
  if (active?.token) {
    localStorage.setItem('vault_token', active.token)
  }

  return {
    user: active?.user ?? null,
    token: active?.token ?? null,
    isAuthenticated: !!active,
    _authReady: true,

    savedAccounts,
    activeAccountId: activeId,

    addAccount: (user, token) => {
      const id = `acc_${Date.now()}_${Math.random().toString(36).slice(2, 8)}`
      const account: SavedAccount = { id, user, token }
      const accounts = [...get().savedAccounts, account]
      persistSavedAccounts(accounts)
      // Also persist token under the key the API interceptor reads
      localStorage.setItem('vault_token', token)
      set({
        savedAccounts: accounts,
        activeAccountId: id,
        user,
        token,
        isAuthenticated: true,
        _authReady: true,
      })
    },

    removeAccount: (accountId) => {
      const { savedAccounts, activeAccountId } = get()
      const accounts = savedAccounts.filter((a) => a.id !== accountId)
      persistSavedAccounts(accounts)

      if (activeAccountId === accountId) {
        const next = accounts[0] ?? null
        set({
          savedAccounts: accounts,
          activeAccountId: next?.id ?? null,
          user: next?.user ?? null,
          token: next?.token ?? null,
          isAuthenticated: !!next,
        })
      } else {
        set({ savedAccounts: accounts })
      }
    },

    switchAccount: (accountId) => {
      const account = get().savedAccounts.find((a) => a.id === accountId)
      if (!account) return
      localStorage.setItem('vault_token', account.token)
      set({
        activeAccountId: accountId,
        user: account.user,
        token: account.token,
        isAuthenticated: true,
      })
    },

    // Demo mode
    demoMode: true,
    toggleDemoMode: () => set((state) => ({ demoMode: !state.demoMode })),

    // UI
    sidebarOpen: true,
    toggleSidebar: () => set((state) => ({ sidebarOpen: !state.sidebarOpen })),

    // Chat
    messages: [],
    chatLoading: false,
    addMessage: (msg) => set((state) => ({ messages: [...state.messages, msg] })),
    updateMessage: (id, update) =>
      set((state) => ({
        messages: state.messages.map((m) => (m.id === id ? { ...m, ...update } : m)),
      })),
    setChatLoading: (loading) => set({ chatLoading: loading }),
    clearChat: () => set({ messages: [] }),

    // Basic auth actions
    setUser: (user) => set({ user, isAuthenticated: !!user }),
    setToken: (token) => set({ token }),
    logout: () => {
      const { activeAccountId, savedAccounts } = get()
      if (activeAccountId) {
        const accounts = savedAccounts.filter((a) => a.id !== activeAccountId)
        persistSavedAccounts(accounts)
        const next = accounts[0] ?? null
        // Sync the active token to the key the API interceptor reads
        if (next?.token) {
          localStorage.setItem('vault_token', next.token)
        } else {
          localStorage.removeItem('vault_token')
        }
        set({
          savedAccounts: accounts,
          activeAccountId: next?.id ?? null,
          user: next?.user ?? null,
          token: next?.token ?? null,
          isAuthenticated: !!next,
        })
      } else {
        localStorage.removeItem('vault_token')
        set({ user: null, token: null, isAuthenticated: false })
      }
    },
  }
})
