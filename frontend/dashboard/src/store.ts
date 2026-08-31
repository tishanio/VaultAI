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

export const useAppStore = create<AppState>((set, get) => {
  const savedAccounts = loadSavedAccounts()
  const activeId = savedAccounts.length > 0 ? savedAccounts[0].id : null
  const active = savedAccounts.find((a) => a.id === activeId) || null

  return {
    user: active?.user ?? null,
    token: active?.token ?? null,
    isAuthenticated: !!active,

    savedAccounts,
    activeAccountId: activeId,

    addAccount: (user, token) => {
      const id = `acc_${Date.now()}_${Math.random().toString(36).slice(2, 8)}`
      const account: SavedAccount = { id, user, token }
      const accounts = [...get().savedAccounts, account]
      persistSavedAccounts(accounts)
      set({
        savedAccounts: accounts,
        activeAccountId: id,
        user,
        token,
        isAuthenticated: true,
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
        set({
          savedAccounts: accounts,
          activeAccountId: next?.id ?? null,
          user: next?.user ?? null,
          token: next?.token ?? null,
          isAuthenticated: !!next,
        })
      } else {
        set({ user: null, token: null, isAuthenticated: false })
      }
    },
  }
})
